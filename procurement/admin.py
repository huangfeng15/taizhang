from django.contrib import admin
from .models import Procurement


@admin.register(Procurement)
class ProcurementAdmin(admin.ModelAdmin):
    list_display = [
        'procurement_code', 'project_name', 'winning_unit',
        'winning_amount', 'procurement_officer', 'created_at'
    ]
    search_fields = [
        'procurement_code', 'project_name', 'winning_unit',
        'procurement_officer', 'demand_department'
    ]
    list_filter = [
        'procurement_category', 'procurement_method',
        'created_at', 'notice_issue_date'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    # 支持在 Contract 中快速搜索采购
    autocomplete_fields = []
    
    def get_search_results(self, request, queryset, search_term):
        """优化搜索性能"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

    fieldsets = (
        ('基本信息', {
            'fields': ('procurement_code', 'project_name', 'procurement_unit')
        }),
        ('中标信息', {
            'fields': ('winning_unit', 'winning_contact', 'winning_amount')
        }),
        ('采购详情', {
            'fields': (
                'procurement_method', 'procurement_category',
                'budget_amount', 'control_price'
            )
        }),
        ('时间信息', {
            'fields': ('planned_end_date', 'notice_issue_date')
        }),
        ('人员信息', {
            'fields': ('procurement_officer', 'demand_department')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']