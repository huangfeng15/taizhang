"""
采购管理 Admin 配置
使用 BusinessModelAdmin 基类统一管理
"""
from django.contrib import admin
from django.urls import reverse
from project.admin_base import BusinessModelAdmin
from .models import Procurement


@admin.register(Procurement)
class ProcurementAdmin(BusinessModelAdmin):
    """采购信息管理"""
    
    # 返回前端列表页配置
    return_to_frontend_list = True
    frontend_list_url_name = 'procurement_list'
    
    list_display = [
        'procurement_code', 'project_link', 'project_name', 'procurement_method',
        'procurement_category', 'procurement_platform', 'winning_bidder',
        'winning_amount', 'result_publicity_release_date', 'procurement_officer'
    ]
    
    search_fields = [
        'procurement_code', 'project_name', 'winning_bidder',
        'procurement_officer', 'demand_department',
        'procurement_category', 'qualification_review_method'
    ]
    
    list_filter = [
        'procurement_method', 'procurement_platform', 'procurement_category',
        'qualification_review_method', 'result_publicity_release_date',
        'bid_opening_date', 'created_at'
    ]
    
    # 支持在 Contract 中快速搜索采购
    autocomplete_fields = ['project']
    
    def get_search_results(self, request, queryset, search_term):
        """优化搜索性能"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct
    
    def get_main_fieldsets(self, request, obj=None):
        """主要字段分组"""
        return (
            ('基本信息', {
                'fields': (
                    'procurement_code', 'project', 'project_name',
                    'procurement_unit', 'procurement_category'
                )
            }),
            ('时间信息', {
                'fields': (
                    'announcement_release_date', 'registration_deadline',
                    'planned_completion_date', 'requirement_approval_date',
                    'bid_opening_date', 'candidate_publicity_end_date',
                    'result_publicity_release_date', 'notice_issue_date',
                    'archive_date'
                )
            }),
            ('人员信息', {
                'fields': (
                    'procurement_officer', 'demand_department', 'demand_contact'
                )
            }),
            ('金额信息', {
                'fields': ('budget_amount', 'control_price', 'winning_amount')
            }),
            ('采购方式', {
                'fields': (
                    'procurement_platform', 'procurement_method',
                    'qualification_review_method', 'bid_evaluation_method',
                    'bid_awarding_method'
                )
            }),
            ('委员会成员', {
                'fields': ('evaluation_committee',)
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
                'fields': ('candidate_publicity_issue', 'non_bidding_explanation'),
                'classes': ('collapse',)
            }),
        )
    
    @admin.display(description='关联项目', ordering='project__project_name')
    def project_link(self, obj):
        """项目链接"""
        return self.get_related_link(obj, 'project')
