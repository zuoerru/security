from app import create_app
from app.cisa.service import CisaService
from app.nvd.service import NvdService
from datetime import datetime, timedelta
import os

def restore_cisa_data():
    """重新导入CISA数据"""
    print("开始重新导入CISA数据...")
    app = create_app()
    with app.app_context():
        success = CisaService.compare_and_update_db()
        if success:
            print("CISA数据重新导入成功")
        else:
            print("CISA数据重新导入失败")

def restore_recent_nvd_data():
    """导入最近30天的NVD数据"""
    print("开始导入最近30天的NVD数据...")
    app = create_app()
    with app.app_context():
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        imported_count = NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
        print(f"最近30天的NVD数据导入完成，新增 {imported_count} 条记录")

def check_logs_for_truncate():
    """检查日志文件中是否有执行truncate或reset脚本的记录"""
    print("\n检查日志文件中是否有执行truncate或reset脚本的记录...")
    log_files = ['app.log', 'monitor.log']
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n检查文件: {log_file}")
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if 'truncate' in content.lower() or 'reset' in content.lower():
                        print(f"⚠️ 在 {log_file} 中发现可能的危险操作记录")
                        # 提取包含这些关键词的行
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'truncate' in line.lower() or 'reset' in line.lower():
                                print(f"  行{i+1}: {line.strip()}")
                    else:
                        print(f"✅ 在 {log_file} 中未发现危险操作记录")
            except Exception as e:
                print(f"读取 {log_file} 时出错: {str(e)}")
        else:
            print(f"文件 {log_file} 不存在")

if __name__ == "__main__":
    check_logs_for_truncate()
    restore_cisa_data()
    restore_recent_nvd_data()