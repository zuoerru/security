from app import create_app, db
from app.cisa.service import CisaService
from app.cisa.models import CisaLog
import traceback

# 创建应用实例
app = create_app()

with app.app_context():
    print("开始调试同步功能和日志记录...")
    
    try:
        # 直接测试日志记录功能
        print("\n测试日志记录功能:")
        try:
            log_entry = CisaLog(
                status="test",
                message="这是一条测试日志",
                affected_count=0
            )
            db.session.add(log_entry)
            db.session.commit()
            print("✓ 测试日志记录成功")
        except Exception as e:
            print(f"✗ 测试日志记录失败: {str(e)}")
            traceback.print_exc()
            db.session.rollback()
        
        # 检查是否有测试日志
        test_logs = CisaLog.query.filter_by(status="test").all()
        print(f"测试日志数量: {len(test_logs)}")
        
        # 现在测试完整的同步功能
        print("\n测试同步功能:")
        # 模拟调用compare_and_update_db
        success = CisaService.compare_and_update_db()
        print(f"同步结果: {'成功' if success else '失败'}")
        
        # 检查同步后是否有日志记录
        recent_logs = CisaLog.query.order_by(CisaLog.sync_time.desc()).limit(3).all()
        print(f"\n最近的同步日志数量: {len(recent_logs)}")
        
        if recent_logs:
            print("最近的同步日志:")
            for log in recent_logs:
                print(f"时间: {log.sync_time}")
                print(f"状态: {log.status}")
                print(f"影响: {log.affected_count}")
                print(f"消息: {log.message}")
                print("-" * 50)
        
    except Exception as e:
        print(f"调试过程出错: {str(e)}")
        traceback.print_exc()