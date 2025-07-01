// 将openModal函数定义在全局作用域
function openModal(ip, user = '', startTime = '', endTime = '', purpose = '') {
    const ipAddressInput = document.getElementById('ip-address');
    const userInput = document.getElementById('user');
    const startTimeInput = document.getElementById('start-time');
    const endTimeInput = document.getElementById('end-time');
    const purposeInput = document.getElementById('purpose');
    const modal = document.getElementById('occupy-modal');
    
    ipAddressInput.value = ip;
    userInput.value = user;
    startTimeInput.value = startTime ? new Date(startTime).toISOString().slice(0, 16) : '';
    endTimeInput.value = endTime ? new Date(endTime).toISOString().slice(0, 16) : '';
    purposeInput.value = purpose;
    modal.style.display = 'block';
}

document.addEventListener('DOMContentLoaded', function() {
    const scanBtn = document.getElementById('scan-btn');
    const networkInput = document.getElementById('network-input');
    const scanStatus = document.getElementById('scan-status');
    const devicesTbody = document.getElementById('devices-tbody');
    const modal = document.getElementById('occupy-modal');
    const closeModal = document.getElementsByClassName('close')[0];
    const occupyForm = document.getElementById('occupy-form');
    const ipAddressInput = document.getElementById('ip-address');
    const userInput = document.getElementById('user');
    const startTimeInput = document.getElementById('start-time');
    const endTimeInput = document.getElementById('end-time');
    const purposeInput = document.getElementById('purpose');

    let scannedOnlineIps = [];
    let scannedOfflineIps = [];
    let occupiedDevices = [];

    // 加载初始数据
    loadOccupiedDevices();

    scanBtn.addEventListener('click', () => {
        const network = networkInput.value.trim();
        if (!network) {
            alert('请输入要扫描的网段，例如 192.168.1.0/24');
            return;
        }
        scanStatus.textContent = '正在扫描中...';
        fetch(`/scan/${network}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                scanStatus.textContent = data.message;
                if (data.online_hosts && Array.isArray(data.online_hosts)) {
                    scannedOnlineIps = data.online_hosts;
                } else {
                    scannedOnlineIps = [];
                }
                if (data.offline_hosts && Array.isArray(data.offline_hosts)) {
                    scannedOfflineIps = data.offline_hosts;
                } else {
                    scannedOfflineIps = [];
                }
                loadOccupiedDevices();
            })
            .catch(error => {
                console.error('扫描出错:', error);
                scanStatus.textContent = '扫描失败：请检查网络地址格式（例如：192.168.1.0/24）';
                scannedOnlineIps = [];
                scannedOfflineIps = [];
                loadOccupiedDevices();
            });
    });

    function loadOccupiedDevices() {
        fetch('/devices/')
            .then(response => response.json())
            .then(data => {
                occupiedDevices = data;
                updateDevicesTable();
            });
    }

    function updateDevicesTable() {
        devicesTbody.innerHTML = '';
        
        // 创建所有IP的集合（在线IP + 离线IP + 已占用的IP）
        const allIps = new Set([
            ...scannedOnlineIps, 
            ...scannedOfflineIps, 
            ...occupiedDevices.map(d => d.ip_address)
        ]);
        
        // 将IP转换为数组并按状态和IP地址排序
        const sortedIps = Array.from(allIps).sort((a, b) => {
            const aIsOnline = scannedOnlineIps.includes(a);
            const bIsOnline = scannedOnlineIps.includes(b);
            
            // 首先按在线状态排序（在线的排在前面）
            if (aIsOnline && !bIsOnline) return -1;
            if (!aIsOnline && bIsOnline) return 1;
            
            // 如果状态相同，则按IP地址排序
            const aNum = a.split('.').map(num => parseInt(num, 10));
            const bNum = b.split('.').map(num => parseInt(num, 10));
            for (let i = 0; i < 4; i++) {
                if (aNum[i] !== bNum[i]) {
                    return aNum[i] - bNum[i];
                }
            }
            return 0;
        });
        
        sortedIps.forEach(ip => {
            const device = occupiedDevices.find(d => d.ip_address === ip);
            const row = devicesTbody.insertRow();
            
            const isOnline = scannedOnlineIps.includes(ip);
            const isOffline = scannedOfflineIps.includes(ip);
            const isOccupied = device && device.user && device.end_time;
            
            // 设置行的样式
            if (isOffline) {
                row.style.color = '#999';
                row.style.backgroundColor = '#f5f5f5';
            }
            
            row.innerHTML = `
                <td>${ip}</td>
                <td>${device ? (device.user || '') : ''}</td>
                <td>${device ? (device.start_time || '') : ''}</td>
                <td>${device ? (device.end_time || '') : ''}</td>
                <td>${device ? (device.purpose || '') : ''}</td>
                <td>
                    ${isOffline ? '' : `
                        <button 
                            class="${isOccupied ? 'occupied-btn' : 'occupy-btn'}" 
                            onclick="openModal('${ip}', '${device ? (device.user || '') : ''}', '${device ? (device.start_time || '') : ''}', '${device ? (device.end_time || '') : ''}', '${device ? (device.purpose || '') : ''}')"
                        >
                            ${isOccupied ? '已占用' : '占用'}
                        </button>
                    `}
                </td>
            `;
        });
    }

    closeModal.onclick = function() {
        modal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    occupyForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const deviceData = {
            ip_address: ipAddressInput.value,
            user: userInput.value,
            start_time: startTimeInput.value ? new Date(startTimeInput.value).toISOString() : null,
            end_time: endTimeInput.value ? new Date(endTimeInput.value).toISOString() : null,
            purpose: purposeInput.value
        };

        fetch('/devices/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(deviceData),
        })
        .then(response => response.json())
        .then(data => {
            console.log('设备信息已保存:', data);
            modal.style.display = 'none';
            loadOccupiedDevices();
        })
        .catch(error => {
            console.error('保存出错:', error);
        });
    });
});