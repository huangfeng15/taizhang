"""
PDF导入表单
"""
from django import forms
from django.core.exceptions import ValidationError
from procurement.models import Procurement
from project.models import Project
from decimal import Decimal


class ProcurementConfirmForm(forms.ModelForm):
    """
    采购信息确认表单
    支持数据验证和详细错误提示
    """
    
    class Meta:
        model = Procurement
        fields = [
            'procurement_code',
            'project',
            'project_name',
            'procurement_unit',
            'procurement_category',
            'procurement_platform',
            'procurement_method',
            'qualification_review_method',
            'bid_evaluation_method',
            'bid_awarding_method',
            'budget_amount',
            'control_price',
            'winning_amount',
            'procurement_officer',
            'demand_department',
            'demand_contact',
            'winning_bidder',
            'winning_contact',
            'planned_completion_date',
            'requirement_approval_date',
            'announcement_release_date',
            'registration_deadline',
            'bid_opening_date',
            'candidate_publicity_end_date',
            'result_publicity_release_date',
            'notice_issue_date',
            'archive_date',
            'evaluation_committee',
            'bid_guarantee',
            'bid_guarantee_return_date',
            'performance_guarantee',
            'candidate_publicity_issue',
            'non_bidding_explanation',
        ]
        widgets = {
            'procurement_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '格式：TQJG+年月日+类型+序号'
            }),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'project_name': forms.TextInput(attrs={'class': 'form-control'}),
            'procurement_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'procurement_category': forms.Select(attrs={'class': 'form-select'}),
            'procurement_platform': forms.TextInput(attrs={'class': 'form-control'}),
            'procurement_method': forms.Select(attrs={'class': 'form-select'}),
            'qualification_review_method': forms.Select(attrs={'class': 'form-select'}),
            'bid_evaluation_method': forms.Select(attrs={'class': 'form-select'}),
            'bid_awarding_method': forms.Select(attrs={'class': 'form-select'}),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'control_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'winning_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'procurement_officer': forms.TextInput(attrs={'class': 'form-control'}),
            'demand_department': forms.TextInput(attrs={'class': 'form-control'}),
            'demand_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'winning_bidder': forms.TextInput(attrs={'class': 'form-control'}),
            'winning_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'requirement_approval_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'announcement_release_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'registration_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'bid_opening_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'candidate_publicity_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'result_publicity_release_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notice_issue_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'evaluation_committee': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'bid_guarantee': forms.TextInput(attrs={'class': 'form-control'}),
            'bid_guarantee_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'performance_guarantee': forms.TextInput(attrs={'class': 'form-control'}),
            'candidate_publicity_issue': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'non_bidding_explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def clean_budget_amount(self):
        """清理预算金额 - 移除逗号"""
        from .utils.amount_parser import AmountParser
        amount = self.cleaned_data.get('budget_amount')
        if amount and isinstance(amount, str):
            return AmountParser.parse_amount(amount)
        return amount
    
    def clean_control_price(self):
        """清理控制价 - 移除逗号"""
        from .utils.amount_parser import AmountParser
        amount = self.cleaned_data.get('control_price')
        if amount and isinstance(amount, str):
            return AmountParser.parse_amount(amount)
        return amount
    
    def clean_winning_amount(self):
        """清理中标金额 - 移除逗号"""
        from .utils.amount_parser import AmountParser
        amount = self.cleaned_data.get('winning_amount')
        if amount and isinstance(amount, str):
            return AmountParser.parse_amount(amount)
        return amount
    
    def clean_procurement_code(self):
        """验证招采编号唯一性"""
        code = self.cleaned_data.get('procurement_code')
        if code:
            # 检查是否已存在（排除当前实例）
            if self.instance.pk:
                exists = Procurement.objects.filter(
                    procurement_code=code
                ).exclude(pk=self.instance.pk).exists()
            else:
                exists = Procurement.objects.filter(
                    procurement_code=code
                ).exists()
            
            if exists:
                raise forms.ValidationError(f'招采编号 {code} 已存在')
        
        return code
    
    def clean(self):
        """跨字段验证 - 业务规则检查"""
        cleaned_data = super().clean()
        errors = []
        
        # 1. 验证金额逻辑
        winning = cleaned_data.get('winning_amount')
        control = cleaned_data.get('control_price')
        budget = cleaned_data.get('budget_amount')
        
        if winning and control and winning > control:
            self.add_error('winning_amount',
                f'❌ 中标金额（{winning:,.2f}元）不能超过控制价（{control:,.2f}元）')
            errors.append('中标金额超过控制价')
        
        if control and budget and control > budget:
            self.add_error('control_price',
                f'❌ 控制价（{control:,.2f}元）不能超过预算金额（{budget:,.2f}元）')
            errors.append('控制价超过预算金额')
        
        # 2. 验证日期逻辑
        req_approval = cleaned_data.get('requirement_approval_date')
        announcement = cleaned_data.get('announcement_release_date')
        registration = cleaned_data.get('registration_deadline')
        bid_opening = cleaned_data.get('bid_opening_date')
        candidate_end = cleaned_data.get('candidate_publicity_end_date')
        result_pub = cleaned_data.get('result_publicity_release_date')
        notice_issue = cleaned_data.get('notice_issue_date')
        archive = cleaned_data.get('archive_date')
        
        # 日期顺序验证
        if req_approval and announcement and announcement < req_approval:
            self.add_error('announcement_release_date',
                '❌ 公告发布时间不能早于需求书审批完成日期')
            errors.append('公告发布时间早于需求书审批')
        
        if announcement and registration and registration < announcement:
            self.add_error('registration_deadline',
                '❌ 报名截止时间不能早于公告发布时间')
            errors.append('报名截止时间早于公告发布')
        
        if registration and bid_opening and bid_opening < registration:
            self.add_error('bid_opening_date',
                '❌ 开标时间不能早于报名截止时间')
            errors.append('开标时间早于报名截止')
        
        if bid_opening and candidate_end and candidate_end < bid_opening:
            self.add_error('candidate_publicity_end_date',
                '❌ 候选人公示结束时间不能早于开标时间')
            errors.append('候选人公示结束时间早于开标')
        
        if candidate_end and result_pub and result_pub < candidate_end:
            self.add_error('result_publicity_release_date',
                '❌ 结果公示发布时间不能早于候选人公示结束时间')
            errors.append('结果公示发布时间顺序错误')
        
        if result_pub and notice_issue and notice_issue < result_pub:
            self.add_error('notice_issue_date',
                '❌ 中标通知书发放日期不能早于结果公示发布时间')
            errors.append('中标通知书发放日期顺序错误')
        
        # 3. 验证必要字段的组合
        winning_bidder = cleaned_data.get('winning_bidder')
        
        if winning and not winning_bidder:
            self.add_error('winning_bidder',
                '⚠️ 填写了中标金额，建议同时填写中标单位')
        
        if winning_bidder and not winning:
            self.add_error('winning_amount',
                '⚠️ 填写了中标单位，建议同时填写中标金额')
        
        # 如果有错误，在表单顶部显示汇总
        if errors:
            raise ValidationError({
                '__all__': [
                    f'发现 {len(errors)} 个验证错误，请修正后重新提交：',
                    *[f'• {err}' for err in errors]
                ]
            })
        
        return cleaned_data
    
    def get_validation_summary(self):
        """获取验证错误摘要"""
        if not self.errors:
            return None
        
        summary = {
            'total_errors': len(self.errors),
            'field_errors': [],
            'non_field_errors': []
        }
        
        for field, errors in self.errors.items():
            if field == '__all__':
                summary['non_field_errors'] = errors
            else:
                field_label = self.fields[field].label if field in self.fields else field
                summary['field_errors'].append({
                    'field': field,
                    'label': field_label,
                    'errors': errors
                })
        
        return summary