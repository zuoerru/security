import requests

# 获取NVD页面的完整HTML内容
response = requests.get('http://localhost:8010/nvd/')

# 将内容保存到临时文件
with open('nvd_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
    
print(f'页面内容已保存到nvd_page.html，共{len(response.text)}个字符')