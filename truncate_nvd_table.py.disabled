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

def truncate_nvd_table():
    """删除nvd表中的所有数据"""
    conn = None
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 检查nvd表是否存在
        cur.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            # 获取清空表前的记录数
            cur.execute("SELECT COUNT(*) FROM nvd")
            before_count = cur.fetchone()[0]
            print(f"清空前nvd表中共有 {before_count} 条记录")
            
            # 使用TRUNCATE TABLE清空表数据（比DELETE更高效）
            cur.execute("TRUNCATE TABLE nvd")
            conn.commit()
            
            # 验证清空结果
            cur.execute("SELECT COUNT(*) FROM nvd")
            after_count = cur.fetchone()[0]
            print(f"清空后nvd表中共有 {after_count} 条记录")
            print("nvd表数据已成功清空")
        else:
            print("nvd表不存在")
        
    except Exception as error:
        print(f"清空表数据过程中出错: {error}")
        traceback.print_exc()
        # 发生错误时回滚
        if conn:
            conn.rollback()
    finally:
        # 关闭游标和连接
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("开始清空nvd表数据...")
    truncate_nvd_table()
    print("操作完成")