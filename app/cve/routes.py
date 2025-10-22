from flask import Blueprint, render_template, jsonify, request, current_app
from datetime import datetime, timedelta, timezone
from app.cve.models import Cves, CvesLog
from app.cve.service import cve_service
import threading
import logging

cve_bp = Blueprint('cve', __name__, url_prefix='/cve')
logger = logging.getLogger('cve_routes')

@cve_bp.route('/')
def cve_index():
    # 获取CVE统计信息
    total_cves = Cves.query.count()
    
    # 获取分页数据用于表格显示
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Cves.query.order_by(Cves.published_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    cves = pagination.items
    
    # 获取统计数据
    critical_count = Cves.query.filter_by(base_severity='CRITICAL').count()
    high_count = Cves.query.filter_by(base_severity='HIGH').count()
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_7_days = Cves.query.filter(Cves.published_date >= seven_days_ago).count()
    
    # 生成年份选项
    current_year = datetime.now().year
    years = range(1999, current_year + 1)[::-1]
    
    # 获取最新的同步日志信息
    latest_log = CvesLog.query.order_by(CvesLog.sync_time.desc()).first()
    last_sync_time = None
    if latest_log:
        # 将UTC时间转换为中国时区（UTC+8）
        china_timezone = timezone(timedelta(hours=8))
        # 如果sync_time没有时区信息，先添加UTC时区
        if latest_log.sync_time.tzinfo is None:
            sync_time_utc = latest_log.sync_time.replace(tzinfo=timezone.utc)
        else:
            sync_time_utc = latest_log.sync_time
        # 转换到中国时区
        sync_time_china = sync_time_utc.astimezone(china_timezone)
        last_sync_time = sync_time_china.strftime('%Y-%m-%d %H:%M:%S')
    
    last_sync_type = '全量' if latest_log and 'full' in latest_log.message.lower() else '增量'
    last_sync_status = '成功' if latest_log and latest_log.status == 'success' else '失败'
    last_sync_count = latest_log.affected_count if latest_log else 0
    
    return render_template('cve/index.html', 
                          total_cves=total_cves,
                          cves=cves,
                          pagination=pagination,
                          years=years,
                          today=datetime.now().strftime('%Y-%m-%d'),
                          critical_count=critical_count,
                          high_count=high_count,
                          recent_7_days=recent_7_days,
                          last_sync_time=last_sync_time,
                          last_sync_type=last_sync_type,
                          last_sync_status=last_sync_status,
                          last_sync_count=last_sync_count)

@cve_bp.route('/list')
def cve_list():
    # 分页获取CVE列表
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 搜索和过滤参数
    search = request.args.get('search', '')
    severity = request.args.get('severity', '')
    min_score = request.args.get('min_score', type=float)
    
    query = Cves.query
    
    # 应用搜索条件
    if search:
        query = query.filter(
            (Cves.cve_id.contains(search)) | 
            (Cves.description.contains(search))
        )
    
    if severity:
        query = query.filter(Cves.base_severity == severity)
    
    if min_score is not None:
        query = query.filter(Cves.base_score >= min_score)
    
    # 按发布日期倒序排列
    query = query.order_by(Cves.published_date.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    cves = pagination.items
    
    return render_template('cve/list.html', 
                          cves=cves,
                          pagination=pagination,
                          search=search,
                          severity=severity,
                          min_score=min_score)

@cve_bp.route('/detail/<cve_id>')
def cve_detail(cve_id):
    cve = Cves.query.filter_by(cve_id=cve_id).first_or_404()
    return render_template('cve/detail.html', cve=cve)

@cve_bp.route('/sync', methods=['POST'])
def sync_cve_data():
    try:
        # 获取日期范围参数
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        full_sync = request.form.get('full_sync') == 'true'
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        # 如果是全量同步，在后台线程中运行
        if full_sync:
            thread = threading.Thread(
                target=cve_service.sync_all_cves,
                daemon=True
            )
            thread.start()
            return jsonify({'status': 'success', 'message': '全量同步已在后台开始，请稍后查看日志'})
        
        # 否则，同步指定日期范围的数据
        if not start_date or not end_date:
            return jsonify({'status': 'error', 'message': '请指定开始和结束日期'}), 400
        
        # 在当前线程中同步（小范围同步）
        sync_log = cve_service.sync_cve_data(start_date, end_date, "manual")
        
        return jsonify({
            'status': sync_log.status,
            'message': sync_log.message,
            'affected_count': sync_log.affected_count
        })
        
    except Exception as e:
        logger.error(f"Error in sync_cve_data: {str(e)}")
        return jsonify({'status': 'error', 'message': f'同步失败: {str(e)}'}), 500

@cve_bp.route('/logs')
def get_sync_logs():
    # 获取同步日志列表
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs = CvesLog.query.order_by(CvesLog.sync_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 转换为JSON格式
    logs_data = [log.to_dict() for log in logs.items]
    
    return jsonify({
        'logs': logs_data,
        'total': logs.total,
        'pages': logs.pages,
        'page': logs.page
    })

@cve_bp.route('/stats')
def get_cve_stats():
    # 获取CVE统计数据
    total_cves = Cves.query.count()
    
    # 按严重级别统计
    severity_counts = {
        'CRITICAL': Cves.query.filter_by(base_severity='CRITICAL').count(),
        'HIGH': Cves.query.filter_by(base_severity='HIGH').count(),
        'MEDIUM': Cves.query.filter_by(base_severity='MEDIUM').count(),
        'LOW': Cves.query.filter_by(base_severity='LOW').count(),
        'NONE': Cves.query.filter_by(base_severity='NONE').count()
    }
    
    # 获取最近7天的新增CVE数量
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_7_days = Cves.query.filter(Cves.published_date >= seven_days_ago).count()
    
    return jsonify({
        'total_cves': total_cves,
        'severity_counts': severity_counts,
        'recent_7_days': recent_7_days
    })