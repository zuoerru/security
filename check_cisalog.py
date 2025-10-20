from app import create_app, db
from app.cisa.models import CisaLog
import datetime

# 创建应用实例
app = create_app()

with app.app_context():
    # 查询最近的5条同步日志
    recent_logs = CisaLog.query.order_by(CisaLog.sync_time.desc()).limit(5).all()
    
    print(f"最近的同步日志记录 (共 {CisaLog.query.count()} 条):")
    print("="*80)
    
    if recent_logs:
        for log in recent_logs:
            print(f"时间: {log.sync_time}")
            print(f"状态: {log.status}")
            print(f"影响记录数: {log.affected_count}")
            print(f"消息: {log.message}")
            print("-"*80)
    else:
        print("未找到同步日志记录")