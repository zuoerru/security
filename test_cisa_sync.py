from app import create_app, db
from app.cisa.service import CisaService
from app.cisa.models import CisaData
import logging
import traceback
import os
import pandas as pd
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()
CisaService.set_app(app)

try:
    with app.app_context():
        logger.info('开始检查CISA同步问题...')
        
        # 检查数据库中的现有记录数量
        existing_count = CisaData.query.count()
        logger.info(f'数据库中现有CISA记录数量: {existing_count}')
        
        # 获取数据库中前5条记录的vuln_id
        existing_vuln_ids = [item.vuln_id for item in CisaData.query.limit(5).all()]
        logger.info(f'数据库中前5条记录的vuln_id: {existing_vuln_ids}')
        
        # 检查compare_and_update_db方法的实现细节
        logger.info('开始下载CSV文件进行分析...')
        
        # 手动下载并解析CSV文件
        today = datetime.now().strftime('%Y-%m-%d')
        csv_url = f'https://www.cisa.gov/sites/default/files/csv/known_exploited_vulnerabilities.csv'
        logger.info(f'尝试下载CSV文件: {csv_url}')
        
        # 使用pandas读取CSV文件
        try:
            df = pd.read_csv(csv_url)
            logger.info(f'成功下载CSV文件，共{len(df)}条记录')
            
            # 检查CSV文件的列名
            logger.info(f'CSV文件列名: {df.columns.tolist()}')
            
            # 获取CSV文件中前5条记录的CVE ID
            csv_cve_ids = df['cveID'].head(5).tolist() if 'cveID' in df.columns else []
            logger.info(f'CSV文件中前5条记录的cveID: {csv_cve_ids}')
            
            # 检查是否有重复的cveID
            if 'cveID' in df.columns:
                duplicate_cves = df[df.duplicated('cveID', keep=False)]['cveID'].tolist()
                if duplicate_cves:
                    logger.warning(f'CSV文件中发现重复的cveID: {duplicate_cves[:5]}')
            
            # 检查数据库中是否已存在CSV中的记录
            if 'cveID' in df.columns:
                sample_cves = df['cveID'].head(10).tolist()
                existing_in_db = CisaData.query.filter(CisaData.vuln_id.in_(sample_cves)).all()
                logger.info(f'样本中有{len(existing_in_db)}条记录已存在于数据库中')
                
        except Exception as csv_error:
            logger.error(f'下载或解析CSV文件失败: {str(csv_error)}')
            traceback.print_exc()
        
        # 尝试单独插入一条记录来测试
        logger.info('尝试插入一条测试记录...')
        try:
            # 使用不存在的vuln_id进行测试
            test_vuln_id = 'TEST-2024-0001'
            # 检查是否已存在
            existing = CisaData.query.filter_by(vuln_id=test_vuln_id).first()
            if existing:
                logger.info(f'测试记录已存在，删除后重新插入')
                db.session.delete(existing)
                db.session.commit()
            
            test_record = CisaData(
                vuln_id=test_vuln_id,
                vendor_project='TestVendor',
                product='TestProduct',
                vulnerability_name='Test Vulnerability',
                date_added=datetime.now().date(),
                cve_id='TEST-2024-0001',
                due_date=(datetime.now() + timedelta(days=30)).date(),
                short_description='Test description',
                required_action='Test action'
            )
            db.session.add(test_record)
            db.session.commit()
            logger.info('成功插入测试记录')
            
            # 清理测试记录
            db.session.delete(test_record)
            db.session.commit()
            logger.info('成功删除测试记录')
            
        except Exception as insert_error:
            logger.error(f'插入测试记录失败: {str(insert_error)}')
            db.session.rollback()
            traceback.print_exc()
            
        logger.info('检查完成')
        
except Exception as e:
    logger.error(f'检查过程中发生错误: {str(e)}')
    logger.error('详细错误堆栈:')
    logger.error(traceback.format_exc())
    print(f'错误类型: {type(e).__name__}')
    print(f'错误消息: {str(e)}')
    print('详细错误堆栈:')
    traceback.print_exc()