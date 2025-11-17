"""
查询计数中间件（仅开发环境）

功能：
1. 统计每个请求的数据库查询次数
2. 查询超标警告（>10次）
3. 显示具体的SQL查询（DEBUG模式）
"""
from django.db import connection
from django.conf import settings


class QueryCountDebugMiddleware:
    """查询计数中间件（仅开发环境）"""

    # 查询次数警告阈值
    QUERY_WARNING_THRESHOLD = 10

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 仅在DEBUG模式启用
        if not settings.DEBUG:
            return self.get_response(request)

        # 记录查询数量
        queries_before = len(connection.queries)

        # 处理请求
        response = self.get_response(request)

        # 计算新增查询
        queries_after = len(connection.queries)
        num_queries = queries_after - queries_before

        # 查询超标警告
        if num_queries > self.QUERY_WARNING_THRESHOLD:
            print(f'\n[警告] 查询次数警告: {request.path}')
            print(f'   数据库查询次数: {num_queries} 次')
            print(f'   建议: 使用select_related()或prefetch_related()优化\n')

            # 显示具体查询（仅前5条）
            recent_queries = connection.queries[queries_before:queries_before + 5]
            for i, query in enumerate(recent_queries, 1):
                sql = query['sql']
                time = query['time']
                print(f'   查询 {i}: {sql[:100]}... ({time}s)')

        # 添加查询次数到响应头（开发环境）
        response['X-DB-Query-Count'] = str(num_queries)

        return response
