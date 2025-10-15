from datetime import datetime, timedelta
from app import create_app, db
from app.nvd.models import NvdData

# 创建应用实例
app = create_app()

# 在应用上下文中查询数据库
with app.app_context():
    # 检查2025年10月所有数据的分布情况
    print("2025年10月数据按日期分布：")
    
    # 查询2025年10月的所有记录
    october_data = NvdData.query.filter(
        NvdData.published_date >= datetime.strptime('2025-10-01', '%Y-%m-%d').date(),
        NvdData.published_date <= datetime.strptime('2025-10-31', '%Y-%m-%d').date()
    ).all()
    
    # 按日期分组统计
    date_counts = {}
    for data in october_data:
        date_str = data.published_date.strftime('%Y-%m-%d')
        if date_str not in date_counts:
            date_counts[date_str] = 0
        date_counts[date_str] += 1
    
    # 排序并打印
    for date_str in sorted(date_counts.keys()):
        print(f"{date_str}: {date_counts[date_str]}条记录")
    
    print(f"\n2025年10月总记录数: {len(october_data)}")
    
    # 检查是否有未来日期的数据
    today = datetime.utcnow().date()
    future_data = NvdData.query.filter(NvdData.published_date > today).all()
    print(f"未来日期的数据数量: {len(future_data)}")
    for data in future_data[:5]:  # 只显示前5条
        print(f"  {data.cve_id}: {data.published_date.strftime('%Y-%m-%d')}")
    
    # 检查数据是否都是low评分
    low_score_count = NvdData.query.filter(
        NvdData.published_date >= datetime.strptime('2025-10-01', '%Y-%m-%d').date(),
        NvdData.published_date <= datetime.strptime('2025-10-31', '%Y-%m-%d').date(),
        NvdData.base_severity == 'LOW'
    ).count()
    print(f"\n2025年10月LOW评分记录数: {low_score_count}")