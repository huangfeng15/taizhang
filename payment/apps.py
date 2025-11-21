from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payment'
    verbose_name = '付款管理'
    
    def ready(self):
        """应用启动时注册信号"""
        import payment.signals  # noqa: F401