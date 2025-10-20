from django.contrib import admin
from .models import SupplierEvaluation


@admin.register(SupplierEvaluation)
class SupplierEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'evaluation_code', 'supplier_name', 'score',
        'evaluation_type', 'evaluator', 'created_at'
    ]
    search_fields = [
        'evaluation_code',
        'supplier_name',
        'contract__contract_code',
        'contract__contract_name',
        'evaluator'
    ]
    list_filter = ['evaluation_type', 'created_at']
    autocomplete_fields = ['contract']
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('evaluation_code', 'contract', 'supplier_name')
        }),
        ('评价详情', {
            'fields': (
                'evaluation_period', 'evaluator', 'score', 'evaluation_type'
            )
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']