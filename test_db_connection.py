from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT 1')).scalar()
            print(f'数据库连接成功: {result}')
    except Exception as e:
        print(f'数据库连接失败: {str(e)}')