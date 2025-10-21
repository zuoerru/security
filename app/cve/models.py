from app import db
from datetime import datetime

class Cves(db.Model):
    __tablename__ = 'cves'
    
    id = db.Column(db.Integer, primary_key=True)
    cve_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    published_date = db.Column(db.DateTime, nullable=False)
    last_modified_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text(collation='utf8mb4_unicode_ci'))
    base_score = db.Column(db.Float)
    base_severity = db.Column(db.String(20))
    attack_vector = db.Column(db.String(50))
    attack_complexity = db.Column(db.String(50))
    privileges_required = db.Column(db.String(50))
    user_interaction = db.Column(db.String(50))
    scope = db.Column(db.String(50))
    confidentiality_impact = db.Column(db.String(50))
    integrity_impact = db.Column(db.String(50))
    availability_impact = db.Column(db.String(50))
    cwe_id = db.Column(db.String(20))
    references = db.Column(db.Text(collation='utf8mb4_unicode_ci'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Cves {self.cve_id}>'

class CvesLog(db.Model):
    __tablename__ = 'cveslogs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success 或 failure
    message = db.Column(db.Text(collation='utf8mb4_unicode_ci'))
    affected_count = db.Column(db.Integer, default=0)  # 影响的记录数
    sync_type = db.Column(db.String(20), default='manual')  # manual或auto，区分手动和自动同步
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    def __repr__(self):
        return f'<CvesLog {self.sync_time} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_time': self.sync_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'message': self.message,
            'affected_count': self.affected_count,
            'sync_type': self.sync_type,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None
        }