from datetime import datetime
from app import create_app, db
from app.nvd.models import SyncLog

if __name__ == '__main__':
    try:
        # 创建Flask应用实例
        app = create_app()
        
        # 在应用上下文中查询数据库
        with app.app_context():
            # 获取所有同步日志
            all_logs = SyncLog.query.all()
            print(f"数据库中共有 {len(all_logs)} 条同步日志记录")
            
            # 获取自动同步的日志
            auto_logs = SyncLog.query.filter_by(action_type='auto').all()
            print(f"其中自动同步(auto)的日志有 {len(auto_logs)} 条")
            
            # 获取手动同步的日志
            manual_logs = SyncLog.query.filter_by(action_type='manual').all()
            print(f"手动同步(manual)的日志有 {len(manual_logs)} 条")
            
            # 显示最近5条日志的详细信息
            print("\n最近5条日志记录：")
            recent_logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).limit(5).all()
            for log in recent_logs:
                print(f"时间: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", end=" | ")
                print(f"类型: {log.action_type}", end=" | ")
                print(f"数量: {log.count}", end=" | ")
                print(f"开始日期: {log.start_date}", end=" | ")
                print(f"结束日期: {log.end_date}")
    except Exception as e:
        print(f"查询同步日志时出错: {str(e)}")