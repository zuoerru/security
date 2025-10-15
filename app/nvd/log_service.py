import os
import json
from datetime import datetime
import threading
from app import db
from app.nvd.models import NvdData, SyncLog

class NvdLogService:
    """NVD数据同步日志服务"""
    
    # 线程锁，确保日志写入的线程安全
    _lock = threading.Lock()
    
    @classmethod
    def add_log(cls, action_type, count, start_date=None, end_date=None):
        """添加同步日志到数据库
        
        参数:
            action_type: 操作类型（'auto'自动同步, 'manual'手动同步）
            count: 新增记录数量
            start_date: 开始日期
            end_date: 结束日期
        """
        with cls._lock:
            # 创建新日志条目
            new_log = SyncLog(
                action_type=action_type,
                count=count,
                start_date=start_date,
                end_date=end_date
            )
            
            try:
                # 添加到数据库
                db.session.add(new_log)
                db.session.commit()
                
                # 限制日志数量，保留最近1000条
                # 先查询当前日志总数
                total_logs = SyncLog.query.count()
                if total_logs > 1000:
                    # 获取最早的日志记录
                    oldest_logs = SyncLog.query.order_by(SyncLog.timestamp).limit(total_logs - 1000).all()
                    # 删除多余的日志记录
                    for log in oldest_logs:
                        db.session.delete(log)
                    db.session.commit()
                
            except Exception as e:
                # 发生错误时回滚
                db.session.rollback()
                print(f"添加同步日志失败: {str(e)}")
    
    @classmethod
    def get_logs(cls, limit=50):
        """从数据库获取同步日志
        
        参数:
            limit: 返回的最大日志条数
        
        返回:
            日志列表（字典形式）
        """
        try:
            # 查询最新的日志记录
            logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).limit(limit).all()
            # 转换为字典列表
            return [log.to_dict() for log in logs]
        except Exception as e:
            print(f"获取同步日志失败: {str(e)}")
            return []
    
    @classmethod
    def get_last_sync_info(cls):
        """获取最后一次同步信息
        
        返回:
            最后一次同步的日志条目，或None
        """
        try:
            last_log = SyncLog.query.order_by(SyncLog.timestamp.desc()).first()
            return last_log.to_dict() if last_log else None
        except Exception as e:
            print(f"获取最后同步信息失败: {str(e)}")
            return None
    
    @classmethod
    def migrate_from_json_to_db(cls):
        """从JSON文件迁移日志到数据库"""
        # 检查是否有旧的JSON日志文件
        LOG_FILE_PATH = '/data_nfs/121/app/security/app/nvd/sync_logs.json'
        if os.path.exists(LOG_FILE_PATH):
            try:
                with open(LOG_FILE_PATH, 'r') as f:
                    old_logs = json.load(f)
                
                # 导入到数据库
                for log_entry in old_logs:
                    # 检查是否已存在相同的日志记录
                    existing_log = SyncLog.query.filter_by(
                        timestamp=datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S'),
                        action_type=log_entry['action_type']
                    ).first()
                    
                    if not existing_log:
                        # 创建新日志记录
                        new_log = SyncLog(
                            timestamp=datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S'),
                            action_type=log_entry['action_type'],
                            count=log_entry['count'],
                            start_date=datetime.strptime(log_entry['start_date'], '%Y-%m-%d') if log_entry['start_date'] else None,
                            end_date=datetime.strptime(log_entry['end_date'], '%Y-%m-%d') if log_entry['end_date'] else None
                        )
                        db.session.add(new_log)
                    
                db.session.commit()
                print(f"成功从JSON文件迁移了 {len(old_logs)} 条日志到数据库")
                
                # 备份JSON文件
                if os.path.exists(LOG_FILE_PATH):
                    backup_path = LOG_FILE_PATH + '.bak'
                    os.rename(LOG_FILE_PATH, backup_path)
                    print(f"JSON日志文件已备份到: {backup_path}")
                
            except Exception as e:
                db.session.rollback()
                print(f"从JSON文件迁移日志到数据库失败: {str(e)}")

# 初始化日志服务
def init_log_service():
    """初始化日志服务"""
    # 不需要创建文件，数据库表会在应用启动时自动创建
    pass

# 初始化日志服务实例
sync_log_service = NvdLogService()

# 注册到app初始化
def register_log_service(app):
    """将日志服务注册到Flask应用"""
    with app.app_context():
        init_log_service()

# 导出服务实例
sync_log_service = NvdLogService()