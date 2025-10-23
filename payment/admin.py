from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_code', 'contract', 'payment_amount', 'payment_date', 'is_settled', 'settlement_archive_date'
    ]
    search_fields = [
        'payment_code', 'contract__contract_code', 'contract__contract_name'
    ]
    list_filter = ['payment_date', 'created_at']
    autocomplete_fields = ['contract']
    date_hierarchy = 'payment_date'
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('payment_code', 'contract')
        }),
        ('付款详情', {
            'fields': ('payment_amount', 'payment_date')
        }),
        ('结算信息', {
            'fields': ('is_settled', 'settlement_amount', 'settlement_archive_date')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def response_add(self, request, obj, post_url_continue=None):
        """新增后返回前端列表页"""
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return HttpResponseRedirect(reverse('payment_list'))
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """修改后返回前端列表页"""
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return HttpResponseRedirect(reverse('payment_list'))
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """删除后返回前端列表页"""
        return HttpResponseRedirect(reverse('payment_list'))