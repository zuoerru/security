#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从NVD (National Vulnerability Database) 获取2015年每个月的CVE数据"""

import os
import requests
import time
import json
from datetime import datetime, timedelta
import gzip
import shutil
import csv
import xml.etree.ElementTree as ET

# 下载目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = BASE_DIR

class NvdCveDownloader:
    @staticmethod
    def download_year_monthly_data(year=2015):
        """从NVD下载指定年份每个月的CVE数据"""
        print(f"开始从NVD下载{year}年的CVE数据...")
        
        try:
            # 为每个月创建请求
            for month in range(1, 13):
                # 构建文件名，例如201501.tsv
                file_name = f"{year}{month:02d}.tsv"
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                
                # 检查文件是否已存在
                if os.path.exists(file_path):
                    print(f"文件{file_name}已存在，跳过下载")
                    continue
                
                print(f"正在下载{year}年{month}月的数据...")
                
                # 构建日期范围
                start_date = f"{year}-{month:02d}-01T00:00:00.000"
                
                # 计算下个月的第一天
                if month == 12:
                    next_month = 1
                    next_year = year + 1
                else:
                    next_month = month + 1
                    next_year = year
                
                end_date = f"{next_year}-{next_month:02d}-01T00:00:00.000"
                
                # 调用NVD API获取数据
                cve_data = NvdCveDownloader._fetch_cve_data(start_date, end_date)
                
                if cve_data:
                    # 将数据保存为TSV格式
                    NvdCveDownloader._save_as_tsv(cve_data, file_path)
                    print(f"成功保存{file_name}，共{len(cve_data)}条记录")
                else:
                    print(f"未获取到{year}年{month}月的数据")
                
                # 添加延迟，避免请求过于频繁
                time.sleep(6)  # NVD API有速率限制，建议至少6秒间隔
            
            print(f"{year}年所有月份的数据下载完成")
            return True
        except Exception as e:
            print(f"下载过程中发生错误: {str(e)}")
            return False
    
    @staticmethod
    def _fetch_cve_data(start_date, end_date):
        """调用NVD API获取指定日期范围内的CVE数据"""
        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        
        params = {
            'pubStartDate': start_date,
            'pubEndDate': end_date,
            'resultsPerPage': 2000,  # 每次请求最多返回2000条记录
        }
        
        all_cves = []
        start_index = 0
        
        while True:
            try:
                print(f"  请求数据，起始索引: {start_index}")
                
                # 更新起始索引
                params['startIndex'] = start_index
                
                # 发送请求
                response = requests.get(base_url, params=params, timeout=60)
                response.raise_for_status()
                
                # 解析响应
                data = response.json()
                
                # 提取CVE数据
                if 'vulnerabilities' in data and data['vulnerabilities']:
                    cves_in_page = data['vulnerabilities']
                    all_cves.extend(cves_in_page)
                    print(f"  成功获取{len(cves_in_page)}条记录")
                
                # 检查是否还有更多数据
                total_results = data.get('totalResults', 0)
                if start_index + len(data.get('vulnerabilities', [])) >= total_results:
                    break
                
                # 更新起始索引
                start_index += len(data.get('vulnerabilities', []))
                
                # 添加延迟
                time.sleep(6)
            except Exception as e:
                print(f"  获取数据时出错: {str(e)}")
                # 尝试处理XML格式的响应（如果API返回XML）
                try:
                    if response and response.text:
                        # 尝试解析XML响应
                        root = ET.fromstring(response.text)
                        # 提取CVE信息
                        # 这里简化处理，实际XML格式可能不同
                        print(f"  收到XML响应，包含{len(root.findall('.//cve'))}条CVE记录")
                        return []  # 简化处理，实际需要根据XML格式解析
                except:
                    pass
                
                # 如果是速率限制错误，增加延迟
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                    print("  达到速率限制，增加延迟")
                    time.sleep(10)
                    continue
                
                break
        
        return all_cves
    
    @staticmethod
    def _save_as_tsv(cve_data, file_path):
        """将CVE数据保存为TSV格式"""
        # 定义TSV文件的字段
        fields = [
            'CVE ID', 'Published Date', 'Last Modified Date', 
            'Description', 'Base Score', 'Base Severity', 
            'Vector String', 'Vendor', 'Product'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as tsvfile:
            writer = csv.DictWriter(tsvfile, fieldnames=fields, delimiter='\t')
            
            # 写入表头
            writer.writeheader()
            
            # 写入数据
            for item in cve_data:
                cve = item.get('cve', {})
                
                # 提取基本信息
                cve_id = cve.get('id', '')
                published_date = cve.get('published', '')
                last_modified_date = cve.get('lastModified', '')
                
                # 提取描述
                descriptions = cve.get('descriptions', [])
                description = descriptions[0].get('value', '') if descriptions else ''
                
                # 提取评分信息
                base_score = ''
                base_severity = ''
                vector_string = ''
                
                metrics = cve.get('metrics', {})
                # 尝试获取CVSS v3评分
                if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                    cvss_data = metrics['cvssMetricV31'][0].get('cvssData', {})
                    base_score = cvss_data.get('baseScore', '')
                    base_severity = cvss_data.get('baseSeverity', '')
                    vector_string = cvss_data.get('vectorString', '')
                # 如果没有v3评分，尝试获取v2评分
                elif 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                    cvss_data = metrics['cvssMetricV2'][0].get('cvssData', {})
                    base_score = cvss_data.get('baseScore', '')
                    base_severity = metrics['cvssMetricV2'][0].get('baseSeverity', '')
                    vector_string = cvss_data.get('vectorString', '')
                
                # 提取厂商和产品信息
                vendor = ''
                product = ''
                
                configurations = cve.get('configurations', [])
                if configurations:
                    nodes = configurations[0].get('nodes', [])
                    if nodes:
                        cpes = nodes[0].get('cpes', [])
                        if cpes:
                            # 解析CPE字符串获取厂商和产品信息
                            cpe_parts = cpes[0].get('cpe23Uri', '').split(':')
                            if len(cpe_parts) >= 5:
                                vendor = cpe_parts[3]
                                product = cpe_parts[4]
                
                # 写入一行数据
                writer.writerow({
                    'CVE ID': cve_id,
                    'Published Date': published_date,
                    'Last Modified Date': last_modified_date,
                    'Description': description,
                    'Base Score': base_score,
                    'Base Severity': base_severity,
                    'Vector String': vector_string,
                    'Vendor': vendor,
                    'Product': product
                })

def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    
    print("NVD CVE数据下载器启动")
    print(f"下载目录: {DOWNLOAD_DIR}")
    
    # 下载2016-2025年的数据
    all_success = True
    for year in range(2016, 2026):
        success = NvdCveDownloader.download_year_monthly_data(year=year)
        if not success:
            all_success = False
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    if all_success:
        print(f"所有年份数据下载完成！总耗时: {duration}")
    else:
        print(f"部分年份数据下载失败！总耗时: {duration}")

if __name__ == "__main__":
    main()