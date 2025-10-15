#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用Selenium从cvedetails.com下载2015年每个月的CVE数据"""

import os
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from urllib.parse import urljoin

# 下载目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = BASE_DIR

class CveDetailsSeleniumDownloader:
    @staticmethod
    def setup_driver():
        """设置Selenium WebDriver"""
        print("正在初始化浏览器...")
        
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # 添加用户代理
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # 禁用自动化特征
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 初始化WebDriver，使用webdriver-manager自动管理
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # 进一步隐藏自动化特征
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 设置隐式等待
        driver.implicitly_wait(10)
        
        print("浏览器初始化完成")
        return driver
    
    @staticmethod
    def random_delay(min_seconds=2, max_seconds=5):
        """添加随机延迟，模拟真实用户行为"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def download_year_monthly_data(year=2015):
        """使用Selenium下载指定年份每个月的CVE数据"""
        print(f"开始下载{year}年的CVE数据...")
        
        driver = None
        try:
            # 初始化WebDriver
            driver = CveDetailsSeleniumDownloader.setup_driver()
            
            # 访问主页面
            base_url = 'https://www.cvedetails.com/browse-by-date.php'
            print(f"访问主页面: {base_url}")
            driver.get(base_url)
            CveDetailsSeleniumDownloader.random_delay()
            
            # 查找指定年份的部分
            year_section_id = f"container_{year}"
            print(f"查找{year}年数据部分: {year_section_id}")
            
            try:
                # 等待年份部分加载完成
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, year_section_id))
                )
            except TimeoutException:
                print(f"超时: 未找到{year}年的数据部分")
                return False
            
            year_section = driver.find_element(By.ID, year_section_id)
            
            # 获取所有月份的链接
            print("查找所有月份的链接...")
            month_links = []
            
            # 查找所有<a>标签
            links = year_section.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href')
                if href and 'date=' in href:
                    month_name = link.text.strip()
                    # 提取月份数字
                    month_num = CveDetailsSeleniumDownloader._get_month_number(month_name)
                    if month_num:
                        month_links.append((month_num, href))
            
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
                
                # 访问月份页面
                driver.get(month_url)
                CveDetailsSeleniumDownloader.random_delay(3, 7)
                
                # 尝试找到export按钮
                export_button = None
                try:
                    # 尝试多种方式查找export按钮
                    # 1. 通过文本内容查找
                    export_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Export') or contains(text(), 'export')]")
                    for btn in export_buttons:
                        if 'tsv' in btn.get_attribute('href').lower():
                            export_button = btn
                            break
                    
                    # 2. 通过class查找
                    if not export_button:
                        export_buttons = driver.find_elements(By.XPATH, "//a[contains(@class, 'export')]")
                        for btn in export_buttons:
                            if 'tsv' in btn.get_attribute('href').lower():
                                export_button = btn
                                break
                    
                    # 3. 通过href包含特定关键词查找
                    if not export_button:
                        export_buttons = driver.find_elements(By.XPATH, "//a[contains(@href, 'export') and contains(@href, 'tsv')]")
                        if export_buttons:
                            export_button = export_buttons[0]
                except Exception as e:
                    print(f"查找export按钮时出错: {str(e)}")
                
                if not export_button:
                    print(f"未找到{year}年{month_num}月的export按钮")
                    continue
                
                # 获取export链接
                export_url = export_button.get_attribute('href')
                print(f"找到export链接: {export_url}")
                
                # 使用requests下载文件（Selenium下载可能不稳定）
                # 获取当前cookie
                cookies = driver.get_cookies()
                session = requests.Session()
                
                # 添加cookie到session
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                
                # 添加请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
                    'Referer': month_url,
                }
                
                try:
                    # 下载文件
                    print(f"开始下载文件: {file_name}")
                    response = session.get(export_url, headers=headers, timeout=60, stream=True)
                    response.raise_for_status()
                    
                    # 保存文件
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"成功下载并保存至{file_name}，文件大小: {os.path.getsize(file_path)}字节")
                except Exception as e:
                    print(f"下载{year}年{month_num}月数据时出错: {str(e)}")
                    # 清理未完成的文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                # 添加随机延迟
                CveDetailsSeleniumDownloader.random_delay(5, 10)
            
            print(f"{year}年所有月份的数据下载完成")
            return True
        except Exception as e:
            print(f"下载过程中发生错误: {str(e)}")
            return False
        finally:
            # 关闭浏览器
            if driver:
                driver.quit()
                print("浏览器已关闭")
    
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

def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    
    print("CVE Details数据下载器启动 (Selenium版本)")
    print(f"下载目录: {DOWNLOAD_DIR}")
    
    # 下载2015年的数据
    success = CveDetailsSeleniumDownloader.download_year_monthly_data(year=2015)
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        print(f"下载任务完成！总耗时: {duration}")
    else:
        print(f"下载任务失败！总耗时: {duration}")

if __name__ == "__main__":
    main()