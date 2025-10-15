#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import logging

"""
脚本用于检查nvd表的实际结构，确定字段名称和类型
"""

# 配置日志记录
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

# 检查nvd表结构
def check_nvd_table_structure():
    """检查nvd表的实际结构"""
    try:
        # 连接数据库
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("正在检查nvd表结构...")
        
        # 查询表结构
        cursor.execute("DESCRIBE nvd")
        columns = cursor.fetchall()
        
        # 打印表结构
        print("\n===== nvd表结构 =====")
        print(f"{'字段名':<30}{'类型':<30}{'是否为空':<10}{'键':<10}{'默认值':<10}{'额外信息'}")
        print("=" * 100)
        
        for column in columns:
            field = column[0]  # 字段名
            type_ = column[1]  # 数据类型
            null = column[2]   # 是否允许为空
            key = column[3]    # 键类型
            default = column[4]  # 默认值
            extra = column[5]   # 额外信息
            
            print(f"{field:<30}{type_:<30}{null:<10}{key:<10}{str(default):<10}{extra}")
        
        # 查询表索引
        cursor.execute("SHOW INDEX FROM nvd")
        indexes = cursor.fetchall()
        
        if indexes:
            print("\n===== 表索引 =====")
            for index in indexes:
                print(f"索引名: {index[2]}, 列名: {index[4]}, 唯一: {index[1] == 'UNIQUE'}")
        
        # 查询表创建语句
        cursor.execute("SHOW CREATE TABLE nvd")
        create_table = cursor.fetchone()[1]
        print(f"\n===== 表创建语句 =====")
        print(create_table)
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"检查表结构时出错: {e}")
        return False

# 主函数
def main():
    print("检查nvd表结构工具")
    check_nvd_table_structure()

if __name__ == "__main__":
    main()