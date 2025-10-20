from django.contrib import admin
from .models import Settlement


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['settlement_code', 'main_contract', 'final_amount', 'completion_date', 'created_at']
    search_fields = [
        'settlement_code',
        'main_contract__contract_code',
        'main_contract__contract_name'
    ]
    list_filter = ['completion_date', 'created_at']
    autocomplete_fields = ['main_contract']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('settlement_code', 'main_contract')
        }),
        ('结算详情', {
            'fields': ('final_amount', 'completion_date', 'remarks')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']