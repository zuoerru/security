import requests
import threading
import time
from datetime import datetime, timedelta
import logging
from app import db
from app.cve.models import Cves, CvesLog
import json
from flask import Flask

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cve_service')

# NVD API配置
NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/1.0"
API_KEY = ""  # 如果有API密钥可以设置，能提高请求限制
REQUEST_DELAY = 6  # NVD API限制，免费用户每秒最多1个请求

class CveService:
    def __init__(self, app=None):
        self.app = app
        self.scheduler_thread = None
        self.running = False
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        # 确保应用实例被正确设置
        if not isinstance(app, Flask):
            raise TypeError("app must be an instance of Flask")
    
    def get_cves_from_nvd(self, start_date=None, end_date=None, results_per_page=2000):
        """
        从NVD API获取CVE数据
        """
        headers = {}
        if API_KEY:
            headers["apiKey"] = API_KEY
        
        params = {
            "resultsPerPage": results_per_page,
            "startIndex": 0
        }
        
        if start_date:
            params["pubStartDate"] = start_date.strftime("%Y-%m-%dT%H:%M:%S:%f")[:-3] + ".000Z"
        if end_date:
            params["pubEndDate"] = end_date.strftime("%Y-%m-%dT%H:%M:%S:%f")[:-3] + ".000Z"
        
        all_cves = []
        total_results = None
        
        while True:
            try:
                response = requests.get(NVD_API_BASE_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                if total_results is None:
                    total_results = data.get("totalResults", 0)
                    logger.info(f"Total CVEs to fetch: {total_results}")
                
                items = data.get("result", {}).get("CVE_Items", [])
                all_cves.extend(items)
                
                logger.info(f"Fetched {len(all_cves)}/{total_results} CVEs")
                
                if len(all_cves) >= total_results:
                    break
                
                params["startIndex"] += results_per_page
                
                # 遵守API请求限制
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error fetching CVEs: {str(e)}")
                raise
        
        return all_cves
    
    def parse_cve_item(self, item):
        """
        解析单个CVE项目数据
        """
        cve_data = item.get("cve", {})
        impact_data = item.get("impact", {})
        published_date = datetime.fromisoformat(item.get("publishedDate", "").replace("Z", ""))
        last_modified_date = datetime.fromisoformat(item.get("lastModifiedDate", "").replace("Z", ""))
        
        # 获取描述
        descriptions = cve_data.get("description", {}).get("description_data", [])
        description = descriptions[0].get("value", "") if descriptions else ""
        
        # 获取评分信息
        base_score = None
        base_severity = None
        attack_vector = None
        attack_complexity = None
        privileges_required = None
        user_interaction = None
        scope = None
        confidentiality_impact = None
        integrity_impact = None
        availability_impact = None
        
        # 尝试从不同版本的评分中获取数据
        if "baseMetricV3" in impact_data:
            v3_metrics = impact_data["baseMetricV3"]["cvssV3"]
            base_score = v3_metrics.get("baseScore")
            base_severity = v3_metrics.get("baseSeverity")
            attack_vector = v3_metrics.get("attackVector")
            attack_complexity = v3_metrics.get("attackComplexity")
            privileges_required = v3_metrics.get("privilegesRequired")
            user_interaction = v3_metrics.get("userInteraction")
            scope = v3_metrics.get("scope")
            confidentiality_impact = v3_metrics.get("confidentialityImpact")
            integrity_impact = v3_metrics.get("integrityImpact")
            availability_impact = v3_metrics.get("availabilityImpact")
        elif "baseMetricV2" in impact_data:
            v2_metrics = impact_data["baseMetricV2"]["cvssV2"]
            base_score = v2_metrics.get("baseScore")
            base_severity = v2_metrics.get("baseSeverity")
            # V2评分不包含所有V3的字段，只设置可用的
        
        # 获取CWE信息
        problem_types = cve_data.get("problemtype", {}).get("problemtype_data", [])
        cwe_id = None
        if problem_types:
            descriptions = problem_types[0].get("description", [])
            if descriptions:
                cwe_id = descriptions[0].get("value", "")
        
        # 获取参考信息
        references_data = cve_data.get("references", {}).get("reference_data", [])
        references = json.dumps([ref.get("url", "") for ref in references_data])
        
        return {
            "cve_id": cve_data.get("CVE_data_meta", {}).get("ID", ""),
            "published_date": published_date,
            "last_modified_date": last_modified_date,
            "description": description,
            "base_score": base_score,
            "base_severity": base_severity,
            "attack_vector": attack_vector,
            "attack_complexity": attack_complexity,
            "privileges_required": privileges_required,
            "user_interaction": user_interaction,
            "scope": scope,
            "confidentiality_impact": confidentiality_impact,
            "integrity_impact": integrity_impact,
            "availability_impact": availability_impact,
            "cwe_id": cwe_id,
            "references": references
        }
    
    def save_cves_to_db(self, cve_items):
        """
        将CVE数据保存到数据库
        """
        affected_count = 0
        for item in cve_items:
            try:
                cve_data = self.parse_cve_item(item)
                
                # 检查是否已存在
                existing_cve = Cves.query.filter_by(cve_id=cve_data["cve_id"]).first()
                
                if existing_cve:
                    # 更新现有记录
                    for key, value in cve_data.items():
                        if key != "cve_id":  # 不更新主键
                            setattr(existing_cve, key, value)
                else:
                    # 创建新记录
                    new_cve = Cves(**cve_data)
                    db.session.add(new_cve)
                
                affected_count += 1
                
            except Exception as e:
                logger.error(f"Error saving CVE {item.get('cve', {}).get('CVE_data_meta', {}).get('ID', 'Unknown')}: {str(e)}")
        
        db.session.commit()
        return affected_count
    
    def sync_cve_data(self, start_date=None, end_date=None, sync_type="manual"):
        """
        同步CVE数据到数据库
        """
        sync_log = CvesLog(
            status="processing",
            message="Starting CVE data synchronization",
            sync_type=sync_type,
            start_date=start_date.date() if start_date else None,
            end_date=end_date.date() if end_date else None
        )
        db.session.add(sync_log)
        db.session.commit()
        
        try:
            logger.info(f"Starting CVE sync: type={sync_type}, start={start_date}, end={end_date}")
            
            # 获取CVE数据
            cve_items = self.get_cves_from_nvd(start_date, end_date)
            
            # 保存到数据库
            affected_count = self.save_cves_to_db(cve_items)
            
            # 更新日志
            sync_log.status = "success"
            sync_log.message = f"Successfully synced {affected_count} CVE records"
            sync_log.affected_count = affected_count
            
            logger.info(f"CVE sync completed successfully: {affected_count} records")
            
        except Exception as e:
            logger.error(f"CVE sync failed: {str(e)}")
            sync_log.status = "failure"
            sync_log.message = f"Sync failed: {str(e)}"
            sync_log.affected_count = 0
        
        db.session.commit()
        return sync_log
    
    def sync_all_cves(self):
        """
        同步所有历史CVE数据（分批同步以避免超时）
        """
        # 从1999年开始，每年同步一次
        current_year = datetime.now().year
        start_year = 1999
        
        total_affected = 0
        
        with self.app.app_context():
            sync_log = CvesLog(
                status="processing",
                message="Starting full historical CVE data synchronization",
                sync_type="manual"
            )
            db.session.add(sync_log)
            db.session.commit()
            
            try:
                for year in range(start_year, current_year + 1):
                    start_date = datetime(year, 1, 1)
                    end_date = datetime(year, 12, 31, 23, 59, 59)
                    
                    # 对于当前年份，只同步到当前日期
                    if year == current_year:
                        end_date = datetime.now()
                    
                    logger.info(f"Syncing CVEs for {year} ({start_date} to {end_date})")
                    
                    try:
                        cve_items = self.get_cves_from_nvd(start_date, end_date)
                        affected_count = self.save_cves_to_db(cve_items)
                        total_affected += affected_count
                        
                        logger.info(f"Completed sync for {year}: {affected_count} records")
                        
                    except Exception as e:
                        logger.error(f"Error syncing CVEs for {year}: {str(e)}")
                
                sync_log.status = "success"
                sync_log.message = f"Successfully fully synced {total_affected} historical CVE records"
                sync_log.affected_count = total_affected
                
            except Exception as e:
                logger.error(f"Full CVE sync failed: {str(e)}")
                sync_log.status = "failure"
                sync_log.message = f"Full sync failed: {str(e)}"
            
            db.session.commit()
    
    def sync_recent_cves(self):
        """
        同步最近3天的CVE数据（用于定期更新）
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        if not self.app:
            logger.error("Cannot sync recent CVEs: application not initialized")
            return
            
        with self.app.app_context():
            self.sync_cve_data(start_date, end_date, "auto")
    
    def run_scheduler(self):
        """
        运行定时任务调度器
        """
        if not self.app:
            logger.error("Cannot run scheduler: application not initialized")
            return
        
        while self.running:
            try:
                logger.info("Running scheduled CVE sync task")
                self.sync_recent_cves()
                
                # 每3小时运行一次
                for _ in range(3 * 6):  # 3小时 = 180分钟，每分钟检查一次是否继续运行
                    if not self.running:
                        break
                    time.sleep(60)
                    
            except Exception as e:
                logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟再继续
    
    def start_scheduler(self, app=None):
        """
        启动定时任务调度器
        """
        if app:
            self.init_app(app)
        
        if not self.app:
            raise RuntimeError("Application not initialized. Call init_app first or pass app to constructor.")
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("CVE scheduler started")
    
    def stop_scheduler(self):
        """
        停止定时任务调度器
        """
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("CVE scheduler stopped")

# 创建全局服务实例
cve_service = CveService()

# 供外部调用的启动函数
def start_scheduler(app):
    """
    启动CVE数据同步调度器
    
    Args:
        app: Flask应用实例
    """
    cve_service.start_scheduler(app)

def init_cve_service(app):
    """
    初始化CVE服务
    
    Args:
        app: Flask应用实例
    """
    cve_service.init_app(app)
    return cve_service