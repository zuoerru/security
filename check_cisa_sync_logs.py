from app import create_app
from app.cisa.models import CisaLog

app = create_app()
with app.app_context():
    logs = CisaLog.query.order_by(CisaLog.sync_time.desc()).limit(10).all()
    for log in logs:
        print(f'{log.sync_time}: {log.status}, {log.message}, 影响{log.affected_count}条, 类型:{log.sync_type}')