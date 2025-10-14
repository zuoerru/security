from datetime import datetime
from app import db

class NvdData(db.Model):
    __tablename__ = 'nvd'
    
    id = db.Column(db.Integer, primary_key=True)
    cve_id = db.Column(db.String(50), unique=True, nullable=False)
    published_date = db.Column(db.Date, nullable=False)
    last_modified_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    base_score = db.Column(db.Float)
    base_severity = db.Column(db.String(20))
    vector_string = db.Column(db.String(255))
    vendor = db.Column(db.String(255))
    product = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<NvdData {self.cve_id}>'