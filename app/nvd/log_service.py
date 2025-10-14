import os
import json
from datetime import datetime
import threading
from app import db
from app.nvd.models import NvdData

class NvdLogService:
    """NVD数据同步日志服务"""
    
    # 日志文件路径
    LOG_FILE_PATH = '/data_nfs/121/app/security/app/nvd/sync_logs.json'
    
    # 线程锁，确保日志写入的线程安全
    _lock = threading.Lock()
    
    @classmethod
    def _ensure_log_file_exists(cls):
        """确保日志文件存在"""
        if not os.path.exists(cls.LOG_FILE_PATH):
            # 创建目录（如果不存在）
            log_dir = os.path.dirname(cls.LOG_FILE_PATH)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            # 创建空的日志文件
            with open(cls.LOG_FILE_PATH, 'w') as f:
                json.dump([], f)
    
    @classmethod
    def add_log(cls, action_type, count, start_date=None, end_date=None):
        """添加同步日志
        
        参数:
            action_type: 操作类型（'auto'自动同步, 'manual'手动同步）
            count: 新增记录数量
            start_date: 开始日期
            end_date: 结束日期
        """
        with cls._lock:
            cls._ensure_log_file_exists()
            
            # 读取现有日志
            with open(cls.LOG_FILE_PATH, 'r') as f:
                logs = json.load(f)
            
            # 创建新日志条目
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action_type': action_type,
                'count': count,
                'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
                'end_date': end_date.strftime('%Y-%m-%d') if end_date else None
            }
            
            # 添加到日志列表开头
            logs.insert(0, log_entry)
            
            # 限制日志数量，保留最近100条
            if len(logs) > 100:
                logs = logs[:100]
            
            # 写回日志文件
            with open(cls.LOG_FILE_PATH, 'w') as f:
                json.dump(logs, f, indent=2)
    
    @classmethod
    def get_logs(cls, limit=50):
        """获取同步日志
        
        参数:
            limit: 返回的最大日志条数
        
        返回:
            日志列表
        """
        with cls._lock:
            cls._ensure_log_file_exists()
            
            # 读取日志文件
            with open(cls.LOG_FILE_PATH, 'r') as f:
                logs = json.load(f)
            
            # 返回指定数量的日志
            return logs[:limit]
    
    @classmethod
    def get_last_sync_info(cls):
        """获取最后一次同步信息
        
        返回:
            最后一次同步的日志条目，或None
        """
        logs = cls.get_logs(1)
        return logs[0] if logs else None

# 初始化日志服务
def init_log_service():
    """初始化日志服务"""
    NvdLogService._ensure_log_file_exists()

# 注册到app初始化
def register_log_service(app):
    """将日志服务注册到Flask应用"""
    with app.app_context():
        init_log_service()

# 导出服务实例
sync_log_service = NvdLogService()