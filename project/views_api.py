from django.core.paginator import Paginator
from project.utils.pagination import apply_pagination
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json

from .models import Project
from procurement.models import Procurement
from contract.models import Contract
from project.services.completeness import get_enabled_fields
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    summary="项目列表",
    description="根据搜索关键字与分页参数获取项目列表。",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            description="按项目编码或名称模糊搜索",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="页码（从1开始）",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            description="每页数量",
            required=False,
        ),
    ],
    tags=["基础数据"],
)
def api_projects_list(request):
    """项目列表API - 支持搜索与分页。"""
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    projects = Project.objects.all()
    if search:
        projects = projects.filter(Q(project_code__icontains=search) | Q(project_name__icontains=search))

    page_obj = apply_pagination(projects, request, page_size=page_size)
    paginator = page_obj.paginator
    data = [
        {
            'id': project.project_code,
            'project_code': project.project_code,
            'project_name': project.project_name,
            'display_text': f"{project.project_code} - {project.project_name}",
        }
        for project in page_obj
    ]
    return JsonResponse(
        {
            'success': True,
            'data': data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        }
    )


@extend_schema(
    summary="采购列表",
    description="根据项目与关键字获取采购列表，用于前端级联选择器。",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            description="按采购编号或项目名称模糊搜索",
            required=False,
        ),
        OpenApiParameter(
            name="project",
            type=str,
            location=OpenApiParameter.QUERY,
            description="过滤指定项目编码下的采购",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="页码（从1开始）",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            description="每页数量",
            required=False,
        ),
    ],
    tags=["基础数据"],
)
def api_procurements_list(request):
    """采购列表API - 支持项目筛选与搜索。"""
    search = request.GET.get('search', '')
    project = request.GET.get('project', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    procurements = Procurement.objects.select_related('project')
    if project:
        procurements = procurements.filter(project__project_code=project)
    if search:
        procurements = procurements.filter(Q(procurement_code__icontains=search) | Q(project_name__icontains=search))

    page_obj = apply_pagination(procurements, request, page_size=page_size)
    paginator = page_obj.paginator
    data = [
        {
            'id': procurement.procurement_code,
            'procurement_code': procurement.procurement_code,
            'project_name': procurement.project_name,
            'project_code': procurement.project.project_code if procurement.project else '',
            'display_text': f"{procurement.procurement_code} - {procurement.project_name}",
        }
        for procurement in page_obj
    ]
    return JsonResponse(
        {
            'success': True,
            'data': data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        }
    )


@extend_schema(
    summary="合同列表",
    description="根据项目、采购和文件定位获取合同列表，用于合同选择器。",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            description="按合同编号、名称或序号模糊搜索",
            required=False,
        ),
        OpenApiParameter(
            name="project",
            type=str,
            location=OpenApiParameter.QUERY,
            description="项目编码（与 project_id 兼容）",
            required=False,
        ),
        OpenApiParameter(
            name="project_id",
            type=str,
            location=OpenApiParameter.QUERY,
            description="历史参数名，等同于 project",
            required=False,
        ),
        OpenApiParameter(
            name="procurement",
            type=str,
            location=OpenApiParameter.QUERY,
            description="关联的采购编号",
            required=False,
        ),
        OpenApiParameter(
            name="file_positioning",
            type=str,
            location=OpenApiParameter.QUERY,
            description="文件定位（主合同/补充协议等枚举值）",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="页码（从1开始）",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            description="每页数量",
            required=False,
        ),
    ],
    tags=["基础数据"],
)
def api_contracts_list(request):
    """合同列表API - 支持项目与采购筛选。"""
    search = request.GET.get('search', '')
    project = request.GET.get('project_id', '') or request.GET.get('project', '')
    procurement = request.GET.get('procurement', '')
    file_positioning = request.GET.get('file_positioning', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    contracts = Contract.objects.select_related('project', 'procurement')
    if project:
        contracts = contracts.filter(project__project_code=project)
    if procurement:
        contracts = contracts.filter(procurement__procurement_code=procurement)
    if file_positioning:
        contracts = contracts.filter(file_positioning=file_positioning)
    if search:
        contracts = contracts.filter(
            Q(contract_code__icontains=search)
            | Q(contract_name__icontains=search)
            | Q(contract_sequence__icontains=search)
        )

    page_obj = apply_pagination(contracts, request, page_size=page_size)
    paginator = page_obj.paginator
    data = [
        {
            'id': contract.contract_code,
            'contract_code': contract.contract_code,
            'contract_name': contract.contract_name,
            'contract_sequence': contract.contract_sequence or '',
            'file_positioning': contract.file_positioning,
            'project_code': contract.project.project_code if contract.project else '',
            'project_name': contract.project.project_name if contract.project else '',
            'procurement_code': contract.procurement.procurement_code if contract.procurement else '',
            'display_text': f"{contract.contract_sequence or contract.contract_code} - {contract.contract_name}",
        }
        for contract in page_obj
    ]
    return JsonResponse(
        {
            'success': True,
            'data': data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        }
    )


# ==================== 齐全性检查快速编辑API ====================

def _format_field_value(value):
    """格式化字段值"""
    if value is None or value == '':
        return ''
    elif isinstance(value, (int, float)):
        return str(value)
    elif hasattr(value, 'strftime'):
        # 确保日期格式为 YYYY-MM-DD（补零）
        return value.strftime('%Y-%m-%d')
    return str(value)


def _parse_field_value(value, field_type):
    """解析字段值"""
    from datetime import datetime
    
    if value == '' or value is None:
        return None
    
    if field_type == 'DateField':
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d').date()
    elif field_type in ['DecimalField', 'FloatField']:
        return float(value) if value else None
    elif field_type == 'IntegerField':
        return int(value) if value else None
    
    return value


def _get_record_detail_for_edit(model_class, code_field, code_value, model_type):
    """通用获取记录详情方法"""
    try:
        record = get_object_or_404(model_class, **{code_field: code_value})
        enabled_fields = get_enabled_fields(model_type)
        
        field_data = {}
        missing_fields = []
        
        for field_name in enabled_fields:
            try:
                field = model_class._meta.get_field(field_name)
                value = getattr(record, field_name, None)
                formatted_value = _format_field_value(value)
                
                if formatted_value == '':
                    missing_fields.append(field.verbose_name)
                
                field_info = {
                    'value': formatted_value,
                    'label': field.verbose_name,
                    'field_type': field.get_internal_type(),
                    'is_required': not field.blank,
                }
                
                # 如果字段有choices，添加选项列表
                if hasattr(field, 'choices') and field.choices:
                    field_info['choices'] = [
                        {'value': choice[0], 'label': choice[1]}
                        for choice in field.choices
                    ]
                
                field_data[field_name] = field_info
            except Exception:
                continue
        
        return JsonResponse({
            'success': True,
            'data': {
                code_field: code_value,
                'fields': field_data,
                'missing_fields': missing_fields,
                'missing_count': len(missing_fields)
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取详情失败: {str(e)}'
        }, status=400)


def _quick_update_record(request, model_class, code_field, code_value, model_type):
    """通用快速更新记录方法"""
    try:
        record = get_object_or_404(model_class, **{code_field: code_value})
        data = json.loads(request.body)
        enabled_fields = get_enabled_fields(model_type)

        # 记录原始值，用于后续构造字段级变更日志
        original_values = {}
        for field_name in enabled_fields:
            if hasattr(record, field_name):
                original_values[field_name] = getattr(record, field_name, None)
        
        updated_fields = []
        for field_name, value in data.items():
            if field_name in enabled_fields and hasattr(record, field_name):
                try:
                    field = model_class._meta.get_field(field_name)
                    parsed_value = _parse_field_value(value, field.get_internal_type())
                    setattr(record, field_name, parsed_value)
                    if parsed_value:
                        updated_fields.append(field.verbose_name)
                except Exception:
                    continue
        
        record.save()

        # 构造字段级变更信息，供操作日志中间件使用
        changes = {}
        for field_name in enabled_fields:
            if not hasattr(record, field_name):
                continue
            old_value = original_values.get(field_name)
            new_value = getattr(record, field_name, None)
            if old_value != new_value:
                changes[field_name] = {
                    "old": str(old_value) if old_value is not None else None,
                    "new": str(new_value) if new_value is not None else None,
                }

        if changes:
            # 中间件会优先使用此结构化 diff 生成更精确的操作日志
            request.operation_log_meta = {"changes": changes}
        
        # 重新计算缺失字段
        missing_fields = []
        for field_name in enabled_fields:
            value = getattr(record, field_name, None)
            if value is None or value == '':
                field = model_class._meta.get_field(field_name)
                missing_fields.append(field.verbose_name)
        
        completeness = ((len(enabled_fields) - len(missing_fields)) / len(enabled_fields) * 100) if enabled_fields else 100
        
        return JsonResponse({
            'success': True,
            'message': f'成功更新 {len(updated_fields)} 个字段',
            'updated_fields': updated_fields,
            'missing_count': len(missing_fields),
            'completeness': round(completeness, 2),
            'is_complete': len(missing_fields) == 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }, status=400)


@require_http_methods(["GET"])
@login_required
@ensure_csrf_cookie
def api_procurement_detail_for_edit(request, procurement_code):
    """获取采购记录详情（用于编辑模态框）"""
    return _get_record_detail_for_edit(Procurement, 'procurement_code', procurement_code, 'procurement')


@require_http_methods(["POST"])
@login_required
def api_procurement_quick_update(request, procurement_code):
    """快速更新采购记录"""
    return _quick_update_record(request, Procurement, 'procurement_code', procurement_code, 'procurement')


@require_http_methods(["GET"])
@login_required
@ensure_csrf_cookie
def api_contract_detail_for_edit(request, contract_code):
    """获取合同记录详情（用于编辑模态框）"""
    return _get_record_detail_for_edit(Contract, 'contract_code', contract_code, 'contract')


@require_http_methods(["POST"])
@login_required
def api_contract_quick_update(request, contract_code):
    """快速更新合同记录"""
    return _quick_update_record(request, Contract, 'contract_code', contract_code, 'contract')
