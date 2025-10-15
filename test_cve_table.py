from app import create_app, db
from datetime import datetime
from sqlalchemy import inspect

# 创建测试用的CveDetails模型类（仅用于测试，不影响实际表结构）
class CveDetails(db.Model):
    __tablename__ = 'cvedetails'
    
    id = db.Column(db.Integer, primary_key=True)
    assigner = db.Column(db.String(255))
    assignerSourceName = db.Column(db.String(255))
    cveNumber = db.Column(db.BigInteger)
    cveId = db.Column(db.String(50), unique=True, nullable=False)
    cveYear = db.Column(db.Integer)
    publishDate = db.Column(db.DateTime)
    updateDate = db.Column(db.DateTime)
    # 其他字段省略...
    
    def __repr__(self):
        return f'<CveDetails {self.cveId}>'

# 在应用上下文中运行测试
app = create_app()
with app.app_context():
    try:
        # 检查表是否存在
        inspector = inspect(db.engine)
        table_exists = 'cvedetails' in inspector.get_table_names()
        print(f"cvedetails表是否存在: {table_exists}")
        
        if table_exists:
            # 查询数据总数
            total_count = db.session.query(CveDetails).count()
            print(f"cvedetails表中的记录总数: {total_count}")
            
            # 查询前5条记录
            print("\n前5条记录:")
            first_5_records = db.session.query(CveDetails).limit(5).all()
            for record in first_5_records:
                print(f"ID: {record.id}, CVE ID: {record.cveId}, 发布日期: {record.publishDate}")
        else:
            print("错误: cvedetails表不存在")
    except Exception as e:
        print(f"查询数据库时出错: {str(e)}")