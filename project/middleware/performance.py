"""
性能监控中间件

功能：
1. 记录每个请求的处理时间
2. 慢查询警告（超过1秒）
3. 在响应头中添加性能指标
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('performance')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """性能监控中间件"""

    # 慢请求阈值（秒）
    SLOW_REQUEST_THRESHOLD = 1.0

    def process_request(self, request):
        """记录请求开始时间"""
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        """计算响应时间并记录"""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time

            # 记录慢查询
            if duration > self.SLOW_REQUEST_THRESHOLD:
                logger.warning(
                    f'慢请求警告: {request.method} {request.path} '
                    f'耗时 {duration:.2f}秒 '
                    f'[User: {getattr(request.user, "username", "匿名")}]'
                )

            # 添加性能指标到响应头
            response['X-Response-Time'] = f'{duration:.3f}s'

            # 开发环境在控制台输出
            from django.conf import settings
            if settings.DEBUG and duration > 0.5:
                print(f'⚠️  {request.path}: {duration:.2f}s')

        return response

    def process_exception(self, request, exception):
        """记录异常请求的时间"""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            logger.error(
                f'请求异常: {request.method} {request.path} '
                f'耗时 {duration:.2f}秒 - {str(exception)}'
            )
        return None
