from datetime import datetime, timedelta
from app import create_app
from app.nvd.service import sync_daily_data
from app.nvd.log_service import sync_log_service

if __name__ == '__main__':
    try:
        print("正在创建Flask应用上下文...")
        app = create_app()
        
        with app.app_context():
            print("手动触发自动同步任务...")
            
            # 调用与定时任务相同的函数进行同步
            # 但不通过定时任务机制，直接调用函数
            print(f"开始同步NVD数据 (手动触发自动同步模式)...")
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 同步最近一天的数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
            
            from app.nvd.service import NvdService
            imported_count = NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
            
            # 手动添加一条自动同步日志
            sync_log_service.add_log('auto', imported_count, start_date, end_date)
            
            # 记录结束时间
            end_time = datetime.now()
            
            print(f"NVD数据同步完成，新增 {imported_count} 条记录")
            print(f"同步耗时: {end_time - start_time}")
            
            # 验证日志是否已添加
            last_log = sync_log_service.get_last_sync_info()
            if last_log:
                print(f"\n最后一条同步日志信息:")
                print(f"  时间戳: {last_log['timestamp']}")
                print(f"  类型: {last_log['action_type']}")
                print(f"  数量: {last_log['count']}")
                print(f"  开始日期: {last_log['start_date']}")
                print(f"  结束日期: {last_log['end_date']}")
            
            # 统计当前自动同步日志数量
            all_logs = sync_log_service.get_logs(limit=1000)
            auto_logs = [log for log in all_logs if log['action_type'] == 'auto']
            print(f"\n当前数据库中自动同步日志总数: {len(auto_logs)}")
    except Exception as e:
        print(f"手动触发自动同步失败: {str(e)}")