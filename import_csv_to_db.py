import pandas as pd
from app import create_app, db
from app.cisa.models import CisaData
import os

# 确保在应用上下文中运行
app = create_app()
with app.app_context():
    # CSV文件路径
    csv_file = 'cisa-20251012.csv'
    
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"错误: 文件 {csv_file} 不存在")
        exit(1)
    
    try:
        # 读取CSV文件
        print(f"正在读取文件: {csv_file}")
        df = pd.read_csv(csv_file)
        
        # 显示文件的前几行和列名，以确认格式
        print(f"文件包含 {len(df)} 条记录")
        print("文件列名:", df.columns.tolist())
        
        # 清空现有的cisa表数据
        print("正在清空现有数据...")
        db.session.query(CisaData).delete()
        db.session.commit()
        
        # 导入数据到数据库 - 使用批处理方式
        print("开始导入数据到数据库...")
        total_imported = 0
        batch_size = 100  # 每批次导入的记录数
        batch_count = 0
        
        # 重置索引，确保我们能遍历所有行
        df.reset_index(drop=True, inplace=True)
        
        # 分批处理数据
        for i in range(0, len(df), batch_size):
            batch_count += 1
            batch = df.iloc[i:i+batch_size]
            batch_imported = 0
            
            try:
                print(f"处理批次 {batch_count}, 记录范围: {i} 到 {min(i+batch_size, len(df))}")
                
                for _, row in batch.iterrows():
                    try:
                        # 使用正确的列名映射数据
                        cve_id = row.get('cveID', None)
                        
                        if not cve_id:
                            # 跳过缺少CVE ID的记录
                            continue
                        
                        # 创建CisaData对象
                        cisa_record = CisaData(
                            vuln_id=cve_id,  # 使用cveID作为vuln_id
                            vendor_project=row.get('vendorProject', None),
                            product=row.get('product', None),
                            vulnerability_name=row.get('vulnerabilityName', None),
                            date_added=row.get('dateAdded', None),
                            short_description=row.get('shortDescription', None),
                            required_action=row.get('requiredAction', None),
                            due_date=row.get('dueDate', None),
                            cve_id=cve_id  # 同时保存到cve_id字段
                        )
                        
                        db.session.add(cisa_record)
                        batch_imported += 1
                        total_imported += 1
                    except Exception as row_error:
                        print(f"处理单行数据时出错: {str(row_error)}")
                        continue
                
                # 提交批次
                db.session.commit()
                print(f"批次 {batch_count} 成功导入 {batch_imported} 条记录")
                
                # 清理会话，释放内存
                db.session.expunge_all()
                
            except Exception as batch_error:
                print(f"处理批次 {batch_count} 时出错: {str(batch_error)}")
                db.session.rollback()
                continue
        
        print(f"数据导入完成，共成功导入 {total_imported} 条记录到数据库")
        
    except Exception as e:
        print(f"导入数据时发生严重错误: {str(e)}")
        db.session.rollback()