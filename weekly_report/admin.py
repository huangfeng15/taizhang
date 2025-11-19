"""
周报管理模块 - Django Admin配置
"""
from django.contrib import admin
from .models import WeeklyReport, ProcurementProgress, WeeklyReportReminder


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    """周报管理"""
    list_display = ['report_code', 'year', 'week', 'recorder', 'status', 'submit_date', 'created_at']
    list_filter = ['status', 'year', 'week', 'recorder']
    search_fields = ['report_code', 'recorder__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('report_code', 'year', 'week', 'recorder')
        }),
        ('状态信息', {
            'fields': ('status', 'submit_date')
        }),
        ('其他信息', {
            'fields': ('remarks', 'created_at', 'updated_at')
        }),
    )


@admin.register(ProcurementProgress)
class ProcurementProgressAdmin(admin.ModelAdmin):
    """采购进度管理"""
    list_display = ['progress_code', 'project_name', 'current_stage', 'is_archived', 
                    'synced_to_ledger', 'has_missing_info', 'created_at']
    list_filter = ['current_stage', 'is_archived', 'synced_to_ledger', 'has_missing_info']
    search_fields = ['progress_code', 'project_name', 'project_code']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('progress_code', 'weekly_report', 'procurement')
        }),
        ('项目信息', {
            'fields': ('project_name', 'project_code')
        }),
        ('阶段信息', {
            'fields': ('current_stage', 'previous_stage', 'stage_data')
        }),
        ('归档状态', {
            'fields': ('is_archived', 'archived_date', 'synced_to_ledger', 'synced_date')
        }),
        ('补录信息', {
            'fields': ('has_missing_info', 'missing_fields')
        }),
        ('其他信息', {
            'fields': ('remarks', 'created_at', 'updated_at')
        }),
    )


@admin.register(WeeklyReportReminder)
class WeeklyReportReminderAdmin(admin.ModelAdmin):
    """周报提醒管理"""
    list_display = ['reminder_code', 'target_user', 'reminder_type', 'is_read', 
                    'is_handled', 'reminder_date']
    list_filter = ['reminder_type', 'is_read', 'is_handled', 'reminder_date']
    search_fields = ['reminder_code', 'target_user__username', 'content']
    readonly_fields = ['reminder_date']
    date_hierarchy = 'reminder_date'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('reminder_code', 'target_user', 'reminder_type', 'content')
        }),
        ('关联信息', {
            'fields': ('related_report', 'related_progress')
        }),
        ('状态信息', {
            'fields': ('is_read', 'read_date', 'is_handled', 'handled_date', 'reminder_date')
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_handled']
    
    def mark_as_read(self, request, queryset):
        """批量标记为已读"""
        from django.utils import timezone
        count = queryset.update(is_read=True, read_date=timezone.now())
        self.message_user(request, f'成功标记 {count} 条提醒为已读')
    mark_as_read.short_description = '标记为已读'
    
    def mark_as_handled(self, request, queryset):
        """批量标记为已处理"""
        from django.utils import timezone
        count = queryset.update(is_handled=True, handled_date=timezone.now())
        self.message_user(request, f'成功标记 {count} 条提醒为已处理')
    mark_as_handled.short_description = '标记为已处理'
