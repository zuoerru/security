#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from collections import Counter

"""分析TSV文件中的Unicode字符编码问题"""

def analyze_file(file_path):
    """分析指定文件中的Unicode字符问题"""
    print(f"\n正在分析文件: {file_path}")
    print("=" * 80)
    
    problematic_lines = []
    non_ascii_chars = Counter()
    total_lines = 0
    problematic_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline()  # 跳过表头
            total_lines += 1
            
            for line_number, line in enumerate(f, 2):  # 行号从2开始
                total_lines += 1
                
                # 检查是否是CVE记录
                if not line.strip().startswith('CVE'):
                    continue
                
                # 检查是否包含非ASCII字符
                has_non_ascii = False
                problematic_chars = []
                
                for char in line:
                    if ord(char) > 127:  # ASCII字符范围是0-127
                        has_non_ascii = True
                        # 使用0x前缀而不是\u转义序列
                        char_info = f"{char} (0x{ord(char):04x})"
                        problematic_chars.append(char_info)
                        non_ascii_chars[char] += 1
                
                if has_non_ascii:
                    # 尝试使用当前的clean_text函数处理
                    cleaned_line = clean_text(line)
                    
                    # 检查清理后是否还有非ASCII字符
                    still_has_non_ascii = any(ord(char) > 127 for char in cleaned_line)
                    
                    # 只收集包含潜在问题的行
                    fields = line.strip().split('\t')
                    if len(fields) > 0:
                        cve_id = fields[0] if fields[0].startswith('CVE') else 'N/A'
                        problematic_lines.append({
                            'line_number': line_number,
                            'cve_id': cve_id,
                            'problematic_chars': problematic_chars,
                            'still_has_non_ascii': still_has_non_ascii
                        })
                        problematic_count += 1
                    
                # 为了性能，只分析前5000行
                if line_number > 5000:
                    break
        
        # 输出分析结果
        print(f"文件总行数: {total_lines}")
        print(f"包含非ASCII字符的CVE记录数: {problematic_count}")
        print("\n最常见的非ASCII字符:")
        for char, count in non_ascii_chars.most_common(20):
            print(f"{char} (0x{ord(char):04x}): {count}次")
        
        # 显示前5条有问题的记录示例
        if problematic_lines:
            print("\n前5条包含非ASCII字符的记录示例:")
            for item in problematic_lines[:5]:
                print(f"行号: {item['line_number']}")
                print(f"CVE ID: {item['cve_id']}")
                print(f"问题字符: {', '.join(item['problematic_chars'][:5])}{'...' if len(item['problematic_chars']) > 5 else ''}")
                print(f"清理后仍有非ASCII字符: {item['still_has_non_ascii']}")
                print("-")
        
    except Exception as e:
        print(f"分析文件时出错: {e}")

# 从import_202501_tsv.py复制的clean_text函数
# 用于比较清理前后的效果
def clean_text(text):
    if not text:
        return text
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or ord(char) in (9, 10, 13))
    # 移除不可打印字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text

# 增强版的clean_text函数，尝试处理更多Unicode字符问题
def enhanced_clean_text(text):
    if not text:
        return text
    # 基础清理
    text = ''.join(char for char in text if ord(char) >= 32 or ord(char) in (9, 10, 13))
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 替换常见的全角字符为半角字符
    full_to_half = {
        '，': ',', '。': '.', '！': '!', '？': '?',
        '：': ':', '；': ';', '“': '"', '”': '"',
        '‘': "'", '’': "'", '（': '(', '）': ')',
        '【': '[', '】': ']', '《': '<', '》': '>',
        '「': '[', '」': ']', '『': '[', '』': ']',
        '、': ',', '—': '-', '～': '~', '…': '...',
        '　': ' ',  # 全角空格
    }
    
    for full_char, half_char in full_to_half.items():
        text = text.replace(full_char, half_char)
    
    return text

def main():
    """主函数"""
    print("Unicode字符编码问题分析工具")
    print("此工具将分析TSV文件中的非ASCII字符，并找出可能导致MySQL导入错误的字符")
    
    # 分析202501.tsv文件
    file_path = '/data_nfs/121/app/security/202501.tsv'
    if os.path.exists(file_path):
        analyze_file(file_path)
    else:
        print(f"错误: 文件 {file_path} 不存在")
        return
    
    print("\n" + "=" * 80)
    print("\n编码问题原因分析:")
    print("1. MySQL的utf8mb4字符集虽然支持大部分Unicode字符，但仍有一些特殊字符可能导致问题")
    print("2. 常见问题字符包括:")
    print("   - 非拉丁字母(如希腊文、斯拉夫文、亚洲文字等)")
    print("   - 特殊标点符号和符号字符")
    print("   - 组合字符和变音符号")
    print("   - 控制字符和不可打印字符")
    print("3. 当前的clean_text函数主要移除控制字符，但对一些特殊的可见Unicode字符可能无效")
    
    print("\n解决方案建议:")
    print("1. 修改clean_text函数，添加更多字符转换规则")
    print("2. 使用enhanced_clean_text函数(本脚本中已提供)进行更全面的字符处理")
    print("3. 对于无法转换的字符，可以选择替换为相似的ASCII字符或完全移除")
    print("4. 在导入前对文件进行预处理，将特殊字符转换为安全的形式")
    print("5. 考虑使用base64编码存储包含特殊字符的字段")

if __name__ == "__main__":
    main()