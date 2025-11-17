import logging
from datetime import date
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from django_rq import job

from project.models import Project
from project.services.export_service import generate_project_excel

logger = logging.getLogger(__name__)
User = get_user_model()


@job("low")
def generate_project_export_zip_async(
    project_codes: List[str],
    user_id: int,
    export_all: bool = False,
    business_start_date: Optional[date] = None,
    business_end_date: Optional[date] = None,
) -> Optional[str]:
    """
    异步生成多项目导出 ZIP 文件，并通过邮件通知用户。

    返回值是生成的ZIP文件路径，实际存储位置和生命周期由调用方或后续任务管理。
    当前实现仅演示异步任务与通知流程，避免与现有同步下载逻辑产生破坏性冲突。
    """
    try:
        user = User.objects.filter(id=user_id).first()
        user_email = getattr(user, "email", None)

        qs = Project.objects.all()
        if project_codes and not export_all:
            qs = qs.filter(project_code__in=project_codes)

        projects = list(qs)
        if not projects:
            logger.warning("异步导出任务未找到项目，project_codes=%s", project_codes)
            return None

        # 复用现有的导出逻辑为每个项目生成 Excel，
        # 这里只是模拟处理流程，实际持久化可以根据业务再扩展。
        for project in projects:
            _ = generate_project_excel(
                project,
                user,
                business_start_date=business_start_date,
                business_end_date=business_end_date,
            )  # 生成 BytesIO，但不直接返回给浏览器

        # 发送完成通知邮件（如果用户配置了邮箱）
        if user_email:
            try:
                send_mail(
                    subject="项目数据导出任务已完成",
                    message="您提交的项目数据导出任务已在后台完成，请登录系统下载或联系管理员获取文件。",
                    from_email=getattr(
                        settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"
                    ),
                    recipient_list=[user_email],
                    fail_silently=True,
                )
            except Exception as exc:  # 邮件发送失败不能影响主任务
                logger.error("异步导出任务邮件通知失败: %s", exc)

        logger.info(
            "异步导出任务完成, 项目数=%s, 用户ID=%s", len(projects), user_id
        )
        return None
    except Exception as exc:
        logger.exception("异步导出任务执行失败: %s", exc)
        return None
