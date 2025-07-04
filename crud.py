from sqlalchemy.orm import Session
from typing import List
import schemas
from database import Device
from datetime import datetime, timedelta

def get_device_by_ip(db: Session, ip_address: str):
    return db.query(Device).filter(Device.ip_address == ip_address).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = Device(
        ip_address=device.ip_address, 
        user=device.user, 
        start_time=device.start_time, 
        end_time=device.end_time, 
        purpose=device.purpose,
        device_type=device.device_type,
        first_offline_time=None  # 新增字段初始化
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def update_device(db: Session, ip_address: str, device: schemas.DeviceUpdate):
    db_device = get_device_by_ip(db, ip_address)
    if db_device:
        update_data = device.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_device, key, value)
        db.commit()
        db.refresh(db_device)
    return db_device

def delete_device(db: Session, ip_address: str):
    db_device = get_device_by_ip(db, ip_address)
    if db_device:
        db.delete(db_device)
        db.commit()
    return db_device

def update_offline_status(db: Session, online_ips: List[str]):
    """
    更新设备离线状态，处理24小时自动删除逻辑
    """
    # 获取所有占用的设备
    occupied_devices = db.query(Device).all()
    current_time = datetime.now()
    
    for device in occupied_devices:
        if device.ip_address not in online_ips:
            # 设备离线
            if device.first_offline_time is None:
                # 首次发现离线，记录时间
                device.first_offline_time = current_time
                db.commit()
            else:
                # 检查是否超过24小时
                time_diff = current_time - device.first_offline_time
                if time_diff > timedelta(hours=24):
                    # 超过24小时，删除占用记录
                    db.delete(device)
                    db.commit()
        else:
            # 设备重新上线，清除离线时间记录
            if device.first_offline_time is not None:
                device.first_offline_time = None
                db.commit()