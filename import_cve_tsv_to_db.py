import pandas as pd
from app import create_app, db
from datetime import datetime
import os

# 确保在应用上下文中运行
app = create_app()
with app.app_context():
    # 定义CveDetails模型类
    class CveDetails(db.Model):
        __tablename__ = 'cvedetails'
        
        id = db.Column(db.Integer, primary_key=True)
        assigner = db.Column(db.String(255))
        assignerSourceName = db.Column(db.String(255))
        cveNumber = db.Column(db.BigInteger)
        cveId = db.Column(db.String(50), unique=True, nullable=False)
        cveYear = db.Column(db.Integer)
        publishDate = db.Column(db.DateTime)
        updateDate = db.Column(db.DateTime)
        exploitExists = db.Column(db.Boolean)
        exploitExistenceChangeDate = db.Column(db.DateTime)
        isInCISAKEV = db.Column(db.Boolean)
        assignerId = db.Column(db.Integer)
        nvdVulnStatus = db.Column(db.String(50))
        summary = db.Column(db.Text)
        evaluatorComment = db.Column(db.Text)
        evaluatorSolution = db.Column(db.Text)
        evaluatorImpact = db.Column(db.Text)
        cisaExploitAdd = db.Column(db.DateTime)
        cisaActionDue = db.Column(db.DateTime)
        cisaVulnerabilityName = db.Column(db.String(255))
        cisaRequiredAction = db.Column(db.Text)
        cisaShortDescription = db.Column(db.Text)
        cisaNotes = db.Column(db.Text)
        epssScore = db.Column(db.Float)
        epssScoreChangeDate = db.Column(db.DateTime)
        epssPercentile = db.Column(db.Float)
        configCount = db.Column(db.Integer)
        configConditionCount = db.Column(db.Integer)
        vendorCommentCount = db.Column(db.Integer)
        referenceCount = db.Column(db.Integer)
        metricCount = db.Column(db.Integer)
        weaknessCount = db.Column(db.Integer)
        maxCvssBaseScore = db.Column(db.Float)
        maxCvssBaseScorev2 = db.Column(db.Float)
        maxCvssBaseScorev3 = db.Column(db.Float)
        maxCvssBaseScorev4 = db.Column(db.Float)
        maxCvssBaseScoreChangeDate = db.Column(db.DateTime)
        maxCvssExploitabilityScore = db.Column(db.Float)
        maxCvssImpactScore = db.Column(db.Float)
        isOverflow = db.Column(db.Boolean)
        isMemoryCorruption = db.Column(db.Boolean)
        isSqlInjection = db.Column(db.Boolean)
        isXss = db.Column(db.Boolean)
        isDirectoryTraversal = db.Column(db.Boolean)
        isFileInclusion = db.Column(db.Boolean)
        isCsrf = db.Column(db.Boolean)
        isXxe = db.Column(db.Boolean)
        isSsrf = db.Column(db.Boolean)
        isOpenRedirect = db.Column(db.Boolean)
        isInputValidation = db.Column(db.Boolean)
        isCodeExecution = db.Column(db.Boolean)
        isBypassSomething = db.Column(db.Boolean)
        isGainPrivilege = db.Column(db.Boolean)
        isDenialOfService = db.Column(db.Boolean)
        isInformationLeak = db.Column(db.Boolean)
        isUsedForRansomware = db.Column(db.Boolean)
        title = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        def __repr__(self):
            return f'<CveDetails {self.cveId}>'
    
    # 创建表（如果不存在）
    print("创建cvedetails表...")
    db.create_all()
    
    # TSV文件路径
    tsv_file = 'cve.tsv'
    
    # 检查文件是否存在
    if not os.path.exists(tsv_file):
        print(f"错误: 文件 {tsv_file} 不存在")
        exit(1)
    
    try:
        # 读取TSV文件
        print(f"正在读取文件: {tsv_file}")
        # 设置quotechar为""以处理引号内的制表符
        df = pd.read_csv(tsv_file, delimiter='\t', quotechar='"', dtype=str)
        
        # 显示文件的前几行和列名，以确认格式
        print(f"文件包含 {len(df)} 条记录")
        print("文件列名:", df.columns.tolist())
        
        # 清空现有的cvedetails表数据
        print("正在清空现有数据...")
        db.session.query(CveDetails).delete()
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
                        # 创建CveDetails对象
                        cve_record = CveDetails()
                        
                        # 动态设置属性
                        for col in df.columns:
                            # 跳过空列名
                            if pd.isna(col) or col == '':
                                continue
                            
                            # 获取值
                            value = row.get(col)
                            
                            # 处理特定类型的列
                            if pd.isna(value) or value == '':
                                setattr(cve_record, col, None)
                            elif col in ['publishDate', 'updateDate', 'exploitExistenceChangeDate', 
                                        'cisaExploitAdd', 'cisaActionDue', 'epssScoreChangeDate', 
                                        'maxCvssBaseScoreChangeDate']:
                                # 处理日期时间类型
                                try:
                                    if isinstance(value, str) and value.strip():
                                        # 尝试解析日期时间
                                        # 处理可能的格式：'2025-10-10 07:15:44'
                                        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                        setattr(cve_record, col, dt)
                                    else:
                                        setattr(cve_record, col, None)
                                except ValueError:
                                    setattr(cve_record, col, None)
                            elif col in ['cveNumber', 'cveYear', 'assignerId', 'configCount', 
                                        'configConditionCount', 'vendorCommentCount', 'referenceCount', 
                                        'metricCount', 'weaknessCount']:
                                # 处理整数类型
                                try:
                                    setattr(cve_record, col, int(value))
                                except (ValueError, TypeError):
                                    setattr(cve_record, col, None)
                            elif col in ['epssScore', 'epssPercentile', 'maxCvssBaseScore', 
                                        'maxCvssBaseScorev2', 'maxCvssBaseScorev3', 'maxCvssBaseScorev4', 
                                        'maxCvssExploitabilityScore', 'maxCvssImpactScore']:
                                # 处理浮点类型
                                try:
                                    setattr(cve_record, col, float(value))
                                except (ValueError, TypeError):
                                    setattr(cve_record, col, None)
                            elif col in ['exploitExists', 'isInCISAKEV', 'isOverflow', 'isMemoryCorruption', 
                                        'isSqlInjection', 'isXss', 'isDirectoryTraversal', 'isFileInclusion', 
                                        'isCsrf', 'isXxe', 'isSsrf', 'isOpenRedirect', 'isInputValidation', 
                                        'isCodeExecution', 'isBypassSomething', 'isGainPrivilege', 
                                        'isDenialOfService', 'isInformationLeak', 'isUsedForRansomware']:
                                # 处理布尔类型
                                if isinstance(value, str):
                                    if value.lower() in ('true', 'yes', '1', 'y'):
                                        setattr(cve_record, col, True)
                                    elif value.lower() in ('false', 'no', '0', 'n'):
                                        setattr(cve_record, col, False)
                                    else:
                                        setattr(cve_record, col, None)
                                else:
                                    setattr(cve_record, col, None)
                            else:
                                # 其他列保持字符串类型
                                setattr(cve_record, col, value)
                            
                        db.session.add(cve_record)
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