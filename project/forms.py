"""
项目模块表单定义
提供美观的前端编辑表单,替代Django Admin界面
"""
from django import forms
from django.core.exceptions import ValidationError
from project.models import Project
from project.enums import (
    ProcurementCategory, ProcurementMethod, QualificationReviewMethod,
    BidEvaluationMethod, BidAwardingMethod, get_enum_choices
)
from contract.models import Contract
from procurement.models import Procurement
from payment.models import Payment


class ProjectForm(forms.ModelForm):
    """项目编辑表单"""
    
    class Meta:
        model = Project
        fields = [
            'project_code',
            'project_name',
            'description',
            'project_manager',
            'status',
            'remarks',
        ]
        widgets = {
            'project_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '项目编码，如: PRJ2025001',
                'readonly': 'readonly',  # 编辑时不允许修改主键
            }),
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入项目名称',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入项目描述（可选）',
                'rows': 3,
            }),
            'project_manager': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入项目负责人（可选）',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入备注信息（可选）',
                'rows': 3,
            }),
        }
        labels = {
            'project_code': '项目编码',
            'project_name': '项目名称',
            'description': '项目描述',
            'project_manager': '项目负责人',
            'status': '项目状态',
            'remarks': '备注',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果是编辑模式，禁用项目编码字段
        if self.instance.pk:
            self.fields['project_code'].disabled = True
            self.fields['project_code'].widget.attrs['readonly'] = True


class ContractForm(forms.ModelForm):
    """合同编辑表单"""
    
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/projects/',
            'data-search-fields': 'project_code,project_name',
            'data-display-format': '{project_code} - {project_name}',
            'data-placeholder': '搜索项目编码或名称...',
            'data-target-field': 'procurement'
        }),
        label='关联项目',
        help_text='选择所属项目，可搜索项目编码或名称'
    )
    
    procurement = forms.ModelChoiceField(
        queryset=Procurement.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/procurements/',
            'data-search-fields': 'procurement_code,project_name',
            'data-display-format': '{procurement_code} - {project_name}',
            'data-placeholder': '先选择项目，再搜索采购...',
            'data-dependent-field': 'project'
        }),
        label='关联采购',
        help_text='选择关联采购，可搜索采购编号或项目名称'
    )
    
    parent_contract = forms.ModelChoiceField(
        queryset=Contract.objects.filter(file_positioning='主合同'),
        empty_label='请选择主合同（补充协议时必填）',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    class Meta:
        model = Contract
        fields = [
            'project',
            'procurement',
            'contract_code',
            'contract_name',
            'file_positioning',
            'contract_type',
            'contract_source',
            'parent_contract',
            'contract_sequence',
            'party_a',
            'party_b',
            'party_a_legal_representative',
            'party_a_contact_person',
            'party_a_manager',
            'party_b_legal_representative',
            'party_b_contact_person',
            'party_b_manager',
            'contract_amount',
            'signing_date',
            'duration',
            'contract_officer',
            'payment_method',
            'performance_guarantee_return_date',
            'archive_date',
        ]
        widgets = {
            'contract_code': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
            }),
            'contract_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入合同名称',
                'required': True,
            }),
            'file_positioning': forms.Select(attrs={
                'class': 'form-control',
            }),
            'contract_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'contract_source': forms.Select(attrs={
                'class': 'form-control',
            }),
            'contract_sequence': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '合同序号，如: BHHY-NH-001',
            }),
            'party_a': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入甲方名称',
            }),
            'party_b': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入乙方名称',
            }),
            'party_a_legal_representative': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '甲方法定代表人及联系方式',
            }),
            'party_a_contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '甲方联系人及联系方式',
            }),
            'party_a_manager': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '甲方负责人及联系方式',
            }),
            'party_b_legal_representative': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '乙方法定代表人及联系方式',
            }),
            'party_b_contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '乙方联系人及联系方式',
            }),
            'party_b_manager': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '乙方负责人及联系方式',
            }),
            'contract_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入合同金额（元）',
                'step': '0.01',
            }),
            'signing_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'duration': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入合同工期/服务期限',
                'rows': 2,
            }),
            'contract_officer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入经办人',
            }),
            'payment_method': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入支付方式',
                'rows': 2,
            }),
            'performance_guarantee_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['contract_code'].disabled = True
            # 设置初始值
            if self.instance.procurement:
                self.fields['procurement'].initial = self.instance.procurement
            if self.instance.parent_contract:
                self.fields['parent_contract'].initial = self.instance.parent_contract


class ProcurementForm(forms.ModelForm):
    """采购编辑表单"""
    
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/projects/',
            'data-search-fields': 'project_code,project_name',
            'data-display-format': '{project_code} - {project_name}',
            'data-placeholder': '搜索项目编码或名称...',
            'data-allow-clear': 'true'
        }),
        label='关联项目',
        help_text='选择所属项目，可搜索项目编码或名称'
    )
    
    class Meta:
        model = Procurement
        fields = [
            'project',  # 新增项目关联字段
            'procurement_code',
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
                'readonly': 'readonly',
            }),
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入采购项目名称',
                'required': True,
            }),
            'procurement_unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入采购单位',
            }),
            'procurement_category': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[('', '请选择采购类别')] + get_enum_choices(ProcurementCategory)),
            'procurement_platform': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: 深圳市阳光采购平台',
            }),
            'procurement_method': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[('', '请选择采购方式')] + get_enum_choices(ProcurementMethod)),
            'qualification_review_method': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[('', '请选择资格审查方式')] + get_enum_choices(QualificationReviewMethod)),
            'bid_evaluation_method': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[('', '请选择评标方式')] + get_enum_choices(BidEvaluationMethod)),
            'bid_awarding_method': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[('', '请选择定标方法')] + get_enum_choices(BidAwardingMethod)),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '采购预算金额（元）',
                'step': '0.01',
            }),
            'control_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '采购控制价（元）',
                'step': '0.01',
            }),
            'winning_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '中标金额（元）',
                'step': '0.01',
            }),
            'procurement_officer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入采购经办人',
            }),
            'demand_department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入需求部门',
            }),
            'demand_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '申请人联系电话（需求部门）',
            }),
            'winning_bidder': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入中标单位',
            }),
            'winning_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入联系人及方式',
            }),
            'planned_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'requirement_approval_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'announcement_release_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'registration_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'bid_opening_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'candidate_publicity_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'result_publicity_release_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'notice_issue_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
            }, format='%Y-%m-%d'),
            'evaluation_committee': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '评标委员会成员名单，多个成员用逗号分隔',
                'rows': 2,
            }),
            'bid_guarantee': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: 银行保函 500000.00',
            }),
            'bid_guarantee_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'performance_guarantee': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: 银行保函 450000.00',
            }),
            'candidate_publicity_issue': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '记录公示期内质疑的受理与处理情况',
                'rows': 3,
            }),
            'non_bidding_explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '如从公开招标调整为单一来源或邀请招标需说明原因',
                'rows': 3,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['procurement_code'].disabled = True


class PaymentForm(forms.ModelForm):
    """付款编辑表单"""
    
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/projects/',
            'data-search-fields': 'project_code,project_name',
            'data-display-format': '{project_code} - {project_name}',
            'data-placeholder': '选择项目以筛选合同...',
            'data-target-field': 'contract'
        }),
        label='筛选项目',
        help_text='选择项目以筛选合同列表（可选）'
    )
    
    contract = forms.ModelChoiceField(
        queryset=Contract.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control smart-selector',
            'data-url': '/api/contracts/',
            'data-search-fields': 'contract_code,contract_name,contract_sequence',
            'data-display-format': '{contract_sequence} - {contract_name}',
            'data-placeholder': '搜索合同编号、序号或名称...',
            'data-dependent-field': 'project'
        }),
        label='关联合同',
        help_text='选择关联合同，可搜索合同编号、序号或名称'
    )
    
    class Meta:
        model = Payment
        fields = [
            'project',
            'contract',
            'payment_code',
            'payment_amount',
            'payment_date',
            'settlement_amount',
            'is_settled',
            'settlement_completion_date',
            'settlement_archive_date',
        ]
        widgets = {
            'payment_code': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': '自动生成，格式：合同序号-FK-序号',
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入付款金额（元）',
                'step': '0.01',
                'required': True,
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }, format='%Y-%m-%d'),
            'settlement_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入结算金额（元，可选）',
                'step': '0.01',
            }),
            'is_settled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'settlement_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'settlement_archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }, format='%Y-%m-%d'),
        }
        labels = {
            'payment_code': '付款编号',
            'payment_amount': '实付金额',
            'payment_date': '付款日期',
            'settlement_amount': '结算价',
            'is_settled': '是否办理结算',
            'settlement_completion_date': '结算完成时间',
            'settlement_archive_date': '结算资料归档时间',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['payment_code'].disabled = True
            # 设置初始值
            if self.instance.contract:
                self.fields['contract'].initial = self.instance.contract
        
        # 合同选项已在字段定义中设置
        pass