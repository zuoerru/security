#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import os
import traceback
import re
import sys
from datetime import datetime
import logging
from collections import defaultdict

"""
修复版TSV文件导入脚本，适配数据库实际表结构
主要修复：
1. 移除了对不存在字段的引用
2. 适配实际的表结构（没有source_identifier和severity字段，但有id自增字段）
3. 增强了Unicode字符处理
4. 优化了日志记录功能
"""

# 配置日志记录
def setup_logging():
    """设置日志记录配置"""
    log_dir = '/data_nfs/121/app/security/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = f'{log_dir}/import_202501_fixed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 配置日志记录器
    logger = logging.getLogger('import_logger')
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_file

# 基础字符清理函数
def basic_clean_text(text):
    """基础字符清理函数，确保文本可以被latin1字符集正确处理"""
    if not text:
        return text
    
    # 移除控制字符和不可打印字符
    text = ''.join(char for char in text if ord(char) >= 32 or ord(char) in (9, 10, 13))
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 替换常见的全角字符为半角字符
    full_to_half = {
        '，': ',', '。': '.', '！': '!', '？': '?',
        '：': ':', '；': ';', '"': '"', '"': '"',
        '‘': "'", '’': "'", '（': '(', '）': ')',
        '【': '[', '】': ']', '《': '<', '》': '>',
        '「': '[', '」': ']', '『': '[', '』': ']',
        '、': ',', '—': '-', '～': '~', '…': '...',
        '　': ' ',  # 全角空格
        '–': '-',  # 短破折号
        '—': '-',  # 长破折号
        '′': "'",  # 撇号
        '″': '"',  # 引号
        '°': ' degrees ',  # 度符号
        '℃': 'C',  # 摄氏度
        '℉': 'F',  # 华氏度
        '€': 'EUR',  # 欧元
        '£': 'GBP',  # 英镑
        '¥': 'Y',  # 日元
    }
    
    for full_char, half_char in full_to_half.items():
        text = text.replace(full_char, half_char)
    
    # 处理特殊Unicode字符，转换为安全的描述文本
    text = re.sub(r'[\u0600-\u06FF\u0750-\u077F]+', '[Arabic text]', text)  # 阿拉伯文
    text = re.sub(r'[\u4E00-\u9FFF]+', '[Chinese text]', text)  # 中文
    text = re.sub(r'[\u3040-\u309F\u30A0-\u30FF]+', '[Japanese text]', text)  # 日文
    text = re.sub(r'[\uAC00-\uD7AF\u1100-\u11FF]+', '[Korean text]', text)  # 韩文
    
    # 替换无法处理的Unicode字符
    problematic_pattern = re.compile(r'[\u0800-\uFFFF]')
    text = problematic_pattern.sub('[Unicode character]', text)
    
    # 确保文本可以被latin1编码处理
    try:
        text.encode('latin1')
    except UnicodeEncodeError:
        # 如果无法编码，使用replace策略
        text = text.encode('latin1', 'replace').decode('latin1')
    
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

# 检查nvd表结构并适配
def check_and_adapt_table(conn, logger):
    """检查并适配nvd表结构"""
    cursor = conn.cursor()
    try:
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            logger.info("nvd表已存在")
            # 查询表结构以确认
            cursor.execute("DESCRIBE nvd")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            logger.info(f"表中的列: {', '.join(column_names)}")
        else:
            logger.warning("nvd表不存在，将创建新表")
            # 创建与实际结构匹配的表
            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS nvd (
                id INT(11) NOT NULL AUTO_INCREMENT,
                cve_id VARCHAR(20) NOT NULL,
                published_date DATETIME DEFAULT NULL,
                last_modified_date DATETIME DEFAULT NULL,
                description TEXT DEFAULT NULL,
                base_score FLOAT DEFAULT NULL,
                base_severity VARCHAR(20) DEFAULT NULL,
                vector_string TEXT DEFAULT NULL,
                vendor TEXT DEFAULT NULL,
                product TEXT DEFAULT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY cve_id (cve_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
            '''
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info("nvd表已创建")
    except Exception as e:
        logger.error(f"检查表结构时出错: {e}")
        logger.debug(traceback.format_exc())
        conn.rollback()
    finally:
        cursor.close()

# 预处理文件
def preprocess_file(file_path, logger):
    """预处理文件，确保数据格式正确"""
    temp_file = f"{file_path}.preprocessed"
    logger.info(f"开始预处理文件: {file_path}")
    
    try:
        problematic_lines = 0
        total_lines = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f_in, \
             open(temp_file, 'w', encoding='utf-8') as f_out:
            # 复制表头
            header = f_in.readline()
            f_out.write(header)
            total_lines += 1
            
            for line in f_in:
                total_lines += 1
                # 简单的预处理，只替换有问题的控制字符，保留制表符和其他结构
                cleaned_line = ''.join(char for char in line if ord(char) >= 32 or ord(char) in (9, 10, 13))
                
                # 处理Unicode替换字符
                if '\ufffd' in cleaned_line:
                    problematic_lines += 1
                    if problematic_lines <= 10:
                        logger.warning(f"预处理发现问题行: {total_lines}")
                
                f_out.write(cleaned_line)
        
        logger.info(f"文件预处理完成，共处理 {total_lines} 行，发现 {problematic_lines} 行可能有问题")
        return temp_file
        
    except Exception as e:
        logger.error(f"预处理文件时出错: {e}")
        logger.debug(traceback.format_exc())
        # 如果预处理失败，返回原始文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return file_path

# 导入特定的TSV文件
def import_specific_tsv_file(file_path, logger):
    """导入特定的TSV文件，适配实际表结构"""
    start_time = datetime.now()
    logger.info(f"开始导入文件: {file_path}")
    logger.info(f"开始时间: {start_time}")
    
    # 统计信息
    stats = {
        'total_records': 0,
        'imported_records': 0,
        'skipped_non_cve_records': 0,
        'skipped_error_records': 0,
        'batch_success_count': 0,
        'batch_failure_count': 0,
        'individual_success_count': 0,
        'individual_failure_count': 0,
        'error_types': defaultdict(int)
    }
    
    # 错误记录
    error_records = []
    max_error_records = 100
    
    try:
        # 连接数据库
        conn = pymysql.connect(**DB_CONFIG)
        logger.info(f"成功连接到数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")
        
        # 检查并适配表结构
        check_and_adapt_table(conn, logger)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"错误: 文件 {file_path} 不存在")
            return False, stats, error_records
        
        # 预处理文件
        preprocessed_file = preprocess_file(file_path, logger)
        
        # 读取并导入数据
        batch_size = 1000
        data_batch = []
        
        # 获取文件总行数用于进度显示
        with open(preprocessed_file, 'r', encoding='utf-8') as f:
            total_file_lines = sum(1 for _ in f)
        
        processed_lines = 0
        
        with open(preprocessed_file, 'r', encoding='utf-8') as f:
            header = f.readline()  # 跳过表头
            processed_lines += 1
            
            for line in f:
                processed_lines += 1
                stats['total_records'] += 1
                
                # 显示进度
                if processed_lines % 1000 == 0:
                    progress = (processed_lines / total_file_lines) * 100
                    logger.info(f"处理进度: {processed_lines}/{total_file_lines} ({progress:.1f}%)")
                
                # 跳过非CVE开头的记录
                if not line.strip().startswith('CVE'):
                    stats['skipped_non_cve_records'] += 1
                    continue
                
                # 处理每一行数据
                fields = line.strip().split('\t')
                
                # 确保字段数量足够 (实际文件格式只有4个字段)
                if len(fields) < 4:
                    stats['skipped_error_records'] += 1
                    stats['error_types']['insufficient_fields'] += 1
                    if len(error_records) < max_error_records:
                        error_records.append({
                            'line': processed_lines,
                            'error_type': 'insufficient_fields',
                            'details': f'字段数量不足: {len(fields)}'
                        })
                    continue
                
                try:
                    # 提取字段值，使用基础清理函数
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
                    
                    # 使用基础清理函数处理文本字段，确保兼容latin1
                    description = basic_clean_text(fields[3].strip())
                    
                    # 对于缺失的字段，设置默认值
                    base_score = 0.0
                    base_severity = ''
                    vector_string = ''
                    vendor = ''
                    product = ''
                    
                    # 添加到批次（注意：不包含id字段，MySQL会自动处理自增）
                    data_batch.append((
                        cve_id, published_date, last_modified_date, description, 
                        base_score, base_severity, vector_string, vendor, product
                    ))
                    
                    # 当批次达到指定大小时，执行批量插入
                    if len(data_batch) >= batch_size:
                        # 批量插入数据
                        try:
                            cursor = conn.cursor()
                            # 适配实际表结构的SQL语句（注意字段顺序与实际表结构匹配）
                            sql = '''
                            INSERT INTO nvd (
                                cve_id, published_date, last_modified_date, description, 
                                base_score, base_severity, vector_string, vendor, product
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                published_date=VALUES(published_date),
                                last_modified_date=VALUES(last_modified_date),
                                description=VALUES(description),
                                base_score=VALUES(base_score),
                                base_severity=VALUES(base_severity),
                                vector_string=VALUES(vector_string),
                                vendor=VALUES(vendor),
                                product=VALUES(product);
                            '''
                            cursor.executemany(sql, data_batch)
                            conn.commit()
                            stats['imported_records'] += len(data_batch)
                            stats['batch_success_count'] += 1
                            data_batch = []
                        except pymysql.err.DataError as e:
                            # 当批量插入遇到数据错误时，尝试逐条插入
                            logger.warning(f"批量插入遇到数据错误: {e}")
                            logger.info("尝试逐条插入...")
                            stats['batch_failure_count'] += 1
                            stats['error_types']['data_error'] += 1
                            
                            for record in data_batch:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute(sql, record)
                                    conn.commit()
                                    stats['imported_records'] += 1
                                    stats['individual_success_count'] += 1
                                except pymysql.err.DataError as de:
                                    # 跳过仍然有问题的记录
                                    logger.warning(f"跳过有问题的记录: {record[0]} - 错误: {de}")
                                    stats['skipped_error_records'] += 1
                                    stats['individual_failure_count'] += 1
                                    stats['error_types']['individual_data_error'] += 1
                                    if len(error_records) < max_error_records:
                                        error_records.append({
                                            'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                            'cve_id': record[0],
                                            'error_type': 'data_error',
                                            'details': str(de)
                                        })
                                except Exception as re:
                                    logger.error(f"插入单条记录时出错: {re}")
                                    stats['skipped_error_records'] += 1
                                    stats['individual_failure_count'] += 1
                                    stats['error_types']['individual_insert_error'] += 1
                                    if len(error_records) < max_error_records:
                                        error_records.append({
                                            'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                            'cve_id': record[0],
                                            'error_type': 'insert_error',
                                            'details': str(re)
                                        })
                            data_batch = []
                        except Exception as e:
                            logger.error(f"批量插入时出错: {e}")
                            logger.debug(traceback.format_exc())
                            stats['batch_failure_count'] += 1
                            stats['error_types']['batch_insert_error'] += 1
                            conn.rollback()
                            
                            # 尝试逐条插入
                            for record in data_batch:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute(sql, record)
                                    conn.commit()
                                    stats['imported_records'] += 1
                                    stats['individual_success_count'] += 1
                                except Exception as re:
                                    logger.error(f"插入单条记录时出错: {re}")
                                    stats['skipped_error_records'] += 1
                                    stats['individual_failure_count'] += 1
                                    if len(error_records) < max_error_records:
                                        error_records.append({
                                            'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                            'cve_id': record[0],
                                            'error_type': 'insert_error',
                                            'details': str(re)
                                        })
                            data_batch = []
                        finally:
                            if 'cursor' in locals():
                                cursor.close()
                    
                except Exception as e:
                    logger.error(f"处理记录时出错: {e}")
                    logger.debug(traceback.format_exc())
                    stats['skipped_error_records'] += 1
                    stats['error_types']['record_processing_error'] += 1
                    if len(error_records) < max_error_records:
                        error_records.append({
                            'line': processed_lines,
                            'error_type': 'processing_error',
                            'details': str(e)
                        })
            
            # 处理剩余的数据批次
            if data_batch:
                try:
                    cursor = conn.cursor()
                    # 适配实际表结构的SQL语句
                    sql = '''
                    INSERT INTO nvd (
                        cve_id, published_date, last_modified_date, description, 
                        base_score, base_severity, vector_string, vendor, product
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        published_date=VALUES(published_date),
                        last_modified_date=VALUES(last_modified_date),
                        description=VALUES(description),
                        base_score=VALUES(base_score),
                        base_severity=VALUES(base_severity),
                        vector_string=VALUES(vector_string),
                        vendor=VALUES(vendor),
                        product=VALUES(product);
                    '''
                    cursor.executemany(sql, data_batch)
                    conn.commit()
                    stats['imported_records'] += len(data_batch)
                    stats['batch_success_count'] += 1
                except pymysql.err.DataError as e:
                    logger.warning(f"批量插入遇到数据错误: {e}")
                    logger.info("尝试逐条插入...")
                    stats['batch_failure_count'] += 1
                    stats['error_types']['data_error'] += 1
                    
                    for record in data_batch:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(sql, record)
                            conn.commit()
                            stats['imported_records'] += 1
                            stats['individual_success_count'] += 1
                        except pymysql.err.DataError as de:
                            logger.warning(f"跳过有问题的记录: {record[0]} - 错误: {de}")
                            stats['skipped_error_records'] += 1
                            stats['individual_failure_count'] += 1
                            if len(error_records) < max_error_records:
                                error_records.append({
                                    'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                    'cve_id': record[0],
                                    'error_type': 'data_error',
                                    'details': str(de)
                                })
                        except Exception as re:
                            logger.error(f"插入单条记录时出错: {re}")
                            stats['skipped_error_records'] += 1
                            stats['individual_failure_count'] += 1
                            if len(error_records) < max_error_records:
                                error_records.append({
                                    'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                    'cve_id': record[0],
                                    'error_type': 'insert_error',
                                    'details': str(re)
                                })
                except Exception as e:
                    logger.error(f"批量插入时出错: {e}")
                    logger.debug(traceback.format_exc())
                    stats['batch_failure_count'] += 1
                    conn.rollback()
                    
                    # 尝试逐条插入
                    for record in data_batch:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(sql, record)
                            conn.commit()
                            stats['imported_records'] += 1
                            stats['individual_success_count'] += 1
                        except Exception as re:
                            logger.error(f"插入单条记录时出错: {re}")
                            stats['skipped_error_records'] += 1
                            stats['individual_failure_count'] += 1
                            if len(error_records) < max_error_records:
                                error_records.append({
                                    'line': processed_lines - len(data_batch) + data_batch.index(record) + 1,
                                    'cve_id': record[0],
                                    'error_type': 'insert_error',
                                    'details': str(re)
                                })
                finally:
                    if 'cursor' in locals():
                        cursor.close()
        
        # 删除预处理文件（如果存在且不是原始文件）
        if preprocessed_file != file_path and os.path.exists(preprocessed_file):
            os.remove(preprocessed_file)
            logger.info(f"已删除临时预处理文件: {preprocessed_file}")
        
        # 验证导入结果
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nvd")
        total_in_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nvd WHERE published_date >= '2025-01-01' AND published_date < '2025-02-01'")
        january_2025_in_db = cursor.fetchone()[0]
        
        cursor.close()
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        
        # 记录导入结果摘要
        logger.info("\n导入结果摘要:")
        logger.info(f"总记录数: {stats['total_records']}")
        logger.info(f"成功导入: {stats['imported_records']}")
        logger.info(f"跳过的非CVE记录: {stats['skipped_non_cve_records']}")
        logger.info(f"跳过的错误记录: {stats['skipped_error_records']}")
        logger.info(f"数据库中总记录数: {total_in_db}")
        logger.info(f"数据库中2025年1月记录数: {january_2025_in_db}")
        logger.info(f"结束时间: {end_time}")
        logger.info(f"耗时: {elapsed_time}")
        
        # 记录批次处理统计
        logger.info("\n批次处理统计:")
        logger.info(f"成功的批次: {stats['batch_success_count']}")
        logger.info(f"失败的批次: {stats['batch_failure_count']}")
        logger.info(f"单条成功插入: {stats['individual_success_count']}")
        logger.info(f"单条插入失败: {stats['individual_failure_count']}")
        
        # 记录错误类型统计
        if stats['error_types']:
            logger.info("\n错误类型统计:")
            for error_type, count in stats['error_types'].items():
                logger.info(f"{error_type}: {count}次")
        
        # 记录错误记录示例
        if error_records:
            logger.info(f"\n前{min(10, len(error_records))}条错误记录示例:")
            for i, error in enumerate(error_records[:10]):
                logger.info(f"{i+1}. 行号: {error.get('line', 'N/A')}, CVE ID: {error.get('cve_id', 'N/A')}")
                logger.info(f"   错误类型: {error['error_type']}")
                logger.info(f"   详细信息: {error['details']}")
            
            if len(error_records) > 10:
                logger.info(f"... 还有{len(error_records) - 10}条错误记录未显示")
        
        return True, stats, error_records
        
    except Exception as e:
        logger.error(f"导入过程中出错: {e}")
        logger.debug(traceback.format_exc())
        return False, stats, error_records
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            logger.info("数据库连接已关闭")

# 主函数
def main():
    """主函数"""
    print("202501.tsv文件导入工具 (修复版)")
    print("此工具适配数据库实际表结构，修复了字段不匹配问题")
    
    # 设置日志记录
    logger, log_file = setup_logging()
    logger.info("=" * 80)
    logger.info("日志文件: {}".format(log_file))
    
    try:
        # 执行导入
        success, stats, error_records = import_specific_tsv_file(TARGET_FILE_PATH, logger)
        
        if success:
            print("\n数据导入成功完成!")
            print(f"日志文件已保存至: {log_file}")
            print("\n修复版功能说明:")
            print("1. 适配了数据库实际表结构（没有source_identifier和severity字段）")
            print("2. 移除了对不存在字段的引用")
            print("3. 优化了字符清理函数，确保兼容latin1字符集")
            print("4. 增强了错误处理和日志记录")
        else:
            print("\n数据导入失败!")
            print(f"详细错误信息请查看日志文件: {log_file}")
            
    except Exception as e:
        print(f"执行过程中发生严重错误: {e}")
        print(f"详细错误信息请查看日志文件: {log_file}")
    finally:
        logger.info("=" * 80)

if __name__ == "__main__":
    main()