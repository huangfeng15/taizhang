"""
合同管理 Admin 配置
使用 BusinessModelAdmin 基类统一管理
"""
from django.contrib import admin
from django.urls import reverse
from django.db.models import Q, Count, Sum
from project.admin_base import BusinessModelAdmin
from .models import Contract


class HasProcurementFilter(admin.SimpleListFilter):
    """自定义过滤器：按是否关联采购筛选合同"""
    title = '是否关联采购'
    parameter_name = 'has_procurement'

    def lookups(self, request, model_admin):
        return [
            ('yes', '已关联采购'),
            ('no', '未关联采购'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(procurement__isnull=True)
        if self.value() == 'no':
            return queryset.filter(procurement__isnull=True)
        return queryset


@admin.register(Contract)
class ContractAdmin(BusinessModelAdmin):
    """合同信息管理"""
    
    # 返回前端列表页配置
    return_to_frontend_list = True
    frontend_list_url_name = 'contract_list'
    
    list_display = [
        'contract_sequence', 'contract_code', 'contract_name', 'file_positioning',
        'contract_source', 'party_a', 'party_b',
        'contract_amount', 'signing_date', 'get_procurement_display'
    ]
    
    search_fields = [
        'contract_code', 'contract_name', 'party_a', 'party_b',
        'party_a_legal_representative', 'party_a_contact_person', 'party_a_manager',
        'party_b_legal_representative', 'party_b_contact_person', 'party_b_manager',
        'procurement__procurement_code', 'procurement__project_name'
    ]
    
    list_filter = [
        'file_positioning',
        'contract_source',
        HasProcurementFilter,
        'signing_date',
        'created_at'
    ]
    
    autocomplete_fields = ['procurement', 'parent_contract', 'project']
    date_hierarchy = 'signing_date'
    
    @admin.display(description='关联采购', ordering='procurement')
    def get_procurement_display(self, obj):
        """显示关联采购信息"""
        if obj.procurement:
            return f"{obj.procurement.procurement_code}"
        return "-"
    
    def get_queryset(self, request):
        """优化查询性能"""
        qs = super().get_queryset(request)
        return qs.select_related('procurement', 'parent_contract', 'project')
    
    def get_main_fieldsets(self, request, obj=None):
        """主要字段分组"""
        return (
            ('基本信息', {
                'fields': ('contract_sequence', 'contract_code', 'contract_name', 'file_positioning', 'contract_source', 'contract_officer')
            }),
            ('关联信息', {
                'fields': ('parent_contract', 'procurement', 'project'),
                'description': '采购合同必须关联采购项目；直接签订合同无需关联采购'
            }),
            ('合同双方', {
                'fields': ('party_a', 'party_b')
            }),
            ('甲方联系信息', {
                'fields': ('party_a_legal_representative', 'party_a_contact_person', 'party_a_manager'),
                'classes': ('collapse',)
            }),
            ('乙方联系信息', {
                'fields': ('party_b_legal_representative', 'party_b_contact_person', 'party_b_manager'),
                'classes': ('collapse',)
            }),
            ('金额与时间', {
                'fields': ('contract_amount', 'signing_date', 'duration')
            }),
            ('其他信息', {
                'fields': ('payment_method', 'performance_guarantee_return_date', 'archive_date'),
                'classes': ('collapse',)
            }),
        )