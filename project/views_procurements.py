from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment

from project.utils.filters import apply_text_filter, apply_multi_field_search
from project.views_helpers import _resolve_global_filters, _get_page_size


def procurement_list(request):
    """采购列表页面（拆分自 project/views.py）。"""
    from .filter_config import get_procurement_filter_config

    global_filters = _resolve_global_filters(request)

    search_query = request.GET.get('q', '')
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.getlist('project')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)

    procurement_code_filter = request.GET.get('procurement_code', '')
    project_name_filter = request.GET.get('project_name', '')
    procurement_unit_filter = request.GET.get('procurement_unit', '')
    procurement_category_filter = request.GET.get('procurement_category', '')
    procurement_method_filter = request.GET.get('procurement_method', '')
    qualification_review_filter = request.GET.get('qualification_review_method', '')
    bid_evaluation_filter = request.GET.get('bid_evaluation_method', '')
    bid_awarding_filter = request.GET.get('bid_awarding_method', '')
    winning_bidder_filter = request.GET.get('winning_bidder', '')
    candidate_publicity_issue_filter = request.GET.get('candidate_publicity_issue', '')
    non_bidding_explanation_filter = request.GET.get('non_bidding_explanation', '')
    announcement_release_date_start = request.GET.get('announcement_release_date_start', '')
    announcement_release_date_end = request.GET.get('announcement_release_date_end', '')
    registration_deadline_start = request.GET.get('registration_deadline_start', '')
    registration_deadline_end = request.GET.get('registration_deadline_end', '')
    bid_opening_date_start = request.GET.get('bid_opening_date_start', '')
    bid_opening_date_end = request.GET.get('bid_opening_date_end', '')
    candidate_publicity_end_start = request.GET.get('candidate_publicity_end_date_start', '')
    candidate_publicity_end_end = request.GET.get('candidate_publicity_end_date_end', '')
    result_publicity_release_start = request.GET.get('result_publicity_release_date_start', '')
    result_publicity_release_end = request.GET.get('result_publicity_release_date_end', '')
    planned_completion_date_start = request.GET.get('planned_completion_date_start', '')
    planned_completion_date_end = request.GET.get('planned_completion_date_end', '')
    notice_issue_date_start = request.GET.get('notice_issue_date_start', '')
    notice_issue_date_end = request.GET.get('notice_issue_date_end', '')
    archive_date_start = request.GET.get('archive_date_start', '')
    archive_date_end = request.GET.get('archive_date_end', '')
    budget_amount_min = request.GET.get('budget_amount_min', '')
    budget_amount_max = request.GET.get('budget_amount_max', '')
    winning_amount_min = request.GET.get('winning_amount_min', '')
    winning_amount_max = request.GET.get('winning_amount_max', '')

    procurements = Procurement.objects.select_related('project')
    if global_filters['year_filter'] is not None:
        procurements = procurements.filter(result_publicity_release_date__year=global_filters['year_filter'])

    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    procurements = apply_multi_field_search(
        procurements,
        ['procurement_code', 'project_name', 'procurement_category', 'winning_bidder'],
        search_query,
        mode=search_mode_value,
    )

    project_filter = [p for p in project_filter if p]
    if not project_filter and global_filters['project']:
        project_filter = [global_filters['project']]
    if project_filter:
        procurements = procurements.filter(project__project_code__in=project_filter)

    procurements = apply_text_filter(procurements, 'procurement_code', procurement_code_filter)
    procurements = apply_text_filter(procurements, 'project_name', project_name_filter)
    procurements = apply_text_filter(procurements, 'procurement_unit', procurement_unit_filter)
    procurements = apply_text_filter(procurements, 'procurement_category', procurement_category_filter)
    procurements = apply_text_filter(procurements, 'procurement_method', procurement_method_filter)
    procurements = apply_text_filter(procurements, 'qualification_review_method', qualification_review_filter)
    procurements = apply_text_filter(procurements, 'bid_evaluation_method', bid_evaluation_filter)
    procurements = apply_text_filter(procurements, 'bid_awarding_method', bid_awarding_filter)
    procurements = apply_text_filter(procurements, 'winning_bidder', winning_bidder_filter)
    procurements = apply_text_filter(procurements, 'candidate_publicity_issue', candidate_publicity_issue_filter)
    procurements = apply_text_filter(procurements, 'non_bidding_explanation', non_bidding_explanation_filter)

    if announcement_release_date_start:
        procurements = procurements.filter(announcement_release_date__gte=announcement_release_date_start)
    if announcement_release_date_end:
        procurements = procurements.filter(announcement_release_date__lte=announcement_release_date_end)
    if registration_deadline_start:
        procurements = procurements.filter(registration_deadline__gte=registration_deadline_start)
    if registration_deadline_end:
        procurements = procurements.filter(registration_deadline__lte=registration_deadline_end)
    if bid_opening_date_start:
        procurements = procurements.filter(bid_opening_date__gte=bid_opening_date_start)
    if bid_opening_date_end:
        procurements = procurements.filter(bid_opening_date__lte=bid_opening_date_end)
    if candidate_publicity_end_start:
        procurements = procurements.filter(candidate_publicity_end_date__gte=candidate_publicity_end_start)
    if candidate_publicity_end_end:
        procurements = procurements.filter(candidate_publicity_end_date__lte=candidate_publicity_end_end)
    if result_publicity_release_start:
        procurements = procurements.filter(result_publicity_release_date__gte=result_publicity_release_start)
    if result_publicity_release_end:
        procurements = procurements.filter(result_publicity_release_date__lte=result_publicity_release_end)
    if planned_completion_date_start:
        procurements = procurements.filter(planned_completion_date__gte=planned_completion_date_start)
    if planned_completion_date_end:
        procurements = procurements.filter(planned_completion_date__lte=planned_completion_date_end)
    if notice_issue_date_start:
        procurements = procurements.filter(notice_issue_date__gte=notice_issue_date_start)
    if notice_issue_date_end:
        procurements = procurements.filter(notice_issue_date__lte=notice_issue_date_end)
    if archive_date_start:
        procurements = procurements.filter(archive_date__gte=archive_date_start)
    if archive_date_end:
        procurements = procurements.filter(archive_date__lte=archive_date_end)
    if budget_amount_min:
        procurements = procurements.filter(budget_amount__gte=budget_amount_min)
    if budget_amount_max:
        procurements = procurements.filter(budget_amount__lte=budget_amount_max)
    if winning_amount_min:
        procurements = procurements.filter(winning_amount__gte=winning_amount_min)
    if winning_amount_max:
        procurements = procurements.filter(winning_amount__lte=winning_amount_max)

    procurements = procurements.order_by('-result_publicity_release_date', '-bid_opening_date', '-created_at')

    paginator = Paginator(procurements, page_size)
    page_obj = paginator.get_page(page)

    filter_config = get_procurement_filter_config(request)

    context = {
        'procurements': page_obj,
        'page_obj': page_obj,
        **filter_config,
    }
    return render(request, 'procurement_list.html', context)


def procurement_detail(request, procurement_code):
    """采购详情页面。"""
    procurement = get_object_or_404(Procurement, procurement_code=procurement_code)

    contracts = Contract.objects.filter(
        procurement=procurement
    ).order_by('-signing_date')

    all_payments = Payment.objects.filter(
        contract__procurement=procurement
    ).order_by('-payment_date')

    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    payment_count = all_payments.count()

    settlement_count = Contract.objects.filter(
        procurement=procurement
    ).filter(
        Q(settlement__isnull=False) |
        Q(payments__is_settled=True) |
        Q(payments__settlement_amount__isnull=False)
    ).distinct().count()

    total_contract_amount = contracts.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0

    context = {
        'procurement': procurement,
        'contracts': contracts,
        'all_payments': all_payments[:10],
        'total_paid': total_paid,
        'payment_count': payment_count,
        'settlement_count': settlement_count,
        'total_contract_amount': total_contract_amount,
    }
    return render(request, 'procurement_detail.html', context)


@require_http_methods(['GET', 'POST'])
def procurement_create(request):
    """
    采购新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ProcurementForm

    if request.method == 'POST':
        form = ProcurementForm(request.POST)
        if form.is_valid():
            try:
                procurement = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '采购项目创建成功',
                    'procurement_code': procurement.procurement_code
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

            return JsonResponse({
                'success': False,
                'message': '表单验证失败：\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)

    form = ProcurementForm()
    form.fields['procurement_code'].widget.attrs.pop('readonly', None)
    form.fields['procurement_code'].disabled = False

    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增采购项目',
        'submit_url': '/procurements/create/',
        'module_type': 'procurement',
    })


@require_http_methods(['GET', 'POST'])
def procurement_edit(request, procurement_code):
    """
    采购编辑视图 - AJAX接口
    """
    from project.forms import ProcurementForm

    try:
        procurement = Procurement.objects.get(procurement_code=procurement_code)
    except Procurement.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '采购项目不存在'
            }, status=404)
        return HttpResponse('采购项目不存在', status=404)

    if request.method == 'POST':
        form = ProcurementForm(request.POST, instance=procurement)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '采购信息更新成功'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

            detailed_message = '表单验证失败：\n' + '\n'.join(error_messages)

            return JsonResponse({
                'success': False,
                'message': detailed_message,
                'errors': form.errors,
                'field_errors': {
                    field: list(errors) for field, errors in form.errors.items()
                }
            }, status=400)

    form = ProcurementForm(instance=procurement)

    initial_display = {}
    if procurement.project:
        initial_display['project'] = f"{procurement.project.project_code} - {procurement.project.project_name}"

    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑采购信息',
        'submit_url': f'/procurements/{procurement_code}/edit/',
        'module_type': 'procurement',
        'initial_display': initial_display,
    })

