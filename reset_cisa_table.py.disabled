from app import create_app, db
from app.cisa.models import CisaData

app = create_app()
with app.app_context():
    # 删除现有的cisa表（如果存在）
    if db.inspect(db.engine).has_table('cisa'):
        CisaData.__table__.drop(db.engine)
        print("已删除旧的cisa表")
    
    # 重新创建cisa表
    db.create_all()
    print("已创建新的cisa表")