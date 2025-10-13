from app import db
from datetime import datetime

class CisaData(db.Model):
    __tablename__ = 'cisa'
    
    id = db.Column(db.Integer, primary_key=True)
    vuln_id = db.Column(db.String(50), unique=True, nullable=False)
    vendor_project = db.Column(db.String(255), nullable=False)
    product = db.Column(db.String(255))
    vulnerability_name = db.Column(db.String(255), nullable=False)
    date_added = db.Column(db.Date, nullable=False)
    short_description = db.Column(db.Text)
    required_action = db.Column(db.Text)
    due_date = db.Column(db.Date)
    cve_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CisaData {self.vuln_id}>'