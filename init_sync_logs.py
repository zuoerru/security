#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化同步日志数据库表并从JSON文件迁移现有日志数据
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.nvd.log_service import sync_log_service
from app.nvd.models import SyncLog

if __name__ == '__main__':
    print("正在初始化同步日志表并迁移数据...")
    
    try:
        # 创建Flask应用实例
        app = create_app()
        
        # 应用上下文
        with app.app_context():
            # 创建数据库表
            from app import db
            db.create_all()
            print("SyncLog数据库表创建成功")
            
            # 检查是否有现有的日志表记录
            existing_logs_count = SyncLog.query.count()
            if existing_logs_count > 0:
                print(f"数据库表中已有 {existing_logs_count} 条日志记录，跳过数据迁移")
            else:
                # 从JSON文件迁移数据到数据库
                print("开始从JSON文件迁移日志数据到数据库...")
                sync_log_service.migrate_from_json_to_db()
                
                # 再次查询确认迁移结果
                new_logs_count = SyncLog.query.count()
                print(f"数据迁移完成，数据库表中现在有 {new_logs_count} 条日志记录")
    
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        sys.exit(1)
    
    print("同步日志初始化完成！")
    sys.exit(0)