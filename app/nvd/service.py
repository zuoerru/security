import requests
import json
import time
import requests
from datetime import datetime, timedelta
import schedule
from threading import Thread
import os
from flask import current_app, jsonify
from .models import NvdData
from app import db
from app.nvd.log_service import sync_log_service

# 存储应用实例的引用
_app = None

# NVD API相关配置
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
REQUEST_DELAY = 6  # 符合NVD API使用政策的延迟时间
BATCH_SIZE = 2000  # 每页获取的记录数

# 下载目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOAD_DIR = BASE_DIR

class NvdService:
    @staticmethod
    def set_app(app):
        """设置应用实例引用，用于在定时任务中访问应用上下文"""
        global _app
        _app = app
    
    @staticmethod
    def get_all_data(page=1, per_page=20, sort_by='', sort_order=''):
        """获取所有NVD数据，支持分页和排序"""
        query = NvdData.query
        
        # 处理排序
        if sort_by and hasattr(NvdData, sort_by):
            sort_column = getattr(NvdData, sort_by)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(NvdData.published_date.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination
    
    @staticmethod
    def search_data(search_query, page=1, per_page=20, sort_by='', sort_order=''):
        """搜索NVD数据"""
        search = f"%{search_query}%"
        query = NvdData.query.filter(
            db.or_(
                NvdData.cve_id.like(search),
                NvdData.description.like(search),
                NvdData.vendor.like(search),
                NvdData.product.like(search)
            )
        )
        
        # 处理排序
        if sort_by and hasattr(NvdData, sort_by):
            sort_column = getattr(NvdData, sort_by)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(NvdData.published_date.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination
    
    @staticmethod
    def get_total_count():
        """获取总记录数"""
        return NvdData.query.count()
    
    @staticmethod
    def get_search_count(search_query):
        """获取搜索结果的记录数"""
        search = f"%{search_query}%"
        return NvdData.query.filter(
            db.or_(
                NvdData.cve_id.like(search),
                NvdData.description.like(search),
                NvdData.vendor.like(search),
                NvdData.product.like(search)
            )
        ).count()
    
    @staticmethod
    def import_from_tsv(file_path):
        """从TSV文件导入数据"""
        import csv
        try:
            # 确保在应用上下文中操作数据库
            if not _app:
                raise RuntimeError("应用上下文未设置")
                
            with _app.app_context():
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter='\t')
                    imported_count = 0
                    
                    for row in reader:
                        # 检查是否已存在
                        existing = NvdData.query.filter_by(cve_id=row['CVE ID']).first()
                        if not existing:
                            # 创建新记录
                            nvd_data = NvdData(
                                cve_id=row['CVE ID'],
                                published_date=datetime.strptime(row['Published Date'], '%Y-%m-%d'),
                                last_modified_date=datetime.strptime(row['Last Modified Date'], '%Y-%m-%d'),
                                description=row['Description'],
                                base_score=float(row['Base Score']) if row['Base Score'] else None,
                                base_severity=row['Base Severity'],
                                vector_string=row['Vector String'],
                                vendor=row['Vendor'],
                                product=row['Product']
                            )
                            db.session.add(nvd_data)
                            imported_count += 1
                            
                    db.session.commit()
                    return imported_count
        except Exception as e:
            db.session.rollback()
            print(f"导入TSV文件时出错: {str(e)}")
            return 0
    
    @staticmethod
    def sync_from_api(start_date=None, end_date=None):
        """从NVD API同步数据"""
        # 使用新的同步并保存TSV的方法
        return NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
    
    @staticmethod
    def save_to_tsv(data, file_path):
        """保存数据到TSV文件"""
        import csv
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 定义TSV文件的列名
            fieldnames = ['CVE ID', 'Published Date', 'Last Modified Date', 'Description', 
                         'Base Score', 'Base Severity', 'Vector String', 'Vendor', 'Product']
            
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
                writer.writeheader()
                
                for item in data:
                    writer.writerow({
                        'CVE ID': item.get('cve_id', ''),
                        'Published Date': item.get('published_date', '').strftime('%Y-%m-%d') if isinstance(item.get('published_date'), datetime) else item.get('published_date', ''),
                        'Last Modified Date': item.get('last_modified_date', '').strftime('%Y-%m-%d') if isinstance(item.get('last_modified_date'), datetime) else item.get('last_modified_date', ''),
                        'Description': item.get('description', ''),
                        'Base Score': item.get('base_score', '') if item.get('base_score') is not None else '',
                        'Base Severity': item.get('base_severity', ''),
                        'Vector String': item.get('vector_string', ''),
                        'Vendor': item.get('vendor', ''),
                        'Product': item.get('product', '')
                    })
            
            return True
        except Exception as e:
            print(f"保存TSV文件时出错: {str(e)}")
            return False
    
    @staticmethod
    def sync_and_save_tsv(start_date=None, end_date=None):
        """同步数据并保存为TSV文件"""
        try:
            # 确保在应用上下文中操作数据库
            if not _app:
                raise RuntimeError("应用上下文未设置")
                
            with _app.app_context():
                # 设置查询参数
                params = {
                    "resultsPerPage": BATCH_SIZE,
                    "startIndex": 0
                }
                
                # 设置日期范围
                if start_date:
                    params["pubStartDate"] = start_date.isoformat() + "Z"
                if end_date:
                    params["pubEndDate"] = end_date.isoformat() + "Z"
                
                total_results = None
                all_vulnerabilities = []
                
                while total_results is None or params["startIndex"] < total_results:
                    # 发送请求
                    import requests
                    response = requests.get(NVD_API_URL, params=params, timeout=60)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # 获取总数
                    if total_results is None:
                        total_results = data.get("totalResults", 0)
                    
                    # 处理漏洞数据
                    vulnerabilities = data.get("vulnerabilities", [])
                    for vuln in vulnerabilities:
                        cve = vuln.get("cve", {})
                        
                        # 获取基本信息
                        cve_id = cve.get("id", "")
                        published_date_str = cve.get("published", "")
                        last_modified_date_str = cve.get("lastModified", "")
                        
                        if not cve_id or not published_date_str or not last_modified_date_str:
                            continue
                        
                        # 解析日期
                        published_date = datetime.strptime(published_date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                        last_modified_date = datetime.strptime(last_modified_date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                        
                        # 获取描述
                        descriptions = cve.get("descriptions", [])
                        description = descriptions[0].get("value", "") if descriptions else ""
                        
                        # 获取评分信息
                        base_score = None
                        base_severity = ""
                        vector_string = ""
                        
                        metrics = cve.get("metrics", {})
                        # 尝试获取CVSS v3评分
                        if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
                            cvss_data = metrics["cvssMetricV31"][0].get("cvssData", {})
                            base_score = cvss_data.get("baseScore")
                            base_severity = cvss_data.get("baseSeverity", "")
                            vector_string = cvss_data.get("vectorString", "")
                        elif "cvssMetricV30" in metrics and metrics["cvssMetricV30"]:
                            cvss_data = metrics["cvssMetricV30"][0].get("cvssData", {})
                            base_score = cvss_data.get("baseScore")
                            base_severity = cvss_data.get("baseSeverity", "")
                            vector_string = cvss_data.get("vectorString", "")
                        # 尝试获取CVSS v2评分
                        elif "cvssMetricV2" in metrics and metrics["cvssMetricV2"]:
                            cvss_data = metrics["cvssMetricV2"][0].get("cvssData", {})
                            base_score = cvss_data.get("baseScore")
                            base_severity = cvss_data.get("baseSeverity", "")
                            vector_string = cvss_data.get("vectorString", "")
                        
                        # 获取厂商和产品信息
                        vendor = ""
                        product = ""
                        configurations = cve.get("configurations", [])
                        if configurations:
                            nodes = configurations[0].get("nodes", [])
                            if nodes:
                                cpe_match = nodes[0].get("cpeMatch", [])
                                if cpe_match:
                                    cpe_uri = cpe_match[0].get("criteria", "")
                                    if cpe_uri:
                                        cpe_parts = cpe_uri.split(':')
                                        if len(cpe_parts) >= 5:
                                            vendor = cpe_parts[3]
                                            product = cpe_parts[4]
                        
                        # 添加到列表
                        all_vulnerabilities.append({
                            'cve_id': cve_id,
                            'published_date': published_date,
                            'last_modified_date': last_modified_date,
                            'description': description,
                            'base_score': base_score,
                            'base_severity': base_severity,
                            'vector_string': vector_string,
                            'vendor': vendor,
                            'product': product
                        })
                    
                    # 更新起始索引
                    params["startIndex"] += BATCH_SIZE
                    
                    # 添加延迟，符合NVD API使用政策
                    if total_results > params["startIndex"]:
                        time.sleep(REQUEST_DELAY)
                
                # 保存为TSV文件
                if all_vulnerabilities:
                    # 生成文件名 (格式: YYYYMMDD.tsv)
                    file_date = end_date if end_date else datetime.utcnow()
                    file_name = file_date.strftime('%Y%m%d') + '.tsv'
                    file_path = os.path.join(DOWNLOAD_DIR, file_name)
                    
                    # 保存TSV文件
                    save_success = NvdService.save_to_tsv(all_vulnerabilities, file_path)
                    
                    if save_success:
                        print(f"成功保存TSV文件: {file_path}")
                        
                        # 导入数据库
                        imported_count = NvdService.import_from_tsv(file_path)
                        print(f"成功从TSV文件导入 {imported_count} 条记录到数据库")
                        return imported_count
                    else:
                        print("保存TSV文件失败")
                        return 0
                else:
                    print("没有获取到新的漏洞数据")
                    return 0
        except Exception as e:
            print(f"同步数据并保存为TSV文件时出错: {str(e)}")
            return 0

# 定时任务相关函数
def run_scheduled_tasks():
    """运行所有定时任务"""
    # 设置每天凌晨0点同步最新数据
    schedule.every().day.at("00:00").do(sync_daily_data)
    
    # 初始同步
    sync_daily_data()
    
    # 循环执行调度任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

def sync_daily_data():
    """同步最近一天的数据"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        print(f"开始同步NVD数据: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        imported_count = NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
        
        # 记录自动同步日志
        sync_log_service.add_log('auto', imported_count, start_date, end_date)
        
        print(f"NVD数据同步完成，新增 {imported_count} 条记录")
    except Exception as e:
        print(f"NVD数据同步任务执行失败: {str(e)}")

def start_scheduler(app):
    """启动调度器"""
    NvdService.set_app(app)
    
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    print("NVD数据同步调度器已启动")