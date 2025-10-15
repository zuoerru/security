#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从cvedetails.com下载2015年每个月的CVE数据"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from datetime import datetime

# 设置请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.google.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
}

# 主页面URL
BASE_URL = 'https://www.cvedetails.com/browse-by-date.php'

# 下载目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = BASE_DIR

class CveDetailsDownloader:
    @staticmethod
    def download_year_monthly_data(year=2015):
        """下载指定年份每个月的CVE数据"""
        print(f"开始下载{year}年的CVE数据...")
        
        try:
            # 创建会话对象，保持连接状态
            session = requests.Session()
            session.headers.update(HEADERS)
            
            # 先访问一个预热页面，获取初始cookie
            session.get('https://www.cvedetails.com', timeout=30)
            time.sleep(2)  # 短暂延迟
            
            # 访问主页面
            response = session.get(BASE_URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找指定年份的所有月份链接
            year_section = soup.find('div', id=f"container_{year}")
            if not year_section:
                print(f"未找到{year}年的数据部分")
                return False
            
            # 获取所有月份的链接
            month_links = []
            for link in year_section.find_all('a', href=True):
                if 'date=' in link.get('href'):
                    month_name = link.text.strip()
                    month_url = urljoin(BASE_URL, link.get('href'))
                    # 提取月份数字
                    month_num = CveDetailsDownloader._get_month_number(month_name)
                    if month_num:
                        month_links.append((month_num, month_url))
            
            if not month_links:
                print(f"未找到{year}年各月份的链接")
                return False
            
            # 按月份排序
            month_links.sort(key=lambda x: x[0])
            
            # 下载每个月的数据
            for month_num, month_url in month_links:
                # 构建文件名，例如201501.tsv
                file_name = f"{year}{month_num:02d}.tsv"
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                
                # 检查文件是否已存在
                if os.path.exists(file_path):
                    print(f"文件{file_name}已存在，跳过下载")
                    continue
                
                print(f"正在下载{year}年{month_num}月的数据...")
                
                # 下载该月份的数据
                success = CveDetailsDownloader._download_month_data(month_url, file_path)
                
                if success:
                    print(f"成功下载并保存至{file_name}")
                else:
                    print(f"下载{year}年{month_num}月数据失败")
                
                # 添加延迟，避免请求过于频繁
                time.sleep(5)
            
            print(f"{year}年所有月份的数据下载完成")
            return True
        except Exception as e:
            print(f"下载过程中发生错误: {str(e)}")
            return False
    
    @staticmethod
    def _get_month_number(month_name):
        """从月份名称中提取月份数字"""
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        # 尝试直接从名称获取
        for name, num in month_map.items():
            if name.lower() in month_name.lower():
                return num
        
        # 尝试从数字获取
        try:
            return int(month_name.strip())
        except ValueError:
            return None
    
    @staticmethod
    def _download_month_data(month_url, file_path):
        """下载指定月份页面中的TSV数据"""
        try:
            # 访问月份页面
            response = session.get(month_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找export按钮链接
            export_link = None
            
            # 查找所有包含'export'或'tsv'的链接
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.text.lower()
                
                if ('export' in href or 'export' in text) and ('tsv' in href or 'tab' in href):
                    export_link = urljoin(BASE_URL, href)
                    break
            
            # 如果没找到，尝试查找class中包含export的按钮
            if not export_link:
                for button in soup.find_all(['button', 'input'], {'class': lambda x: x and 'export' in x.lower()}):
                    if button.get('onclick'):
                        onclick = button.get('onclick')
                        # 尝试从onclick事件中提取链接
                        if 'location.href=' in onclick:
                            start = onclick.find('"') + 1
                            end = onclick.rfind('"')
                            if start < end:
                                export_link = urljoin(BASE_URL, onclick[start:end])
                                break
            
            if not export_link:
                print("未找到export按钮链接")
                return False
            
            print(f"找到export链接: {export_link}")
            
            # 下载TSV文件
            response = session.get(export_link, timeout=60)
            response.raise_for_status()
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"文件大小: {len(response.content)} 字节")
            return True
        except Exception as e:
            print(f"下载月份数据时出错: {str(e)}")
            return False

def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    
    print("CVE Details数据下载器启动")
    print(f"下载目录: {DOWNLOAD_DIR}")
    
    # 下载2015年的数据
    success = CveDetailsDownloader.download_year_monthly_data(year=2015)
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        print(f"下载任务完成！总耗时: {duration}")
    else:
        print(f"下载任务失败！总耗时: {duration}")

if __name__ == "__main__":
    main()