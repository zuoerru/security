import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import schedule
import time
from threading import Thread
from flask import current_app
from .models import CisaData
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
    def compare_and_update_db():
        """比较当天和前一天的CSV文件，将新增内容更新到数据库"""
        current_file = CisaService.download_csv()
        if not current_file:
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
            
            # 将新增内容导入数据库
            if not new_entries.empty:
                with _app.app_context():
                    for _, row in new_entries.iterrows():
                        # 映射CSV列到数据库字段 - 使用实际的CSV列名
                        cisa_data = CisaData(
                            vuln_id=CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str),  # 使用cveID作为vuln_id
                            vendor_project=CisaService._get_value(row, ['vendorProject', 'Vendor/Project', 'vendor'], str),
                            product=CisaService._get_value(row, ['product', 'Product'], str),
                            vulnerability_name=CisaService._get_value(row, ['vulnerabilityName', 'Vulnerability Name'], str),
                            date_added=CisaService._parse_date(CisaService._get_value(row, ['dateAdded', 'Date Added'], str)),
                            short_description=CisaService._get_value(row, ['shortDescription', 'Short Description'], str),
                            required_action=CisaService._get_value(row, ['requiredAction', 'Required Action'], str),
                            due_date=CisaService._parse_date(CisaService._get_value(row, ['dueDate', 'Due Date'], str)),
                            cve_id=CisaService._get_value(row, ['cveID', 'CVE ID', 'CVE'], str)
                        )
                        db.session.add(cisa_data)
                    
                    db.session.commit()
                    print(f"成功导入 {len(new_entries)} 条新记录到数据库")
            else:
                print("没有发现新增记录")
            
            return True
        except Exception as e:
            with _app.app_context():
                db.session.rollback()
            print(f"比较和更新数据库失败: {str(e)}")
            return False
    
    @staticmethod
    def _get_value(row, possible_columns, value_type=str):
        """尝试从DataFrame行中获取值，支持多种可能的列名"""
        for col in possible_columns:
            if col in row.index:
                val = row[col]
                if pd.isna(val):
                    return None if value_type == str else value_type()
                try:
                    return value_type(val)
                except:
                    return str(val) if value_type == str else None
        return None if value_type == str else value_type()
    
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
    # 每天0点执行CISA数据更新
    schedule.every().day.at("00:00").do(CisaService.compare_and_update_db)
    
    # 初始运行一次，确保有数据
    CisaService.compare_and_update_db()
    
    # 持续运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

def start_scheduler(app):
    """在后台线程中启动调度器"""
    # 设置应用实例引用
    set_app(app)
    
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    print("CISA数据同步调度器已启动")