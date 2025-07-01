import subprocess
import threading
import ipaddress
import queue
import platform

# 用于存放待扫描的IP地址
ip_queue = queue.Queue()
# 存放结果
up_hosts = []
down_hosts = []

class ScanThread(threading.Thread):
    def __init__(self, q):
        threading.Thread.__init__(self)
        self.q = q

    def run(self):
        while not self.q.empty():
            ip = self.q.get()
            # 根据操作系统选择不同的ping参数
            param = '-n 1 -w 500' if platform.system().lower() == 'windows' else '-c 1 -W 0.5'
            command = ['ping', param, str(ip)]

            try:
                # Popen的stdout和stderr设置为DEVNULL可以提高性能
                ret = subprocess.call(
                    ' '.join(command),
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if ret == 0:
                    print(f'[+] {ip} is up')
                    up_hosts.append(str(ip))
                else:
                    # print(f'[-] {ip} is down')
                    down_hosts.append(str(ip))
            except Exception as e:
                print(f'[!] Error scanning {ip}: {e}')
                down_hosts.append(str(ip))
            self.q.task_done()

def main():
    network_str = input("请输入要扫描的网段 (例如, 192.168.1.0/24): ")
    try:
        network = ipaddress.ip_network(network_str)
    except ValueError:
        print("无效的网段格式.")
        return

    for ip in network.hosts():
        ip_queue.put(ip)

    # 设置线程数，可以根据需要调整
    thread_count = 100
    for i in range(thread_count):
        worker = ScanThread(ip_queue)
        worker.daemon = True
        worker.start()

    ip_queue.join()

    print("\n--- 扫描结果 ---")
    print(f"存活的主机 ({len(up_hosts)}):")
    for host in sorted(up_hosts, key=ipaddress.ip_address):
        print(host)

    print(f"\n不存活的主机 ({len(down_hosts)}).")
    # 如果需要显示不存活的主机，取消下面的注释
    # for host in sorted(down_hosts, key=ipaddress.ip_address):
    #     print(host)

if __name__ == '__main__':
    main()