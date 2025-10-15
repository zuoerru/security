#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查CVE数据下载进度"""

import os
import re
from collections import defaultdict

# 定义目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义需要下载的年份范围
START_YEAR = 2016
END_YEAR = 2025

# 定义月份数量
MONTHS = 12


def check_download_progress():
    """检查下载进度"""
    # 获取当前目录下所有文件
    files = os.listdir(BASE_DIR)
    
    # 初始化计数器
    downloaded_files = defaultdict(set)
    
    # 匹配TSV文件
    pattern = r'(\d{4})(\d{2})\.tsv'
    
    # 遍历所有文件
    for file in files:
        match = re.match(pattern, file)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            
            # 只关注目标年份范围
            if START_YEAR <= year <= END_YEAR:
                downloaded_files[year].add(month)
    
    # 计算下载进度
    total_months = (END_YEAR - START_YEAR + 1) * MONTHS
    downloaded_months = sum(len(months) for months in downloaded_files.values())
    
    # 打印进度摘要
    print(f"CVE数据下载进度")
    print(f"目标范围: {START_YEAR}-{END_YEAR}年，共{total_months}个月")
    print(f"已下载: {downloaded_months}个月 ({downloaded_months/total_months*100:.2f}%)")
    print()
    
    # 打印详细进度
    for year in range(START_YEAR, END_YEAR + 1):
        downloaded_months_for_year = downloaded_files.get(year, set())
        total_months_for_year = MONTHS
        percentage = len(downloaded_months_for_year)/total_months_for_year*100
        
        print(f"{year}年: 已下载{len(downloaded_months_for_year)}/{total_months_for_year}个月 ({percentage:.2f}%)")
        
        # 显示已下载的月份
        if downloaded_months_for_year:
            print(f"  已下载月份: {sorted(downloaded_months_for_year)}")
        
        # 显示未下载的月份
        missing_months = set(range(1, MONTHS + 1)) - downloaded_months_for_year
        if missing_months:
            print(f"  未下载月份: {sorted(missing_months)}")
    
    # 检查是否有2015年的数据（如果有的话）
    if downloaded_files.get(2015):
        print()
        print(f"注意: 检测到2015年的数据，共{len(downloaded_files[2015])}个月")


if __name__ == "__main__":
    check_download_progress()