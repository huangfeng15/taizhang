"""
供应商管理模块 - 表单定义
提供约谈记录的前端编辑表单
"""
from django import forms
from django.core.exceptions import ValidationError
from supplier_eval.models import SupplierInterview, SupplierEvaluation
from contract.models import Contract


class SupplierInterviewForm(forms.ModelForm):
    """供应商约谈记录编辑表单"""
    
    contract = forms.ModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/contracts/',
            'data-search-fields': 'contract_code,contract_name,contract_sequence',
            'data-display-format': '{contract_sequence} - {contract_name}',
            'data-placeholder': '搜索合同编号、序号或名称（可选）...',
            'data-allow-clear': 'true'
        }),
        label='关联合同',
        help_text='选择关联合同，可搜索合同编号、序号或名称（可选）'
    )
    
    class Meta:
        model = SupplierInterview
        fields = [
            'supplier_name',
            'contract',
            'interview_type',
            'interview_date',
            'interviewer',
            'supplier_representative',
            'reason',
            'content',
            'rectification_requirements',
            'result',
            'status',
            'has_contract',
            'attachments',
        ]
        widgets = {
            'supplier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入供应商名称',
                'required': True,
            }),
            'interview_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'interview_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }, format='%Y-%m-%d'),
            'interviewer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入约谈人（我方参与人员）',
                'required': True,
            }),
            'supplier_representative': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入供应商代表（可选）',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请详细说明约谈原因',
                'rows': 3,
                'required': True,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请详细记录约谈内容和沟通要点',
                'rows': 4,
                'required': True,
            }),
            'rectification_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '如为违约约谈，请填写整改要求（可选）',
                'rows': 3,
            }),
            'result': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请记录处理结果和后续跟进（可选）',
                'rows': 3,
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'has_contract': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'attachments': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '相关文件记录（可选）',
                'rows': 2,
            }),
        }
        labels = {
            'supplier_name': '供应商名称',
            'contract': '关联合同',
            'interview_type': '约谈类型',
            'interview_date': '约谈日期',
            'interviewer': '约谈人',
            'supplier_representative': '供应商代表',
            'reason': '约谈原因',
            'content': '约谈内容',
            'rectification_requirements': '整改要求',
            'result': '处理结果',
            'status': '跟进状态',
            'has_contract': '是否已签约供应商',
            'attachments': '附件说明',
        }
        help_texts = {
            'supplier_name': '填写被约谈的供应商名称',
            'interview_type': '选择约谈类型：违约约谈、履约沟通、商务洽谈等',
            'interview_date': '约谈发生的日期',
            'interviewer': '填写我方约谈人员姓名',
            'supplier_representative': '填写对方参与人员（可选）',
            'reason': '详细说明为什么进行此次约谈',
            'content': '详细记录约谈过程中的沟通内容',
            'rectification_requirements': '如为违约约谈，填写要求供应商整改的内容',
            'result': '填写约谈后的处理结果和后续跟进安排',
            'status': '选择当前跟进状态',
            'has_contract': '勾选表示该供应商已签约，未勾选表示潜在供应商',
            'attachments': '记录相关文件名称或说明',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 如果是编辑模式，设置初始值
        if self.instance.pk:
            if self.instance.contract:
                self.fields['contract'].initial = self.instance.contract
    
    def clean(self):
        """表单整体验证"""
        cleaned_data = super().clean()
        
        interview_type = cleaned_data.get('interview_type')
        status = cleaned_data.get('status')
        rectification_requirements = cleaned_data.get('rectification_requirements')
        
        # 如果是违约约谈，建议填写整改要求
        if interview_type == '违约约谈':
            if status in ['待整改', '整改中'] and not rectification_requirements:
                self.add_error(
                    'rectification_requirements',
                    '违约约谈且状态为待整改或整改中时，建议填写整改要求'
                )
        
        return cleaned_data
    
    def clean_supplier_name(self):
        """供应商名称验证"""
        supplier_name = self.cleaned_data.get('supplier_name')
        
        if supplier_name:
            # 去除首尾空格
            supplier_name = supplier_name.strip()
            
            # 长度验证
            if len(supplier_name) < 2:
                raise ValidationError('供应商名称至少需要2个字符')
            
            if len(supplier_name) > 200:
                raise ValidationError('供应商名称不能超过200个字符')
        
        return supplier_name
    
    def clean_interview_date(self):
        """约谈日期验证"""
        interview_date = self.cleaned_data.get('interview_date')
        
        if interview_date:
            from django.utils import timezone
            from datetime import date
            
            # 约谈日期不能是未来日期
            today = timezone.now().date()
            if interview_date > today:
                raise ValidationError('约谈日期不能是未来日期')
            
            # 约谈日期不能太早（例如不早于2000年）
            min_date = date(2000, 1, 1)
            if interview_date < min_date:
                raise ValidationError('约谈日期不能早于2000年1月1日')
        
        return interview_date


class SupplierEvaluationForm(forms.ModelForm):
    """供应商履约评价编辑表单"""
    
    class Meta:
        model = SupplierEvaluation
        fields = [
            'contract',
            'supplier_name',
            'comprehensive_score',
            'last_evaluation_score',
            'score_2025',
            'score_2024',
            'score_2023',
            'score_2022',
            'score_2021',
            'score_2020',
            'score_2019',
            'irregular_evaluation_1',
            'irregular_evaluation_2',
            'remarks',
        ]
        widgets = {
            'contract': forms.HiddenInput(),  # 合同字段将通过智能选择器渲染
            'supplier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入供应商名称',
                'required': True,
            }),
            'comprehensive_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '综合评分（可选，留空则自动计算）',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'last_evaluation_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '末次评价得分（权重60%）',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2025': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2025年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2024': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2024年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2023': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2023年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2022': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2022年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2021': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2021年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2020': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2020年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'score_2019': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2019年度评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'irregular_evaluation_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '第一次不定期评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'irregular_evaluation_2': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '第二次不定期评价得分',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '备注信息（可选）',
                'rows': 3,
            }),
        }
        labels = {
            'contract': '关联合同',
            'supplier_name': '供应商名称',
            'comprehensive_score': '综合评分',
            'last_evaluation_score': '末次评价得分',
            'score_2025': '2025年度评价',
            'score_2024': '2024年度评价',
            'score_2023': '2023年度评价',
            'score_2022': '2022年度评价',
            'score_2021': '2021年度评价',
            'score_2020': '2020年度评价',
            'score_2019': '2019年度评价',
            'irregular_evaluation_1': '第一次不定期评价',
            'irregular_evaluation_2': '第二次不定期评价',
            'remarks': '备注',
        }
        help_texts = {
            'supplier_name': '填写供应商名称（自动从合同获取）',
            'comprehensive_score': '留空则根据末次评价和过程评价自动计算',
            'last_evaluation_score': '末次评价得分，权重60%',
            'score_2025': '2025年度评价得分（可选）',
            'score_2024': '2024年度评价得分（可选）',
            'score_2023': '2023年度评价得分（可选）',
            'score_2022': '2022年度评价得分（可选）',
            'score_2021': '2021年度评价得分（可选）',
            'score_2020': '2020年度评价得分（可选）',
            'score_2019': '2019年度评价得分（可选）',
            'irregular_evaluation_1': '第一次不定期评价得分（可选）',
            'irregular_evaluation_2': '第二次不定期评价得分（可选）',
            'remarks': '其他备注信息',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 如果是编辑模式，设置初始值
        if self.instance.pk:
            if self.instance.contract:
                self.fields['contract'].initial = self.instance.contract
    
    def clean_supplier_name(self):
        """供应商名称验证"""
        supplier_name = self.cleaned_data.get('supplier_name')
        
        if supplier_name:
            supplier_name = supplier_name.strip()
            if len(supplier_name) < 2:
                raise ValidationError('供应商名称至少需要2个字符')
            if len(supplier_name) > 200:
                raise ValidationError('供应商名称不能超过200个字符')
        
        return supplier_name
    
    def clean(self):
        """表单整体验证"""
        cleaned_data = super().clean()
        
        # 验证评分范围
        score_fields = [
            'comprehensive_score', 'last_evaluation_score',
            'score_2025', 'score_2024', 'score_2023', 'score_2022',
            'score_2021', 'score_2020', 'score_2019',
            'irregular_evaluation_1', 'irregular_evaluation_2'
        ]
        
        for field_name in score_fields:
            score = cleaned_data.get(field_name)
            if score is not None:
                if score < 0 or score > 100:
                    self.add_error(field_name, '评分必须在0-100之间')
        
        return cleaned_data