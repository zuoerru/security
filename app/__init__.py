from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import pymysql
pymysql.install_as_MySQLdb()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # 配置数据库连接
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Xl123,56@192.168.233.121:3306/security'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        from app.cisa.models import CisaData
        try:
            # 检查表是否存在，不存在则创建
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if not inspector.has_table('cisa'):
                db.create_all()
                print("CISA表创建成功")
        except Exception as e:
            print(f"创建数据库表时出错: {str(e)}")
    
    # 注册蓝图
    from app.cisa.routes import cisa_bp
    from app.cve.routes import cve_bp
    from app.nessus.routes import nessus_bp
    
    app.register_blueprint(cisa_bp)
    app.register_blueprint(cve_bp)
    app.register_blueprint(nessus_bp)
    
    # 主页路由
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # 启动CISA数据同步调度器
    try:
        from app.cisa.service import start_scheduler
        start_scheduler(app)
    except Exception as e:
        print(f"启动CISA数据同步调度器时出错: {str(e)}")
    
    return app