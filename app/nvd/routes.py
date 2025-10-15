from flask import Blueprint, render_template, request, jsonify
from .service import NvdService
from .log_service import sync_log_service

nvd_bp = Blueprint('nvd', __name__, url_prefix='/nvd')

@nvd_bp.route('/')
def nvd_index():
    # 获取搜索参数
    search_query = request.args.get('search', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 获取排序参数
    sort_by = request.args.get('sort_by', '')
    sort_order = request.args.get('sort_order', '')
    
    # 获取数据
    if search_query:
        pagination = NvdService.search_data(search_query, page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = NvdService.get_search_count(search_query)
    else:
        pagination = NvdService.get_all_data(page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = NvdService.get_total_count()
    
    # 可用的每页显示条数选项
    per_page_options = [20, 30, 50, 100]
    
    return render_template(
        'nvd/index.html', 
        data=pagination.items, 
        search_query=search_query,
        pagination=pagination,
        total_count=total_count,
        per_page=per_page,
        per_page_options=per_page_options,
        sort_by=sort_by,
        sort_order=sort_order
    )

@nvd_bp.route('/sync')
def sync_data():
    """手动触发数据同步"""
    from datetime import datetime, timedelta
    from flask import request, redirect, url_for, flash
    
    # 获取时间范围参数
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # 如果没有提供时间范围，默认同步最近7天的数据
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('日期格式错误，请使用YYYY-MM-DD格式', 'danger')
            return redirect(url_for('nvd.nvd_index'))
    else:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    
    # 调用同步方法
    success_count = NvdService.sync_and_save_tsv(start_date=start_date, end_date=end_date)
    
    # 记录同步日志并显示消息
    if success_count >= 0:
        sync_log_service.add_log('manual', success_count, start_date, end_date)
        flash(f'数据同步成功，新增 {success_count} 条记录', 'success')
    else:
        # 记录失败日志
        sync_log_service.add_log('manual', 0, start_date, end_date)
        flash('数据同步失败', 'danger')
    
    # 重定向回NVD主页面
    return redirect(url_for('nvd.nvd_index'))

@nvd_bp.route('/init-db')
def init_db():
    """初始化数据库表"""
    from app import db
    from .models import NvdData
    db.create_all()
    return "NVD数据库表已初始化"

@nvd_bp.route('/api/data')
def api_data():
    """提供API接口，返回JSON格式的NVD数据"""
    # 获取搜索参数
    search_query = request.args.get('search', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 获取排序参数
    sort_by = request.args.get('sort_by', '')
    sort_order = request.args.get('sort_order', '')
    
    # 获取数据
    if search_query:
        pagination = NvdService.search_data(search_query, page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = NvdService.get_search_count(search_query)
    else:
        pagination = NvdService.get_all_data(page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = NvdService.get_total_count()
    
    # 转换为JSON格式
    result = []
    for item in pagination.items:
        result.append({
            'cve_id': item.cve_id,
            'published_date': item.published_date.strftime('%Y-%m-%d') if item.published_date else '',
            'last_modified_date': item.last_modified_date.strftime('%Y-%m-%d') if item.last_modified_date else '',
            'description': item.description or '',
            'base_score': item.base_score or '',
            'base_severity': item.base_severity or '',
            'vector_string': item.vector_string or '',
            'vendor': item.vendor or '',
            'product': item.product or ''
        })
    
    return jsonify({
        'data': result,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })

@nvd_bp.route('/api/logs')
def api_logs():
    """提供同步日志API接口"""
    from flask import request, jsonify
    
    # 获取参数
    limit = int(request.args.get('limit', 50))
    
    # 获取日志
    logs = sync_log_service.get_logs(limit=limit)
    
    # 返回JSON响应
    return jsonify(logs)
    
@nvd_bp.route('/cve/<cve_id>')
def cve_detail(cve_id):
    """显示单个CVE的详细信息"""
    cve_data = NvdService.get_by_cve_id(cve_id)
    
    if not cve_data:
        # 如果找不到对应的CVE，显示错误信息
        from flask import flash, redirect, url_for
        flash(f'未找到CVE ID为 {cve_id} 的记录', 'danger')
        return redirect(url_for('nvd.nvd_index'))
    
    return render_template('nvd/cve_detail.html', cve_data=cve_data)