import requests
import json

# 测试第1页
response = requests.get('http://localhost:8011/cisa/api/data')
if response.status_code == 200:
    data = response.json()
    print(f"第1页 - 每页条数: {data.get('per_page')}, 总记录数: {data.get('total')}, 总页数: {data.get('pages')}")
    print(f"数据项数量: {len(data.get('data', []))}")
else:
    print(f"第1页请求失败: {response.status_code}")

# 测试第2页
response = requests.get('http://localhost:8011/cisa/api/data?page=2')
if response.status_code == 200:
    data = response.json()
    print(f"第2页 - 每页条数: {data.get('per_page')}, 当前页: {data.get('page')}")
    print(f"数据项数量: {len(data.get('data', []))}")
else:
    print(f"第2页请求失败: {response.status_code}")

# 测试修改每页显示数量
response = requests.get('http://localhost:8011/cisa/api/data?per_page=50')
if response.status_code == 200:
    data = response.json()
    print(f"每页50条 - 每页条数: {data.get('per_page')}, 总页数: {data.get('pages')}")
    print(f"数据项数量: {len(data.get('data', []))}")
else:
    print(f"每页50条请求失败: {response.status_code}")