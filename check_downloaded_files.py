#!/usr/bin/env python3
import os
import glob
from datetime import datetime, timedelta

# 获取昨天的日期格式
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
print(f'检查昨天({yesterday})的TSV文件...')

# 查找匹配的文件
matching_files = glob.glob(f'cve_yesterday_{yesterday}*.tsv')

if matching_files:
    print(f'找到 {len(matching_files)} 个TSV文件:')
    for file in matching_files:
        file_size = os.path.getsize(file)
        print(f'  - {file}: {file_size} 字节')
else:
    print('未找到昨天的TSV文件')

# 查看是否有HTML文件
html_files = glob.glob(f'cve_yesterday_{yesterday}*.html')
if html_files:
    print(f'找到 {len(html_files)} 个HTML文件:')
    for file in html_files:
        file_size = os.path.getsize(file)
        print(f'  - {file}: {file_size} 字节')