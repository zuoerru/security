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

class CisaLog(db.Model):
    __tablename__ = 'cisalog'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), nullable=False)  # success 或 failure
    message = db.Column(db.Text)
    affected_count = db.Column(db.Integer, default=0)  # 影响的记录数
    sync_type = db.Column(db.String(20), default='manual')  # manual或auto，区分手动和自动同步
    
    def __repr__(self):
        return f'<CisaLog {self.sync_time} - {self.status}>'