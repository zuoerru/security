from flask import Blueprint, render_template, request, jsonify
from .service import CisaService

cisa_bp = Blueprint('cisa', __name__, url_prefix='/cisa')

@cisa_bp.route('/')
def cisa_index():
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
        pagination = CisaService.search_data(search_query, page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = CisaService.get_search_count(search_query)
    else:
        pagination = CisaService.get_all_data(page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = CisaService.get_total_count()
    
    # 可用的每页显示条数选项
    per_page_options = [20, 30, 50, 100]
    
    return render_template(
        'cisa/index.html', 
        data=pagination.items, 
        search_query=search_query,
        pagination=pagination,
        total_count=total_count,
        per_page=per_page,
        per_page_options=per_page_options,
        sort_by=sort_by,
        sort_order=sort_order
    )

@cisa_bp.route('/sync')
def sync_data():
    """手动触发数据同步"""
    success = CisaService.compare_and_update_db()
    if success:
        return "数据同步成功"
    else:
        return "数据同步失败"

@cisa_bp.route('/init-db')
def init_db():
    """初始化数据库表"""
    from app import db
    from .models import CisaData
    db.create_all()
    return "CISA数据库表已初始化"

@cisa_bp.route('/api/data')
def api_data():
    """提供API接口，返回JSON格式的CISA数据"""
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
        pagination = CisaService.search_data(search_query, page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = CisaService.get_search_count(search_query)
    else:
        pagination = CisaService.get_all_data(page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        total_count = CisaService.get_total_count()
    
    # 转换为JSON格式
    result = []
    for item in pagination.items:
        result.append({
            'vuln_id': item.vuln_id,
            'vendor_project': item.vendor_project,
            'product': item.product or '',
            'vulnerability_name': item.vulnerability_name,
            'date_added': item.date_added.strftime('%Y-%m-%d') if item.date_added else '',
            'cve_id': item.cve_id or '',
            'due_date': item.due_date.strftime('%Y-%m-%d') if item.due_date else ''
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

@cisa_bp.route('/vuln/<vuln_id>')
def vuln_detail(vuln_id):
    """显示单个漏洞的详细信息"""
    # 从数据库获取漏洞详情
    cisa_data = CisaService.get_by_vuln_id(vuln_id)
    
    # 如果找不到漏洞，重定向到首页并显示错误消息
    if not cisa_data:
        from flask import redirect, url_for, flash
        flash(f'未找到漏洞ID: {vuln_id}', 'error')
        return redirect(url_for('cisa.cisa_index'))
    
    # 渲染漏洞详情页面
    return render_template('cisa/vuln_detail.html', cisa_data=cisa_data)