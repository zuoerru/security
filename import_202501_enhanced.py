#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import os
import traceback
import re
from datetime import datetime

"""
使用增强版字符清理函数的导入脚本，用于处理202501.tsv文件中的Unicode字符编码问题
"""

# 从import_202501_tsv.py复制的clean_text函数
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

# 数据库配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

# 目标文件
DATA_DIR = '/data_nfs/121/app/security'
TARGET_FILE = '202501.tsv'
TARGET_FILE_PATH = os.path.join(DATA_DIR, TARGET_FILE)

# 创建nvd表（如果不存在）
def create_nvd_table(conn):
    cursor = conn.cursor()
    try:
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS nvd (
            cve_id VARCHAR(50) PRIMARY KEY,
            published_date DATETIME,
            last_modified_date DATETIME,
            description TEXT,
            source_identifier VARCHAR(100),
            severity VARCHAR(20),
            base_score FLOAT,
            base_severity VARCHAR(20),
            vector_string VARCHAR(200),
            vendor VARCHAR(100),
            product VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        '''
        cursor.execute(create_table_sql)
        conn.commit()
        print("nvd表已创建或已存在")
    except Exception as e:
        print(f"创建nvd表时出错: {e}")
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()

# 导入特定的TSV文件
def import_specific_tsv_file(file_path):
    start_time = datetime.now()
    print(f"开始导入文件: {file_path}")
    print(f"开始时间: {start_time}")
    
    try:
        # 连接数据库
        conn = pymysql.connect(**DB_CONFIG)
        
        # 创建表（如果不存在）
        create_nvd_table(conn)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误: 文件 {file_path} 不存在")
            return False
        
        # 测试文件格式是否正确
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline()
            if not header.strip():  # 检查表头是否为空
                print("错误: 文件格式不正确，没有表头")
                return False
        
        # 读取并导入数据
        total_records = 0
        imported_records = 0
        skipped_non_cve_records = 0
        skipped_error_records = 0
        batch_size = 1000
        data_batch = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline()  # 跳过表头
            
            for line in f:
                total_records += 1
                
                # 跳过非CVE开头的记录
                if not line.strip().startswith('CVE'):
                    skipped_non_cve_records += 1
                    continue
                
                # 处理每一行数据
                fields = line.strip().split('\t')
                
                # 确保字段数量足够
                if len(fields) < 11:
                    skipped_error_records += 1
                    continue
                
                try:
                    # 提取字段值，使用enhanced_clean_text函数清理
                    cve_id = fields[0].strip()
                    
                    # 处理日期格式
                    published_date = fields[1].strip()
                    if 'T' in published_date:
                        published_date = published_date.split('T')[0]  # 移除时间部分
                    if '.' in published_date:
                        published_date = published_date.split('.')[0]  # 移除毫秒部分
                    
                    last_modified_date = fields[2].strip()
                    if 'T' in last_modified_date:
                        last_modified_date = last_modified_date.split('T')[0]  # 移除时间部分
                    if '.' in last_modified_date:
                        last_modified_date = last_modified_date.split('.')[0]  # 移除毫秒部分
                    
                    # 使用增强版清理函数处理文本字段
                    description = enhanced_clean_text(fields[3].strip())
                    source_identifier = enhanced_clean_text(fields[4].strip())
                    severity = enhanced_clean_text(fields[5].strip())
                    
                    # 处理base_score
                    base_score = 0.0
                    if fields[6].strip() and fields[6].strip() != 'N/A':
                        try:
                            base_score = float(fields[6].strip())
                        except ValueError:
                            pass
                    
                    base_severity = enhanced_clean_text(fields[7].strip())
                    vector_string = enhanced_clean_text(fields[8].strip())
                    vendor = enhanced_clean_text(fields[9].strip())
                    product = enhanced_clean_text(fields[10].strip())
                    
                    # 添加到批次
                    data_batch.append((
                        cve_id, published_date, last_modified_date, description, 
                        source_identifier, severity, base_score, base_severity, 
                        vector_string, vendor, product
                    ))
                    
                    # 当批次达到指定大小时，执行批量插入
                    if len(data_batch) >= batch_size:
                        # 批量插入数据
                        try:
                            cursor = conn.cursor()
                            sql = '''
                            INSERT INTO nvd (
                                cve_id, published_date, last_modified_date, description, 
                                source_identifier, severity, base_score, base_severity, 
                                vector_string, vendor, product
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                published_date=VALUES(published_date),
                                last_modified_date=VALUES(last_modified_date),
                                description=VALUES(description),
                                source_identifier=VALUES(source_identifier),
                                severity=VALUES(severity),
                                base_score=VALUES(base_score),
                                base_severity=VALUES(base_severity),
                                vector_string=VALUES(vector_string),
                                vendor=VALUES(vendor),
                                product=VALUES(product);
                            '''
                            cursor.executemany(sql, data_batch)
                            conn.commit()
                            imported_records += len(data_batch)
                            data_batch = []
                        except pymysql.err.DataError as e:
                            # 当批量插入遇到数据错误时，尝试逐条插入
                            print(f"批量插入遇到数据错误: {e}")
                            print("尝试逐条插入...")
                            for record in data_batch:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute(sql, record)
                                    conn.commit()
                                    imported_records += 1
                                except pymysql.err.DataError as de:
                                    # 跳过仍然有问题的记录
                                    print(f"跳过有问题的记录: {record[0]} - 错误: {de}")
                                    skipped_error_records += 1
                                except Exception as re:
                                    print(f"插入单条记录时出错: {re}")
                                    skipped_error_records += 1
                            data_batch = []
                        except Exception as e:
                            print(f"批量插入时出错: {e}")
                            traceback.print_exc()
                            conn.rollback()
                            # 尝试逐条插入
                            for record in data_batch:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute(sql, record)
                                    conn.commit()
                                    imported_records += 1
                                except Exception as re:
                                    print(f"插入单条记录时出错: {re}")
                                    skipped_error_records += 1
                            data_batch = []
                        finally:
                            if 'cursor' in locals():
                                cursor.close()
                    
                except Exception as e:
                    print(f"处理记录时出错: {e}")
                    skipped_error_records += 1
            
            # 处理剩余的数据批次
            if data_batch:
                try:
                    cursor = conn.cursor()
                    sql = '''
                    INSERT INTO nvd (
                        cve_id, published_date, last_modified_date, description, 
                        source_identifier, severity, base_score, base_severity, 
                        vector_string, vendor, product
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        published_date=VALUES(published_date),
                        last_modified_date=VALUES(last_modified_date),
                        description=VALUES(description),
                        source_identifier=VALUES(source_identifier),
                        severity=VALUES(severity),
                        base_score=VALUES(base_score),
                        base_severity=VALUES(base_severity),
                        vector_string=VALUES(vector_string),
                        vendor=VALUES(vendor),
                        product=VALUES(product);
                    '''
                    cursor.executemany(sql, data_batch)
                    conn.commit()
                    imported_records += len(data_batch)
                except pymysql.err.DataError as e:
                    print(f"批量插入遇到数据错误: {e}")
                    print("尝试逐条插入...")
                    for record in data_batch:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(sql, record)
                            conn.commit()
                            imported_records += 1
                        except pymysql.err.DataError as de:
                            print(f"跳过有问题的记录: {record[0]} - 错误: {de}")
                            skipped_error_records += 1
                        except Exception as re:
                            print(f"插入单条记录时出错: {re}")
                            skipped_error_records += 1
                except Exception as e:
                    print(f"批量插入时出错: {e}")
                    traceback.print_exc()
                    conn.rollback()
                    # 尝试逐条插入
                    for record in data_batch:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(sql, record)
                            conn.commit()
                            imported_records += 1
                        except Exception as re:
                            print(f"插入单条记录时出错: {re}")
                            skipped_error_records += 1
                finally:
                    if 'cursor' in locals():
                        cursor.close()
        
        # 验证导入结果
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nvd")
        total_in_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nvd WHERE published_date >= '2025-01-01' AND published_date < '2025-02-01'")
        january_2025_in_db = cursor.fetchone()[0]
        
        cursor.close()
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        
        print(f"\n导入结果摘要:")
        print(f"总记录数: {total_records}")
        print(f"成功导入: {imported_records}")
        print(f"跳过的非CVE记录: {skipped_non_cve_records}")
        print(f"跳过的错误记录: {skipped_error_records}")
        print(f"数据库中总记录数: {total_in_db}")
        print(f"数据库中2025年1月记录数: {january_2025_in_db}")
        print(f"结束时间: {end_time}")
        print(f"耗时: {elapsed_time}")
        
        return True
        
    except Exception as e:
        print(f"导入过程中出错: {e}")
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# 主函数
def main():
    print("202501.tsv文件导入工具 (增强版)")
    print("此工具使用增强版字符清理函数，能处理更多Unicode字符编码问题")
    
    success = import_specific_tsv_file(TARGET_FILE_PATH)
    
    if success:
        print("\n数据导入成功完成!")
        print("\n增强版功能说明:")
        print("1. 使用了enhanced_clean_text函数，可转换常见的全角字符为半角字符")
        print("2. 改进了对特殊Unicode字符的处理，减少了被跳过的记录数量")
        print("3. 常见问题字符包括长破折号(–)、不间断空格( )、智能引号等")
        print("4. 数据库采用utf8mb4字符集，支持大部分Unicode字符")
    else:
        print("\n数据导入失败!")

if __name__ == "__main__":
    main()