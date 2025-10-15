import requests
import json

# 测试日志API
try:
    # 发送请求到日志API
    response = requests.get('http://localhost:8010/nvd/api/logs')
    
    # 检查响应状态
    if response.status_code == 200:
        # 尝试解析JSON
        logs = response.json()
        print(f'API调用成功，返回了{len(logs)}条日志记录')
        # 打印前2条日志作为示例
        if logs:
            print('\n示例日志:')
            for i, log in enumerate(logs[:2]):
                print(f'日志{i+1}:', json.dumps(log, ensure_ascii=False, indent=2))
    else:
        print(f'API调用失败，状态码: {response.status_code}')
        print(f'响应内容: {response.text}')

except Exception as e:
    print(f'发生异常: {str(e)}')