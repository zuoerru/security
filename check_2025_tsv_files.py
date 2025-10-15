#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义要检查的文件列表
FILES_TO_CHECK = [
    '202501.tsv',
    '202502.tsv',
    '202503.tsv',
    '202504.tsv',
    '202505.tsv',
    '202506.tsv',
    '202507.tsv',
    '202508.tsv',
    '202509.tsv',
    '202510.tsv'
]

# 定义数据目录
DATA_DIR = '/data_nfs/121/app/security'


def check_file_exists(file_path):
    """检查文件是否存在"""
    return os.path.isfile(file_path)


def get_file_size(file_path):
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return -1

def count_records_in_tsv(file_path):
    """计算TSV文件中的记录数"""
    try:
        # 使用pandas读取TSV文件
        df = pd.read_csv(file_path, sep='\t', header=None, on_bad_lines='skip')
        return len(df)
    except Exception as e:
        logger.error(f"读取文件 {file_path} 时出错: {e}")
        return -1

def count_records_line_by_line(file_path):
    """使用逐行读取的方式计算记录数，处理大文件"""
    try:
        count = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for _ in f:
                count += 1
        return count
    except Exception as e:
        logger.error(f"逐行读取文件 {file_path} 时出错: {e}")
        return -1

def check_file_structure(file_path):
    """检查文件的列数和前几行内容"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            first_line = f.readline().strip()
            columns = first_line.split('\t')
            return len(columns)
    except Exception as e:
        logger.error(f"检查文件结构 {file_path} 时出错: {e}")
        return -1

def main():
    """主函数"""
    logger.info("开始检查2025年TSV文件...")
    total_records = 0
    file_results = []
    
    # 遍历所有要检查的文件
    for file_name in FILES_TO_CHECK:
        file_path = os.path.join(DATA_DIR, file_name)
        result = {
            'file_name': file_name,
            'exists': False,
            'size_bytes': 0,
            'record_count': 0,
            'column_count': 0,
            'status': '未找到'
        }
        
        if check_file_exists(file_path):
            result['exists'] = True
            result['size_bytes'] = get_file_size(file_path)
            result['column_count'] = check_file_structure(file_path)
            
            # 如果文件较小，使用pandas读取；如果文件较大，使用逐行读取
            if result['size_bytes'] < 10 * 1024 * 1024:  # 小于10MB的文件
                result['record_count'] = count_records_in_tsv(file_path)
            else:
                result['record_count'] = count_records_line_by_line(file_path)
            
            if result['record_count'] >= 0:
                total_records += result['record_count']
                result['status'] = '正常'
            else:
                result['status'] = '读取错误'
        
        file_results.append(result)
    
    # 输出检查结果
    print("\n===== 2025年TSV文件检查结果 =====")
    print(f"{'文件名':<12}{'是否存在':<10}{'文件大小(KB)':<15}{'记录数':<10}{'列数':<10}{'状态':<10}")
    print("=" * 70)
    
    for result in file_results:
        size_kb = round(result['size_bytes'] / 1024, 2) if result['size_bytes'] >= 0 else 'N/A'
        print(f"{result['file_name']:<12}{'是' if result['exists'] else '否':<10}{size_kb:<15}{result['record_count'] if result['record_count'] >= 0 else 'N/A':<10}{result['column_count'] if result['column_count'] >= 0 else 'N/A':<10}{result['status']:<10}")
    
    print("=" * 70)
    print(f"总计记录数: {total_records}")
    print(f"MySQL数据库nvd表记录数: 104664")
    print("\n数据量对比分析:")
    
    if total_records == 0:
        print("警告: 未找到有效的2025年TSV文件记录。")
    elif abs(total_records - 104664) < 100:  # 允许100条以内的误差
        print("数据量基本一致，MySQL中的数据录入正确。")
    else:
        print(f"数据量不一致，MySQL记录数与文件记录数相差: {abs(total_records - 104664)}条")
    
    logger.info("文件检查完成")


if __name__ == "__main__":
    main()