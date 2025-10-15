# -*- coding: utf-8 -*-

import pymysql

# 数据库连接配置
DB_CONFIG = {
    'host': '192.168.233.121',
    'user': 'root',
    'password': 'Xl123,56',
    'port': 3306,
    'db': 'security',
    'charset': 'utf8mb4'
}

def verify_202501_data():
    """验证2025年1月导入的数据"""
    try:
        # 连接到MySQL数据库
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 检查nvd表中2025年1月的数据总数
        cur.execute("SELECT COUNT(*) FROM nvd WHERE published_date LIKE '2025-01%'")
        count = cur.fetchone()[0]
        print(f"2025年1月的记录总数: {count}")
        
        # 检查前10条2025年1月的数据
        print("\n2025年1月的前10条记录示例:")
        cur.execute("SELECT cve_id, published_date, description, base_score FROM nvd WHERE published_date LIKE '2025-01%' LIMIT 10")
        
        for row in cur.fetchall():
            cve_id, published_date, description, base_score = row
            print(f"CVE ID: {cve_id}")
            print(f"发布日期: {published_date}")
            print(f"CVSS评分: {base_score}")
            print(f"描述: {description[:100]}...")  # 只显示前100个字符
            print("-------------------------")
        
        # 检查CVE ID的唯一性（虽然表结构已经有UNIQUE约束，但再确认一下）
        cur.execute("SELECT COUNT(*) FROM nvd WHERE published_date LIKE '2025-01%' AND cve_id IN "
                    "(SELECT cve_id FROM nvd WHERE published_date LIKE '2025-01%' GROUP BY cve_id HAVING COUNT(*) > 1)")
        duplicate_count = cur.fetchone()[0]
        print(f"\n2025年1月数据中的重复CVE ID数量: {duplicate_count}")
        
        # 检查不同严重性级别的分布
        print("\n2025年1月数据的严重性级别分布:")
        cur.execute("SELECT base_severity, COUNT(*) as count FROM nvd WHERE published_date LIKE '2025-01%' GROUP BY base_severity ORDER BY count DESC")
        for row in cur.fetchall():
            severity, count = row
            print(f"{severity}: {count}")
        
        # 检查评分范围分布
        print("\n2025年1月数据的CVSS评分分布:")
        cur.execute("SELECT \
                     CASE \
                         WHEN base_score >= 9 THEN 'Critical (9.0-10.0)' \
                         WHEN base_score >= 7 THEN 'High (7.0-8.9)' \
                         WHEN base_score >= 4 THEN 'Medium (4.0-6.9)' \
                         WHEN base_score >= 0 THEN 'Low (0.0-3.9)' \
                         ELSE 'N/A' \
                     END AS score_range, \
                     COUNT(*) as count \
                     FROM nvd WHERE published_date LIKE '2025-01%' \
                     GROUP BY score_range ORDER BY count DESC")
        for row in cur.fetchall():
            score_range, count = row
            print(f"{score_range}: {count}")
        
        # 检查2025年1月数据在整个数据库中的占比
        cur.execute("SELECT COUNT(*) FROM nvd")
        total_count = cur.fetchone()[0]
        percentage = (count / total_count) * 100 if total_count > 0 else 0
        print(f"\n2025年1月数据占数据库总记录的比例: {percentage:.2f}%")
        
        print("\n数据验证完成")
        
    except Exception as error:
        print(f"验证数据时出错: {error}")
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
    print("开始验证2025年1月导入的数据...")
    verify_202501_data()

if __name__ == "__main__":
    main()