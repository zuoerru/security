#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import traceback

# 数据库连接配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

def check_nvd_table():
    """检查nvd表是否存在并验证数据"""
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 检查nvd表是否存在
        cur.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            print("nvd表已成功创建")
            
            # 查看表结构
            print("\n表结构:")
            cur.execute("DESCRIBE nvd")
            for row in cur.fetchall():
                print(row)
            
            # 检查记录数
            cur.execute("SELECT COUNT(*) FROM nvd")
            count = cur.fetchone()[0]
            print(f"\nnvd表中共有 {count} 条记录")
            
            # 查看前5条记录
            print("\n前5条记录示例:")
            cur.execute("SELECT * FROM nvd LIMIT 5")
            for row in cur.fetchall():
                print(row)
        else:
            print("nvd表不存在")
            
            # 尝试创建表
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
            print("已尝试创建nvd表")
        
        # 关闭游标和连接
        cur.close()
        conn.close()
        
    except Exception as error:
        print(f"检查过程中出错: {error}")
        traceback.print_exc()

if __name__ == "__main__":
    print("开始检查nvd表...")
    check_nvd_table()
    print("检查完成")