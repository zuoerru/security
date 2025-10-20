import sys
import os
sys.path.append('/data_nfs/121/app/security')

from app import create_app, db

app = create_app()

with app.app_context():
    # 检查并修复nvd表的编码
    try:
        print("检查并修复nvd表的编码...")
        
        # 首先检查表是否存在
        inspector = db.inspect(db.engine)
        if 'nvd' in inspector.get_table_names():
            # 修复表编码
            db.engine.execute("ALTER TABLE nvd CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print("nvd表编码已修复为utf8mb4")
        else:
            print("nvd表不存在")
            
        # 也检查并修复sync_logs表
        if 'sync_logs' in inspector.get_table_names():
            db.engine.execute("ALTER TABLE sync_logs CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print("sync_logs表编码已修复为utf8mb4")
        else:
            print("sync_logs表不存在")
    except Exception as e:
        print(f"修复数据库编码时出错: {str(e)}")
