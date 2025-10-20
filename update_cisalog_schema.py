#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新cisalog表结构，添加sync_type字段
"""
import sys
sys.path.append('/data_nfs/121/app/security')

from app import create_app, db
from sqlalchemy import text

# 创建应用实例
app = create_app()

with app.app_context():
    print("===== 更新cisalog表结构 =====")
    
    try:
        # 使用SQL直接添加字段，避免使用迁移工具的复杂性
        with db.engine.connect() as conn:
            # 检查字段是否已存在
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'cisalog' 
                AND column_name = 'sync_type'
            """)
            result = conn.execute(check_query).fetchall()
            
            if not result:
                print("添加sync_type字段到cisalog表...")
                # 添加字段
                add_column_query = text("""
                    ALTER TABLE cisalog 
                    ADD COLUMN sync_type VARCHAR(20) NOT NULL DEFAULT 'manual'
                """)
                conn.execute(add_column_query)
                conn.commit()
                print("✓ 成功添加sync_type字段")
            else:
                print("✓ sync_type字段已存在")
            
            # 更新现有记录的sync_type为manual（默认值）
            print("更新现有记录的sync_type值...")
            update_query = text("""
                UPDATE cisalog 
                SET sync_type = 'manual' 
                WHERE sync_type IS NULL
            """)
            result = conn.execute(update_query)
            conn.commit()
            print(f"✓ 更新了 {result.rowcount} 条记录的sync_type值")
            
        print("\n表结构更新完成！")
        print("请重启服务以应用所有修改。")
        
    except Exception as e:
        print(f"✗ 更新表结构时出错: {str(e)}")
        sys.exit(1)