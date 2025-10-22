from app import db
from datetime import datetime, timezone, timedelta

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
    sync_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success 或 failure
    message = db.Column(db.Text(collation='utf8mb4_unicode_ci'))
    affected_count = db.Column(db.Integer, default=0)  # 影响的记录数
    insert_count = db.Column(db.Integer, default=0)  # 新增记录数
    update_count = db.Column(db.Integer, default=0)  # 更新记录数
    sync_type = db.Column(db.String(20), default='manual')  # manual或auto，区分手动和自动同步
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    def __repr__(self):
        return f'<CvesLog {self.sync_time} - {self.status}>'
    
    def to_dict(self):
        # 将UTC时间转换为中国时区（UTC+8）
        china_timezone = timezone(timedelta(hours=8))
        # 如果sync_time没有时区信息，先添加UTC时区
        if self.sync_time.tzinfo is None:
            sync_time_utc = self.sync_time.replace(tzinfo=timezone.utc)
        else:
            sync_time_utc = self.sync_time
        # 转换到中国时区
        sync_time_china = sync_time_utc.astimezone(china_timezone)
        
        return {
            'id': self.id,
            'sync_time': sync_time_china.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'message': self.message,
            'affected_count': self.affected_count,
            'insert_count': self.insert_count,
            'update_count': self.update_count,
            'sync_type': self.sync_type,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None
        }