import os
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


def generate_strong_password(length: int = 16) -> str:
    """生成强密码，用于默认管理员账号初始密码。"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = (
        "确保默认管理员账号存在，并使用强密码。"
        "推荐通过环境变量或命令参数传入账号信息，未提供密码时将自动生成强密码。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("DEFAULT_ADMIN_USERNAME", "admin"),
            help="管理员用户名（默认：admin，可通过DEFAULT_ADMIN_USERNAME配置）",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("DEFAULT_ADMIN_PASSWORD"),
            help=(
                "管理员密码（推荐通过命令参数或DEFAULT_ADMIN_PASSWORD传入；"
                "未提供时系统将自动生成强随机密码）"
            ),
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@example.com"),
            help="管理员邮箱（默认：admin@example.com，可通过DEFAULT_ADMIN_EMAIL配置）",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        user_model = get_user_model()

        with transaction.atomic():
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )

            generated_password = None

            # 新建管理员账号时，如未显式提供密码则自动生成强密码
            if created:
                if not password:
                    generated_password = generate_strong_password()
                    password = generated_password

                user.set_password(password)
                user.email = email or user.email
                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=["password", "email", "is_staff", "is_superuser"])

                if generated_password:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"已创建默认管理员账号：{username}，"
                            f"系统为其生成的初始密码为：{generated_password}。"
                            "请管理员首次登录后立即修改密码。"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"已创建默认管理员账号：{username}。"
                            "请管理员首次登录后确认密码安全性。"
                        )
                    )

            # 已存在管理员账号时，仅在显式提供密码时才更新密码
            else:
                if password:
                    user.set_password(password)
                    user.email = email or user.email
                    user.is_staff = True
                    user.is_superuser = True
                    user.save(update_fields=["password", "email", "is_staff", "is_superuser"])
                    self.stdout.write(
                        self.style.WARNING(
                            f"管理员账号 {username} 已存在，密码已根据参数/环境变量更新。"
                        )
                    )
                else:
                    # 未提供密码，则不修改现有密码，仅确保权限标志正确
                    updated_fields = []
                    if not user.is_staff:
                        user.is_staff = True
                        updated_fields.append("is_staff")
                    if not user.is_superuser:
                        user.is_superuser = True
                        updated_fields.append("is_superuser")
                    if email and user.email != email:
                        user.email = email
                        updated_fields.append("email")

                    if updated_fields:
                        user.save(update_fields=updated_fields)
                        self.stdout.write(
                            self.style.WARNING(
                                f"管理员账号 {username} 已存在，已校正权限/邮箱信息。"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"管理员账号 {username} 已存在，未修改密码（未提供新密码）。"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS("默认管理员账号检查完成，请确保生产环境使用安全密码存储方案。")
        )
