#!/usr/bin/env python3
"""
使用requests库访问cvedetails.com的工具
此工具不依赖浏览器和图形界面，适合在服务器环境中使用
"""

import sys
import os
import time
import requests
from datetime import datetime
from requests.exceptions import RequestException

print("===== cvedetails.com 无浏览器访问工具 =====")
print("注意：此工具使用requests库直接访问网页，无需浏览器和图形界面")
print("注意：由于Cloudflare保护，直接访问可能会被拦截")

# 显示菜单选项
def show_menu():
    print("\n请选择操作模式：")
    print("1. 使用requests访问cvedetails.com")
    print("2. 查看Playwright录制器命令")
    print("3. 生成基础自动化脚本")
    print("4. 退出")
    
    choice = input("请输入选择 [1-4]: ")
    return choice

# 使用requests访问cvedetails.com
def try_requests_access():
    print("\n===== 尝试使用requests访问cvedetails.com =====")
    print("这将使用requests库直接发送HTTP请求")
    print("注意：由于Cloudflare保护，这种方法很可能会被拦截")
    
    try:
        # 设置请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        print("正在发送请求...")
        response = requests.get("https://www.cvedetails.com", headers=headers, timeout=30)
        
        # 检查响应状态
        if response.status_code == 200:
            print(f"请求成功，状态码: {response.status_code}")
            
            # 保存页面内容
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            page_path = f"cvedetails_requests_page_{timestamp}.html"
            
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"页面内容已保存到: {page_path}")
            
            # 检查是否包含Cloudflare验证相关内容
            if "cloudflare" in response.text.lower():
                print("警告：页面包含Cloudflare验证内容，访问可能受到限制")
                print("建议使用以下方法：")
                print("1. 在有图形界面的环境中使用Playwright录制器")
                print("2. 使用浏览器手动访问并导出Cookie用于自动化")
            else:
                print("成功访问页面！您可以分析页面内容并提取所需信息。")
                
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print("这很可能是由于Cloudflare保护机制导致的")
            print("\n===== 解决方案建议 =====")
            print("1. 在有图形界面的环境中使用Playwright录制器:")
            print("   python -m playwright codegen https://www.cvedetails.com")
            print("2. 使用Selenium或Puppeteer配合无头浏览器")
            print("3. 考虑使用API或其他数据源获取CVE信息")
            
            # 保存错误页面内容
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            error_path = f"cvedetails_error_{timestamp}.html"
            
            with open(error_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"错误页面内容已保存到: {error_path}")
            
    except ImportError:
        print("错误：未安装requests库。请运行以下命令安装：")
        print("   pip install requests")
    except RequestException as e:
        print(f"请求时出错: {e}")
        print("\n===== 解决方案建议 =====")
        print("1. 检查网络连接和防火墙设置")
        print("2. 在有图形界面的环境中使用Playwright录制器")
        print("3. 尝试使用其他网络或代理服务器")
    except Exception as e:
        print(f"运行时出错: {e}")

# 显示Playwright录制器命令
def show_recorder_command():
    print("\n===== Playwright录制器命令 =====")
    print("要在有图形界面的环境中录制操作，请使用以下命令：")
    print("\n   python -m playwright codegen https://www.cvedetails.com")
    print("\n这个命令会打开一个浏览器窗口，您可以在其中执行操作，")
    print("同时Playwright会自动记录这些操作并生成相应的Python代码。")
    print("\n注意：您需要在有图形界面的环境中运行此命令。")
    print("如果您现在没有图形界面，可以将此命令保存下来，稍后在支持的环境中使用。")
    print("\n录制完成后，您可以将生成的脚本复制到当前环境中，并将headless参数设置为True。")

# 生成基础自动化脚本
def generate_base_script():
    script = '''#!/usr/bin/env python3
"""
使用requests库访问cvedetails.com的基础脚本
"""

import requests
import time

# 设置请求头，模拟浏览器
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def main():
    try:
        print("正在访问 https://www.cvedetails.com...")
        response = requests.get("https://www.cvedetails.com", headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"请求成功，状态码: {response.status_code}")
            
            # 在这里处理页面内容
            # 例如：提取特定的CVE信息
            # 由于Cloudflare保护，直接解析可能会遇到困难
            
            # 保存页面内容
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            page_path = f"cvedetails_page_{timestamp}.html"
            
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"页面内容已保存到: {page_path}")
            
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print("这很可能是由于Cloudflare保护机制导致的")
            
    except Exception as e:
        print(f"运行时出错: {e}")

if __name__ == "__main__":
    main()
'''
    
    # 保存脚本
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    script_path = f"cvedetails_requests_script_{timestamp}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    
    print(f"\n基础requests脚本已保存到: {script_path}")
    print("您可以编辑此脚本，添加您需要的数据提取和处理逻辑。")
    print("请注意，由于Cloudflare保护，直接访问可能会受到限制。")

# 主程序
def main():
    while True:
        choice = show_menu()
        
        if choice == '1':
            try_requests_access()
        elif choice == '2':
            show_recorder_command()
        elif choice == '3':
            generate_base_script()
        elif choice == '4':
            print("\n感谢使用cvedetails.com访问工具，再见！")
            break
        else:
            print("无效的选择，请重新输入。")

if __name__ == "__main__":
    main()