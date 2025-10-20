from app import create_app
from app.cisa.service import CisaService
import logging
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()
CisaService.set_app(app)

try:
    with app.app_context():
        logger.info('开始测试修复后的CISA同步功能...')
        # 直接调用compare_and_update_db方法
        success = CisaService.compare_and_update_db(sync_type='manual')
        if success:
            logger.info('CISA同步成功!')
        else:
            logger.error('CISA同步失败!')
except Exception as e:
    logger.error(f'测试过程中发生错误: {str(e)}')
    logger.error('详细错误堆栈:')
    logger.error(traceback.format_exc())