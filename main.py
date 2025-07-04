from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Generator
import json
import time
import queue
import threading
import uuid
import hashlib
from datetime import datetime, timedelta

import crud, schemas, scanner
from database import SessionLocal, Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 缓存管理器
class ScanCacheManager:
    def __init__(self):
        self.cache = {}  # 存储格式: {network_hash: {"result": data, "timestamp": datetime, "network": network_str}}
        self.cache_duration = timedelta(minutes=5)  # 5分钟缓存
    
    def _get_network_hash(self, network: str) -> str:
        """生成网络段的哈希值作为缓存键"""
        return hashlib.md5(network.encode()).hexdigest()
    
    def get_cached_result(self, network: str):
        """获取缓存的扫描结果"""
        network_hash = self._get_network_hash(network)
        
        if network_hash in self.cache:
            cache_entry = self.cache[network_hash]
            # 检查缓存是否过期
            if datetime.now() - cache_entry["timestamp"] < self.cache_duration:
                return cache_entry["result"]
            else:
                # 缓存过期，删除
                del self.cache[network_hash]
        
        return None
    
    def set_cache_result(self, network: str, result):
        """设置缓存结果"""
        network_hash = self._get_network_hash(network)
        self.cache[network_hash] = {
            "result": result,
            "timestamp": datetime.now(),
            "network": network
        }
    
    def clear_expired_cache(self):
        """清理过期的缓存"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, cache_entry in self.cache.items():
            if current_time - cache_entry["timestamp"] >= self.cache_duration:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
    
    def get_cache_info(self):
        """获取缓存信息"""
        self.clear_expired_cache()
        return {
            "cached_networks": len(self.cache),
            "cache_entries": [
                {
                    "network": entry["network"],
                    "cached_time": entry["timestamp"].isoformat(),
                    "expires_in_seconds": int((self.cache_duration - (datetime.now() - entry["timestamp"])).total_seconds())
                }
                for entry in self.cache.values()
            ]
        }

# 创建缓存管理器实例
scan_cache = ScanCacheManager()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/devices/", response_model=List[schemas.Device])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    devices = crud.get_devices(db, skip=skip, limit=limit)
    return devices

@app.post("/devices/", response_model=schemas.Device)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    db_device = crud.get_device_by_ip(db, ip_address=device.ip_address)
    if db_device:
        return crud.update_device(db=db, ip_address=device.ip_address, device=device)
    return crud.create_device(db=db, device=device)

@app.get("/scan/{network:path}")
def start_scan(network: str, db: Session = Depends(get_db)):
    """
    扫描网络并自动检测设备类型（带缓存功能）
    """
    # 首先检查缓存
    cached_result = scan_cache.get_cached_result(network)
    if cached_result:
        # 即使使用缓存，也要更新数据库中的设备状态
        online_hosts = cached_result.get("online_hosts", [])
        crud.update_offline_status(db, online_hosts)
        
        return {
            "message": f"从缓存返回结果，发现 {len(cached_result.get('online_devices', []))} 个在线设备",
            "online_hosts": cached_result.get("online_hosts", []),
            "offline_hosts": cached_result.get("offline_hosts", []),
            "online_devices": cached_result.get("online_devices", []),
            "offline_devices": cached_result.get("offline_devices", []),
            "from_cache": True,
            "cache_info": "结果来自缓存，5分钟内有效（已更新设备状态）"
        }
    
    # 缓存中没有，执行实际扫描
    results = scanner.scan_network_with_detection(network)
    if results is None:
        raise HTTPException(status_code=400, detail="Invalid network format")
    
    # 分离在线和离线设备
    online_devices = [r for r in results if r['status'] == 'online']
    offline_devices = [r for r in results if r['status'] == 'offline']
    
    # 为了保持与前端的兼容性，同时返回旧格式和新格式
    online_hosts = [d['ip'] for d in online_devices]
    offline_hosts = [d['ip'] for d in offline_devices]
    
    # 新增：处理占用设备的离线状态
    crud.update_offline_status(db, online_hosts)
    
    # 构建结果
    scan_result = {
        "online_hosts": online_hosts,
        "offline_hosts": offline_hosts,
        "online_devices": online_devices,
        "offline_devices": offline_devices
    }
    
    # 将结果存入缓存
    scan_cache.set_cache_result(network, scan_result)
    
    return {
        "message": f"扫描完成，发现 {len(online_devices)} 个在线设备",
        "online_hosts": online_hosts,
        "offline_hosts": offline_hosts,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "from_cache": False,
        "cache_info": "结果已缓存，5分钟内有效"
    }

# 保留旧的接口以防需要
@app.get("/scan_simple/{network:path}")
def start_simple_scan(network: str, db: Session = Depends(get_db)):
    """
    简单扫描（不检测设备类型，带缓存功能）
    """
    # 检查缓存（简化版）
    cached_result = scan_cache.get_cached_result(f"simple_{network}")
    if cached_result:
        # 即使使用缓存，也要更新数据库中的设备状态
        online_hosts = cached_result.get("online_hosts", [])
        crud.update_offline_status(db, online_hosts)
        
        return {
            "message": f"从缓存返回结果，发现 {len(cached_result.get('online_hosts', []))} 个在线设备",
            "online_hosts": cached_result.get("online_hosts", []),
            "offline_hosts": cached_result.get("offline_hosts", []),
            "from_cache": True
        }
    
    up_hosts, down_hosts = scanner.scan_network(network)
    if up_hosts is None:
        raise HTTPException(status_code=400, detail="Invalid network format")
    
    # 缓存简单扫描结果
    simple_result = {
        "online_hosts": up_hosts,
        "offline_hosts": down_hosts
    }
    scan_cache.set_cache_result(f"simple_{network}", simple_result)
    
    return {
        "message": f"扫描完成，发现 {len(up_hosts)} 个在线设备",
        "online_hosts": up_hosts,
        "offline_hosts": down_hosts,
        "from_cache": False
    }

# 新增：缓存管理接口
@app.get("/cache/info")
def get_cache_info():
    """获取缓存信息"""
    return scan_cache.get_cache_info()

@app.delete("/cache/clear")
def clear_cache():
    """清空所有缓存"""
    scan_cache.cache.clear()
    return {"message": "缓存已清空"}

# 全局扫描状态管理
class ScanManager:
    def __init__(self):
        self.active_scans: Dict[str, queue.Queue] = {}
        self.scan_results: Dict[str, list] = {}
    
    def start_scan(self, scan_id: str):
        self.active_scans[scan_id] = queue.Queue()
        self.scan_results[scan_id] = []
    
    def add_message(self, scan_id: str, message: dict):
        if scan_id in self.active_scans:
            self.active_scans[scan_id].put(message)
    
    def get_messages(self, scan_id: str) -> Generator[str, None, None]:
        if scan_id not in self.active_scans:
            return
        
        message_queue = self.active_scans[scan_id]
        while True:
            try:
                message = message_queue.get(timeout=1)
                yield f"data: {json.dumps(message)}\n\n"
                
                # 如果收到完成消息，结束生成器
                if message.get('type') == 'complete' or message.get('type') == 'error':
                    break
            except queue.Empty:
                # 发送心跳消息保持连接
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    def end_scan(self, scan_id: str):
        if scan_id in self.active_scans:
            del self.active_scans[scan_id]
        if scan_id in self.scan_results:
            del self.scan_results[scan_id]

scan_manager = ScanManager()

@app.get("/scan_stream/{scan_id}")
async def scan_stream(scan_id: str):
    """Server-Sent Events 流"""
    return StreamingResponse(
        scan_manager.get_messages(scan_id),
        media_type="text/event-stream",  # 修改为正确的MIME类型
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/scan_realtime/{network:path}")
def start_realtime_scan(network: str, db: Session = Depends(get_db)):
    """
    启动实时扫描（带缓存功能）
    """
    # 检查缓存
    cached_result = scan_cache.get_cached_result(network)
    if cached_result:
        # 即使使用缓存，也要更新数据库中的设备状态
        online_hosts = cached_result.get("online_hosts", [])
        crud.update_offline_status(db, online_hosts)
        
        # 如果有缓存，直接返回缓存结果
        scan_id = str(uuid.uuid4())
        scan_manager.start_scan(scan_id)
        
        def send_cached_result():
            # 发送缓存的在线设备
            online_devices = cached_result.get('online_devices', [])
            offline_devices = cached_result.get('offline_devices', [])
            
            # 发送在线设备
            for device in online_devices:
                scan_manager.add_message(scan_id, {
                    'type': 'device_found',
                    'ip': device['ip'],
                    'device_type': device.get('device_type', 'Unknown'),
                    'device_details': device.get('device_details', None),
                    'from_cache': True
                })
                time.sleep(0.05)  # 减少延迟
            
            # 发送离线设备（可选，如果前端需要显示）
            for device in offline_devices:
                scan_manager.add_message(scan_id, {
                    'type': 'device_offline',
                    'ip': device['ip'],
                    'device_type': device.get('device_type', 'Unknown'),
                    'device_details': device.get('device_details', None),
                    'from_cache': True
                })
                time.sleep(0.05)
            
            # 发送完成消息
            scan_manager.add_message(scan_id, {
                'type': 'complete',
                'message': f'从缓存返回结果，发现 {len(online_devices)} 个在线设备，{len(offline_devices)} 个离线设备',
                'online_count': len(online_devices),
                'offline_count': len(offline_devices),
                'from_cache': True
            })
        
        # 启动发送缓存结果的线程
        cache_thread = threading.Thread(target=send_cached_result)
        cache_thread.daemon = True
        cache_thread.start()
        
        return {"message": "从缓存返回实时扫描结果", "scan_id": scan_id, "from_cache": True}
    
    # 没有缓存，执行正常的实时扫描
    scan_id = str(uuid.uuid4())
    
    # 初始化扫描
    scan_manager.start_scan(scan_id)
    
    def callback(data):
        scan_manager.add_message(scan_id, data)
    
    # 在 start_realtime_scan 函数中，需要确保 scanner.scan_network_with_realtime_detection 
    # 正确调用了 callback 函数来发送 device_found 消息
    
    def run_scan():
        try:
            results = scanner.scan_network_with_realtime_detection(network, callback)
            if results:
                # 处理扫描结果并更新数据库
                online_devices = [r for r in results if r['status'] == 'online']
                offline_devices = [r for r in results if r['status'] == 'offline']
                online_hosts = [d['ip'] for d in online_devices]
                offline_hosts = [d['ip'] for d in offline_devices]
                
                crud.update_offline_status(db, online_hosts)
                
                # 缓存扫描结果
                scan_result = {
                    "online_hosts": online_hosts,
                    "offline_hosts": offline_hosts,
                    "online_devices": online_devices,
                    "offline_devices": offline_devices
                }
                scan_cache.set_cache_result(network, scan_result)
        except Exception as e:
            callback({
                'type': 'error',
                'message': f'扫描过程中出现错误: {str(e)}'
            })
        finally:
            # 清理扫描状态
            time.sleep(2)  # 等待前端接收完成消息
            scan_manager.end_scan(scan_id)
    
    # 启动后台扫描任务
    scan_thread = threading.Thread(target=run_scan)
    scan_thread.daemon = True
    scan_thread.start()
    
    return {"message": "实时扫描已开始", "scan_id": scan_id, "from_cache": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)