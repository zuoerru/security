import threading
import time
from datetime import datetime, timedelta
import logging
from app import db
from app.cve.models import Cves, CvesLog
import json
from flask import Flask
import os
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cve_service')

# 本地TSV文件配置
TSV_DATA_DIR = "/data_nfs/121/app/security"

# 清理Unicode控制字符和无法识别的字符
def clean_text(text):
    if not text:
        return text
    
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or ord(char) in (9, 10, 13))
    # 移除不可打印字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 处理可能导致数据库编码问题的字符
    # 保留ASCII字符和常见符号
    result = []
    for char in text:
        if ord(char) < 128 or char in '\t\n\r':
            result.append(char)
        else:
            # 对于非ASCII字符，使用占位符或转换
            try:
                # 尝试编码，如果成功则保留
                char.encode('utf-8')
                result.append(char)
            except:
                # 无法编码的字符替换为占位符
                result.append('[Unicode]')
    
    # 限制文本长度，避免过长的描述字段
    max_length = 3000  # 根据数据库字段限制调整
    if len(result) > max_length:
        return ''.join(result[:max_length]) + '...'
    
    return ''.join(result)

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
        从本地TSV文件获取CVE数据
        """
        all_cves = []
        
        # 更严格的文本清理函数，用于数据库插入
        def strict_clean_text(text):
            if not text:
                return text
            # 仅保留ASCII字符和基本空格/制表符/换行符
            result = []
            for char in text:
                if ord(char) < 128 or char in '\t\n\r':
                    result.append(char)
                else:
                    # 将所有非ASCII字符替换为占位符
                    result.append('?')
            # 限制长度
            max_length = 3000
            if len(result) > max_length:
                return ''.join(result[:max_length]) + '...'
            return ''.join(result)
        
        # 获取所有TSV文件，优先处理
        all_tsv_files = []
        for file_name in os.listdir(TSV_DATA_DIR):
            if file_name.endswith(".tsv") and file_name != "cve.tsv":  # 排除可能的汇总文件
                all_tsv_files.append(os.path.join(TSV_DATA_DIR, file_name))
        
        # 确定要处理的文件范围
        files_to_process = []
        if start_date and end_date:
            start_year = start_date.year
            end_year = end_date.year
            logger.info(f"Filtering files for years: {start_year} to {end_year}")
            
            # 对每个文件进行年份过滤
            for file_path in all_tsv_files:
                file_name = os.path.basename(file_path)
                
                # 尝试从文件名中提取年份信息
                try:
                    # 处理YYYYMM.tsv格式
                    if len(file_name) == 9 and file_name[6:] == ".tsv":
                        file_year = int(file_name[:4])
                        if start_year <= file_year <= end_year:
                            files_to_process.append(file_path)
                    # 处理YYYYMMDD.tsv格式
                    elif len(file_name) == 12 and file_name[8:] == ".tsv":
                        file_year = int(file_name[:4])
                        if start_year <= file_year <= end_year:
                            files_to_process.append(file_path)
                    # 处理其他可能的格式，如YYYYMM.tsv
                    elif file_name.startswith("20") and len(file_name) >= 8:
                        # 尝试提取前4个数字作为年份
                        file_year_str = file_name[:4]
                        if file_year_str.isdigit():
                            file_year = int(file_year_str)
                            if start_year <= file_year <= end_year:
                                files_to_process.append(file_path)
                except Exception as e:
                    # 如果文件名解析失败，仍然添加该文件以确保不丢失数据
                    logger.warning(f"Could not parse year from filename {file_name}, adding anyway: {str(e)}")
                    files_to_process.append(file_path)
        else:
            # 处理所有TSV文件
            files_to_process = all_tsv_files
        
        # 去重文件列表
        files_to_process = list(set(files_to_process))
        logger.info(f"Processing {len(files_to_process)} TSV files for date range: {start_date} to {end_date}")
        for file_path in files_to_process:
            logger.info(f"Included file: {os.path.basename(file_path)}")
        
        # 处理每个文件
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    if not lines:
                        continue
                    
                    # 跳过表头
                    for line in lines[1:]:
                        try:
                            fields = line.strip().split('\t')
                            # 确保fields有足够的元素
                            while len(fields) < 9:
                                fields.append('')
                            
                            # 过滤掉非CVE开头的行，使用严格清理函数
                            raw_cve_id = strict_clean_text(fields[0])
                            
                            # 使用正则表达式提取有效的CVE ID格式
                            cve_match = re.search(r'CVE-\d{4}-\d+', raw_cve_id)
                            if not cve_match:
                                logger.warning(f"Invalid CVE ID format: {raw_cve_id}, skipping line")
                                continue
                            
                            cve_id = cve_match.group(0)
                            # 确保cve_id不超过数据库字段长度限制
                            if len(cve_id) > 50:  # 假设数据库字段限制为50个字符
                                logger.warning(f"CVE ID too long: {cve_id}, skipping line")
                                continue
                            
                            # 构建模拟的NVD API响应格式的数据结构，对所有文本字段进行严格清理
                            cve_item = {
                                "cve": {
                                    "CVE_data_meta": {
                                        "ID": cve_id
                                    },
                                    "description": {
                                        "description_data": [
                                            {"value": strict_clean_text(fields[3])}
                                        ]
                                    },
                                    "problemtype": {
                                        "problemtype_data": []
                                    },
                                    "references": {
                                        "reference_data": []
                                    }
                                },
                                "impact": {},
                                "publishedDate": strict_clean_text(fields[1]) if fields[1] else "1999-01-01T00:00:00.000",
                                "lastModifiedDate": strict_clean_text(fields[2]) if fields[2] else "1999-01-01T00:00:00.000"
                            }
                            
                            # 添加评分信息
                            if fields[4] and fields[4] != 'N/A':
                                try:
                                    base_score = float(fields[4])
                                    base_severity = strict_clean_text(fields[5]) if fields[5] else "NONE"
                                    
                                    # 确定严重级别
                                    if base_severity == "NONE":
                                        if base_score >= 9.0:
                                            base_severity = "CRITICAL"
                                        elif base_score >= 7.0:
                                            base_severity = "HIGH"
                                        elif base_score >= 4.0:
                                            base_severity = "MEDIUM"
                                        elif base_score > 0:
                                            base_severity = "LOW"
                                    
                                    cve_item["impact"] = {
                                        "baseMetricV3": {
                                            "cvssV3": {
                                                "baseScore": base_score,
                                                "baseSeverity": base_severity
                                            }
                                        }
                                    }
                                except:
                                    pass
                            
                            all_cves.append(cve_item)
                            
                        except Exception as line_error:
                            logger.error(f"Error processing line in {file_path}: {str(line_error)}")
                            continue
                
                logger.info(f"Processed file {os.path.basename(file_path)}, added {len(all_cves)} CVEs")
                
            except Exception as file_error:
                logger.error(f"Error reading file {file_path}: {str(file_error)}")
                continue
        
        logger.info(f"Total CVEs fetched from TSV files: {len(all_cves)}")
        return all_cves
    
    def parse_cve_item(self, item):
        """
        解析单个CVE项目数据
        """
        cve_data = item.get("cve", {})
        impact_data = item.get("impact", {})
        
        # 先验证并清理cve_id
        cve_id = cve_data.get("CVE_data_meta", {}).get("ID", "")
        if cve_id:
            # 使用正则表达式提取有效的CVE ID格式
            cve_match = re.search(r'CVE-\d{4}-\d+', cve_id)
            if cve_match:
                cve_id = cve_match.group(0)
            else:
                logger.error(f"Invalid CVE ID format in parsed item: {cve_id}")
                cve_id = ""
        
        # 安全地处理日期
        published_date_str = item.get("publishedDate", "").replace("Z", "")
        last_modified_date_str = item.get("lastModifiedDate", "").replace("Z", "")
        
        try:
            if '.' in published_date_str:
                published_date_str = published_date_str.split('.')[0]
            published_date = datetime.fromisoformat(published_date_str)
        except Exception as e:
            logger.error(f"Error parsing published_date: {published_date_str}, using default date")
            published_date = datetime(1999, 1, 1)
        
        try:
            if '.' in last_modified_date_str:
                last_modified_date_str = last_modified_date_str.split('.')[0]
            last_modified_date = datetime.fromisoformat(last_modified_date_str)
        except Exception as e:
            logger.error(f"Error parsing last_modified_date: {last_modified_date_str}, using default date")
            last_modified_date = datetime(1999, 1, 1)
        
        # 获取描述
        descriptions = cve_data.get("description", {}).get("description_data", [])
        description = descriptions[0].get("value", "") if descriptions else ""
        # 确保描述经过清理
        description = clean_text(description)
        
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
        
        返回:
            tuple: (affected_count, insert_count, update_count)
        """
        affected_count = 0
        error_count = 0
        insert_count = 0
        update_count = 0
        
        for item in cve_items:
            try:
                cve_data = self.parse_cve_item(item)
                
                # 确保cve_id存在且格式正确
                if not cve_data.get("cve_id") or not re.match(r'CVE-\d{4}-\d+', cve_data.get("cve_id")):
                    logger.warning(f"Skipping record with invalid CVE ID: {cve_data.get('cve_id')}")
                    error_count += 1
                    continue
                
                # 确保cve_id长度不超过数据库字段限制
                if len(cve_data.get("cve_id")) > 50:
                    logger.warning(f"Skipping record with too long CVE ID: {cve_data.get('cve_id')}")
                    error_count += 1
                    continue
                
                # 检查是否已存在
                existing_cve = Cves.query.filter_by(cve_id=cve_data["cve_id"]).first()
                
                if existing_cve:
                    # 更新现有记录
                    for key, value in cve_data.items():
                        if key != "cve_id":  # 不更新主键
                            setattr(existing_cve, key, value)
                    # 更新时间戳
                    existing_cve.updated_at = datetime.utcnow()
                    update_count += 1
                else:
                    # 创建新记录
                    new_cve = Cves(**cve_data)
                    db.session.add(new_cve)
                    insert_count += 1
                
                affected_count += 1
                
                # 每100条记录提交一次，减少事务压力
                if affected_count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Processed {affected_count} records (insert: {insert_count}, update: {update_count})")
                    
            except Exception as e:
                cve_id = cve_data.get("cve_id", item.get('cve', {}).get('CVE_data_meta', {}).get('ID', 'Unknown'))
                logger.error(f"Error saving CVE {cve_id}: {str(e)}")
                # 回滚当前事务以处理下一条记录
                db.session.rollback()
                error_count += 1
        
        # 确保最后一批记录被提交
        try:
            db.session.commit()
            logger.info(f"Database commit successful. Total processed: {affected_count}, errors: {error_count}")
            logger.info(f"Inserted: {insert_count}, Updated: {update_count}")
        except Exception as commit_error:
            logger.error(f"Error during final commit: {str(commit_error)}")
            db.session.rollback()
        
        return (affected_count, insert_count, update_count)
    
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
            affected_count, insert_count, update_count = self.save_cves_to_db(cve_items)
            
            # 更新日志
            sync_log.status = "success"
            sync_log.message = f"Successfully synced {affected_count} CVE records (inserted: {insert_count}, updated: {update_count})"
            sync_log.affected_count = affected_count
            sync_log.insert_count = insert_count
            sync_log.update_count = update_count
            
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
                        affected_count, insert_count, update_count = self.save_cves_to_db(cve_items)
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