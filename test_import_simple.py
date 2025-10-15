#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import os
import logging
from datetime import datetime

"""
简化版测试脚本，用于隔离和排查数据导入问题
专注于基本的数据库连接和单条记录插入
"""

# 配置日志记录
def setup_test_logging():
    """设置测试日志"""
    log_dir = '/data_nfs/121/app/security/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = f'{log_dir}/test_import_simple_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 配置日志记录器
    logger = logging.getLogger('test_logger')
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

# 数据库配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

# 测试数据库连接
def test_db_connection(logger):
    """测试数据库连接是否正常"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 测试查询
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        logger.info(f"成功连接到数据库: {db_name}")
        
        # 检查nvd表是否存在
        cursor.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cursor.fetchone() is not None
        logger.info(f"nvd表存在: {table_exists}")
        
        # 查询当前记录数
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM nvd")
            total_records = cursor.fetchone()[0]
            logger.info(f"数据库中总记录数: {total_records}")
            
            cursor.execute("SELECT COUNT(*) FROM nvd WHERE published_date >= '2025-01-01' AND published_date < '2025-02-01'")
            january_2025_records = cursor.fetchone()[0]
            logger.info(f"数据库中2025年1月记录数: {january_2025_records}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

# 测试插入单条记录
def test_single_insert(logger):
    """测试插入单条记录到数据库"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 准备测试数据（简单有效的记录）
        test_data = (
            'CVE-2025-99999',  # 测试CVE ID
            '2025-01-01',      # published_date
            '2025-01-01',      # last_modified_date
            'Test description for debugging',  # description
            '',                # source_identifier
            '',                # severity
            0.0,               # base_score
            '',                # base_severity
            '',                # vector_string
            '',                # vendor
            ''                 # product
        )
        
        # 插入测试数据
        sql = '''
        INSERT INTO nvd (
            cve_id, published_date, last_modified_date, description, 
            source_identifier, severity, base_score, base_severity, 
            vector_string, vendor, product
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            published_date=VALUES(published_date),
            last_modified_date=VALUES(last_modified_date),
            description=VALUES(description);
        '''
        
        cursor.execute(sql, test_data)
        conn.commit()
        logger.info(f"成功插入测试记录: {test_data[0]}")
        
        # 验证插入结果
        cursor.execute("SELECT * FROM nvd WHERE cve_id = %s", (test_data[0],))
        result = cursor.fetchone()
        if result:
            logger.info(f"验证成功: 测试记录已存在于数据库中")
        else:
            logger.warning(f"验证失败: 测试记录不在数据库中")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"插入测试记录失败: {e}")
        # 尝试回滚
        if 'conn' in locals() and conn.open:
            conn.rollback()
        return False

# 测试读取202501.tsv文件
def test_file_reading(logger):
    """测试读取202501.tsv文件"""
    file_path = '/data_nfs/121/app/security/202501.tsv'
    
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        logger.info(f"文件大小: {file_size} 字节")
        
        # 读取文件头几行
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # 读取表头
            header = f.readline().strip()
            logger.info(f"文件表头: {header}")
            
            # 读取前5条数据行
            for i in range(5):
                line = f.readline()
                if not line:
                    break
                
                # 检查字段数量
                fields = line.strip().split('\t')
                logger.info(f"行 {i+1}: {len(fields)} 个字段 - 第一个字段: {fields[0] if fields else '空'}")
                
        return True
    except Exception as e:
        logger.error(f"读取文件时出错: {e}")
        return False

# 主函数
def main():
    print("===== 数据导入问题排查测试 =====")
    
    # 设置日志
    logger, log_file = setup_test_logging()
    print(f"日志文件已创建: {log_file}")
    
    # 测试数据库连接
    print("\n1. 测试数据库连接...")
    db_test_result = test_db_connection(logger)
    print(f"数据库连接测试: {'成功' if db_test_result else '失败'}")
    
    # 测试插入单条记录
    print("\n2. 测试插入单条记录...")
    insert_test_result = test_single_insert(logger)
    print(f"单条记录插入测试: {'成功' if insert_test_result else '失败'}")
    
    # 测试文件读取
    print("\n3. 测试读取202501.tsv文件...")
    file_test_result = test_file_reading(logger)
    print(f"文件读取测试: {'成功' if file_test_result else '失败'}")
    
    print(f"\n测试完成，详细信息请查看日志文件: {log_file}")

if __name__ == "__main__":
    main()