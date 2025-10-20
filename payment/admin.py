from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_code', 'contract', 'payment_amount', 'payment_date'
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
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']