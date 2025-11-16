"""项目级权限/角色装饰器。

提供基于 Django 权限系统与自定义 Role 模型的轻量封装，避免在视图中散落权限判断逻辑。
"""
from functools import wraps
from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from project.models import UserProfile


ViewFunc = Callable[..., HttpResponse]


def require_permission(permission_codename: str) -> Callable[[ViewFunc], ViewFunc]:
    """基于 Django 内置权限的访问控制装饰器。

    参数示例: 'contract.view_contract'。
    """

    def decorator(view_func: ViewFunc) -> ViewFunc:
        @wraps(view_func)
        def wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                raise PermissionDenied("请先登录后再执行此操作。")
            if not request.user.has_perm(permission_codename):
                raise PermissionDenied("您没有执行此操作的权限。")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def require_role(role_name: str) -> Callable[[ViewFunc], ViewFunc]:
    """基于自定义 Role 模型的访问控制装饰器。

    典型用法: @require_role('采购管理员')。
    """

    def decorator(view_func: ViewFunc) -> ViewFunc:
        @wraps(view_func)
        def wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                raise PermissionDenied("请先登录后再执行此操作。")

            try:
                profile: UserProfile = request.user.profile  # 通过 related_name 访问
            except UserProfile.DoesNotExist:  # pragma: no cover - 运行时保护
                raise PermissionDenied("当前用户未配置角色，请联系管理员。")

            if not profile.roles.filter(name=role_name).exists():
                raise PermissionDenied(f"需要角色‘{role_name}’才能访问此功能。")

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
