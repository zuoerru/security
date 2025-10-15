from datetime import datetime
from app import create_app, db
from app.nvd.models import NvdData, SyncLog

# 创建应用实例
app = create_app()

# 在应用上下文中查询数据库
with app.app_context():
    # 检查10月14日数据
    oct14_date = datetime.strptime('2025-10-14', '%Y-%m-%d').date()
    oct14_count = NvdData.query.filter_by(published_date=oct14_date).count()
    print(f"10月14日数据数量: {oct14_count}")
    
    # 检查最新同步日志
    print("\n最新的5条同步日志:")
    latest_logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).limit(5).all()
    for log in latest_logs:
        print(f"时间: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  类型: {'自动' if log.action_type == 'auto' else '手动'}")
        print(f"  数量: {log.count}")
        print(f"  起止日期: {log.start_date.strftime('%Y-%m-%d')} ~ {log.end_date.strftime('%Y-%m-%d')}")