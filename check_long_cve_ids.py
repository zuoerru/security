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

def check_long_cve_ids():
    """检查nvd表中cve_id长度大于50的记录"""
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 检查nvd表是否存在
        cur.execute("SHOW TABLES LIKE 'nvd'")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            print("nvd表已存在")
            
            # 查询cve_id长度大于50的记录
            query = """ 
            SELECT cve_id, LENGTH(cve_id) as cve_id_length 
            FROM nvd 
            WHERE LENGTH(cve_id) > 50
            """
            
            cur.execute(query)
            long_cve_ids = cur.fetchall()
            
            count = len(long_cve_ids)
            print(f"nvd表中cve_id长度大于50的记录共有 {count} 条\n")
            
            # 打印前10条长cve_id记录作为示例
            if count > 0:
                print("前10条长cve_id记录示例:")
                print("--------------------------------------------")
                print("cve_id\t\t\t\t长度")
                print("--------------------------------------------")
                
                for i, (cve_id, length) in enumerate(long_cve_ids[:10]):
                    # 由于cve_id可能很长，我们只显示前30个字符和后10个字符
                    if len(cve_id) > 40:
                        display_cve_id = f"{cve_id[:30]}...{cve_id[-10:]}"
                    else:
                        display_cve_id = cve_id
                    print(f"{display_cve_id}\t{length}")
                
                # 如果有超过10条记录，提示用户
                if count > 10:
                    print(f"\n... 还有 {count - 10} 条记录未显示 ...")
        else:
            print("nvd表不存在")
        
        # 关闭游标和连接
        cur.close()
        conn.close()
        
    except Exception as error:
        print(f"检查过程中出错: {error}")
        traceback.print_exc()

if __name__ == "__main__":
    print("开始检查nvd表中cve_id长度大于50的记录...")
    check_long_cve_ids()
    print("检查完成")