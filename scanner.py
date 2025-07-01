import subprocess
import threading
import ipaddress
import queue
import platform

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