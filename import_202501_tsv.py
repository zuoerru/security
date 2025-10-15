# -*- coding: utf-8 -*-

import pymysql
import os
import traceback
import re
from datetime import datetime

# 清理Unicode控制字符和无法识别的字符
def clean_text(text):
    if not text:
        return text
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or ord(char) in (9, 10, 13))
    # 移除不可打印字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text

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
# 只导入202501.tsv文件
TARGET_FILE = '202501.tsv'

def import_specific_tsv_file():
    """导入特定的TSV文件到nvd表"""
    conn = None
    cur = None
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 构造完整的文件路径
        file_path = os.path.join(DATA_DIR, TARGET_FILE)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误: 文件 {file_path} 不存在")
            return
        
        print(f"开始导入特定文件: {TARGET_FILE}")
        
        # 先检查nvd表是否存在
        cur.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cur.fetchone() is not None
        
        if not table_exists:
            print("警告: nvd表不存在，正在创建...")
            # 创建nvd表
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
        
        # 测试文件格式
        print(f"正在测试文件格式: {TARGET_FILE}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
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
                    print("文件格式测试通过，继续导入文件")
                else:
                    print(f"警告: 文件格式可能不正确，每行需要至少9个字段，实际只有{len(test_fields)}个字段")
            else:
                print("警告: 测试文件没有数据行")
        
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
                        
                        # 清理文本字段
                        clean_desc = clean_text(fields[3])
                        clean_vendor = clean_text(fields[7])
                        clean_product = clean_text(fields[8])
                        clean_vector = clean_text(fields[6])
                        clean_severity = clean_text(fields[5])
                        
                        data.append((
                            fields[0],  # cve_id
                            published_date,
                            last_modified_date,
                            clean_desc,  # description (已清理)
                            base_score,
                            clean_severity,  # base_severity (已清理)
                            clean_vector,  # vector_string (已清理)
                            clean_vendor,  # vendor (已清理)
                            clean_product  # product (已清理)
                        ))
                    except Exception as line_error:
                        print(f"处理行数据时出错: {line_error}")
                        # 打印出有问题的行，方便调试
                        print(f"问题行内容: {line.strip()[:200]}...")
                        continue
                
                if data:
                    # 批量执行插入，但限制批次大小以避免内存问题
                    batch_size = 1000
                    total_imported = 0
                    
                    for i in range(0, len(data), batch_size):
                        batch = data[i:i+batch_size]
                        try:
                            cur.executemany(insert_sql, batch)
                            conn.commit()
                            batch_imported = len(batch)
                            total_imported += batch_imported
                            print(f"已导入批次 {i//batch_size + 1}: {batch_imported} 条记录")
                        except pymysql.err.DataError as e:
                            # 处理数据编码错误，尝试单条插入并跳过错误行
                            print(f"批次插入遇到编码问题: {e}")
                            print("尝试逐条插入并跳过错误记录...")
                            batch_imported = 0
                            
                            for row in batch:
                                try:
                                    cur.execute(insert_sql, row)
                                    conn.commit()
                                    batch_imported += 1
                                    total_imported += 1
                                except pymysql.err.DataError as single_e:
                                    print(f"跳过有问题的记录: {single_e}")
                                    print(f"问题记录ID: {row[0]}")
                                    conn.rollback()
                                    continue
                            
                            print(f"批次 {i//batch_size + 1} 完成，成功导入 {batch_imported} 条记录")
                    
                    print(f"成功导入 {total_imported} 条记录")
                    if skipped_count > 0:
                        print(f"跳过了 {skipped_count} 条非CVE开头的记录")
                else:
                    print("没有有效的数据行可导入")
                    if skipped_count > 0:
                        print(f"跳过了 {skipped_count} 条非CVE开头的记录")
            else:
                print("文件为空或只有表头，跳过导入")
        
        # 验证导入结果
        print("\n验证导入结果:")
        cur.execute("SELECT COUNT(*) FROM nvd")
        count = cur.fetchone()[0]
        print(f"nvd表中现在共有 {count} 条记录")
        
        # 查询2025年1月的记录数
        cur.execute("SELECT COUNT(*) FROM nvd WHERE published_date LIKE '2025-01%'")
        jan_2025_count = cur.fetchone()[0]
        print(f"2025年1月的记录数: {jan_2025_count}")
        
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

def main():
    """主函数"""
    print(f"开始将 {TARGET_FILE} 导入到MySQL数据库的nvd表...")
    start_time = datetime.now()
    
    # 导入特定的TSV文件
    import_specific_tsv_file()
    
    end_time = datetime.now()
    print(f"\n数据导入完成，耗时: {end_time - start_time}")

if __name__ == "__main__":
    main()