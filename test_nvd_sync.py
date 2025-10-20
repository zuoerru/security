import sys
import os
sys.path.append('/data_nfs/121/app/security')

from datetime import datetime, timedelta
from app import create_app
from app.nvd.service import NvdService

app = create_app()

# 设置应用上下文
NvdService.set_app(app)

# 尝试同步最近3天的数据
try:
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=3)
    
    print(f"测试同步NVD数据: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    with app.app_context():
        # 直接调用同步方法
        imported_count = NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
        print(f"同步结果: 成功导入 {imported_count} 条记录")

except Exception as e:
    print(f"同步过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()