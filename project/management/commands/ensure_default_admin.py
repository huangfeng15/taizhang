import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '确保默认管理员账号存在，默认使用 admin / admin123。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default=os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin'),
            help='管理员用户名（默认：admin）',
        )
        parser.add_argument(
            '--password',
            default=os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123'),
            help='管理员密码（默认：admin123）',
        )
        parser.add_argument(
            '--email',
            default=os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com'),
            help='管理员邮箱（默认：admin@example.com）',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        if not password:
            self.stderr.write(self.style.ERROR('密码不能为空，请传入 --password 选项。'))
            return

        user_model = get_user_model()

        with transaction.atomic():
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': True,
                    'is_superuser': True,
                },
            )

            # 如果用户是新建的，直接设置密码；否则更新密码保持一致
            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
                self.stdout.write(self.style.SUCCESS(
                    f'已创建默认管理员账号：{username}'
                ))
            else:
                user.set_password(password)
                user.email = email or user.email
                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=['password', 'email', 'is_staff', 'is_superuser'])
                self.stdout.write(self.style.WARNING(
                    f'管理员账号 {username} 已存在，密码已重置。'
                ))

        self.stdout.write(self.style.SUCCESS(
            '默认管理员账号配置完成，请尽快修改为生产环境安全密码。'
        ))
