#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查CISA同步日志的时间戳是否正确
"""
import sys
sys.path.append('/data_nfs/121/app/security')

from app import create_app, db
from app.cisa.models import CisaLog
from datetime import datetime
import pytz

# 创建应用实例
app = create_app()

with app.app_context():
    print("===== CISA同步时间检查 =====")
    
    # 获取当前时间
    current_utc = datetime.utcnow()
    current_local = datetime.now()
    print(f"当前UTC时间: {current_utc}")
    print(f"当前本地时间: {current_local}")
    
    # 尝试获取时区信息
    try:
        # 假设服务器在中国时区
        china_tz = pytz.timezone('Asia/Shanghai')
        current_china = datetime.now(china_tz)
        print(f"当前中国时间: {current_china}")
    except Exception as e:
        print(f"获取时区信息失败: {e}")
    
    # 查询最近的5条同步日志
    logs = CisaLog.query.order_by(CisaLog.sync_time.desc()).limit(5).all()
    
    if not logs:
        print("\n没有找到同步日志记录")
    else:
        print(f"\n找到 {len(logs)} 条最近的同步日志记录:")
        print("-" * 80)
        print(f"{'ID':<5} {'UTC同步时间':<25} {'本地时间(估算)':<25} {'状态':<10} {'影响记录数':<10}")
        print("-" * 80)
        
        for log in logs:
            # 显示UTC时间
            utc_time = log.sync_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 估算本地时间（假设UTC+8）
            try:
                # 简单的UTC+8转换（不考虑夏令时）
                import datetime as dt
                local_time_est = (log.sync_time + dt.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                local_time_est = "无法计算"
            
            print(f"{log.id:<5} {utc_time:<25} {local_time_est:<25} {log.status:<10} {log.affected_count:<10}")
        
        print("-" * 80)
        print("\n注意：sync_time字段存储的是UTC时间，如果需要显示本地时间，前端需要进行时区转换")
    
    # 检查数据库表结构
    print("\n===== 表结构信息 =====")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = inspector.get_columns('cisalog')
    
    for column in columns:
        if column['name'] == 'sync_time':
            print(f"sync_time字段类型: {column['type']}")
            print(f"sync_time字段默认值: {column['default']}")
    
    print("\n检查完成。如果sync_time显示为UTC时间但需要显示本地时间，需要在前端或服务端进行时区转换。")