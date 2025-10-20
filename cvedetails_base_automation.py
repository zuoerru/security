#!/usr/bin/env python3
"""
Playwright自动化访问cvedetails.com参考脚本
"""

from playwright.sync_api import sync_playwright
import time

def run_automation():
    with sync_playwright() as p:
        # 选择浏览器（firefox、chromium或webkit）
        browser = p.firefox.launch(
            headless=False,  # 设置为True可以在无头模式下运行
            slow_mo=100,     # 放慢操作速度，便于观察
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # 创建新页面
        page = browser.new_page()
        
        # 设置用户代理
        page.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
        
        # 导航到cvedetails.com
        print("正在访问 https://www.cvedetails.com...")
        page.goto("https://www.cvedetails.com", wait_until="networkidle")
        
        # 等待Cloudflare验证完成
        time.sleep(5)  # 根据实际情况调整等待时间
        
        # 在这里添加您需要自动化的操作
        # 例如:
        # page.click("selector") - 点击元素
        # page.fill("selector", "value") - 填写表单
        # page.wait_for_load_state("networkidle") - 等待页面加载完成
        
        # 操作完成后的等待时间
        time.sleep(3)
        
        # 关闭浏览器
        browser.close()
        
        print("自动化操作完成")

if __name__ == "__main__":
    run_automation()
