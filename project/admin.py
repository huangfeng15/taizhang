from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import Project, Role, UserProfile
from .models_completeness_config import CompletenessFieldConfig
from .models_procurement_method_config import ProcurementMethodFieldConfig


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

    # ✅ Django最佳实践：查询优化
    # select_related用于外键关联（减少查询次数）
    list_select_related = []  # Project模型暂无外键，保留为空

    # 性能优化：只查询显示所需字段
    # list_display_links = ['project_code']
    
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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["permissions"]
    list_per_page = 50
    readonly_fields = ["created_at"]

    fieldsets = (
        ("角色基础信息", {
            "fields": ("name", "description"),
            "description": "请输入角色名称，并用简短的文字说明该角色在系统中的职责和定位。",
        }),
        ("权限配置", {
            "fields": ("permissions",),
            "description": "为该角色分配可以访问的功能和可执行的操作，例如查看、维护采购、合同、付款等数据。",
        }),
        ("审计信息", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    class Media:
        js = ("js/admin-role-helptext.js",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "department",
        "phone",
        "get_roles_display",
    ]
    search_fields = ["user__username", "user__email", "department", "phone"]
    list_filter = ["department"]
    filter_horizontal = ["roles"]
    list_select_related = ["user"]

    fieldsets = (
        ("用户基本信息", {
            "fields": ("user", "department", "phone"),
            "description": "维护用户所在部门及联系方式，用于在业务记录中标识责任人。",
        }),
        ("角色与权限", {
            "fields": ("roles",),
            "description": "为用户分配一个或多个角色，用户将自动继承这些角色对应的权限。",
        }),
    )

    class Media:
        js = ("js/admin-role-helptext.js",)

    def get_roles_display(self, obj):
        names = obj.roles.values_list("name", flat=True)
        return "、".join(names) if names else "（无角色）"

    get_roles_display.short_description = "角色"


@admin.register(CompletenessFieldConfig)
class CompletenessFieldConfigAdmin(admin.ModelAdmin):
    """完整率字段配置管理"""
    list_display = ['model_type', 'field_name', 'field_label', 'is_enabled', 'sort_order']
    list_filter = ['model_type', 'is_enabled']
    search_fields = ['field_name', 'field_label']
    list_editable = ['is_enabled', 'sort_order']
    ordering = ['model_type', 'sort_order', 'field_name']
    list_per_page = 50


@admin.register(ProcurementMethodFieldConfig)
class ProcurementMethodFieldConfigAdmin(admin.ModelAdmin):
    """采购方式字段配置管理"""
    list_display = ['method_type', 'field_name', 'field_label', 'is_required', 'sort_order']
    list_filter = ['method_type', 'is_required']
    search_fields = ['field_name', 'field_label']
    list_editable = ['is_required', 'sort_order']
    ordering = ['method_type', 'sort_order', 'field_name']
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('method_type', 'field_name', 'field_label')
        }),
        ('配置选项', {
            'fields': ('is_required', 'sort_order')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
