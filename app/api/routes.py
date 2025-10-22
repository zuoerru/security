from flask import Blueprint, request, jsonify
from app.cve.models import Cves
from app.nvd.models import NvdData
from app.cisa.models import CisaData
from datetime import datetime, timezone, timedelta
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger('api_routes')

@api_bp.route('/cve/<cve_id>', methods=['GET'])
def get_cve_info(cve_id):
    """
    查询指定CVE ID的详细信息，同时从cves、nvd和cisa三张表中获取数据
    
    Args:
        cve_id: CVE编号，如CVE-2021-44228
        
    Returns:
        JSON格式的CVE详细信息，包含各表中的相关数据
    """
    try:
        # 参数验证
        if not cve_id or not cve_id.startswith('CVE-'):
            return jsonify({
                'error': True,
                'message': '无效的CVE ID格式，请使用标准格式如CVE-2021-44228'
            }), 400
        
        # 查询各表数据
        cve_data = None
        nvd_data = None
        cisa_data = None
        
        # 查询cves表
        cve_record = Cves.query.filter_by(cve_id=cve_id).first()
        if cve_record:
            # 将UTC时间转换为中国时区
            china_timezone = timezone(timedelta(hours=8))
            
            # 处理时间字段
            def format_datetime(dt):
                if dt.tzinfo is None:
                    dt_utc = dt.replace(tzinfo=timezone.utc)
                else:
                    dt_utc = dt
                return dt_utc.astimezone(china_timezone).strftime('%Y-%m-%d %H:%M:%S')
            
            cve_data = {
                'cve_id': cve_record.cve_id,
                'published_date': format_datetime(cve_record.published_date),
                'last_modified_date': format_datetime(cve_record.last_modified_date),
                'description': cve_record.description,
                'base_score': cve_record.base_score,
                'base_severity': cve_record.base_severity,
                'attack_vector': cve_record.attack_vector,
                'attack_complexity': cve_record.attack_complexity,
                'privileges_required': cve_record.privileges_required,
                'user_interaction': cve_record.user_interaction,
                'scope': cve_record.scope,
                'confidentiality_impact': cve_record.confidentiality_impact,
                'integrity_impact': cve_record.integrity_impact,
                'availability_impact': cve_record.availability_impact,
                'cwe_id': cve_record.cwe_id,
                'references': cve_record.references
            }
        
        # 查询nvd表
        nvd_record = NvdData.query.filter_by(cve_id=cve_id).first()
        if nvd_record:
            nvd_data = {
                'cve_id': nvd_record.cve_id,
                'published_date': nvd_record.published_date.strftime('%Y-%m-%d') if nvd_record.published_date else None,
                'last_modified_date': nvd_record.last_modified_date.strftime('%Y-%m-%d') if nvd_record.last_modified_date else None,
                'description': nvd_record.description,
                'base_score': nvd_record.base_score,
                'base_severity': nvd_record.base_severity,
                'vector_string': nvd_record.vector_string,
                'vendor': nvd_record.vendor,
                'product': nvd_record.product
            }
        
        # 查询cisa表
        cisa_records = CisaData.query.filter_by(cve_id=cve_id).all()
        if cisa_records:
            cisa_data = []
            for record in cisa_records:
                cisa_data.append({
                    'vuln_id': record.vuln_id,
                    'vendor_project': record.vendor_project,
                    'product': record.product,
                    'vulnerability_name': record.vulnerability_name,
                    'date_added': record.date_added.strftime('%Y-%m-%d') if record.date_added else None,
                    'short_description': record.short_description,
                    'required_action': record.required_action,
                    'due_date': record.due_date.strftime('%Y-%m-%d') if record.due_date else None,
                    'cve_id': record.cve_id
                })
        
        # 检查是否有数据返回
        if not cve_data and not nvd_data and not cisa_data:
            return jsonify({
                'error': False,
                'message': f'未找到CVE ID: {cve_id}的相关信息',
                'data': None
            }), 404
        
        # 构建响应
        response = {
            'error': False,
            'message': '查询成功',
            'data': {
                'cve_id': cve_id,
                'cves_table': cve_data,
                'nvd_table': nvd_data,
                'cisa_table': cisa_data,
                'timestamp': datetime.now(china_timezone).strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"查询CVE信息失败: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'查询过程中发生错误: {str(e)}'
        }), 500

@api_bp.route('/cve/batch', methods=['POST'])
def batch_get_cve_info():
    """
    批量查询多个CVE ID的信息
    
    请求体格式:
    {
        "cve_ids": ["CVE-2021-44228", "CVE-2021-22204"]
    }
    
    Returns:
        JSON格式的批量查询结果
    """
    try:
        data = request.get_json()
        if not data or 'cve_ids' not in data:
            return jsonify({
                'error': True,
                'message': '请求体格式错误，需要包含cve_ids字段'
            }), 400
        
        cve_ids = data['cve_ids']
        if not isinstance(cve_ids, list) or not cve_ids:
            return jsonify({
                'error': True,
                'message': 'cve_ids必须是非空数组'
            }), 400
        
        # 限制批量查询数量
        if len(cve_ids) > 50:
            return jsonify({
                'error': True,
                'message': '批量查询数量不能超过50个'
            }), 400
        
        # 验证CVE ID格式
        for cve_id in cve_ids:
            if not cve_id or not cve_id.startswith('CVE-'):
                return jsonify({
                    'error': True,
                    'message': f'无效的CVE ID格式: {cve_id}'
                }), 400
        
        # 批量查询
        results = []
        for cve_id in cve_ids:
            # 这里复用get_cve_info的逻辑，但不返回响应
            cve_data = None
            nvd_data = None
            cisa_data = None
            
            # 查询cves表
            cve_record = Cves.query.filter_by(cve_id=cve_id).first()
            if cve_record:
                # 时间处理逻辑类似
                china_timezone = timezone(timedelta(hours=8))
                
                def format_datetime(dt):
                    if dt.tzinfo is None:
                        dt_utc = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt_utc = dt
                    return dt_utc.astimezone(china_timezone).strftime('%Y-%m-%d %H:%M:%S')
                
                cve_data = {
                    'cve_id': cve_record.cve_id,
                    'published_date': format_datetime(cve_record.published_date),
                    'last_modified_date': format_datetime(cve_record.last_modified_date),
                    'description': cve_record.description,
                    'base_score': cve_record.base_score,
                    'base_severity': cve_record.base_severity,
                    'attack_vector': cve_record.attack_vector,
                    'attack_complexity': cve_record.attack_complexity,
                    'privileges_required': cve_record.privileges_required,
                    'user_interaction': cve_record.user_interaction,
                    'scope': cve_record.scope,
                    'confidentiality_impact': cve_record.confidentiality_impact,
                    'integrity_impact': cve_record.integrity_impact,
                    'availability_impact': cve_record.availability_impact,
                    'cwe_id': cve_record.cwe_id,
                    'references': cve_record.references
                }
            
            # 查询nvd表
            nvd_record = NvdData.query.filter_by(cve_id=cve_id).first()
            if nvd_record:
                nvd_data = {
                    'cve_id': nvd_record.cve_id,
                    'published_date': nvd_record.published_date.strftime('%Y-%m-%d') if nvd_record.published_date else None,
                    'last_modified_date': nvd_record.last_modified_date.strftime('%Y-%m-%d') if nvd_record.last_modified_date else None,
                    'description': nvd_record.description,
                    'base_score': nvd_record.base_score,
                    'base_severity': nvd_record.base_severity,
                    'vector_string': nvd_record.vector_string,
                    'vendor': nvd_record.vendor,
                    'product': nvd_record.product
                }
            
            # 查询cisa表
            cisa_records = CisaData.query.filter_by(cve_id=cve_id).all()
            if cisa_records:
                cisa_data = []
                for record in cisa_records:
                    cisa_data.append({
                        'vuln_id': record.vuln_id,
                        'vendor_project': record.vendor_project,
                        'product': record.product,
                        'vulnerability_name': record.vulnerability_name,
                        'date_added': record.date_added.strftime('%Y-%m-%d') if record.date_added else None,
                        'short_description': record.short_description,
                        'required_action': record.required_action,
                        'due_date': record.due_date.strftime('%Y-%m-%d') if record.due_date else None,
                        'cve_id': record.cve_id
                    })
            
            results.append({
                'cve_id': cve_id,
                'cves_table': cve_data,
                'nvd_table': nvd_data,
                'cisa_table': cisa_data,
                'has_data': cve_data is not None or nvd_data is not None or cisa_data is not None
            })
        
        response = {
            'error': False,
            'message': '批量查询成功',
            'data': {
                'results': results,
                'total': len(results),
                'timestamp': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"批量查询CVE信息失败: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'查询过程中发生错误: {str(e)}'
        }), 500