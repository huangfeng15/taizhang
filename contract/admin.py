from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Sum
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
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'contract_code', 'contract_name', 'contract_type', 'contract_source',
        'party_b', 'contract_amount', 'signing_date', 'get_procurement_display'
    ]
    search_fields = [
        'contract_code', 'contract_name', 'party_a', 'party_b',
        'procurement__procurement_code', 'procurement__project_name'
    ]
    list_filter = [
        'contract_type',
        'contract_source',
        HasProcurementFilter,
        'signing_date',
        'created_at'
    ]
    autocomplete_fields = ['procurement', 'parent_contract']
    date_hierarchy = 'signing_date'
    list_per_page = 50
    
    @admin.display(description='关联采购', ordering='procurement')
    def get_procurement_display(self, obj):
        """显示关联采购信息"""
        if obj.procurement:
            return f"{obj.procurement.procurement_code}"
        return "-"
    
    def get_queryset(self, request):
        """优化查询性能"""
        qs = super().get_queryset(request)
        return qs.select_related('procurement', 'parent_contract')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('contract_code', 'contract_name', 'contract_type', 'contract_source')
        }),
        ('关联信息', {
            'fields': ('parent_contract', 'procurement'),
            'description': '采购合同必须关联采购项目；直接签订合同无需关联采购'
        }),
        ('合同方信息', {
            'fields': ('party_a', 'party_b')
        }),
        ('金额与时间', {
            'fields': ('contract_amount', 'signing_date', 'duration')
        }),
        ('其他信息', {
            'fields': ('contract_officer', 'payment_method'),
            'classes': ('collapse',)
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']