import subprocess
import threading
import ipaddress
import queue
import platform
import paramiko
import socket
from typing import Tuple, Optional
import asyncio
from typing import Callable

def detect_device_type(ip: str) -> str:
    """
    通过SSH登录检测设备类型 (Mock实现)
    实际实现中会通过SSH执行命令来判断设备类型
    """
    # Mock实现 - 模拟不同的设备类型
    import random
    device_types = [
        "Linux Server",
        "Windows Server", 
        "Network Switch",
        "Router",
        "Ubuntu Desktop",
        "CentOS Server",
        "Unknown Device"
    ]
    return random.choice(device_types)

def ssh_login_and_detect(ip: str, username: str = "admin", password: str = "admin") -> Optional[dict]:
    """
    SSH登录并检测设备类型
    目前为Mock实现，返回模拟的设备类型信息
    """
    try:
        # Mock SSH连接检测
        # 实际实现中会使用paramiko进行SSH连接
        # ssh = paramiko.SSHClient()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh.connect(ip, username=username, password=password, timeout=5)
        # 
        # # 执行命令检测系统类型
        # stdin, stdout, stderr = ssh.exec_command('uname -a')
        # system_info = stdout.read().decode()
        # ssh.close()
        # 
        # # 根据系统信息判断设备类型
        # if 'Linux' in system_info:
        #     return "Linux Server"
        # elif 'Windows' in system_info:
        #     return "Windows Server"
        # else:
        #     return "Unknown Device"
        
        # Mock返回 - 返回包含名称和详细信息的字典
        import random
        device_info = [
            {
                "name": "Linux服务器",
                "details": "Ubuntu 20.04 LTS\nCPU: Intel Xeon E5-2680\nRAM: 32GB\nDisk: 1TB SSD\nServices: Apache, MySQL, SSH"
            },
            {
                "name": "Windows服务器", 
                "details": "Windows Server 2019\nCPU: Intel Core i7-9700\nRAM: 16GB\nDisk: 500GB SSD\nServices: IIS, SQL Server, RDP"
            },
            {
                "name": "网络交换机",
                "details": "Cisco Catalyst 2960\n端口数: 24\n速率: 1Gbps\n管理IP: SNMP\nVLAN支持: 是"
            },
            {
                "name": "路由器",
                "details": "Cisco ISR 4321\nWAN接口: 2个\nLAN接口: 3个\n无线: 802.11ac\n防火墙: 内置"
            },
            {
                "name": "Ubuntu工作站",
                "details": "Ubuntu 22.04 Desktop\nCPU: AMD Ryzen 7 5800X\nRAM: 16GB\nGPU: NVIDIA RTX 3070\nDisk: 512GB NVMe"
            },
            {
                "name": "CentOS服务器",
                "details": "CentOS 8\nCPU: Intel Xeon Silver 4214\nRAM: 64GB\nDisk: 2TB HDD\nServices: Docker, Kubernetes"
            },
            {
                "name": "未知设备",
                "details": "设备类型: 未识别\n响应端口: 22\n操作系统: 未知\n服务: SSH可访问"
            }
        ]
        return random.choice(device_info)
    except Exception as e:
        print(f"SSH连接失败 {ip}: {e}")
        return {
            "name": "连接失败",
            "details": f"无法连接到设备\n错误信息: {str(e)}\n建议检查网络连接和认证信息"
        }

def scan_ip_with_detection(ip, results):
    """
    扫描IP并检测设备类型
    """
    param = '-n 1 -w 500' if platform.system().lower() == 'windows' else '-c 1 -W 0.5'
    command = ['ping', param, str(ip)]
    try:
        ret = subprocess.call(
            ' '.join(command),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if ret == 0:
            # Ping通后尝试SSH检测设备类型
            device_info = ssh_login_and_detect(str(ip))
            results.append({
                'ip': str(ip),
                'status': 'online',
                'device_type': device_info['name'] if device_info else None,
                'device_details': device_info['details'] if device_info else None
            })
        else:
            results.append({
                'ip': str(ip),
                'status': 'offline',
                'device_type': None,
                'device_details': None
            })
    except Exception:
        results.append({
            'ip': str(ip),
            'status': 'offline',
            'device_type': None,
            'device_details': None
        })

def scan_ip(ip, up_hosts, down_hosts):
    param = '-n 1 -w 500' if platform.system().lower() == 'windows' else '-c 1 -W 0.5'
    command = ['ping', param, str(ip)]
    try:
        ret = subprocess.call(
            ' '.join(command),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if ret == 0:
            up_hosts.append(str(ip))
        else:
            down_hosts.append(str(ip))
    except Exception:
        down_hosts.append(str(ip))

def scan_network_with_detection(network_str: str):
    """
    扫描网络并检测设备类型
    """
    try:
        network = ipaddress.ip_network(network_str)
    except ValueError:
        return None

    ip_queue = queue.Queue()
    for ip in network.hosts():
        ip_queue.put(ip)

    results = []
    threads = []
    thread_count = 50  # 减少线程数以避免SSH连接过多

    def worker():
        while not ip_queue.empty():
            try:
                ip = ip_queue.get_nowait()
                scan_ip_with_detection(ip, results)
                ip_queue.task_done()
            except queue.Empty:
                break

    for _ in range(thread_count):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return results

def scan_network(network_str: str):
    try:
        network = ipaddress.ip_network(network_str)
    except ValueError:
        return None, None

    ip_queue = queue.Queue()
    for ip in network.hosts():
        ip_queue.put(ip)

    up_hosts = []
    down_hosts = []
    threads = []
    thread_count = 100

    def worker():
        while not ip_queue.empty():
            ip = ip_queue.get()
            scan_ip(ip, up_hosts, down_hosts)
            ip_queue.task_done()

    for _ in range(thread_count):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    ip_queue.join()

    return sorted(up_hosts, key=ipaddress.ip_address), sorted(down_hosts, key=ipaddress.ip_address)


def scan_network_with_realtime_detection(network_str: str, callback_func: Callable = None):
    """
    实时扫描网络并检测设备类型
    """
    try:
        network = ipaddress.ip_network(network_str)
    except ValueError:
        if callback_func:
            callback_func({
                'type': 'error',
                'message': '无效的网络格式'
            })
        return None

    ip_list = list(network.hosts())
    total_ips = len(ip_list)
    
    if callback_func:
        callback_func({
            'type': 'start',
            'message': f'开始扫描 {network_str}，共 {total_ips} 个IP地址'
        })

    results = []
    completed = 0
    
    def scan_with_callback(ip):
        nonlocal completed
        try:
            param = '-n 1 -w 500' if platform.system().lower() == 'windows' else '-c 1 -W 0.5'
            command = ['ping', param, str(ip)]
            ret = subprocess.call(
                ' '.join(command),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if ret == 0:
                # 设备在线，检测设备类型
                device_info = ssh_login_and_detect(str(ip))
                result = {
                    'ip': str(ip),
                    'status': 'online',
                    'device_type': device_info['name'] if device_info else 'Unknown',
                    'device_details': device_info['details'] if device_info else None
                }
                results.append(result)
                
                # 发送实时消息
                if callback_func:
                    callback_func({
                        'type': 'device_found',
                        'ip': str(ip),
                        'device_type': device_info['name'] if device_info else 'Unknown',
                        'device_details': device_info['details'] if device_info else None
                    })
            else:
                # 设备离线
                result = {
                    'ip': str(ip),
                    'status': 'offline',
                    'device_type': None,
                    'device_details': None
                }
                results.append(result)
                
                # 可选：也发送离线设备消息
                if callback_func:
                    callback_func({
                        'type': 'device_offline',
                        'ip': str(ip),
                        'device_type': None,
                        'device_details': None
                    })
                    
        except Exception:
            result = {
                'ip': str(ip),
                'status': 'offline',
                'device_type': None,
                'device_details': None
            }
            results.append(result)
        
        # 更新进度
        completed += 1
        if callback_func:
            percentage = int((completed / total_ips) * 100)
            callback_func({
                'type': 'progress',
                'completed': completed,
                'total': total_ips,
                'percentage': percentage
            })
    
    # 使用线程池扫描
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(scan_with_callback, ip_list)
    
    # 发送完成消息
    if callback_func:
        online_count = len([r for r in results if r['status'] == 'online'])
        callback_func({
            'type': 'complete',
            'message': f'扫描完成，发现 {online_count} 个在线设备'
        })
    
    return results