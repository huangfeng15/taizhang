"""
PDF导入管理后台配置
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import PDFImportSession


@admin.register(PDFImportSession)
class PDFImportSessionAdmin(admin.ModelAdmin):
    """PDF导入会话管理"""
    
    list_display = [
        'session_id',
        'created_by',
        'status_badge',
        'pdf_count',
        'extracted_fields',
        'created_at',
        'expires_at',
        'is_expired_badge'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'expires_at',
    ]
    
    search_fields = [
        'session_id',
        'created_by__username',
        'procurement__procurement_code',
    ]
    
    readonly_fields = [
        'session_id',
        'created_at',
        'updated_at',
        'pdf_files_display',
        'extracted_data_display',
        'validation_result_display',
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('session_id', 'created_by', 'status', 'procurement')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'expires_at')
        }),
        ('PDF文件', {
            'fields': ('pdf_files_display',),
            'classes': ('collapse',)
        }),
        ('提取数据', {
            'fields': ('extracted_data_display',),
            'classes': ('collapse',)
        }),
        ('验证结果', {
            'fields': ('validation_result_display', 'requires_confirmation'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """状态徽章"""
        colors = {
            'extracting': '#17a2b8',      # 蓝色
            'pending_review': '#ffc107',  # 黄色
            'confirmed': '#28a745',       # 绿色
            'saved': '#6c757d',           # 灰色
            'expired': '#dc3545',         # 红色
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    
    def pdf_count(self, obj):
        """PDF文件数量"""
        count = obj.get_pdf_count()
        return f'{count} 个' if count > 0 else '-'
    pdf_count.short_description = 'PDF数量'
    
    def extracted_fields(self, obj):
        """已提取字段数"""
        count = obj.get_extracted_field_count()
        return f'{count} 个' if count > 0 else '-'
    extracted_fields.short_description = '已提取字段'
    
    def is_expired_badge(self, obj):
        """是否过期"""
        if obj.is_expired():
            return format_html(
                '<span style="color: red; font-weight: bold;">已过期</span>'
            )
        return format_html('<span style="color: green;">有效</span>')
    is_expired_badge.short_description = '有效性'
    
    def pdf_files_display(self, obj):
        """PDF文件详情显示"""
        if not obj.pdf_files:
            return '-'
        
        html = '<ul style="margin: 0; padding-left: 20px;">'
        for file_info in obj.pdf_files:
            name = file_info.get('name', '未知')
            size_kb = file_info.get('size', 0) / 1024
            detected_type = file_info.get('detected_type', '未识别')
            confidence = file_info.get('confidence', 0) * 100
            html += f'<li><strong>{name}</strong> ({size_kb:.1f} KB) - {detected_type} (置信度: {confidence:.0f}%)</li>'
        html += '</ul>'
        return format_html(html)
    pdf_files_display.short_description = 'PDF文件列表'
    
    def extracted_data_display(self, obj):
        """提取数据显示"""
        if not obj.extracted_data:
            return '-'
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background: #f0f0f0;"><th style="padding: 5px; border: 1px solid #ddd;">字段</th><th style="padding: 5px; border: 1px solid #ddd;">值</th></tr>'
        for key, value in obj.extracted_data.items():
            if value:
                html += f'<tr><td style="padding: 5px; border: 1px solid #ddd;"><code>{key}</code></td><td style="padding: 5px; border: 1px solid #ddd;">{value}</td></tr>'
        html += '</table>'
        return format_html(html)
    extracted_data_display.short_description = '提取的数据'
    
    def validation_result_display(self, obj):
        """验证结果显示"""
        if not obj.validation_result:
            return '-'
        
        is_valid = obj.validation_result.get('is_valid', False)
        errors = obj.validation_result.get('errors', [])
        
        html = f'<p><strong>整体状态:</strong> '
        if is_valid:
            html += '<span style="color: green;">✓ 通过验证</span>'
        else:
            html += '<span style="color: red;">✗ 验证失败</span>'
        html += '</p>'
        
        if errors:
            html += '<p><strong>错误信息:</strong></p><ul>'
            for error in errors:
                html += f'<li style="color: red;">{error}</li>'
            html += '</ul>'
        
        return format_html(html)
    validation_result_display.short_description = '验证结果'
    
    def has_add_permission(self, request):
        """禁止手动添加（应通过导入流程创建）"""
        return False
    
    actions = ['delete_expired_sessions']
    
    def delete_expired_sessions(self, request, queryset):
        """批量删除过期会话"""
        from django.utils import timezone
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f'已删除 {count} 个过期会话')
    delete_expired_sessions.short_description = '删除过期会话'