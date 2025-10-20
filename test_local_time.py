#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修改后的sync_time字段是否使用本地时间
"""
import sys
sys.path.append('/data_nfs/121/app/security')

from app import create_app, db
from app.cisa.models import CisaLog
from datetime import datetime

# 创建应用实例
app = create_app()

with app.app_context():
    print("===== 测试本地时间同步 =====")
    
    # 获取当前本地时间
    current_local = datetime.now()
    print(f"当前本地时间: {current_local}")
    
    # 创建一条新的测试日志记录
    test_log = CisaLog(
        status="test_local_time",
        message="测试本地时间记录",
        affected_count=0
    )
    db.session.add(test_log)
    db.session.commit()
    
    # 查询刚创建的记录
    new_log = CisaLog.query.filter_by(status="test_local_time").order_by(CisaLog.sync_time.desc()).first()
    if new_log:
        print(f"\n创建的测试日志记录:")
        print(f"日志ID: {new_log.id}")
        print(f"sync_time值: {new_log.sync_time}")
        
        # 比较时间差（应该很小）
        time_diff = (current_local - new_log.sync_time).total_seconds()
        print(f"与当前时间差: {time_diff:.2f} 秒")
        
        if abs(time_diff) < 5:  # 允许5秒误差
            print("✓ 成功：sync_time字段现在使用本地时间")
        else:
            print("✗ 警告：sync_time与当前本地时间差异较大")
    else:
        print("✗ 错误：未找到创建的测试日志记录")
    
    print("\n请手动触发同步来验证实际同步操作中的时间记录是否正确")