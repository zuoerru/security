from app import create_app, db
from app.cisa.models import CisaData

app = create_app()
with app.app_context():
    print("CISA表记录总数:", CisaData.query.count())