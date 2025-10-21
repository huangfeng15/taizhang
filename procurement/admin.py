from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Procurement


@admin.register(Procurement)
class ProcurementAdmin(admin.ModelAdmin):
    list_display = [
        'procurement_code', 'project_name', 'procurement_method',
        'procurement_platform', 'winning_bidder', 'winning_amount',
        'bid_opening_date', 'procurement_officer'
    ]
    search_fields = [
        'procurement_code', 'project_name', 'winning_bidder',
        'procurement_officer', 'demand_department'
    ]
    list_filter = [
        'procurement_method', 'procurement_platform',
        'created_at', 'notice_issue_date', 'bid_opening_date'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    # 支持在 Contract 中快速搜索采购
    autocomplete_fields = ['project']
    
    def get_search_results(self, request, queryset, search_term):
        """优化搜索性能"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

    fieldsets = (
        ('基本信息', {
            'fields': ('procurement_code', 'project', 'project_name', 'procurement_unit')
        }),
        ('时间信息', {
            'fields': (
                'planned_completion_date', 'requirement_approval_date',
                'bid_opening_date', 'platform_publicity_date',
                'notice_issue_date', 'archive_date'
            )
        }),
        ('人员信息', {
            'fields': (
                'procurement_officer', 'demand_department', 'demand_contact'
            )
        }),
        ('金额信息', {
            'fields': ('budget_amount', 'control_price', 'winning_amount', 'procurement_cost')
        }),
        ('采购方式', {
            'fields': (
                'procurement_platform', 'procurement_method',
                'bid_evaluation_method', 'bid_awarding_method'
            )
        }),
        ('委员会成员', {
            'fields': ('evaluation_committee', 'awarding_committee')
        }),
        ('中标信息', {
            'fields': ('winning_bidder', 'winning_contact')
        }),
        ('担保信息', {
            'fields': (
                'bid_guarantee', 'bid_guarantee_return_date',
                'performance_guarantee'
            )
        }),
        ('其他信息', {
            'fields': ('has_complaint', 'non_bidding_explanation'),
            'classes': ('collapse',)
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def response_add(self, request, obj, post_url_continue=None):
        """新增后返回前端列表页"""
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return HttpResponseRedirect(reverse('procurement_list'))
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """修改后返回前端列表页"""
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return HttpResponseRedirect(reverse('procurement_list'))
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """删除后返回前端列表页"""
        return HttpResponseRedirect(reverse('procurement_list'))