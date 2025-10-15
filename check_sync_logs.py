from datetime import datetime, timedelta
from app import create_app, db
from app.nvd.models import SyncLog, NvdData

# 创建应用实例
app = create_app()

# 在应用上下文中查询数据库
with app.app_context():
    # 查看最近的同步日志
    print("最近的同步日志：")
    recent_logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).limit(20).all()
    for log in recent_logs:
        print(f"时间: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, \
              类型: {'自动' if log.action_type == 'auto' else '手动'}, \
              数量: {log.count}, \
              起始日期: {log.start_date.strftime('%Y-%m-%d') if log.start_date else 'N/A'}, \
              结束日期: {log.end_date.strftime('%Y-%m-%d') if log.end_date else 'N/A'}")
    
    # 检查NVD表中最新的数据日期
    print("\nNVD表中最新的10条记录：")
    recent_nvd_data = NvdData.query.order_by(NvdData.published_date.desc()).limit(10).all()
    for data in recent_nvd_data:
        print(f"CVE ID: {data.cve_id}, 发布日期: {data.published_date.strftime('%Y-%m-%d')}")
    
    # 检查是否有2025-10-14的数据
    print("\n检查2025-10-14的数据：")
    target_date = datetime.strptime('2025-10-14', '%Y-%m-%d').date()
    data_count = NvdData.query.filter_by(published_date=target_date).count()
    print(f"2025-10-14的数据数量: {data_count}")