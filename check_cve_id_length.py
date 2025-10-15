#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# 文件路径
TSV_FILE = '/data_nfs/121/app/security/201707.tsv'

# 要查看的行范围
START_ROW = 745
END_ROW = 755

def check_cve_id_length():
    """检查TSV文件中特定行的cve_id字段长度"""
    try:
        print(f"正在检查文件: {TSV_FILE}")
        print(f"查看行范围: {START_ROW} 到 {END_ROW}")
        
        with open(TSV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 获取文件头
            header = lines[0].strip().split('\t')
            print(f"文件头: {header}")
            
            # 查找cve_id列的索引
            cve_id_index = -1
            for i, col in enumerate(header):
                if 'CVE' in col.upper():
                    cve_id_index = i
                    break
            
            if cve_id_index == -1:
                print("未找到CVE ID列")
                return
            
            print(f"CVE ID列索引: {cve_id_index}")
            
            # 检查指定范围内的行
            for i in range(max(1, START_ROW), min(len(lines), END_ROW + 1)):
                line = lines[i].strip()
                if not line:
                    continue
                
                # 分割行数据
                parts = line.split('\t')
                
                # 确保有足够的字段
                if len(parts) <= cve_id_index:
                    print(f"第{i}行: 字段数不足，跳过")
                    continue
                
                # 获取cve_id并计算长度
                cve_id = parts[cve_id_index]
                cve_id_length = len(cve_id)
                
                print(f"第{i}行: CVE ID = '{cve_id}', 长度 = {cve_id_length}")
                
                # 如果长度特别长，特别标记
                if cve_id_length > 50:
                    print(f"⚠️ 警告: 第{i}行的CVE ID长度为{cve_id_length}，超过了50个字符")
        
    except Exception as e:
        print(f"检查文件时出错: {e}")

if __name__ == "__main__":
    check_cve_id_length()