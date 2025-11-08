"""
供应商履约评价模块 - Admin后台配置
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from .models import SupplierEvaluation, SupplierInterview


@admin.register(SupplierEvaluation)
class SupplierEvaluationAdmin(admin.ModelAdmin):
    """供应商履约评价Admin配置"""
    
    # 列表页显示字段
    list_display = [
        'evaluation_code',
        'supplier_name_link',
        'contract_link',
        'comprehensive_score_badge',
        'last_evaluation_score',
        'score_level',
        'created_at',
    ]
    
    # 搜索字段
    search_fields = [
        'evaluation_code',
        'supplier_name',
        'contract__contract_code',
        'contract__contract_name',
        'contract__party_b',
        'remarks',
    ]
    
    # 筛选器
    list_filter = [
        'created_at',
        'updated_at',
        ('comprehensive_score', admin.EmptyFieldListFilter),
        ('last_evaluation_score', admin.EmptyFieldListFilter),
    ]
    
    # 关联字段自动补全
    autocomplete_fields = ['contract']
    
    # 时间层级导航
    date_hierarchy = 'created_at'
    
    # 每页显示数量
    list_per_page = 50
    
    # 列表页可编辑字段
    list_editable = []
    
    # 只读字段
    readonly_fields = [
        'evaluation_code',
        'supplier_name',
        'comprehensive_score',
        'created_at',
        'updated_at',
        'calculated_score_info',
    ]
    
    # 字段集分组
    fieldsets = (
        ('基本信息', {
            'fields': (
                'evaluation_code',
                'contract',
                'supplier_name',
            )
        }),
        ('综合评分', {
            'fields': (
                'comprehensive_score',
                'last_evaluation_score',
                'calculated_score_info',
            ),
            'description': '综合评分 = 末次评价×60% + 过程评价平均×40%',
        }),
        ('过程评价得分（动态年度）', {
            'fields': (
                'annual_scores',
                'irregular_scores',
            ),
            'description': 'JSON格式存储，支持任意年份和次数的动态扩展',
            'classes': ('collapse',),
        }),
        ('其他信息', {
            'fields': (
                'remarks',
            ),
            'classes': ('collapse',),
        }),
        ('审计信息', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # 操作选项
    actions = [
        'recalculate_comprehensive_score',
        'export_selected_evaluations',
    ]
    
    def supplier_name_link(self, obj):
        """供应商名称链接"""
        if obj.supplier_name:
            # 链接到该供应商的所有评价
            url = f'/admin/supplier_eval/supplierevaluation/?supplier_name={obj.supplier_name}'
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.supplier_name
            )
        return '-'
    supplier_name_link.short_description = '供应商名称'
    
    def contract_link(self, obj):
        """合同链接"""
        if obj.contract:
            url = f'/admin/contract/contract/{obj.contract.contract_code}/change/'
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                obj.contract.contract_code
            )
        return '-'
    contract_link.short_description = '关联合同'
    
    def comprehensive_score_badge(self, obj):
        """综合评分徽章"""
        if not obj.comprehensive_score:
            return format_html(
                '<span style="color: #999;">未评分</span>'
            )
        
        score = float(obj.comprehensive_score)
        if score >= 90:
            color = '#28a745'  # 绿色 - 优秀
            level = '优秀'
        elif score >= 80:
            color = '#17a2b8'  # 蓝色 - 良好
            level = '良好'
        elif score >= 70:
            color = '#ffc107'  # 黄色 - 合格
            level = '合格'
        else:
            color = '#dc3545'  # 红色 - 不合格
            level = '不合格'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{:.2f} ({})</span>',
            color,
            score,
            level
        )
    comprehensive_score_badge.short_description = '综合评分'
    
    def score_level(self, obj):
        """评分等级"""
        return obj.get_score_level()
    score_level.short_description = '评分等级'
    
    def calculated_score_info(self, obj):
        """显示综合评分计算详情（支持动态年度）"""
        if not obj.last_evaluation_score:
            return '无法计算(缺少末次评价得分)'

        # 获取过程评价
        process_scores = []
        process_items = []

        # 年度评价（从JSONField动态获取）
        if obj.annual_scores:
            years = sorted([int(y) for y in obj.annual_scores.keys()])
            for year in years:
                score = obj.annual_scores[str(year)]
                if score is not None:
                    process_scores.append(float(score))
                    process_items.append(f'{year}年度: {score}')

        # 不定期评价（从JSONField动态获取）
        if obj.irregular_scores:
            indices = sorted([int(i) for i in obj.irregular_scores.keys()])
            for index in indices:
                score = obj.irregular_scores[str(index)]
                if score is not None:
                    process_scores.append(float(score))
                    process_items.append(f'第{index}次不定期: {score}')

        if not process_scores:
            calculated = obj.last_evaluation_score
            formula = f'综合评分 = 末次评价 = {obj.last_evaluation_score}'
        else:
            process_avg = sum(process_scores) / len(process_scores)
            calculated = float(obj.last_evaluation_score) * 0.6 + process_avg * 0.4
            formula = f'综合评分 = {obj.last_evaluation_score} × 60% + {process_avg:.2f} × 40% = {calculated:.2f}'

        process_info = '<br>'.join(process_items) if process_items else '无过程评价'

        return format_html(
            '<div style="line-height: 1.6;">'
            '<strong>计算公式:</strong><br>{}<br><br>'
            '<strong>过程评价明细:</strong><br>{}'
            '</div>',
            formula,
            process_info
        )
    calculated_score_info.short_description = '评分计算详情'
    
    def recalculate_comprehensive_score(self, request, queryset):
        """批量重新计算综合评分"""
        updated_count = 0
        for evaluation in queryset:
            if evaluation.last_evaluation_score:
                old_score = evaluation.comprehensive_score
                evaluation.comprehensive_score = evaluation.calculate_comprehensive_score()
                evaluation.save()
                updated_count += 1
        
        self.message_user(
            request,
            f'已重新计算 {updated_count} 条评价的综合评分'
        )
    recalculate_comprehensive_score.short_description = '重新计算综合评分'
    
    def export_selected_evaluations(self, request, queryset):
        """导出选中的评价记录"""
        # TODO: 实现导出功能
        self.message_user(
            request,
            f'导出功能开发中...(选中 {queryset.count()} 条记录)'
        )
    export_selected_evaluations.short_description = '导出选中记录'


@admin.register(SupplierInterview)
class SupplierInterviewAdmin(admin.ModelAdmin):
    """供应商约谈记录Admin配置"""
    
    # 列表页显示字段
    list_display = [
        'id',
        'interview_date',
        'supplier_name_link',
        'interview_type_badge',
        'status_badge',
        'interviewer',
        'has_contract_icon',
        'created_at',
    ]
    
    # 搜索字段
    search_fields = [
        'supplier_name',
        'interviewer',
        'supplier_representative',
        'reason',
        'content',
        'rectification_requirements',
        'result',
        'contract__contract_code',
        'contract__contract_name',
    ]
    
    # 筛选器
    list_filter = [
        'interview_type',
        'status',
        'has_contract',
        'interview_date',
        'created_at',
    ]
    
    # 关联字段自动补全
    autocomplete_fields = ['contract']
    
    # 时间层级导航
    date_hierarchy = 'interview_date'
    
    # 每页显示数量
    list_per_page = 50
    
    # 只读字段
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    # 字段集分组
    fieldsets = (
        ('基本信息', {
            'fields': (
                'supplier_name',
                'contract',
                'has_contract',
            )
        }),
        ('约谈信息', {
            'fields': (
                'interview_type',
                'interview_date',
                'interviewer',
                'supplier_representative',
            )
        }),
        ('约谈内容', {
            'fields': (
                'reason',
                'content',
                'rectification_requirements',
                'result',
            )
        }),
        ('状态管理', {
            'fields': (
                'status',
            )
        }),
        ('附件说明', {
            'fields': (
                'attachments',
            ),
            'classes': ('collapse',),
        }),
        ('审计信息', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # 操作选项
    actions = [
        'mark_as_completed',
        'mark_as_followup_needed',
        'export_selected_interviews',
    ]
    
    def supplier_name_link(self, obj):
        """供应商名称链接"""
        if obj.supplier_name:
            # 链接到该供应商的所有约谈记录
            url = f'/admin/supplier_eval/supplierinterview/?supplier_name={obj.supplier_name}'
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.supplier_name
            )
        return '-'
    supplier_name_link.short_description = '供应商名称'
    
    def interview_type_badge(self, obj):
        """约谈类型徽章"""
        color = obj.get_type_badge_color()
        color_map = {
            'danger': '#dc3545',
            'primary': '#007bff',
            'info': '#17a2b8',
            'success': '#28a745',
            'secondary': '#6c757d',
        }
        bg_color = color_map.get(color, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            bg_color,
            obj.interview_type
        )
    interview_type_badge.short_description = '约谈类型'
    
    def status_badge(self, obj):
        """状态徽章"""
        color = obj.get_status_color()
        color_map = {
            'danger': '#dc3545',
            'warning': '#ffc107',
            'success': '#28a745',
            'secondary': '#6c757d',
        }
        bg_color = color_map.get(color, '#6c757d')
        text_color = 'white' if color != 'warning' else '#000'
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            bg_color,
            text_color,
            obj.status
        )
    status_badge.short_description = '跟进状态'
    
    def has_contract_icon(self, obj):
        """是否已签约图标"""
        if obj.has_contract:
            return format_html(
                '<span style="color: #28a745; font-size: 16px;" title="已签约供应商">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d; font-size: 16px;" title="潜在供应商">○</span>'
            )
    has_contract_icon.short_description = '已签约'
    
    def mark_as_completed(self, request, queryset):
        """批量标记为已完成"""
        updated = queryset.update(status='已完成')
        self.message_user(
            request,
            f'已将 {updated} 条约谈记录标记为已完成'
        )
    mark_as_completed.short_description = '标记为已完成'
    
    def mark_as_followup_needed(self, request, queryset):
        """批量标记为待整改"""
        updated = queryset.update(status='待整改')
        self.message_user(
            request,
            f'已将 {updated} 条约谈记录标记为待整改'
        )
    mark_as_followup_needed.short_description = '标记为待整改'
    
    def export_selected_interviews(self, request, queryset):
        """导出选中的约谈记录"""
        # TODO: 实现导出功能
        self.message_user(
            request,
            f'导出功能开发中...(选中 {queryset.count()} 条记录)'
        )
    export_selected_interviews.short_description = '导出选中记录'
    
    def get_queryset(self, request):
        """优化查询性能"""
        qs = super().get_queryset(request)
        return qs.select_related('contract')