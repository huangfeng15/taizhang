"""工作量统计视图 - 独立文件"""
from django.shortcuts import render
from project.services.monitors.workload_statistics import WorkloadStatistics


def workload_statistics_view(request):
    """工作量统计视图"""
    # 解析参数
    time_dimension = request.GET.get('time_dimension', 'recent_month')
    dimension_type = request.GET.get('dimension_type', 'person')

    # 获取工作量统计
    stats = WorkloadStatistics(time_dimension=time_dimension, dimension_type=dimension_type)
    ranking = stats.get_workload_ranking()

    # 时间维度标签
    time_labels = {
        'recent_month': '最近一个月',
        'last_month': '上一个月',
        'current_year': '今年累计'
    }

    context = {
        'ranking': ranking,
        'time_dimension': time_dimension,
        'dimension_type': dimension_type,
        'time_label': time_labels.get(time_dimension, '最近一个月'),
        'page_title': '工作量统计',
    }
    return render(request, 'monitoring/workload_statistics.html', context)
