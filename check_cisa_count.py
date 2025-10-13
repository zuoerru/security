from app import create_app, db
from app.cisa.models import CisaData

# 创建应用实例
app = create_app()

with app.app_context():
    count = CisaData.query.count()
    print(f'数据库中共有 {count} 条CISA数据记录')