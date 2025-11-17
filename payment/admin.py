"""
付款管理 Admin 配置
使用 BusinessModelAdmin 基类统一管理
"""
from django.contrib import admin
from django.urls import reverse
from project.admin_base import BusinessModelAdmin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(BusinessModelAdmin):
    """付款信息管理"""
    
    # 返回前端列表页配置
    return_to_frontend_list = True
    frontend_list_url_name = 'payment_list'
    
    list_display = [
        'payment_code', 'contract_link', 'payment_amount', 'payment_date', 
        'is_settled', 'settlement_amount', 'settlement_completion_date', 'settlement_archive_date'
    ]
    
    search_fields = [
        'payment_code', 'contract__contract_code', 'contract__contract_name'
    ]
    
    list_filter = ['payment_date', 'is_settled', 'created_at']
    
    autocomplete_fields = ['contract']
    date_hierarchy = 'payment_date'
    
    def get_main_fieldsets(self, request, obj=None):
        """主要字段分组"""
        return (
            ('基本信息', {
                'fields': ('payment_code', 'contract')
            }),
            ('付款详情', {
                'fields': ('payment_amount', 'payment_date')
            }),
            ('结算信息', {
                'fields': ('is_settled', 'settlement_amount', 'settlement_completion_date', 'settlement_archive_date')
            }),
        )
    
    @admin.display(description='关联合同', ordering='contract__contract_code')
    def contract_link(self, obj):
        """合同链接"""
        return self.get_related_link(obj, 'contract')