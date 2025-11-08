"""
登录验证中间件
确保所有页面都需要登录才能访问
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.deprecation import MiddlewareMixin


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    全局登录验证中间件
    确保所有页面（除登录、登出、静态资源外）都需要登录访问
    """
    
    # 不需要登录验证的URL路径
    EXEMPT_URLS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/admin/login/',
        '/admin/logout/',
        '/static/',
        '/media/',
    ]
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        在视图函数执行前进行登录验证
        """
        # 检查当前路径是否在豁免列表中
        path = request.path_info
        
        # 如果是豁免路径，直接放行
        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return None
        
        # 如果用户未登录，重定向到登录页
        if not request.user.is_authenticated:
            login_url = reverse('login')
            # 保存原始请求URL，登录后可以跳转回来
            return redirect(f'{login_url}?next={path}')
        
        # 用户已登录，继续处理请求
        return None