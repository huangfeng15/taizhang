"""操作日志视图"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST
from project.models_operation_log import OperationLog


@login_required
@require_http_methods(['GET'])
def operation_logs_list(request):
    """操作日志列表页面"""
    logs = OperationLog.objects.select_related('user').all()
    
    # 分页
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'operation_logs.html', context)


@login_required
@require_POST
def delete_operation_log(request):
    """删除操作日志(仅超级用户)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': '权限不足'}, status=403)
    
    import json
    data = json.loads(request.body)
    log_id = data.get('log_id')
    
    if not log_id:
        return JsonResponse({'success': False, 'message': '缺少日志ID'}, status=400)
    
    try:
        log = OperationLog.objects.get(id=log_id)
        log.delete()
        return JsonResponse({'success': True, 'message': '删除成功'})
    except OperationLog.DoesNotExist:
        return JsonResponse({'success': False, 'message': '日志不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'}, status=500)