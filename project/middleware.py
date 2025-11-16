"""
登录验证中间件
确保所有页面都需要登录才能访问
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
import logging
from datetime import datetime

logger = logging.getLogger('audit')


class LoginRequiredMiddleware(MiddlewareMixin):
    """全局登录验证中间件 + 轻量审计日志。

    确保所有页面（除登录、登出、静态资源外）都需要登录访问，
    并在用户已登录时记录脱敏后的请求日志。
    """
    
    # 不需要登录验证/审计的URL路径前缀
    EXEMPT_URLS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/admin/login/',
        '/admin/logout/',
        '/api/import/template/',
        '/static/',
        '/media/',
    ]
    
    SENSITIVE_FIELDS = ['password', 'token', 'secret', 'credit_card']

    def _is_exempt(self, path: str) -> bool:
        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return True
        return False

    def _sanitize_data(self, data: dict) -> dict:
        """对请求数据中的敏感字段做简单脱敏。"""
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(field in key_lower for field in self.SENSITIVE_FIELDS):
                sanitized[key] = '*' * len(str(value))
            else:
                sanitized[key] = value
        return sanitized
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """在视图函数执行前进行登录验证与审计记录。"""
        path = request.path_info
        
        # 豁免路径：既不做登录校验，也不记录审计
        if self._is_exempt(path):
            return None
        
        # 未登录：重定向到登录页
        if not request.user.is_authenticated:
            login_url = reverse('login')
            return redirect(f'{login_url}?next={path}')
        
        # 已登录用户：记录脱敏后的请求日志
        try:
            if request.method in ['POST', 'PUT', 'PATCH']:
                payload = request.POST.dict() if request.POST else {}
            else:
                payload = {}
            safe_data = self._sanitize_data(payload)

            logger.info(
                "user=%s method=%s path=%s data=%s time=%s",
                getattr(request.user, 'username', 'anonymous'),
                request.method,
                path,
                safe_data,
                datetime.now().isoformat(timespec='seconds'),
            )
        except Exception:
            # 审计日志失败不能影响主流程
            pass
        
        return None
