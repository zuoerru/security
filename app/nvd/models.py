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

class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    action_type = db.Column(db.String(10), nullable=False)  # 'auto' 或 'manual'
    count = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action_type': self.action_type,
            'count': self.count,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None
        }
    
    def __repr__(self):
        return f'<SyncLog {self.timestamp} - {self.action_type}>'