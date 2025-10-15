from flask import Flask, render_template
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
    
    # 设置secret_key用于会话加密（flash消息需要）
    app.config['SECRET_KEY'] = '78d1f34b2e5c8a9d0f6e7b3a4c2d5f8e9a0b1c7d2f3a4b5e6c7d8e9f0a1b2c3d'
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        # 导入所有模型
        from app.cisa.models import CisaData
        from app.nvd.models import NvdData
        
        try:
            # 检查表是否存在，不存在则创建
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # 创建CISA表
            if not inspector.has_table('cisa'):
                db.create_all()
                print("CISA表创建成功")
            
            # 创建NVD表
            if not inspector.has_table('nvd'):
                db.create_all()
                print("NVD表创建成功")
                
        except Exception as e:
            print(f"创建数据库表时出错: {str(e)}")
    
    # 注册蓝图
    from app.cisa.routes import cisa_bp
    from app.cve.routes import cve_bp
    from app.nessus.routes import nessus_bp
    from app.nvd.routes import nvd_bp
    
    app.register_blueprint(cisa_bp)
    app.register_blueprint(cve_bp)
    app.register_blueprint(nessus_bp)
    app.register_blueprint(nvd_bp)
    
    # 主页路由
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # 初始化NVD日志服务
    try:
        from app.nvd.log_service import register_log_service
        register_log_service(app)
        print("NVD日志服务初始化成功")
    except Exception as e:
        print(f"初始化NVD日志服务时出错: {str(e)}")
    
    # 启动CISA数据同步调度器
    try:
        from app.cisa.service import start_scheduler as start_cisa_scheduler
        start_cisa_scheduler(app)
    except Exception as e:
        print(f"启动CISA数据同步调度器时出错: {str(e)}")
    
    # 启动NVD数据同步调度器
    try:
        from app.nvd.service import start_scheduler as start_nvd_scheduler
        start_nvd_scheduler(app)
    except Exception as e:
        print(f"启动NVD数据同步调度器时出错: {str(e)}")
    
    return app