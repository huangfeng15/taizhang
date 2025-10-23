"""
管理命令：设置用户的staff权限
使用方法：python manage.py set_staff_permission <username>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = '为指定用户设置staff权限（职员状态）'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='要设置权限的用户名')
        parser.add_argument(
            '--remove',
            action='store_true',
            help='移除staff权限而不是添加'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        remove = options.get('remove', False)
        
        try:
            user = User.objects.get(username=username)
            
            if remove:
                user.is_staff = False
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 已移除用户 "{username}" 的staff权限')
                )
            else:
                user.is_staff = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 已为用户 "{username}" 设置staff权限')
                )
            
            # 显示用户当前状态
            self.stdout.write('\n当前用户状态：')
            self.stdout.write(f'  用户名: {user.username}')
            self.stdout.write(f'  职员状态 (is_staff): {user.is_staff}')
            self.stdout.write(f'  超级用户 (is_superuser): {user.is_superuser}')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'✗ 错误：用户 "{username}" 不存在')
            )
            self.stdout.write('\n当前系统中的用户：')
            for u in User.objects.all():
                self.stdout.write(f'  - {u.username} (staff={u.is_staff}, superuser={u.is_superuser})')