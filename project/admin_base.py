"""
Django Admin 基类
统一管理审计字段、分页、返回链接等通用配置
遵循 SOLID 原则，提供可扩展的基类架构
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse


class BaseAuditAdmin(admin.ModelAdmin):
    """
    审计模型基类 Admin
    包含创建/更新时间和用户等审计字段的通用配置
    """
    
    # 分页配置
    list_per_page = 50
    
    # 审计字段（只读）
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    # 日期过滤
    date_hierarchy = 'created_at'
    
    def get_readonly_fields(self, request, obj=None):
        """动态设置只读字段"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        # 编辑时，ID字段也设为只读
        if obj:
            readonly.append('id')
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """保存时自动设置创建/更新用户"""
        if not change:  # 新建
            if hasattr(obj, 'created_by') and not obj.created_by:
                obj.created_by = request.user.username
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user.username
        super().save_model(request, obj, form, change)
    
    def get_list_display(self, request):
        """获取列表显示字段（子类可覆盖）"""
        return self.list_display
    
    def get_fieldsets(self, request, obj=None):
        """
        获取字段分组
        子类应实现 get_main_fieldsets() 返回主要字段
        """
        main_fieldsets = self.get_main_fieldsets(request, obj)
        
        # 添加审计信息分组
        audit_fieldset = ('审计信息', {
            'classes': ('collapse',),
            'fields': self.readonly_fields
        })
        
        return main_fieldsets + (audit_fieldset,)
    
    def get_main_fieldsets(self, request, obj=None):
        """
        子类需要实现此方法，返回主要字段的分组
        例如：
        return (
            ('基本信息', {'fields': ('name', 'code')}),
            ('详细信息', {'fields': ('description',)}),
        )
        """
        raise NotImplementedError("子类必须实现 get_main_fieldsets 方法")


class BusinessModelAdmin(BaseAuditAdmin):
    """
    业务模型基类 Admin
    在审计基类上增加关联跳转、高级搜索等功能
    """
    
    # 搜索字段（子类覆盖）
    search_fields = []
    
    # 列表过滤（子类覆盖）
    list_filter = []
    
    # 可排序字段
    sortable_by = []
    
    def get_related_link(self, obj, field_name, display_text=None):
        """
        生成关联对象的链接
        
        Args:
            obj: 当前对象
            field_name: 关联字段名
            display_text: 显示文本（默认使用对象的 __str__）
        
        Returns:
            HTML 链接或 '-'
        """
        related_obj = getattr(obj, field_name, None)
        if not related_obj:
            return '-'
        
        # 获取关联对象的 Admin URL
        app_label = related_obj._meta.app_label
        model_name = related_obj._meta.model_name
        
        try:
            url = reverse(f'admin:{app_label}_{model_name}_change', args=[related_obj.pk])
        except:
            # 如果获取 URL 失败，返回纯文本
            return str(related_obj)
        
        # 显示文本
        text = display_text or str(related_obj)
        
        return format_html('<a href="{}">{}</a>', url, text)
    
    def get_back_link(self, request):
        """生成返回列表的链接"""
        referer = request.META.get('HTTP_REFERER', '')
        if 'changelist' in referer:
            return format_html('<a href="{}">← 返回列表</a>', referer)
        return ''
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """添加返回链接到上下文"""
        extra_context = extra_context or {}
        extra_context['back_link'] = self.get_back_link(request)
        return super().change_view(request, object_id, form_url, extra_context)
    
    def response_add(self, request, obj, post_url_continue=None):
        """
        新增后返回前端列表页
        子类可以通过设置 return_to_frontend_list 属性和 frontend_list_url_name 来自定义返回行为
        """
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            if hasattr(self, 'return_to_frontend_list') and self.return_to_frontend_list:
                if hasattr(self, 'frontend_list_url_name'):
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect(reverse(self.frontend_list_url_name))
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """
        修改后返回前端列表页
        子类可以通过设置 return_to_frontend_list 属性和 frontend_list_url_name 来自定义返回行为
        """
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            if hasattr(self, 'return_to_frontend_list') and self.return_to_frontend_list:
                if hasattr(self, 'frontend_list_url_name'):
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect(reverse(self.frontend_list_url_name))
        return super().response_change(request, obj)
    
    def response_delete(self, request, obj_display, obj_id):
        """
        删除后返回前端列表页
        子类可以通过设置 return_to_frontend_list 属性和 frontend_list_url_name 来自定义返回行为
        """
        if hasattr(self, 'return_to_frontend_list') and self.return_to_frontend_list:
            if hasattr(self, 'frontend_list_url_name'):
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(reverse(self.frontend_list_url_name))
        return super().response_delete(request, obj_display, obj_id)