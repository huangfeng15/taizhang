from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from .models import Project
from procurement.models import Procurement
from contract.models import Contract


def api_projects_list(request):
    """项目列表API - 支持搜索与分页。"""
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    projects = Project.objects.all()
    if search:
        projects = projects.filter(Q(project_code__icontains=search) | Q(project_name__icontains=search))

    paginator = Paginator(projects, page_size)
    page_obj = paginator.get_page(page)
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

    paginator = Paginator(procurements, page_size)
    page_obj = paginator.get_page(page)
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

    paginator = Paginator(contracts, page_size)
    page_obj = paginator.get_page(page)
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

