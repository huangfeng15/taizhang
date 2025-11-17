"""
创建编辑员账户和角色的管理命令
该账户拥有增改查权限，但不能删除数据
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from project.models import Role, UserProfile


class Command(BaseCommand):
    help = '创建编辑员账户，拥有增改查权限但不能删除'

    def handle(self, *args, **options):
        username = 'editor'
        password = 'Editor@2024'
        email = 'editor@example.com'

        with transaction.atomic():
            # 1. 创建或获取编辑员角色
            role, role_created = Role.objects.get_or_create(
                name='编辑员',
                defaults={
                    'description': '拥有增改查权限，但不能删除数据的角色'
                }
            )

            if role_created:
                self.stdout.write(self.style.SUCCESS(f'[成功] 创建角色: {role.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'[提示] 角色已存在: {role.name}'))

            # 2. 获取所有模型的增改查权限（排除删除权限）
            permission_codenames = []
            
            # 获取项目相关的所有 ContentType
            app_labels = ['project', 'procurement', 'contract', 'payment', 'settlement', 'supplier_eval']
            
            for app_label in app_labels:
                content_types = ContentType.objects.filter(app_label=app_label)
                
                for ct in content_types:
                    # 添加 add, change, view 权限，排除 delete
                    for action in ['add', 'change', 'view']:
                        codename = f'{action}_{ct.model}'
                        permission_codenames.append(codename)

            # 批量获取权限
            permissions = Permission.objects.filter(codename__in=permission_codenames)
            
            # 为角色分配权限
            role.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f'[成功] 为角色分配了 {permissions.count()} 个权限'))

            # 3. 创建或更新用户
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': True,  # 允许登录后台
                    'is_superuser': False,  # 不是超级管理员
                }
            )

            if user_created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'[成功] 创建用户: {username}'))
                self.stdout.write(self.style.SUCCESS(f'  密码: {password}'))
            else:
                # 用户已存在，更新密码
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = False
                user.save()
                self.stdout.write(self.style.WARNING(f'[提示] 用户已存在，已更新密码: {username}'))
                self.stdout.write(self.style.SUCCESS(f'  新密码: {password}'))

            # 4. 创建或更新用户档案
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'department': '编辑部',
                }
            )

            # 为用户分配编辑员角色
            profile.roles.add(role)
            
            if profile_created:
                self.stdout.write(self.style.SUCCESS(f'[成功] 创建用户档案'))
            else:
                self.stdout.write(self.style.WARNING(f'[提示] 用户档案已存在，已更新角色'))

            # 5. 为用户直接分配权限（作为备用）
            user.user_permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f'[成功] 为用户直接分配了权限'))

        # 输出汇总信息
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('账户创建成功！'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'用户名: {username}')
        self.stdout.write(f'密码: {password}')
        self.stdout.write(f'角色: 编辑员')
        self.stdout.write(f'权限: 可以新增、修改、查看数据，但不能删除')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('[警告] 请妥善保管账户信息，建议首次登录后修改密码'))