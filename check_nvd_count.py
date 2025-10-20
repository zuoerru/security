from app import create_app, db
from app.nvd.models import NvdData

app = create_app()
with app.app_context():
    print("NVD表记录总数:", NvdData.query.count())