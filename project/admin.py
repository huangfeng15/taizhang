from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'project_code', 'project_name', 'project_manager',
        'status', 'created_at'
    ]
    search_fields = [
        'project_code', 'project_name', 'project_manager', 'description'
    ]
    list_filter = ['status', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    # 添加自定义CSS（全局注入到admin模板）
    class Media:
        css = {
            'all': ('css/admin-fix.css',),
        }
    
    fieldsets = (
        ('基本信息', {
            'fields': ('project_code', 'project_name', 'description')
        }),
        ('项目详情', {
            'fields': ('project_manager', 'status')
        }),
        ('其他信息', {
            'fields': ('remarks',),
            'classes': ('collapse',)
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
            return HttpResponseRedirect(reverse('project_list'))
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """修改后返回前端项目详情页"""
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return HttpResponseRedirect(reverse('project_detail', args=[obj.project_code]))
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """删除后返回前端列表页"""
        return HttpResponseRedirect(reverse('project_list'))
