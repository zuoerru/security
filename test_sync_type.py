#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试同步类型字段是否正常工作
"""
import sys
sys.path.append('/data_nfs/121/app/security')

from app import create_app, db
from app.cisa.models import CisaLog
from app.cisa.service import CisaService
from datetime import datetime

# 创建应用实例
app = create_app()

with app.app_context():
    print("===== 测试同步类型字段 =====")
    
    # 检查数据库表结构
    print("1. 检查数据库表结构...")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = inspector.get_columns('cisalog')
    
    sync_type_exists = False
    for column in columns:
        if column['name'] == 'sync_type':
            sync_type_exists = True
            print(f"✓ sync_type字段存在，类型: {column['type']}")
            print(f"  默认值: {column['default']}")
            break
    
    if not sync_type_exists:
        print("✗ 警告: sync_type字段不存在，请重启服务让数据库变更生效")
    
    # 测试手动同步类型记录
    print("\n2. 测试手动同步类型记录...")
    manual_log = CisaLog(
        status="test",
        message="测试手动同步类型",
        affected_count=0,
        sync_type="manual"
    )
    db.session.add(manual_log)
    
    # 测试自动同步类型记录
    auto_log = CisaLog(
        status="test",
        message="测试自动同步类型",
        affected_count=0,
        sync_type="auto"
    )
    db.session.add(auto_log)
    
    db.session.commit()
    
    # 查询测试记录
    test_logs = CisaLog.query.filter(CisaLog.status == "test").all()
    print(f"  创建了 {len(test_logs)} 条测试记录")
    
    for log in test_logs:
        print(f"  ID: {log.id}, 类型: {log.sync_type}, 消息: {log.message}")
    
    print("\n测试完成。请重启服务应用所有修改并测试实际的同步功能。")