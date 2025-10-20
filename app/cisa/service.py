import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import schedule
import time
from threading import Thread
from flask import current_app
from .models import CisaData, CisaLog
from app import db

# 存储应用实例的引用
_app = None

def set_app(app):
    """设置应用实例引用，用于在定时任务中访问应用上下文"""
    global _app
    _app = app

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOAD_DIR = BASE_DIR

class CisaService:
    @staticmethod
    def get_csv_url():
        """从CISA网站获取CSV下载链接"""
        url = 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog'
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # 查找CSV下载链接
            csv_link = None
            # 寻找包含CSV文本的按钮或链接
            for link in soup.find_all('a', href=True):
                if 'csv' in link.get('href', '').lower() or 'CSV' in link.text:
                    csv_link = link.get('href')
                    break
            
            # 如果没找到，尝试其他方式
            if not csv_link:
                for button in soup.find_all('button'):
                    if 'csv' in button.text.lower():
                        # 检查按钮相关的链接或数据属性
                        if button.get('data-url'):
                            csv_link = button.get('data-url')
                            break
                        # 或者检查父元素的链接
                        parent = button.find_parent('a')
                        if parent and parent.get('href'):
                            csv_link = parent.get('href')
                            break
            
            if csv_link and not csv_link.startswith('http'):
                csv_link = f'https://www.cisa.gov{csv_link}'
                
            return csv_link
        except Exception as e:
            print(f"获取CSV链接失败: {str(e)}")
            return None
    
    @staticmethod
    def download_csv():        
        """下载CSV文件并按日期命名"""
        try:
            csv_url = CisaService.get_csv_url()
            if not csv_url:
                print("未找到CSV下载链接")
                return None
            
            # 获取当前日期，格式为YYYYMMDD
            current_date = datetime.now().strftime('%Y%m%d')
            file_name = f'cisa-{current_date}.csv'
            file_path = os.path.join(DOWNLOAD_DIR, file_name)
            
            response = requests.get(csv_url, timeout=60)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"CSV文件已下载: {file_path}")
            return file_path
        except Exception as e:
            print(f"下载CSV文件失败: {str(e)}")
            return None
    
    @staticmethod
    def get_previous_day_file():
        """获取前一天的CSV文件路径"""
        previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        file_path = os.path.join(DOWNLOAD_DIR, f'cisa-{previous_date}.csv')
        if os.path.exists(file_path):
            return file_path
        return None
    
    @staticmethod
    def get_by_vuln_id(vuln_id):
        """根据漏洞ID获取单个漏洞详情"""
        return CisaData.query.filter_by(vuln_id=vuln_id).first()
    
    @staticmethod
    def compare_and_update_db(sync_type='auto'):
        """比较当天和前一天的CSV文件，将新增内容更新到数据库，并记录同步日志"""
        affected_count = 0
        message = ""
        status = "success"
        # 默认使用auto表示自动同步，手动调用时传入manual
        
        current_file = CisaService.download_csv()
        if not current_file:
            message = "下载CSV文件失败"
            status = "failure"
            # 记录失败日志
            CisaService._log_sync_result(status, message, affected_count)
            return False
        
        previous_file = CisaService.get_previous_day_file()
        
        try:
            # 读取当前CSV文件
            current_df = pd.read_csv(current_file)
            
            if previous_file:
                # 读取前一天的CSV文件
                previous_df = pd.read_csv(previous_file)
                
                # 找出新增的内容（基于cveID列）
                # 使用cveID作为比较的唯一标识
                vuln_id_column = None
                for col in current_df.columns:
                    if 'cve' in col.lower() and 'id' in col.lower():
                        vuln_id_column = col
                        break
                
                if vuln_id_column:
                    # 基于cveID列比较
                    current_ids = set(current_df[vuln_id_column])
                    previous_ids = set(previous_df[vuln_id_column])
                    new_ids = current_ids - previous_ids
                    new_entries = current_df[current_df[vuln_id_column].isin(new_ids)]
                else:
                    # 如果找不到cveID列，使用所有列进行比较
                    merged = pd.merge(current_df, previous_df, how='outer', indicator=True)
                    new_entries = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
            else:
                # 如果没有前一天的文件，所有内容都视为新增
                new_entries = current_df
            
            # 使用当前应用上下文或_app上下文
            try:
                # 尝试直接使用当前上下文（如果存在）
                if not new_entries.empty:
                    for _, row in new_entries.iterrows():
                        # 获取vuln_id
                        vuln_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                        
                        # 检查记录是否已存在
                        existing_record = CisaData.query.filter_by(vuln_id=vuln_id).first()
                        
                        if existing_record:
                            # 如果记录存在，则更新
                            existing_record.vendor_project = CisaService._get_value(row, ['vendorProject', 'Vendor/Project', 'vendor'], str)
                            existing_record.product = CisaService._get_value(row, ['product', 'Product'], str)
                            existing_record.vulnerability_name = CisaService._get_value(row, ['vulnerabilityName', 'Vulnerability Name'], str)
                            existing_record.date_added = CisaService._parse_date(CisaService._get_value(row, ['dateAdded', 'Date Added'], str))
                            
                            # 对描述字段应用额外的安全处理
                            raw_description = CisaService._get_value(row, ['shortDescription', 'Short Description'], str)
                            existing_record.short_description = CisaService._ensure_safe_description(raw_description)
                            
                            existing_record.required_action = CisaService._get_value(row, ['requiredAction', 'Required Action'], str)
                            existing_record.due_date = CisaService._parse_date(CisaService._get_value(row, ['dueDate', 'Due Date'], str))
                            existing_record.cve_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                            existing_record.updated_at = datetime.utcnow()
                        else:
                            # 如果记录不存在，则创建新记录
                            # 获取基础值并应用特殊处理
                            vendor_project = CisaService._get_value(row, ['vendorProject', 'Vendor/Project', 'vendor'], str)
                            product = CisaService._get_value(row, ['product', 'Product'], str)
                            vulnerability_name = CisaService._get_value(row, ['vulnerabilityName', 'Vulnerability Name'], str)
                            date_added = CisaService._parse_date(CisaService._get_value(row, ['dateAdded', 'Date Added'], str))
                            
                            # 对描述字段应用额外的安全处理
                            raw_description = CisaService._get_value(row, ['shortDescription', 'Short Description'], str)
                            short_description = CisaService._ensure_safe_description(raw_description)
                            
                            required_action = CisaService._get_value(row, ['requiredAction', 'Required Action'], str)
                            due_date = CisaService._parse_date(CisaService._get_value(row, ['dueDate', 'Due Date'], str))
                            cve_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                            
                            # 创建CisaData对象
                            cisa_data = CisaData(
                                vuln_id=vuln_id,
                                vendor_project=vendor_project,
                                product=product,
                                vulnerability_name=vulnerability_name,
                                date_added=date_added,
                                short_description=short_description,
                                required_action=required_action,
                                due_date=due_date,
                                cve_id=cve_id
                            )
                            db.session.add(cisa_data)
                    
                    db.session.commit()
                    affected_count = len(new_entries)
                    message = f"成功导入 {affected_count} 条新记录到数据库"
                    print(message)
                else:
                    message = "没有发现新增记录"
                    print(message)
                
                # 记录成功日志
                CisaService._log_sync_result(status, message, affected_count, sync_type)
                return True
            except RuntimeError:
                # 如果没有应用上下文，则使用_app上下文（定时任务情况）
                with _app.app_context():
                    if not new_entries.empty:
                        for _, row in new_entries.iterrows():
                            # 获取vuln_id
                            vuln_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                            
                            # 检查记录是否已存在
                            existing_record = CisaData.query.filter_by(vuln_id=vuln_id).first()
                            
                            if existing_record:
                                # 如果记录存在，则更新
                                existing_record.vendor_project = CisaService._get_value(row, ['vendorProject', 'Vendor/Project', 'vendor'], str)
                                existing_record.product = CisaService._get_value(row, ['product', 'Product'], str)
                                existing_record.vulnerability_name = CisaService._get_value(row, ['vulnerabilityName', 'Vulnerability Name'], str)
                                existing_record.date_added = CisaService._parse_date(CisaService._get_value(row, ['dateAdded', 'Date Added'], str))
                                
                                # 对描述字段应用额外的安全处理
                                raw_description = CisaService._get_value(row, ['shortDescription', 'Short Description'], str)
                                existing_record.short_description = CisaService._ensure_safe_description(raw_description)
                                
                                existing_record.required_action = CisaService._get_value(row, ['requiredAction', 'Required Action'], str)
                                existing_record.due_date = CisaService._parse_date(CisaService._get_value(row, ['dueDate', 'Due Date'], str))
                                existing_record.cve_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                                existing_record.updated_at = datetime.utcnow()
                            else:
                                # 如果记录不存在，则创建新记录
                                # 获取基础值并应用特殊处理
                                vendor_project = CisaService._get_value(row, ['vendorProject', 'Vendor/Project', 'vendor'], str)
                                product = CisaService._get_value(row, ['product', 'Product'], str)
                                vulnerability_name = CisaService._get_value(row, ['vulnerabilityName', 'Vulnerability Name'], str)
                                date_added = CisaService._parse_date(CisaService._get_value(row, ['dateAdded', 'Date Added'], str))
                                
                                # 对描述字段应用额外的安全处理
                                raw_description = CisaService._get_value(row, ['shortDescription', 'Short Description'], str)
                                short_description = CisaService._ensure_safe_description(raw_description)
                                
                                required_action = CisaService._get_value(row, ['requiredAction', 'Required Action'], str)
                                due_date = CisaService._parse_date(CisaService._get_value(row, ['dueDate', 'Due Date'], str))
                                cve_id = CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                                
                                # 创建CisaData对象
                                cisa_data = CisaData(
                                    vuln_id=vuln_id,
                                    vendor_project=vendor_project,
                                    product=product,
                                    vulnerability_name=vulnerability_name,
                                    date_added=date_added,
                                    short_description=short_description,
                                    required_action=required_action,
                                    due_date=due_date,
                                    cve_id=cve_id
                                )
                                db.session.add(cisa_data)
                        
                        db.session.commit()
                        affected_count = len(new_entries)
                        message = f"成功导入 {affected_count} 条新记录到数据库"
                        print(message)
                    else:
                        message = "没有发现新增记录"
                        print(message)
                    
                    # 记录成功日志
                    CisaService._log_sync_result(status, message, affected_count, sync_type)
                    return True
        except Exception as e:
            error_msg = f"比较和更新数据库失败: {str(e)}"
            print(error_msg)
            status = "failure"
            message = error_msg
            # 尝试使用当前上下文回滚
            try:
                db.session.rollback()
                CisaService._log_sync_result(status, message, affected_count, sync_type)
            except RuntimeError:
                # 如果没有应用上下文，则使用_app上下文
                with _app.app_context():
                    db.session.rollback()
                    CisaService._log_sync_result(status, message, affected_count, sync_type)
            return False
    
    @staticmethod
    def _log_sync_result(status, message, affected_count, sync_type='manual'):
        """记录同步操作的结果到数据库日志表"""
        try:
            # 尝试直接使用当前上下文（如果存在）
            log_entry = CisaLog(
                status=status,
                message=message,
                affected_count=affected_count,
                sync_type=sync_type
            )
            db.session.add(log_entry)
            db.session.commit()
        except RuntimeError:
            # 如果没有应用上下文，则使用_app上下文（定时任务情况）
            try:
                with _app.app_context():
                    log_entry = CisaLog(
                        status=status,
                        message=message,
                        affected_count=affected_count,
                        sync_type=sync_type
                    )
                    db.session.add(log_entry)
                    db.session.commit()
            except Exception as e:
                print(f"记录同步日志失败（使用_app上下文）: {str(e)}")
                with _app.app_context():
                    db.session.rollback()
        except Exception as e:
            print(f"记录同步日志失败: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
    
    @staticmethod
    def get_sync_logs(page=1, per_page=20):
        """获取同步日志记录，支持分页"""
        # 按时间倒序排列，最新的记录在前
        query = CisaLog.query.order_by(CisaLog.sync_time.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_logs_count():
        """获取日志记录总数"""
        return CisaLog.query.count()
    
    @staticmethod
    def _get_value(row, possible_columns, value_type=str):
        """尝试从DataFrame行中获取值，支持多种可能的列名，并处理字符串编码"""
        for col in possible_columns:
            if col in row.index:
                val = row[col]
                if pd.isna(val):
                    return None if value_type == str else value_type()
                try:
                    # 如果是字符串类型，进行编码处理
                    if value_type == str and isinstance(val, str):
                        # 1. 首先导入re模块
                        import re
                        # 2. 更彻底地处理字符编码问题
                        # 只保留ASCII字符和常用可打印字符
                        val = ''.join(char if 32 <= ord(char) <= 126 or char in '\t\n\r' else '?' for char in val)
                        # 3. 完全移除UTF-8替换字符和其他潜在问题字符
                        val = re.sub(r'[\xEF\xBF\xBD]', '', val)  # 完全移除替换字符
                        # 4. 使用ASCII编码并忽略错误字符
                        val = val.encode('ascii', errors='ignore').decode('ascii')
                        # 5. 限制字符串长度（给数据库字段更多余量）
                        if len(val) > 800:  # 进一步减少长度限制
                            val = val[:797] + '...'
                        # 6. 清理空格
                        val = re.sub(r'\s+', ' ', val).strip()
                    return value_type(val)
                except Exception as e:
                    # 如果转换失败，返回空字符串或安全默认值
                    return '' if value_type == str else value_type()
        return None if value_type == str else value_type()
    
    @staticmethod
    def _ensure_safe_description(description):
        """确保描述字段安全，只保留常见的可打印字符"""
        if not description or not isinstance(description, str):
            return ''
        
        # 仅保留字母、数字、常见标点符号和空格
        safe_chars = re.sub(r'[^a-zA-Z0-9\s\.,!\?\-\(\)\[\]\{\}"\'\:\;\/\_\@\#\$\%\^\&\*\+\=]', '', str(description))
        
        # 限制长度
        return safe_chars[:700]
    
    @staticmethod
    def _parse_date(date_str):
        """解析日期字符串为datetime对象"""
        if not date_str or pd.isna(date_str):
            return None
        
        # 尝试多种日期格式
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y', '%d-%b-%Y']
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except:
                continue
        
        return None
    
    @staticmethod
    def get_all_data(page=1, per_page=20, sort_by='', sort_order=''):
        """从数据库获取所有CISA数据，支持分页和排序"""
        query = CisaData.query
        
        # 添加排序
        if sort_by == 'date_added':
            if sort_order == 'asc':
                query = query.order_by(CisaData.date_added.asc())
            else:
                query = query.order_by(CisaData.date_added.desc())
        else:
            # 默认按日期降序排序
            query = query.order_by(CisaData.date_added.desc())
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def search_data(query, page=1, per_page=20, sort_by='', sort_order=''):
        """根据查询条件搜索CISA数据，支持分页和排序"""
        search = f"%{query}%"
        query = CisaData.query.filter(
            CisaData.vendor_project.like(search) | 
            CisaData.product.like(search) |
            CisaData.vulnerability_name.like(search) |
            CisaData.cve_id.like(search)
        )
        
        # 添加排序
        if sort_by == 'date_added':
            if sort_order == 'asc':
                query = query.order_by(CisaData.date_added.asc())
            else:
                query = query.order_by(CisaData.date_added.desc())
        else:
            # 默认按日期降序排序
            query = query.order_by(CisaData.date_added.desc())
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_total_count():
        """获取CISA数据的总条数"""
        return CisaData.query.count()
    
    @staticmethod
    def get_search_count(query):
        """获取搜索结果的总条数"""
        search = f"%{query}%"
        return CisaData.query.filter(
            CisaData.vendor_project.like(search) | 
            CisaData.product.like(search) |
            CisaData.vulnerability_name.like(search) |
            CisaData.cve_id.like(search)
        ).count()

# 定时任务相关功能
def run_scheduled_tasks():
    """运行定时任务"""
    # 每6小时执行CISA数据更新
    schedule.every(6).hours.do(CisaService.compare_and_update_db, sync_type='auto')
    
    # 持续运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler(app):
    """在后台线程中启动调度器"""
    # 设置应用实例引用
    set_app(app)
    
    # 启动定时任务线程
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    print("CISA数据同步调度器已启动")
    print("CISA模块已配置定时任务，每6小时自动同步数据")
    
    # 初始运行一次，避免启动后长时间不更新
    Thread(target=lambda: time.sleep(60) or CisaService.compare_and_update_db(sync_type='auto')).start()
    print("服务启动后将在1分钟后开始同步CISA数据...")
    print("启动时延迟同步线程已启动，将在1分钟后执行同步操作")