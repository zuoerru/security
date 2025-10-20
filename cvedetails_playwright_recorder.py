#!/usr/bin/env python3
"""
使用Playwright记录在cvedetails.com上的操作
"""

import sys
import asyncio
from playwright.async_api import async_playwright
import time
import os

def generate_automation_script(actions):
    """根据记录的操作生成自动化脚本"""
    script = '''#!/usr/bin/env python3
"""
使用Playwright自动化访问cvedetails.com
此脚本是通过录制您的操作自动生成的
"""

from playwright.sync_api import sync_playwright
import time

def run_automation():
    with sync_playwright() as p:
        # 启动浏览器
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
        
        # 自动化操作部分
'''
    
    # 添加记录的操作
    for action in actions:
        script += f"        {action}\n"
        script += "        time.sleep(1)  # 操作间的等待时间\n"
    
    # 添加结束部分
    script += '''
        # 操作完成后的等待时间
        time.sleep(3)
        
        # 关闭浏览器
        browser.close()
        
        print("自动化操作完成")

if __name__ == "__main__":
    run_automation()
'''
    
    return script

def generate_base_script():
    """生成基础参考脚本"""
    return '''#!/usr/bin/env python3
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
'''

async def main():
    print("===== Playwright录制工具 - cvedetails.com ======")
    print("注意：当前系统可能缺少一些Playwright所需的依赖库")
    print("如果遇到问题，请查看输出的错误信息并尝试安装缺失的依赖")
    print("\n尝试启动Playwright浏览器...\n")
    
    try:
        # 启动Playwright并创建浏览器实例
        async with async_playwright() as p:
            # 尝试使用Firefox浏览器
            try:
                browser = await p.firefox.launch(
                    headless=False,  # 显示浏览器窗口，让用户可以操作
                    slow_mo=100,     # 放慢操作速度，便于观察
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
            except Exception as e:
                print(f"无法启动Firefox浏览器: {e}")
                print("尝试使用Chromium浏览器...")
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=100,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
            
            # 创建新页面
            page = await browser.new_page()
            
            # 设置用户代理，避免被识别为机器人
            await page.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
            
            # 导航到cvedetails.com
            print("正在访问 https://www.cvedetails.com...")
            try:
                await page.goto("https://www.cvedetails.com", wait_until="networkidle")
                print("页面加载完成")
            except Exception as e:
                print(f"访问页面时出错: {e}")
                print("可能遇到了Cloudflare验证，请在浏览器中手动完成验证")
            
            # 等待用户操作完成
            print("\n===== 录制说明 =====")
            print("1. 在打开的浏览器窗口中执行您需要自动化的操作")
            print("2. 完成所有操作后，请不要关闭浏览器，返回终端按Enter键继续")
            print("3. 系统将生成自动化脚本并保存到当前目录")
            print("\n按Enter键开始记录您的操作...")
            
            # 等待用户开始操作
            input()
            
            print("\n开始记录您的操作...")
            print("请在浏览器中执行您的操作...")
            
            # 记录开始时间
            start_time = time.time()
            
            # 收集所有操作的列表
            actions = []
            
            # 监听页面事件
            async def handle_click(event):
                selector = await event.target.selector()
                if selector:
                    actions.append(f"page.click('{selector}')")
                    print(f"记录点击: {selector}")
            
            async def handle_fill(event):
                selector = await event.target.selector()
                if selector:
                    value = await event.target.get_attribute('value')
                    if value:
                        actions.append(f"page.fill('{selector}', '{value}')")
                        print(f"记录填写: {selector} = {value}")
            
            # 注册事件监听器
            page.on("click", handle_click)
            page.on("input", handle_fill)
            
            # 等待用户完成操作
            print("\n完成所有操作后，请按Enter键结束录制...")
            input()
            
            # 计算录制时间
            end_time = time.time()
            print(f"\n录制完成，耗时: {end_time - start_time:.2f}秒")
            print(f"记录了 {len(actions)} 个操作")
            
            # 生成自动化脚本
            script_content = generate_automation_script(actions)
            
            # 保存脚本
            script_path = "cvedetails_automation.py"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            print(f"\n自动化脚本已保存到: {script_path}")
            print("您可以直接运行这个脚本来自动化执行您刚才的操作")
            print("\n注意：生成的脚本可能需要根据实际情况进行调整")
            
            # 关闭浏览器
            await browser.close()
            
    except Exception as e:
        print(f"\n运行时出错: {e}")
        print("\n===== 替代方案 ======")
        print("由于系统依赖问题，无法直接运行Playwright浏览器。")
        print("您可以使用以下命令在支持的环境中启动Playwright录制器：")
        print("   python -m playwright codegen https://www.cvedetails.com")
        print("\n或者，您可以尝试安装缺失的系统依赖：")
        print("   sudo dnf install -y libwebp enchant-2 libsecret hyphen libffi mesa-libGLES x264-libs")
        print("\n如果这些方法都不行，我们已经为您生成了一个基础脚本供参考。")
        
        # 生成基础参考脚本
        base_script = generate_base_script()
        base_script_path = "cvedetails_base_automation.py"
        with open(base_script_path, "w", encoding="utf-8") as f:
            f.write(base_script)
        
        print(f"基础参考脚本已保存到: {base_script_path}")


if __name__ == "__main__":
    asyncio.run(main())