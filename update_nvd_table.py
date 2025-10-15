#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import traceback

# 数据库连接配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'port': 3306,
    'user': 'root',
    'password': 'Xl123,56',
    'database': 'security',
    'charset': 'utf8mb4'
}

def update_nvd_table():
    """修改nvd表结构，增加cve_id列的长度"""
    conn = None
    cur = None
    try:
        # 连接数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("开始修改nvd表结构...")
        
        # 查看当前表结构
        print("当前表结构：")
        cur.execute("DESCRIBE nvd")
        for row in cur.fetchall():
            print(row)
        
        # 修改cve_id列的长度从varchar(1000)改回varchar(20)
        alter_sql = "ALTER TABLE nvd MODIFY COLUMN cve_id VARCHAR(20) NOT NULL UNIQUE"
        cur.execute(alter_sql)
        conn.commit()
        
        print("\nnvd表结构修改成功！cve_id列长度已从varchar(1000)改回varchar(20)")
        
        # 验证修改后的表结构
        print("\n修改后的表结构：")
        cur.execute("DESCRIBE nvd")
        for row in cur.fetchall():
            print(row)
            
    except Exception as e:
        print(f"修改表结构时出错：{e}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        # 关闭游标和连接
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    update_nvd_table()