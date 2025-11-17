from django.core.paginator import Paginator
from project.utils.pagination import apply_pagination
from django.db.models import Q
from django.http import JsonResponse

from .models import Project
from procurement.models import Procurement
from contract.models import Contract
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
