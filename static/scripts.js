// 将openModal函数定义在全局作用域
function openModal(ip, user = '', startTime = '', endTime = '', purpose = '', deviceType = '') {
    const modal = document.getElementById('occupy-modal');
    
    // 填充表单数据
    document.getElementById('ip-address').value = ip;
    document.getElementById('user').value = user;
    document.getElementById('start-time').value = startTime;
    document.getElementById('end-time').value = endTime;
    document.getElementById('purpose').value = purpose;
    document.getElementById('device-type').value = deviceType;
    
    // 显示模态框
    modal.style.display = 'block';
}

// 添加悬浮框智能定位函数
function handleTooltipPosition() {
    const tooltipContainers = document.querySelectorAll('.device-type-container');
    
    tooltipContainers.forEach(container => {
        const tooltip = container.querySelector('.device-tooltip');
        if (!tooltip) return;
        
        // 移除之前的事件监听器
        container.removeEventListener('mouseenter', container._tooltipHandler);
        container.removeEventListener('mouseleave', container._tooltipLeaveHandler);
        
        // 创建新的事件处理器
        container._tooltipHandler = function(e) {
            const rect = container.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            
            // 先临时显示悬浮框以获取真实尺寸
            tooltip.style.visibility = 'hidden';
            tooltip.style.opacity = '1';
            tooltip.style.display = 'block';
            tooltip.style.position = 'fixed';
            tooltip.style.left = '0px';
            tooltip.style.top = '0px';
            tooltip.style.transform = 'none';
            
            // 获取悬浮框真实尺寸
            const tooltipRect = tooltip.getBoundingClientRect();
            const tooltipWidth = tooltipRect.width;
            const tooltipHeight = tooltipRect.height;
            
            // 重置样式
            tooltip.style.display = '';
            tooltip.style.visibility = '';
            tooltip.style.opacity = '';
            
            // 计算最佳位置
            let left = rect.left + (rect.width / 2);
            let top = rect.top;
            
            // 水平位置调整
            if (left + tooltipWidth / 2 > viewportWidth - 20) {
                // 右侧超出，靠右显示
                tooltip.style.left = (viewportWidth - tooltipWidth - 20) + 'px';
                tooltip.style.right = 'auto';
                tooltip.style.transform = 'none';
            } else if (left - tooltipWidth / 2 < 20) {
                // 左侧超出，靠左显示
                tooltip.style.left = '20px';
                tooltip.style.right = 'auto';
                tooltip.style.transform = 'none';
            } else {
                // 居中显示
                tooltip.style.left = left + 'px';
                tooltip.style.right = 'auto';
                tooltip.style.transform = 'translateX(-50%)';
            }
            
            // 垂直位置调整
            if (top - tooltipHeight - 15 < 20) {
                // 上方空间不足，显示在下方
                tooltip.style.top = (rect.bottom + 10) + 'px';
                tooltip.style.bottom = 'auto';
                tooltip.classList.add('tooltip-bottom');
            } else {
                // 显示在上方
                tooltip.style.top = (top - tooltipHeight - 10) + 'px';
                tooltip.style.bottom = 'auto';
                tooltip.classList.remove('tooltip-bottom');
            }
        };
        
        container._tooltipLeaveHandler = function(e) {
            tooltip.classList.remove('tooltip-bottom');
        };
        
        // 添加事件监听器
        container.addEventListener('mouseenter', container._tooltipHandler);
        container.addEventListener('mouseleave', container._tooltipLeaveHandler);
    });
}

// 在文档加载完成后添加悬浮框定位逻辑
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
    const deviceTypeInput = document.getElementById('device-type');

    let scannedOnlineIps = [];
    let scannedOfflineIps = [];
    let scannedDevices = []; // 存储带设备类型的扫描结果
    let occupiedDevices = [];
    let eventSource = null;
    let isScanning = false;

    // 加载初始数据
    loadOccupiedDevices();

    // 处理实时消息
    function handleRealtimeMessage(data) {
        console.log('收到消息:', data); // 添加调试日志
        
        switch(data.type) {
            case 'start':
                updateScanStatus(data.message);
                break;
                
            case 'progress':
                updateProgress(data.completed, data.total, data.percentage);
                break;
                
            case 'device_found':
                console.log('发现设备:', data.ip, data.device_type); // 调试日志
                addRealtimeResult(data.ip, data.device_type, 'online', data.device_details);
                updateDevicesTable();
                break;
                
            case 'device_offline':  // 新增：处理离线设备
                addRealtimeResult(data.ip, data.device_type, 'offline', data.device_details);
                updateDevicesTable();
                break;
                
            case 'complete':
                isScanning = false;
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                
                const cacheInfo = data.from_cache ? ' (来自缓存)' : '';
                scanStatus.innerHTML = `<div class="scan-success">✅ ${data.message}${cacheInfo}</div>`;
                
                // 移除进度条
                const progressContainer = document.querySelector('.progress-container');
                if (progressContainer) {
                    progressContainer.remove();
                }
                loadOccupiedDevices(); // 重新加载设备列表
                break;
                
            case 'error':
                isScanning = false;
                scanStatus.innerHTML = `<div class="scan-error">❌ ${data.message}</div>`;
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                break;
                
            case 'heartbeat':
                // 心跳消息，不需要处理
                break;
        }
    }
    
    // 更新扫描状态
    function updateScanStatus(message) {
        const statusDiv = document.querySelector('.current-scan-status');
        if (statusDiv) {
            statusDiv.textContent = message;
        } else {
            const newDiv = document.createElement('div');
            newDiv.className = 'current-scan-status';
            newDiv.textContent = message;
            scanStatus.appendChild(newDiv);
        }
    }
    
    // 更新进度条
    function updateProgress(completed, total, percentage) {
        let progressDiv = document.querySelector('.progress-container');
        if (!progressDiv) {
            progressDiv = document.createElement('div');
            progressDiv.className = 'progress-container';
            progressDiv.innerHTML = `
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div class="progress-text"></div>
            `;
            scanStatus.appendChild(progressDiv);
        }
        
        const progressFill = progressDiv.querySelector('.progress-fill');
        const progressText = progressDiv.querySelector('.progress-text');
        
        progressFill.style.width = percentage + '%';
        progressText.textContent = `${completed}/${total} (${percentage}%)`;
    }
    
    // 实时添加发现的设备
    function addRealtimeResult(ip, deviceType, status, deviceDetails = null) {
        // 更新扫描结果数组
        if (status === 'online') {
            if (!scannedOnlineIps.includes(ip)) {
                scannedOnlineIps.push(ip);
            }
            // 从离线列表中移除（如果存在）
            const offlineIndex = scannedOfflineIps.indexOf(ip);
            if (offlineIndex > -1) {
                scannedOfflineIps.splice(offlineIndex, 1);
            }
        } else if (status === 'offline') {
            if (!scannedOfflineIps.includes(ip)) {
                scannedOfflineIps.push(ip);
            }
            // 从在线列表中移除（如果存在）
            const onlineIndex = scannedOnlineIps.indexOf(ip);
            if (onlineIndex > -1) {
                scannedOnlineIps.splice(onlineIndex, 1);
            }
        }
        
        // 更新或添加设备信息
        const existingDeviceIndex = scannedDevices.findIndex(d => d.ip === ip);
        const deviceInfo = {
            ip: ip,
            device_type: deviceType,
            device_details: deviceDetails,
            status: status
        };
        
        if (existingDeviceIndex > -1) {
            scannedDevices[existingDeviceIndex] = deviceInfo;
        } else {
            scannedDevices.push(deviceInfo);
        }
    }

    scanBtn.addEventListener('click', () => {
        const network = networkInput.value.trim();
        if (!network) {
            alert('请输入要扫描的网段，例如 192.168.1.0/24');
            return;
        }
        
        if (isScanning) {
            alert('扫描正在进行中，请等待完成');
            return;
        }
        
        isScanning = true;
        scanStatus.innerHTML = '<div class="scan-preparing">🚀 准备开始扫描...</div>';
        
        // 清空之前的扫描结果
        scannedOnlineIps = [];
        scannedOfflineIps = [];
        scannedDevices = [];
        
        // 启动实时扫描
        fetch(`/scan_realtime/${network}`, {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('实时扫描已启动:', data.message);
            
            // 建立EventSource连接
            eventSource = new EventSource(`/scan_stream/${data.scan_id}`);
            
            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleRealtimeMessage(data);
                } catch (e) {
                    console.error('解析消息失败:', e);
                }
            };
            
            eventSource.onerror = function(event) {
                console.error('EventSource错误:', event);
                if (eventSource.readyState === EventSource.CLOSED) {
                    isScanning = false;
                    scanStatus.innerHTML = '<div class="scan-error">❌ 连接已断开</div>';
                }
            };
        })
        .catch(error => {
            console.error('启动扫描出错:', error);
            isScanning = false;
            scanStatus.innerHTML = '<div class="scan-error">❌ 启动扫描失败，请检查网络地址格式</div>';
        });
    });

    function loadOccupiedDevices() {
        fetch('/devices/')
            .then(response => response.json())
            .then(data => {
                occupiedDevices = data;
                updateDevicesTable();
            })
            .catch(error => {
                console.error('加载设备数据出错:', error);
                occupiedDevices = [];
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
            if (aIsOnline !== bIsOnline) {
                return bIsOnline - aIsOnline;
            }
            
            // 然后按IP地址排序
            const aNum = a.split('.').map(num => parseInt(num, 10).toString().padStart(3, '0')).join('.');
            const bNum = b.split('.').map(num => parseInt(num, 10).toString().padStart(3, '0')).join('.');
            return aNum.localeCompare(bNum);
        });
        
        sortedIps.forEach(ip => {
            const row = document.createElement('tr');
            const isOnline = scannedOnlineIps.includes(ip);
            const occupiedDevice = occupiedDevices.find(d => d.ip_address === ip);
            const scannedDevice = scannedDevices.find(d => d.ip === ip);
            
            // 设置行的样式
            if (isOnline) {
                row.classList.add('online');
            } else if (scannedOfflineIps.includes(ip)) {
                row.classList.add('offline-row');
            }
            
            if (occupiedDevice) {
                row.classList.add('occupied');
            }
            
            // 获取设备类型信息
            const deviceTypeName = occupiedDevice?.device_type || scannedDevice?.device_type || '';
            const deviceDetails = scannedDevice?.device_details || '';
            
            // 创建设备类型显示内容
            let deviceTypeDisplay = '';
            if (deviceTypeName) {
                if (deviceDetails) {
                    deviceTypeDisplay = `
                        <div class="device-type-container">
                            <span class="device-type-name">${deviceTypeName}</span>
                            <div class="device-tooltip">${deviceDetails}</div>
                        </div>
                    `;
                } else {
                    deviceTypeDisplay = deviceTypeName;
                }
            }
            
            // 根据设备状态显示不同的按钮
            let actionButton = '';
            if (isOnline) {
                if (occupiedDevice) {
                    // 已占用的设备显示红色"已占用"按钮
                    actionButton = `<button onclick="openModal('${ip}', '${occupiedDevice.user || ''}', '${occupiedDevice.start_time || ''}', '${occupiedDevice.end_time || ''}', '${occupiedDevice.purpose || ''}', '${deviceTypeName}')" class="occupied-btn">已占用</button>`;
                } else {
                    // 未占用的在线设备显示绿色"占用"按钮
                    actionButton = `<button onclick="openModal('${ip}', '', '', '', '', '${deviceTypeName}')" class="occupy-btn">占用</button>`;
                }
            }
            // 离线设备不显示任何按钮
            
            // 确保按钮在操作列（第7列）
            row.innerHTML = `
                <td>${ip}</td>
                <td>${occupiedDevice ? occupiedDevice.user || '' : ''}</td>
                <td>${occupiedDevice && occupiedDevice.start_time ? new Date(occupiedDevice.start_time).toLocaleString() : ''}</td>
                <td>${occupiedDevice && occupiedDevice.end_time ? new Date(occupiedDevice.end_time).toLocaleString() : ''}</td>
                <td>${occupiedDevice ? occupiedDevice.purpose || '' : ''}</td>
                <td>${deviceTypeDisplay}</td>
                <td>
                    ${actionButton}
                </td>
            `;
            
            devicesTbody.appendChild(row);
        });
        
        // 在表格更新后重新绑定悬浮框事件
        setTimeout(handleTooltipPosition, 100);
    }

    // 关闭模态框
    closeModal.onclick = function() {
        modal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    // 处理表单提交
    occupyForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const deviceData = {
            ip_address: ipAddressInput.value,
            user: userInput.value,
            start_time: startTimeInput.value ? new Date(startTimeInput.value).toISOString() : null,
            end_time: endTimeInput.value ? new Date(endTimeInput.value).toISOString() : null,
            purpose: purposeInput.value,
            device_type: deviceTypeInput.value
        };
        
        fetch('/devices/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(deviceData)
        })
        .then(response => response.json())
        .then(data => {
            modal.style.display = 'none';
            loadOccupiedDevices();
        })
        .catch(error => {
            console.error('保存设备信息出错:', error);
            alert('保存失败，请重试');
        });
    });
    
    // 页面卸载时关闭连接
    window.addEventListener('beforeunload', function() {
        if (eventSource) {
            eventSource.close();
        }
    });
    
    // 初始绑定悬浮框事件
    handleTooltipPosition();
});