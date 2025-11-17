from typing import Optional
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from project.utils.pagination import apply_pagination
from django.db.models import (
    Count,
    Sum,
    Q,
    OuterRef,
    Subquery,
    Value,
    DecimalField,
    Case,
    When,
    Exists,
    F,
    BooleanField,
    ExpressionWrapper,
    DateField,
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Project
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement

from project.utils.filters import apply_text_filter, apply_multi_field_search
from project.views_helpers import _resolve_global_filters, _get_page_size


def contract_list(request):
    """合同列表页面（拆分自 project/views.py）。"""
    from .filter_config import get_contract_filter_config

    global_filters = _resolve_global_filters(request)

    # 获取过滤参数
    search_query = request.GET.get('q', '')
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.get('project', '') or global_filters['project']
    file_positioning_filter = request.GET.get('file_positioning', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)

    # 排序参数
    sort_field = request.GET.get('sort', 'signing_date')
    sort_order = request.GET.get('order', 'desc')

    # 高级筛选参数
    contract_code_filter = request.GET.get('contract_code', '')
    contract_sequence_filter = request.GET.get('contract_sequence', '')
    contract_name_filter = request.GET.get('contract_name', '')
    party_a_filter = request.GET.get('party_a', '')
    party_b_filter = request.GET.get('party_b', '')
    party_b_contact_person_filter = request.GET.get('party_b_contact_person', '')
    contract_officer_filter = request.GET.get('contract_officer', '')
    contract_source_filter = request.GET.get('contract_source', '')
    contract_type_filter = request.GET.getlist('contract_type')
    party_a_legal_representative_filter = request.GET.get('party_a_legal_representative', '')
    party_a_contact_person_filter = request.GET.get('party_a_contact_person', '')
    party_a_manager_filter = request.GET.get('party_a_manager', '')
    party_b_legal_representative_filter = request.GET.get('party_b_legal_representative', '')
    party_b_manager_filter = request.GET.get('party_b_manager', '')
    has_settlement_filter = request.GET.get('has_settlement', '')
    payment_ratio_min = request.GET.get('payment_ratio_min', '')
    payment_ratio_max = request.GET.get('payment_ratio_max', '')
    signing_date_start = request.GET.get('signing_date_start', '')
    signing_date_end = request.GET.get('signing_date_end', '')
    performance_guarantee_return_date_start = request.GET.get('performance_guarantee_return_date_start', '')
    performance_guarantee_return_date_end = request.GET.get('performance_guarantee_return_date_end', '')
    contract_amount_min = request.GET.get('contract_amount_min', '')
    contract_amount_max = request.GET.get('contract_amount_max', '')

    # 基础查询
    contracts = Contract.objects.select_related('project')

    # 年度筛选
    if global_filters['year_filter'] is not None:
        contracts = contracts.filter(signing_date__year=global_filters['year_filter'])

    # 搜索过滤
    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    contracts = apply_multi_field_search(
        contracts,
        ['contract_sequence', 'contract_name', 'party_b'],
        search_query,
        mode=search_mode_value,
    )

    # 项目过滤
    if project_filter:
        contracts = contracts.filter(project__project_code=project_filter)

    # 合同类型过滤
    if file_positioning_filter:
        contracts = contracts.filter(file_positioning=file_positioning_filter)
    if contract_type_filter:
        contracts = contracts.filter(contract_type__in=contract_type_filter)

    contracts = apply_text_filter(contracts, 'contract_code', contract_code_filter)
    contracts = apply_text_filter(contracts, 'contract_sequence', contract_sequence_filter)
    contracts = apply_text_filter(contracts, 'contract_name', contract_name_filter)
    contracts = apply_text_filter(contracts, 'party_a', party_a_filter)
    contracts = apply_text_filter(contracts, 'party_b', party_b_filter)
    contracts = apply_text_filter(contracts, 'party_b_contact_person', party_b_contact_person_filter)
    contracts = apply_text_filter(contracts, 'contract_officer', contract_officer_filter)
    contracts = apply_text_filter(contracts, 'party_a_legal_representative', party_a_legal_representative_filter)
    contracts = apply_text_filter(contracts, 'party_a_contact_person', party_a_contact_person_filter)
    contracts = apply_text_filter(contracts, 'party_a_manager', party_a_manager_filter)
    contracts = apply_text_filter(contracts, 'party_b_legal_representative', party_b_legal_representative_filter)
    contracts = apply_text_filter(contracts, 'party_b_manager', party_b_manager_filter)

    # 合同来源等过滤
    if contract_source_filter:
        contracts = contracts.filter(contract_source=contract_source_filter)
    if signing_date_start:
        contracts = contracts.filter(signing_date__gte=signing_date_start)
    if signing_date_end:
        contracts = contracts.filter(signing_date__lte=signing_date_end)
    if performance_guarantee_return_date_start:
        contracts = contracts.filter(performance_guarantee_return_date__gte=performance_guarantee_return_date_start)
    if performance_guarantee_return_date_end:
        contracts = contracts.filter(performance_guarantee_return_date__lte=performance_guarantee_return_date_end)
    if contract_amount_min:
        contracts = contracts.filter(contract_amount__gte=contract_amount_min)
    if contract_amount_max:
        contracts = contracts.filter(contract_amount__lte=contract_amount_max)

    zero_decimal = Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2))
    contracts = contracts.annotate(
        total_paid_amount=Coalesce(Sum('payments__payment_amount'), zero_decimal),
        payment_count=Count('payments', distinct=True),
    )

    supplements_subquery = (
        Contract.objects.filter(parent_contract=OuterRef('pk'))
        .values('parent_contract')
        .annotate(total=Sum('contract_amount'))
        .values('total')
    )

    settlement_payment_subquery = (
        Payment.objects.filter(
            contract=OuterRef('pk'),
            is_settled=True,
            settlement_amount__isnull=False,
        )
        .order_by('-payment_date')
        .values('settlement_amount')[:1]
    )

    settlement_record_subquery = (
        Settlement.objects.filter(main_contract=OuterRef('pk')).values('final_amount')[:1]
    )

    settlement_payment_completion_subquery = (
        Payment.objects.filter(
            contract=OuterRef('pk'),
            is_settled=True,
            settlement_completion_date__isnull=False,
        )
        .order_by('-settlement_completion_date', '-payment_date')
        .values('settlement_completion_date')[:1]
    )

    settlement_record_completion_subquery = (
        Settlement.objects.filter(
            main_contract=OuterRef('pk'),
            completion_date__isnull=False,
        )
        .values('completion_date')[:1]
    )

    contracts = contracts.annotate(
        supplements_total=Coalesce(
            Subquery(
                supplements_subquery,
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            zero_decimal,
        ),
        settlement_final_amount=Subquery(
            settlement_record_subquery,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_payment_amount=Subquery(
            settlement_payment_subquery,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_record_completion_date=Subquery(
            settlement_record_completion_subquery,
            output_field=DateField(),
        ),
        settlement_payment_completion_date=Subquery(
            settlement_payment_completion_subquery,
            output_field=DateField(),
        ),
        has_settlement_record=Exists(Settlement.objects.filter(main_contract=OuterRef('pk'))),
        has_settlement_payment=Exists(
            Payment.objects.filter(contract=OuterRef('pk'), is_settled=True)
        ),
    )

    contracts = contracts.annotate(
        contract_plus_supplements=ExpressionWrapper(
            Coalesce(F('contract_amount'), zero_decimal)
            + Coalesce(F('supplements_total'), zero_decimal),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_amount=Coalesce(
            F('settlement_final_amount'),
            F('settlement_payment_amount'),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_completion_date=Coalesce(
            F('settlement_record_completion_date'),
            F('settlement_payment_completion_date'),
            output_field=DateField(),
        ),
        has_settlement=Case(
            When(has_settlement_record=True, then=Value(True)),
            When(has_settlement_payment=True, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )

    contracts = contracts.annotate(
        base_amount=Case(
            When(
                file_positioning='主合同',
                settlement_amount__isnull=False,
                then=F('settlement_amount'),
            ),
            When(file_positioning='主合同', then=F('contract_plus_supplements')),
            default=Coalesce(F('contract_amount'), zero_decimal),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )

    contracts = contracts.annotate(
        payment_ratio=Case(
            When(
                base_amount__gt=0,
                then=ExpressionWrapper(
                    F('total_paid_amount')
                    * Value(100, output_field=DecimalField(max_digits=5, decimal_places=2))
                    / F('base_amount'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            ),
            default=Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    # 应用排序
    sort_field_mapping = {
        'contract_sequence': 'contract_sequence',
        'contract_code': 'contract_code',
        'contract_name': 'contract_name',
        'party_b': 'party_b',
        'contract_amount': 'contract_amount',
        'signing_date': 'signing_date',
        'payment_ratio': 'payment_ratio',
    }

    if sort_field not in sort_field_mapping:
        sort_field = 'signing_date'
        sort_order = 'desc'

    actual_sort_field = sort_field_mapping[sort_field]
    if sort_order.lower() == 'desc':
        contracts = contracts.order_by(f'-{actual_sort_field}')
    else:
        contracts = contracts.order_by(actual_sort_field)

    def _parse_decimal(value: str) -> Optional[Decimal]:
        if value in (None, ''):
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            return None

    if has_settlement_filter:
        normalized = has_settlement_filter.lower()
        if normalized == 'true':
            contracts = contracts.filter(has_settlement=True)
        elif normalized == 'false':
            contracts = contracts.filter(has_settlement=False)

    min_ratio = _parse_decimal(payment_ratio_min)
    max_ratio = _parse_decimal(payment_ratio_max)
    if min_ratio is not None:
        contracts = contracts.filter(payment_ratio__gte=min_ratio)
    if max_ratio is not None:
        contracts = contracts.filter(payment_ratio__lte=max_ratio)

    page_obj = apply_pagination(contracts, request, page_size=page_size)

    contract_data = []
    for contract in page_obj.object_list:
        contract_data.append(
            {
                'contract': contract,
                'total_paid_amount': contract.total_paid_amount or Decimal('0'),
                'payment_count': contract.payment_count or 0,
                'has_settlement': bool(contract.has_settlement),
                'settlement_amount': contract.settlement_amount,
                'settlement_completion_date': contract.settlement_completion_date,
                'payment_ratio': contract.payment_ratio or Decimal('0'),
            }
        )

    # 获取全部项目用于过滤
    projects = Project.objects.all()

    # 获取筛选配置
    filter_config = get_contract_filter_config(request)

    context = {
        'contracts': contract_data,
        'page_obj': page_obj,
        'projects': projects,
        'search_query': search_query,
        'project_filter': project_filter,
        'file_positioning_filter': file_positioning_filter,
        'file_positionings': Contract._meta.get_field('file_positioning').choices,
        'current_sort': sort_field,
        'current_order': sort_order,
        **filter_config,
    }
    return render(request, 'contract_list.html', context)


def contract_list_enhanced(request):
    """增强合同列表（Vue友好数据）。"""
    import json

    contracts = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'file_positioning', 'contract_source',
        'party_b', 'contract_amount', 'signing_date',
        'project__project_code', 'project__project_name'
    ).order_by('-signing_date')

    contracts_data = [
        {
            'contract_code': c.contract_code,
            'contract_name': c.contract_name,
            'file_positioning': c.file_positioning,
            'contract_source': c.contract_source,
            'party_b': c.party_b,
            'contract_amount': float(c.contract_amount) if c.contract_amount else None,
            'signing_date': c.signing_date.strftime('%Y-%m-%d') if c.signing_date else None,
            'project': {
                'project_code': c.project.project_code,
                'project_name': c.project.project_name
            } if c.project else None
        }
        for c in contracts
    ]

    projects = Project.objects.only('project_code', 'project_name').order_by('project_name')
    projects_data = [
        {
            'project_code': p.project_code,
            'project_name': p.project_name
        }
        for p in projects
    ]

    context = {
        'contracts_json': json.dumps(contracts_data, ensure_ascii=False),
        'projects_json': json.dumps(projects_data, ensure_ascii=False),
    }
    return render(request, 'contract_list_enhanced.html', context)


def contract_detail(request, contract_code):
    """合同详情页面。"""
    from project.enums import FilePositioning

    contract = get_object_or_404(Contract, contract_code=contract_code)

    payments = Payment.objects.filter(contract=contract).order_by('-payment_date')
    total_paid = payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0

    payment_progress = 0
    if contract.contract_amount and contract.contract_amount > 0:
        payment_progress = (total_paid / contract.contract_amount) * 100

    procurement = contract.procurement if contract.procurement else None

    settlement = None
    if contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
        try:
            settlement = getattr(contract, 'settlement', None)
        except Exception:
            settlement = None

    supplements = []
    if contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
        supplements = getattr(contract, 'supplements', Contract.objects.none()).all().order_by('signing_date')

    # 获取履约评价记录
    from supplier_eval.models import SupplierEvaluation
    evaluations = SupplierEvaluation.objects.filter(contract=contract).order_by('-created_at')

    context = {
        'contract': contract,
        'payments': payments,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
        'procurement': procurement,
        'settlement': settlement,
        'supplements': supplements,
        'evaluations': evaluations,
    }
    return render(request, 'contract_detail.html', context)


@require_http_methods(['GET', 'POST'])
def contract_create(request):
    """合同新增视图。

    - 普通请求: 渲染全页表单，支持从任意页面跳回（通过 return_url 维护来源）。
    - AJAX 请求: 保持原有行为，返回用于模态框的 HTML 或 JSON 结果。
    """
    from project.forms import ContractForm
    from django.urls import reverse

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            try:
                contract = form.save()

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': '合同创建成功',
                        'contract_code': contract.contract_code
                    })

                # 非 AJAX 场景: 表单提交成功后跳转回来源页面或详情页
                return_url = request.POST.get('return_url') or request.GET.get('return_url')
                if return_url:
                    return redirect(return_url)
                return redirect('contract_detail', contract_code=contract.contract_code)

            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'保存失败: {str(e)}'
                    }, status=400)

                context = {
                    'form': form,
                    'submit_url': reverse('contract_create'),
                    'return_url': request.POST.get('return_url') or request.GET.get('return_url') or request.META.get('HTTP_REFERER', ''),
                    'initial_display': {},
                }
                return render(request, 'contract_create.html', context, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '表单验证失败：\n' + '\n'.join(error_messages),
                    'errors': form.errors
                }, status=400)

            context = {
                'form': form,
                'submit_url': reverse('contract_create'),
                'return_url': request.POST.get('return_url') or request.GET.get('return_url') or request.META.get('HTTP_REFERER', ''),
                'initial_display': {},
            }
            return render(request, 'contract_create.html', context, status=400)

    # GET请求 - 返回表单HTML
    from project.forms import ContractForm as _ContractForm
    form = _ContractForm()
    form.fields['contract_code'].widget.attrs.pop('readonly', None)
    form.fields['contract_code'].disabled = False

    if is_ajax:
        return render(request, 'components/edit_form.html', {
            'form': form,
            'title': '新增合同',
            'submit_url': '/contracts/create/',
            'module_type': 'contract',
        })

    submit_url = reverse('contract_create')
    return_url = request.GET.get('return_url') or request.META.get('HTTP_REFERER', '')

    context = {
        'form': form,
        'submit_url': submit_url,
        'return_url': return_url,
        'initial_display': {},
    }
    return render(request, 'contract_create.html', context)


@require_http_methods(['GET', 'POST'])
def contract_edit(request, contract_code):
    """
    合同编辑视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ContractForm

    try:
        contract = Contract.objects.get(contract_code=contract_code)
    except Contract.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '合同不存在'
            }, status=404)
        return HttpResponse('合同不存在', status=404)

    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '合同信息更新成功'
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

    form = ContractForm(instance=contract)

    initial_display = {}
    if contract.project:
        initial_display['project'] = f"{contract.project.project_code} - {contract.project.project_name}"
    if contract.procurement:
        initial_display['procurement'] = f"{contract.procurement.procurement_code} - {contract.procurement.project_name}"
    if contract.parent_contract:
        initial_display['parent_contract'] = f"{contract.parent_contract.contract_sequence or contract.parent_contract.contract_code} - {contract.parent_contract.contract_name}"

    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑合同信息',
        'submit_url': f'/contracts/{contract_code}/edit/',
        'module_type': 'contract',
        'initial_display': initial_display,
    })
