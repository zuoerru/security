#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import os
import glob
import traceback
from datetime import datetime

# 数据库连接配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

# 文件路径配置
DATA_DIR = '/data_nfs/121/app/security'
# 导入2015-2025年的所有数据
FILE_PATTERN = '2015*.tsv 2016*.tsv 2017*.tsv 2018*.tsv 2019*.tsv 2020*.tsv 2021*.tsv 2022*.tsv 2023*.tsv 2024*.tsv 2025*.tsv'


def create_nvd_table():
    """在MySQL数据库中创建nvd表"""
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 创建nvd表（如果不存在）
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS nvd (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cve_id VARCHAR(20) UNIQUE NOT NULL,
            published_date DATETIME,
            last_modified_date DATETIME,
            description TEXT,
            base_score FLOAT,
            base_severity VARCHAR(20),
            vector_string TEXT,
            vendor TEXT,
            product TEXT
        )
        '''
        cur.execute(create_table_query)
        conn.commit()
        
        print("nvd表创建成功")
        
        # 关闭游标和连接
        cur.close()
        conn.close()
        
    except (Exception, pymysql.MySQLError) as error:
        print(f"创建表时出错: {error}")


def import_tsv_files():
    """导入所有符合条件的TSV文件到nvd表"""
    conn = None
    cur = None
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 获取所有符合条件的TSV文件
        tsv_files = []
        for pattern in FILE_PATTERN.split():
            tsv_files.extend(glob.glob(os.path.join(DATA_DIR, pattern)))
        
        # 按文件名排序（确保按年份和月份顺序处理）
        tsv_files.sort()
        
        print(f"找到 {len(tsv_files)} 个TSV文件需要导入")
        
        # 先测试一个小文件看看格式是否正确
        if tsv_files:
            test_file = tsv_files[0]  # 使用第一个文件进行测试
            print(f"正在测试文件格式: {os.path.basename(test_file)}")
            
            with open(test_file, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
                print(f"文件头: {header}")
                
                # 读取第一行数据进行测试
                if f.readline():
                    first_data_line = f.readline().strip()
                    print(f"第一行数据示例: {first_data_line[:100]}...")
                    
                    # 测试数据分割
                    test_fields = first_data_line.split('\t')
                    print(f"分割后字段数: {len(test_fields)}")
                    
                    # 如果文件格式测试通过，再继续导入
                    if len(test_fields) >= 9:
                        print("文件格式测试通过，继续导入所有文件")
                    else:
                        print(f"警告: 文件格式可能不正确，每行需要至少9个字段，实际只有{len(test_fields)}个字段")
                else:
                    print("警告: 测试文件没有数据行")
        
        # 逐个导入TSV文件
        total_records = 0
        for file_path in tsv_files:
            filename = os.path.basename(file_path)
            print(f"正在导入文件: {filename}")
            
            try:
                # 计算文件中的记录数（减去表头）
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    record_count = len(lines) - 1  # 减去表头行
                    
                    if record_count > 0:
                        # 准备插入语句
                        insert_sql = '''
                        INSERT INTO nvd (cve_id, published_date, last_modified_date, description, 
                                       base_score, base_severity, vector_string, vendor, product)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            published_date = VALUES(published_date),
                            last_modified_date = VALUES(last_modified_date),
                            description = VALUES(description),
                            base_score = VALUES(base_score),
                            base_severity = VALUES(base_severity),
                            vector_string = VALUES(vector_string),
                            vendor = VALUES(vendor),
                            product = VALUES(product)
                        '''
                        
                        # 读取文件中的每一行并准备数据
                        data = []
                        skipped_count = 0
                        for line in lines[1:]:  # 跳过表头
                            try:
                                fields = line.strip().split('\t')
                                # 确保fields有9个元素
                                while len(fields) < 9:
                                    fields.append('')
                                
                                # 过滤掉非CVE开头的行
                                if not fields[0].startswith('CVE'):
                                    skipped_count += 1
                                    continue
                                
                                # 处理日期格式（ISO 8601到MySQL DATETIME）
                                published_date = None
                                if fields[1]:
                                    try:
                                        date_part, time_part = fields[1].split('T')
                                        time_part = time_part.split('.')[0]  # 去掉毫秒部分
                                        published_date = f"{date_part} {time_part}"
                                    except:
                                        pass
                                
                                last_modified_date = None
                                if fields[2]:
                                    try:
                                        date_part, time_part = fields[2].split('T')
                                        time_part = time_part.split('.')[0]  # 去掉毫秒部分
                                        last_modified_date = f"{date_part} {time_part}"
                                    except:
                                        pass
                                
                                # 处理base_score（转换为浮点数）
                                base_score = None
                                if fields[4] and fields[4] != 'N/A':
                                    try:
                                        base_score = float(fields[4])
                                    except:
                                        pass
                                
                                data.append((
                                    fields[0],  # cve_id
                                    published_date,
                                    last_modified_date,
                                    fields[3],  # description
                                    base_score,
                                    fields[5],  # base_severity
                                    fields[6],  # vector_string
                                    fields[7],  # vendor
                                    fields[8]   # product
                                ))
                            except Exception as line_error:
                                print(f"处理行数据时出错: {line_error}")
                                # 打印出有问题的行，方便调试
                                print(f"问题行内容: {line.strip()[:200]}...")
                                continue
                        
                        if data:
                            # 批量执行插入，但限制批次大小以避免内存问题
                            batch_size = 1000
                            for i in range(0, len(data), batch_size):
                                batch = data[i:i+batch_size]
                                cur.executemany(insert_sql, batch)
                                conn.commit()
                                
                            print(f"成功导入 {len(data)} 条记录")
                            if skipped_count > 0:
                                print(f"跳过了 {skipped_count} 条非CVE开头的记录")
                            total_records += len(data)
                        else:
                            print("没有有效的数据行可导入")
                            if skipped_count > 0:
                                print(f"跳过了 {skipped_count} 条非CVE开头的记录")
                    else:
                        print("文件为空或只有表头，跳过导入")
            except Exception as file_error:
                print(f"导入文件 {filename} 时出错: {file_error}")
                traceback.print_exc()
                # 继续处理下一个文件
                continue
        
        print(f"所有文件导入完成，共导入 {total_records} 条记录")
        
    except Exception as error:
        print(f"导入数据时出错: {error}")
        traceback.print_exc()
    finally:
        # 确保关闭游标和连接
        if cur:
            cur.close()
        if conn:
            try:
                conn.close()
            except:
                pass


def verify_import():
    """验证数据导入结果"""
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 查询总记录数
        cur.execute("SELECT COUNT(*) FROM nvd")
        count = cur.fetchone()[0]
        print(f"nvd表中共有 {count} 条记录")
        
        # 查询前5条记录以验证数据
        cur.execute("SELECT * FROM nvd LIMIT 5")
        print("\n前5条记录示例:")
        for row in cur.fetchall():
            print(row)
        
        # 关闭游标和连接
        cur.close()
        conn.close()
        
    except (Exception, pymysql.MySQLError) as error:
        print(f"验证数据时出错: {error}")


def main():
    """主函数"""
    print(f"开始导入NVD数据到MySQL数据库...")
    start_time = datetime.now()
    
    # 创建nvd表
    create_nvd_table()
    
    # 导入TSV文件
    import_tsv_files()
    
    # 验证导入结果
    verify_import()
    
    end_time = datetime.now()
    print(f"\n数据导入完成，耗时: {end_time - start_time}")


if __name__ == "__main__":
    main()