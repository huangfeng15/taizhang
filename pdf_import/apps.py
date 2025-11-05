"""
PDF导入应用配置
"""
from django.apps import AppConfig


class PdfImportConfig(AppConfig):
    """PDF智能导入应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdf_import'
    verbose_name = 'PDF智能导入'
    
    def ready(self):
        """应用就绪时的初始化"""
        pass