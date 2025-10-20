#!/usr/bin/env python3
"""
在无图形界面环境中访问cvedetails.com的自动化工具
此工具提供多种解决方案，适应不同的环境限制
"""

import sys
import os
import time

print("===== cvedetails.com 无图形界面自动化工具 =====")
print("注意：当前环境可能缺少图形界面(X server)，我们提供多种解决方案")

# 显示菜单选项
def show_menu():
    print("\n请选择操作模式：")
    print("1. 尝试使用无头模式访问cvedetails.com")
    print("2. 查看Playwright录制器命令")
    print("3. 生成基础自动化脚本")
    print("4. 退出")
    
    choice = input("请输入选择 [1-4]: ")
    return choice

# 尝试使用无头模式访问cvedetails.com
def try_headless_mode():
    print("\n===== 尝试使用无头模式访问cvedetails.com =====")
    print("这将使用Firefox的无头模式尝试访问cvedetails.com")
    print("注意：由于Cloudflare保护，这种方法可能会失败")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            print("启动无头Firefox浏览器...")
            browser = p.firefox.launch(
                headless=True,  # 使用无头模式
                slow_mo=100,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            page = browser.new_page()
            
            # 设置用户代理
            page.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
            
            print("正在访问 https://www.cvedetails.com...")
            page.goto("https://www.cvedetails.com", wait_until="networkidle", timeout=30000)
            
            # 保存页面内容，检查是否成功访问
            page_content = page.content()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            page_path = f"cvedetails_headless_page_{timestamp}.html"
            
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(page_content)
            
            print(f"页面内容已保存到: {page_path}")
            
            # 检查是否包含Cloudflare验证相关内容
            if "cloudflare" in page_content.lower():
                print("警告：页面可能包含Cloudflare验证，自动化访问可能失败")
                print("建议使用以下方法：")
                print("1. 在有图形界面的环境中使用Playwright录制器")
                print("2. 使用浏览器手动访问并导出Cookie用于自动化")
            else:
                print("成功访问页面！可以尝试添加自动化操作。")
                
            browser.close()
            
    except ImportError:
        print("错误：未安装Playwright。请运行以下命令安装：")
        print("   pip install playwright")
        print("   playwright install")
    except Exception as e:
        print(f"运行时出错: {e}")
        print("\n===== 解决方案建议 =====")
        print("1. 安装Playwright系统依赖:")
        print("   sudo dnf install -y libwebp enchant-2 libsecret hyphen libffi mesa-libGLES x264-libs")
        print("2. 使用Playwright录制器命令在有图形界面的环境中:")
        print("   python -m playwright codegen https://www.cvedetails.com")
        print("3. 使用其他工具如Selenium或Puppeteer")

# 显示Playwright录制器命令
def show_recorder_command():
    print("\n===== Playwright录制器命令 =====")
    print("要在有图形界面的环境中录制操作，请使用以下命令：")
    print("\n   python -m playwright codegen https://www.cvedetails.com")
    print("\n这个命令会打开一个浏览器窗口，您可以在其中执行操作，")
    print("同时Playwright会自动记录这些操作并生成相应的Python代码。")
    print("\n注意：您需要在有图形界面的环境中运行此命令。")
    print("如果您现在没有图形界面，可以将此命令保存下来，稍后在支持的环境中使用。")

# 生成基础自动化脚本
def generate_base_script():
    script = '''#!/usr/bin/env python3
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
        
        # 等待Cloudflare验证完成（如果需要）
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
    
    # 保存脚本
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    script_path = f"cvedetails_base_automation_{timestamp}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    
    print(f"\n基础自动化脚本已保存到: {script_path}")
    print("您可以编辑此脚本，添加您需要的自动化操作。")
    print("请将您在浏览器中执行的操作转换为相应的Playwright API调用。")

# 主程序
def main():
    while True:
        choice = show_menu()
        
        if choice == '1':
            try_headless_mode()
        elif choice == '2':
            show_recorder_command()
        elif choice == '3':
            generate_base_script()
        elif choice == '4':
            print("\n感谢使用cvedetails.com自动化工具，再见！")
            break
        else:
            print("无效的选择，请重新输入。")

if __name__ == "__main__":
    main()