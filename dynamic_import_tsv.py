# -*- coding: utf-8 -*-

import pymysql
import os
import traceback
import re
import sys
import argparse
from datetime import datetime
import logging
from collections import defaultdict

"""
动态TSV文件导入工具
支持通过命令行参数指定要导入的单个或多个TSV文件
每个文件都会生成独立的日志并进行数据验证
"""

# 配置日志记录
def setup_logging(log_prefix):
    """设置日志记录配置"""
    log_dir = '/data_nfs/121/app/security/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = f'{log_dir}/{log_prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 配置日志记录器
    logger = logging.getLogger(f'import_logger_{log_prefix}')
    logger.setLevel(logging.INFO)
    
    # 清除可能存在的处理器
    if logger.handlers:
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()
    
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

# 数据目录
DATA_DIR = '/data_nfs/121/app/security'

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
    
    # 获取文件名（不含扩展名）用于日期范围判断
    file_name = os.path.basename(file_path)
    file_base = os.path.splitext(file_name)[0]
    
    # 从文件名中提取年份和月份
    year_month = file_base[:6]  # 例如 '202502'
    year = year_month[:4]
    month = year_month[4:6]
    
    # 构建日期范围
    start_date = f"{year}-{month}-01"
    if month == '12':
        next_month = f"{int(year)+1}-01-01"
    else:
        next_month = f"{year}-{str(int(month)+1).zfill(2)}-01"
    
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
        
        # 根据当前处理的文件获取对应月份的记录数
        cursor.execute(f"SELECT COUNT(*) FROM nvd WHERE published_date >= '{start_date}' AND published_date < '{next_month}'")
        current_month_in_db = cursor.fetchone()[0]
        
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
        logger.info(f"数据库中{year}年{int(month)}月记录数: {current_month_in_db}")
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

# 验证导入结果
def verify_import_result(file_path, logger):
    """验证导入结果"""
    try:
        # 连接数据库
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 获取文件名（不含扩展名）用于日期范围判断
        file_name = os.path.basename(file_path)
        file_base = os.path.splitext(file_name)[0]
        
        # 从文件名中提取年份和月份
        year_month = file_base[:6]  # 例如 '202502'
        year = year_month[:4]
        month = year_month[4:6]
        
        # 构建日期范围
        start_date = f"{year}-{month}-01"
        if month == '12':
            next_month = f"{int(year)+1}-01-01"
        else:
            next_month = f"{year}-{str(int(month)+1).zfill(2)}-01"
        
        # 查询该月份的记录数
        cursor.execute(f"SELECT COUNT(*) FROM nvd WHERE published_date >= '{start_date}' AND published_date < '{next_month}'")
        month_count = cursor.fetchone()[0]
        
        # 检查是否有重复的CVE ID
        cursor.execute(f"SELECT COUNT(*) FROM nvd WHERE published_date >= '{start_date}' AND published_date < '{next_month}' AND cve_id IN "
                     f"(SELECT cve_id FROM nvd WHERE published_date >= '{start_date}' AND published_date < '{next_month}' GROUP BY cve_id HAVING COUNT(*) > 1)")
        duplicate_count = cursor.fetchone()[0]
        
        # 查询该月份的评分分布
        cursor.execute(f"SELECT \
                     CASE \
                         WHEN base_score >= 9 THEN 'Critical (9.0-10.0)' \
                         WHEN base_score >= 7 THEN 'High (7.0-8.9)' \
                         WHEN base_score >= 4 THEN 'Medium (4.0-6.9)' \
                         WHEN base_score >= 0 THEN 'Low (0.0-3.9)' \
                         ELSE 'N/A' \
                     END AS score_range, \
                     COUNT(*) as count \
                     FROM nvd WHERE published_date >= '{start_date}' AND published_date < '{next_month}' \
                     GROUP BY score_range ORDER BY count DESC")
        score_distribution = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"\n导入验证结果 ({file_name}):")
        logger.info(f"{year}年{int(month)}月的记录总数: {month_count}")
        logger.info(f"重复的CVE ID数量: {duplicate_count}")
        
        if score_distribution:
            logger.info("评分分布:")
            for score_range, count in score_distribution:
                logger.info(f"  {score_range}: {count}")
        
        # 验证通过条件：记录数大于0，无重复记录
        if month_count > 0 and duplicate_count == 0:
            logger.info(f"验证通过: {file_name} 导入的数据完整且无重复")
            return True
        else:
            logger.warning(f"验证警告: {file_name} 导入的数据可能存在问题")
            return False
        
    except Exception as e:
        logger.error(f"验证导入结果时出错: {e}")
        return False

# 批量导入主函数
def batch_import(file_paths):
    """批量导入TSV文件，接受文件路径列表作为参数"""
    print("TSV文件动态导入工具")
    print("此工具将导入您指定的TSV文件")
    print("每个文件都会生成独立的日志文件并进行验证")
    print("=" * 80)
    
    # 导入结果统计
    batch_stats = {
        'total_files': len(file_paths),
        'success_files': 0,
        'failed_files': 0,
        'total_records': 0,
        'total_imported': 0,
        'total_skipped': 0
    }
    
    # 创建主日志
    log_prefix = f'dynamic_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    main_logger, main_log_file = setup_logging(log_prefix)
    main_logger.info("开始TSV文件动态导入")
    main_logger.info(f"共需要导入 {len(file_paths)} 个文件")
    for file_path in file_paths:
        main_logger.info(f"待导入文件: {file_path}")
    
    start_time = datetime.now()
    
    try:
        # 逐个处理文件
        for i, file_path in enumerate(file_paths):
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(DATA_DIR, file_path)
            
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            
            print(f"\n{'=' * 80}")
            print(f"开始处理第 {i+1}/{len(file_paths)} 个文件: {file_name}")
            main_logger.info(f"\n{'=' * 80}")
            main_logger.info(f"开始处理第 {i+1}/{len(file_paths)} 个文件: {file_name}")
            
            # 为每个文件创建独立的日志记录器
            file_logger, file_log_path = setup_logging(f'import_{file_base}')
            main_logger.info(f"文件日志已创建: {file_log_path}")
            
            # 执行导入
            success, stats, _ = import_specific_tsv_file(file_path, file_logger)
            
            if success:
                # 导入成功后进行验证
                verify_success = verify_import_result(file_path, file_logger)
                
                if verify_success:
                    print(f"文件 {file_name} 导入并验证成功!")
                    print(f"成功导入记录数: {stats['imported_records']}")
                    print(f"日志文件: {file_log_path}")
                    main_logger.info(f"文件 {file_name} 导入并验证成功")
                    main_logger.info(f"成功导入记录数: {stats['imported_records']}")
                    main_logger.info(f"文件日志: {file_log_path}")
                    batch_stats['success_files'] += 1
                else:
                    print(f"文件 {file_name} 导入成功但验证失败!")
                    print(f"请查看日志文件了解详情: {file_log_path}")
                    main_logger.warning(f"文件 {file_name} 导入成功但验证失败")
                    batch_stats['failed_files'] += 1
                
                # 更新批量统计信息
                batch_stats['total_records'] += stats['total_records']
                batch_stats['total_imported'] += stats['imported_records']
                batch_stats['total_skipped'] += (stats['skipped_non_cve_records'] + stats['skipped_error_records'])
                
            else:
                print(f"文件 {file_name} 导入失败!")
                print(f"请查看日志文件了解详情: {file_log_path}")
                main_logger.error(f"文件 {file_name} 导入失败")
                batch_stats['failed_files'] += 1
            
            # 释放文件日志资源
            for handler in file_logger.handlers:
                handler.close()
        
        # 批量导入完成后的总结
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        
        print(f"\n{'=' * 80}")
        print("批量导入完成!")
        print(f"总文件数: {batch_stats['total_files']}")
        print(f"成功文件数: {batch_stats['success_files']}")
        print(f"失败文件数: {batch_stats['failed_files']}")
        print(f"总记录数: {batch_stats['total_records']}")
        print(f"成功导入记录数: {batch_stats['total_imported']}")
        print(f"跳过记录数: {batch_stats['total_skipped']}")
        print(f"总耗时: {elapsed_time}")
        print(f"主日志文件: {main_log_file}")
        
        main_logger.info("\n批量导入完成总结:")
        main_logger.info(f"总文件数: {batch_stats['total_files']}")
        main_logger.info(f"成功文件数: {batch_stats['success_files']}")
        main_logger.info(f"失败文件数: {batch_stats['failed_files']}")
        main_logger.info(f"总记录数: {batch_stats['total_records']}")
        main_logger.info(f"成功导入记录数: {batch_stats['total_imported']}")
        main_logger.info(f"跳过记录数: {batch_stats['total_skipped']}")
        main_logger.info(f"总耗时: {elapsed_time}")
        
    except Exception as e:
        print(f"批量导入过程中发生严重错误: {e}")
        main_logger.error(f"批量导入过程中发生严重错误: {e}")
        main_logger.debug(traceback.format_exc())
    finally:
        main_logger.info("=" * 80)

# 解析命令行参数
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='动态TSV文件导入工具，支持导入单个或多个TSV文件到MySQL数据库')
    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                       help='要导入的TSV文件路径（可以是相对路径或绝对路径）')
    return parser.parse_args()

# 主函数
def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 执行批量导入
    batch_import(args.files)

if __name__ == "__main__":
    main()