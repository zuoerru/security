#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""增强版：从cvedetails.com下载2015年每个月的CVE数据"""

import os
import requests
import re
import time
import random
from datetime import datetime
from urllib.parse import urljoin, urlparse
from http.cookiejar import LWPCookieJar
import ssl
from bs4 import BeautifulSoup

# 下载目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = BASE_DIR

# 创建SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class CveDetailsEnhancedDownloader:
    def __init__(self):
        # 创建会话对象
        self.session = requests.Session()
        self.session.cookies = LWPCookieJar('cookies.txt')
        
        # 加载已保存的cookie（如果有）
        try:
            self.session.cookies.load(ignore_discard=True)
        except Exception:
            pass
        
        # 设置请求头池，模拟不同浏览器
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69'
        ]
        
        # 设置默认请求头
        self.update_headers()
    
    def update_headers(self):
        """更新请求头，使用随机用户代理"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers',
        }
        self.session.headers.update(headers)
    
    def random_delay(self, min_seconds=2, max_seconds=5):
        """添加随机延迟，模拟真实用户行为"""
        delay = random.uniform(min_seconds, max_seconds)
        print(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    def warmup(self):
        """预热网站，建立信任"""
        print("正在预热网站...")
        
        # 先访问主页
        home_url = 'https://www.cvedetails.com'
        self.update_headers()
        self.session.headers['Referer'] = 'https://www.google.com/'
        
        try:
            response = self.session.get(home_url, timeout=30, verify=False)
            response.raise_for_status()
            print(f"预热请求成功，状态码: {response.status_code}")
            
            # 保存cookie
            self.session.cookies.save(ignore_discard=True)
            
            # 随机点击几个链接，增加信任度
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            random_links = random.sample([link for link in links if link['href'].startswith('/') and len(link['href']) > 1], min(3, len(links)))
            
            for link in random_links:
                self.random_delay()
                self.update_headers()
                link_url = urljoin(home_url, link['href'])
                self.session.headers['Referer'] = home_url
                
                try:
                    sub_response = self.session.get(link_url, timeout=30, verify=False)
                    print(f"访问链接: {link_url}, 状态码: {sub_response.status_code}")
                except Exception as e:
                    print(f"访问链接失败: {str(e)}")
                
            return True
        except Exception as e:
            print(f"预热失败: {str(e)}")
            return False
    
    def download_year_monthly_data(self, year=2015):
        """下载指定年份每个月的CVE数据"""
        print(f"开始下载{year}年的CVE数据...")
        
        # 预热网站
        if not self.warmup():
            print("预热失败，尝试直接继续...")
        
        try:
            # 访问主页面
            base_url = 'https://www.cvedetails.com/browse-by-date.php'
            self.update_headers()
            self.session.headers['Referer'] = 'https://www.cvedetails.com/'
            
            print(f"访问主页面: {base_url}")
            response = self.session.get(base_url, timeout=30, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找指定年份的部分
            year_section_id = f"container_{year}"
            print(f"查找{year}年数据部分: {year_section_id}")
            
            year_section = soup.find('div', id=year_section_id)
            if not year_section:
                # 如果直接查找ID失败，尝试其他方式
                print(f"未通过ID找到{year}年的数据部分，尝试其他方式...")
                
                # 尝试查找包含年份文本的div
                year_divs = soup.find_all('div', class_=lambda x: x and 'container' in x)
                for div in year_divs:
                    if str(year) in div.text:
                        year_section = div
                        break
            
            if not year_section:
                print(f"未找到{year}年的数据部分")
                return False
            
            # 获取所有月份的链接
            print("查找所有月份的链接...")
            month_links = []
            
            # 查找所有<a>标签
            links = year_section.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and 'date=' in href:
                    month_name = link.text.strip()
                    # 提取月份数字
                    month_num = self._get_month_number(month_name)
                    if month_num:
                        full_url = urljoin(base_url, href)
                        month_links.append((month_num, full_url))
            
            if not month_links:
                print(f"未找到{year}年各月份的链接")
                return False
            
            # 按月份排序
            month_links.sort(key=lambda x: x[0])
            
            print(f"找到{len(month_links)}个月份的链接")
            
            # 下载每个月的数据
            for month_num, month_url in month_links:
                # 构建文件名，例如201501.tsv
                file_name = f"{year}{month_num:02d}.tsv"
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                
                # 检查文件是否已存在
                if os.path.exists(file_path):
                    print(f"文件{file_name}已存在，跳过下载")
                    continue
                
                print(f"正在处理{year}年{month_num}月的数据...")
                
                # 随机延迟
                self.random_delay(3, 7)
                
                # 访问月份页面
                self.update_headers()
                self.session.headers['Referer'] = base_url
                
                try:
                    response = self.session.get(month_url, timeout=30, verify=False)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 尝试找到export按钮链接
                    export_link = None
                    
                    # 尝试多种方式查找export链接
                    # 1. 通过文本内容查找
                    export_links = soup.find_all('a', string=lambda text: text and ('Export' in text or 'export' in text))
                    for link in export_links:
                        href = link.get('href')
                        if href and ('tsv' in href or 'tab' in href):
                            export_link = urljoin(base_url, href)
                            break
                    
                    # 2. 通过href包含特定关键词查找
                    if not export_link:
                        export_links = soup.find_all('a', href=lambda href: href and 'export' in href and 'tsv' in href)
                        if export_links:
                            export_link = urljoin(base_url, export_links[0].get('href'))
                    
                    # 3. 通过class查找
                    if not export_link:
                        export_links = soup.find_all('a', class_=lambda x: x and 'export' in x)
                        for link in export_links:
                            href = link.get('href')
                            if href and ('tsv' in href or 'tab' in href):
                                export_link = urljoin(base_url, href)
                                break
                    
                    if not export_link:
                        print(f"未找到{year}年{month_num}月的export链接")
                        continue
                    
                    print(f"找到export链接: {export_link}")
                    
                    # 随机延迟
                    self.random_delay(2, 4)
                    
                    # 下载TSV文件
                    self.update_headers()
                    self.session.headers['Referer'] = month_url
                    
                    print(f"开始下载文件: {file_name}")
                    response = self.session.get(export_link, timeout=60, verify=False, stream=True)
                    response.raise_for_status()
                    
                    # 保存文件
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"成功下载并保存至{file_name}，文件大小: {os.path.getsize(file_path)}字节")
                    
                    # 保存cookie
                    self.session.cookies.save(ignore_discard=True)
                except Exception as e:
                    print(f"处理{year}年{month_num}月数据时出错: {str(e)}")
                    # 清理未完成的文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # 如果是403错误，尝试更激进的反反爬虫措施
                    if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
                        print("遇到403 Forbidden，尝试更换IP或稍后再试")
                        # 增加延迟
                        self.random_delay(10, 15)
                        # 重新预热
                        self.warmup()
            
            print(f"{year}年所有月份的数据下载完成")
            return True
        except Exception as e:
            print(f"下载过程中发生错误: {str(e)}")
            return False
    
    def _get_month_number(self, month_name):
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

def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    
    print("CVE Details数据下载器启动 (增强版)")
    print(f"下载目录: {DOWNLOAD_DIR}")
    
    # 创建下载器实例
    downloader = CveDetailsEnhancedDownloader()
    
    # 下载2015年的数据
    success = downloader.download_year_monthly_data(year=2015)
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        print(f"下载任务完成！总耗时: {duration}")
    else:
        print(f"下载任务失败！总耗时: {duration}")

if __name__ == "__main__":
    main()