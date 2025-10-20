from app import create_app, db
from sqlalchemy import text

# 创建应用实例
app = create_app()

with app.app_context():
    print("开始修复cisalog表的字符集...")
    
    try:
        # 修改表的字符集
        db.session.execute(text("ALTER TABLE cisalog CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        db.session.commit()
        print("✓ 成功修改cisalog表的字符集为utf8mb4")
        
        # 验证修改是否生效
        result = db.session.execute(text("SHOW CREATE TABLE cisalog"))
        create_table_sql = result.fetchone()[1]
        print(f"表结构: {create_table_sql}")
        
        # 测试是否能插入中文数据
        print("\n测试插入中文数据:")
        from app.cisa.models import CisaLog
        test_log = CisaLog(
            status="test",
            message="这是一条测试日志 - 包含中文字符",
            affected_count=1
        )
        db.session.add(test_log)
        db.session.commit()
        print("✓ 成功插入包含中文的测试日志")
        
        # 查询测试数据
        logs = CisaLog.query.filter_by(status="test").all()
        print(f"找到 {len(logs)} 条测试日志")
        
    except Exception as e:
        print(f"✗ 修复过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()