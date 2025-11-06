"""
登录验证中间件
确保所有页面都需要登录才能访问
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class LoginRequiredMiddleware:
    """
    全局登录验证中间件
    所有页面都需要登录才能访问（除了登录页面本身）
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 不需要登录验证的URL路径
        self.exempt_urls = [
            '/accounts/login/',
            '/admin/login/',
        ]
        # 不需要登录验证的URL前缀
        self.exempt_prefixes = [
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # 检查是否是豁免URL
        path = request.path_info
        
        # 检查是否在豁免列表中
        if path in self.exempt_urls:
            return self.get_response(request)
        
        # 检查是否匹配豁免前缀
        for prefix in self.exempt_prefixes:
            if path.startswith(prefix):
                return self.get_response(request)
        
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            # 未登录，重定向到登录页面
            login_url = '/accounts/login/'
            # 保存原始请求路径，登录后可以返回
            return redirect(f'{login_url}?next={path}')
        
        # 已登录，继续处理请求
        response = self.get_response(request)
        return response