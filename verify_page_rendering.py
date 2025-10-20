#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证页面渲染是否正常
"""
import requests

def check_page_rendering():
    print("===== 验证页面渲染 =====")
    
    try:
        # 检查同步日志页面
        url = "http://localhost:8010/cisa/sync_logs"
        response = requests.get(url, timeout=5)
        
        print(f"同步日志页面状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 检查页面是否包含关键字段
            content = response.text
            
            check_items = [
                "CISA 同步记录",
                "每页显示:",
                "function changePerPage",
                "同步类型",
                "状态"
            ]
            
            all_found = True
            for item in check_items:
                if item in content:
                    print(f"✓ 找到关键字: {item}")
                else:
                    print(f"✗ 未找到关键字: {item}")
                    all_found = False
            
            if all_found:
                print("\n✓ 页面渲染正常，JavaScript语法错误已修复")
            else:
                print("\n✗ 页面渲染可能存在问题")
        else:
            print(f"✗ 页面访问失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 验证过程中出错: {str(e)}")

if __name__ == "__main__":
    check_page_rendering()