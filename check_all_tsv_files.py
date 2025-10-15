#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义数据目录
DATA_DIR = '/data_nfs/121/app/security'


def check_file_exists(file_path):
    """检查文件是否存在"""
    return os.path.isfile(file_path)


def count_records_line_by_line(file_path):
    """使用逐行读取的方式计算记录数，处理大文件"""
    try:
        count = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for _ in f:
                count += 1
        # 减去表头行
        return count - 1 if count > 0 else 0
    except Exception as e:
        logger.error(f"逐行读取文件 {file_path} 时出错: {e}")
        return -1


def get_cve_count(file_path):
    """计算文件中以CVE开头的记录数（模拟import_nvd_data.py的过滤逻辑）"""
    try:
        count = 0
        skipped = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            next(f)  # 跳过表头
            for line in f:
                if line.strip() and line.strip().startswith('CVE'):
                    count += 1
                else:
                    skipped += 1
        return count, skipped
    except Exception as e:
        logger.error(f"计算CVE记录数时出错 {file_path}: {e}")
        return -1, 0


def main():
    """主函数"""
    logger.info("开始检查所有年份的TSV文件...")
    
    # 按年份分组统计
    year_patterns = ['2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']
    year_results = {year: {'file_count': 0, 'total_records': 0, 'cve_records': 0, 'skipped_records': 0} for year in year_patterns}
    
    # 遍历所有文件
    for year in year_patterns:
        for month in range(1, 13):
            file_name = f"{year}{month:02d}.tsv"
            file_path = os.path.join(DATA_DIR, file_name)
            
            if check_file_exists(file_path):
                year_results[year]['file_count'] += 1
                
                # 计算总记录数（减去表头）
                total_records = count_records_line_by_line(file_path)
                if total_records >= 0:
                    year_results[year]['total_records'] += total_records
                
                # 计算符合条件的CVE记录数（模拟导入逻辑）
                cve_count, skipped = get_cve_count(file_path)
                if cve_count >= 0:
                    year_results[year]['cve_records'] += cve_count
                    year_results[year]['skipped_records'] += skipped
    
    # 计算总计
    total_all_files = sum(year_results[year]['file_count'] for year in year_patterns)
    total_all_records = sum(year_results[year]['total_records'] for year in year_patterns)
    total_cve_records = sum(year_results[year]['cve_records'] for year in year_patterns)
    total_skipped_records = sum(year_results[year]['skipped_records'] for year in year_patterns)
    
    # 输出检查结果
    print("\n===== 所有年份TSV文件检查结果 =====")
    print(f"{'年份':<8}{'文件数':<8}{'总记录数':<12}{'有效CVE记录数':<16}{'跳过记录数':<12}")
    print("=" * 60)
    
    for year in year_patterns:
        print(f"{year:<8}{year_results[year]['file_count']:<8}{year_results[year]['total_records']:<12}{year_results[year]['cve_records']:<16}{year_results[year]['skipped_records']:<12}")
    
    print("=" * 60)
    print(f"总计    {total_all_files:<8}{total_all_records:<12}{total_cve_records:<16}{total_skipped_records:<12}")
    print(f"\nMySQL数据库nvd表记录数: 104664")
    
    # 数据量对比分析
    print("\n数据量对比分析:")
    print(f"文件中所有有效CVE记录数: {total_cve_records}")
    print(f"MySQL数据库nvd表记录数: 104664")
    
    if abs(total_cve_records - 104664) < 100:  # 允许100条以内的误差
        print("数据量基本一致，MySQL中的数据录入正确。")
    else:
        print(f"数据量不一致，MySQL记录数与文件中有效CVE记录数相差: {abs(total_cve_records - 104664)}条")
        
        # 查找可能的原因
        if total_cve_records > 104664:
            print("可能的原因：MySQL数据库中存在重复的CVE ID，导入时被去重处理。")
        else:
            print("可能的原因：部分文件未能成功导入，或者导入过程中出现了错误。")
    
    logger.info("文件检查完成")


if __name__ == "__main__":
    main()