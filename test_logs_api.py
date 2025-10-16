import requests
import json

# 测试日志API
try:
    # 发送请求到日志API
    # 尝试不同端口
    ports = ['8010', '5000']
    response = None
    
    for port in ports:
        try:
            url = f'http://localhost:{port}/nvd/api/logs'
            print(f'尝试访问: {url}')
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            print(f'成功连接到端口: {port}')
            break
        except requests.exceptions.RequestException as e:
            print(f'端口{port}连接失败: {str(e)}')
            if port == ports[-1]:
                raise
    
    # 检查响应状态
    if response and response.status_code == 200:
        # 尝试解析JSON
        logs = response.json()
        print(f'API调用成功，返回了{len(logs)}条日志记录')
        
        # 统计自动同步和手动同步的日志数量
        auto_logs = [log for log in logs if log.get('action_type') == 'auto']
        manual_logs = [log for log in logs if log.get('action_type') == 'manual']
        
        print(f'自动同步(auto)日志数量: {len(auto_logs)}')
        print(f'手动同步(manual)日志数量: {len(manual_logs)}')
        
        # 打印前5条日志详细信息:
        print('\n前5条日志详细信息:')
        for i, log in enumerate(logs[:5]):
            print(f'日志{i+1}:')
            print(f"  时间戳: {log.get('timestamp')}")
            print(f"  类型: {log.get('action_type')}")
            print(f"  数量: {log.get('count')}")
            print(f"  开始日期: {log.get('start_date')}")
            print(f"  结束日期: {log.get('end_date')}")
            print()
        
        # 如果有自动同步日志，单独显示
        if auto_logs:
            print('\n自动同步日志示例:')
            for i, log in enumerate(auto_logs[:2]):
                print(f'自动日志{i+1}:', json.dumps(log, ensure_ascii=False, indent=2))
    else:
        print(f"API调用失败，状态码: {response.status_code if response else '无响应'}")
        print(f"响应内容: {response.text if response else '无内容'}")

except Exception as e:
    print(f'发生异常: {str(e)}')