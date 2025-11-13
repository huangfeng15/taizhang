from django.core.paginator import Paginator
from project.utils.pagination import apply_pagination
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from payment.models import Payment

from project.utils.filters import apply_text_filter, apply_multi_field_search
from project.views_helpers import _resolve_global_filters, _get_page_size


def payment_list(request):
    """付款列表页面（拆分自 project/views.py）。"""
    from .filter_config import get_payment_filter_config

    global_filters = _resolve_global_filters(request)

    search_query = request.GET.get('q', '')
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.getlist('project')
    is_settled_filter = request.GET.getlist('is_settled')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20, max_size=1000)

    payment_code_filter = request.GET.get('payment_code', '')
    contract_name_filter = request.GET.get('contract_name', '')
    payment_date_start = request.GET.get('payment_date_start', '')
    payment_date_end = request.GET.get('payment_date_end', '')
    payment_amount_min = request.GET.get('payment_amount_min', '')
    payment_amount_max = request.GET.get('payment_amount_max', '')

    payments = Payment.objects.select_related('contract', 'contract__project')

    if global_filters['year_filter'] is not None:
        payments = payments.filter(payment_date__year=global_filters['year_filter'])

    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    payments = apply_multi_field_search(
        payments,
        ['payment_code', 'contract__contract_name'],
        search_query,
        mode=search_mode_value,
    )

    project_filter = [p for p in project_filter if p]
    if not project_filter and global_filters['project']:
        project_filter = [global_filters['project']]
    if project_filter:
        payments = payments.filter(contract__project__project_code__in=project_filter)

    is_settled_filter = [s for s in is_settled_filter if s]
    if is_settled_filter:
        is_settled_values = [v.lower() == 'true' for v in is_settled_filter]
        payments = payments.filter(is_settled__in=is_settled_values)

    payments = apply_text_filter(payments, 'payment_code', payment_code_filter)
    payments = apply_text_filter(payments, 'contract__contract_name', contract_name_filter)

    if payment_date_start:
        payments = payments.filter(payment_date__gte=payment_date_start)
    if payment_date_end:
        payments = payments.filter(payment_date__lte=payment_date_end)
    if payment_amount_min:
        payments = payments.filter(payment_amount__gte=payment_amount_min)
    if payment_amount_max:
        payments = payments.filter(payment_amount__lte=payment_amount_max)

    payments = payments.order_by('-payment_date')

    page_obj = apply_pagination(payments, request, page_size=page_size)

    filter_config = get_payment_filter_config(request)

    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        **filter_config,
    }
    return render(request, 'payment_list.html', context)


def payment_detail(request, payment_code):
    """付款详情页面。"""
    payment = get_object_or_404(Payment, payment_code=payment_code)
    contract = payment.contract

    all_payments = Payment.objects.filter(contract=contract).order_by('-payment_date')

    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    payment_progress = 0
    if contract.contract_amount and contract.contract_amount > 0:
        payment_progress = (total_paid / contract.contract_amount) * 100

    context = {
        'payment': payment,
        'contract': contract,
        'all_payments': all_payments,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
    }
    return render(request, 'payment_detail.html', context)


@require_http_methods(['GET', 'POST'])
def payment_create(request):
    """
    付款新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import PaymentForm

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '付款记录创建成功',
                    'payment_code': payment.payment_code
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

    form = PaymentForm()
    form.fields['payment_code'].required = False
    form.fields['payment_code'].widget.attrs['placeholder'] = '可留空自动生成'

    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增付款记录',
        'submit_url': '/payments/create/',
        'module_type': 'payment',
    })


@require_http_methods(['GET', 'POST'])
def payment_edit(request, payment_code):
    """
    付款编辑视图 - AJAX接口
    """
    from project.forms import PaymentForm

    try:
        payment = Payment.objects.get(payment_code=payment_code)
    except Payment.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '付款记录不存在'
            }, status=404)
        return HttpResponse('付款记录不存在', status=404)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '付款信息更新成功'
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

    form = PaymentForm(instance=payment)

    initial_display = {}
    if payment.contract:
        initial_display['contract'] = f"{payment.contract.contract_sequence or payment.contract.contract_code} - {payment.contract.contract_name}"
        if payment.contract.project:
            initial_display['project'] = f"{payment.contract.project.project_code} - {payment.contract.project.project_name}"

    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑付款信息',
        'submit_url': f'/payments/{payment_code}/edit/',
        'module_type': 'payment',
        'initial_display': initial_display,
    })
