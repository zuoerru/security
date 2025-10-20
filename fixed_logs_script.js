// 加载同步日志
        function loadLogs() {
            const logsContent = document.getElementById('logs-content');
            logsContent.innerHTML = '<div class="text-center text-muted">加载日志中...</div>';
            
            // 从服务器获取日志内容
            const baseUrl = window.location.origin + '/nvd/api/logs';
            fetch(baseUrl)
                .then(function(response) {
                    if (!response.ok) {
                        throw new Error('网络响应错误: ' + response.status);
                    }
                    return response.json();
                })
                .then(function(logs) {
                    console.log('获取到的日志数据:', logs);
                    if (logs && logs.length > 0) {
                        // 统计不同类型的日志数量
                        const autoLogsCount = logs.filter(log => log.action_type === 'auto').length;
                        const manualLogsCount = logs.filter(log => log.action_type === 'manual').length;
                        
                        let logsHTML = '<div class="mb-4 text-sm text-gray-500">共 ' + logs.length + ' 条日志 (自动同步: ' + autoLogsCount + ' 条, 手动同步: ' + manualLogsCount + ' 条)</div>';
                        logsHTML += '<ul class="list-unstyled">';
                        
                        // 按时间戳排序（确保最新的在前面）
                        const sortedLogs = logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                        
                        for (let i = 0; i < sortedLogs.length; i++) {
                            const log = sortedLogs[i];
                            const actionType = log.action_type === 'auto' ? '自动同步' : '手动同步';
                            const actionClass = log.action_type === 'auto' ? 'badge-secondary' : 'badge-primary';
                            const dateRange = log.start_date && log.end_date 
                                ? ' <small class="text-muted">(</small><small class="text-info">' + log.start_date + '</small> <small class="text-muted">至</small> <small class="text-info">' + log.end_date + '</small><small class="text-muted">)</small>' 
                                : '';
                            
                            // 使用标准Bootstrap样式
                            logsHTML += '<li class="p-3 bg-light rounded border border-gray-200 mb-3 shadow-sm">';
                            logsHTML += '<div class="text-sm text-gray-500 mb-2">' + log.timestamp + '</div>';
                            logsHTML += '<div class="d-flex flex-wrap align-items-center gap-2">';
                            logsHTML += '<span class="badge ' + actionClass + ' px-2 py-1">' + actionType + '</span>';
                            logsHTML += '<span class="text-gray-800">完成，新增 <span class="font-bold text-primary">' + log.count + '</span> 条记录</span>';
                            logsHTML += dateRange;
                            logsHTML += '</div>';
                            logsHTML += '</li>';
                        }
                        logsHTML += '</ul>';
                        logsContent.innerHTML = logsHTML;
                    } else {
                        logsContent.innerHTML = '<div class="text-center text-muted py-4">暂无同步日志</div>';
                    }
                })
                .catch(function(error) {
                    console.error('获取日志失败:', error);
                    logsContent.innerHTML = '<div class="text-center text-danger py-4">获取日志失败，请稍后重试</div>';
                });
        }