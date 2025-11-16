"""初始化基础角色与用户档案(UserProfile)。

- 创建若干基础角色（如系统管理员/采购管理员/只读用户）；
- 为所有现有用户补齐 UserProfile；
- 为超级用户自动关联“系统管理员”角色（仅在首次创建该角色时处理）。

该命令设计为幂等，可重复执行。
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.models import Permission

from project.models import Role, UserProfile


class Command(BaseCommand):
    help = "初始化基础角色和用户档案（UserProfile）。"

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING("开始初始化基础角色与用户档案..."))

        with transaction.atomic():
            # 1. 创建基础角色
            base_roles = [
                {
                    "name": "系统管理员",
                    "description": "拥有系统全部权限的管理员角色。",
                    "grant_all_perms": True,
                },
                {
                    "name": "采购管理员",
                    "description": "负责采购与合同等业务管理的角色（权限可在后台细化配置）。",
                    "grant_all_perms": False,
                },
                {
                    "name": "只读用户",
                    "description": "仅允许查看数据的用户角色（默认不授予写权限）。",
                    "grant_all_perms": False,
                },
            ]

            role_created_count = 0
            system_admin_role = None

            for cfg in base_roles:
                role, created = Role.objects.get_or_create(
                    name=cfg["name"],
                    defaults={"description": cfg["description"]},
                )
                if created:
                    role_created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"已创建角色: {role.name}")
                    )

                    if cfg["grant_all_perms"]:
                        # 仅在首次创建“系统管理员”时授予所有权限
                        all_perms = Permission.objects.all()
                        role.permissions.set(all_perms)
                        self.stdout.write(
                            self.style.NOTICE(
                                f"角色 {role.name} 已授予所有当前权限 ({all_perms.count()} 条)。"
                            )
                        )
                else:
                    # 已存在则不修改权限配置，避免覆盖人工调整
                    self.stdout.write(
                        self.style.WARNING(f"角色已存在，跳过创建: {role.name}")
                    )

                if role.name == "系统管理员":
                    system_admin_role = role

            # 2. 为所有现有用户创建 UserProfile
            users = User.objects.all()
            profile_created_count = 0
            bound_admin_count = 0

            for user in users:
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created:
                    profile_created_count += 1

                # 为超级用户绑定“系统管理员”角色（若存在该角色）
                if system_admin_role and user.is_superuser:
                    if not profile.roles.filter(pk=system_admin_role.pk).exists():
                        profile.roles.add(system_admin_role)
                        bound_admin_count += 1

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(
                f"角色创建完成，新建角色数: {role_created_count}"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"用户档案初始化完成，新建 UserProfile 数: {profile_created_count}"
            ))
            if system_admin_role:
                self.stdout.write(self.style.SUCCESS(
                    f"已为 {bound_admin_count} 个超级用户绑定角色: {system_admin_role.name}"
                ))

        self.stdout.write(self.style.SUCCESS("初始化基础角色与用户档案完成。"))
