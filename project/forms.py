"""
项目模块表单定义
提供美观的前端编辑表单,替代Django Admin界面
"""
from django import forms
from django.core.exceptions import ValidationError
from project.models import Project
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
    
    class Meta:
        model = Contract
        fields = [
            'contract_code',
            'contract_name',
            'file_positioning',
            'contract_source',
            'party_a',
            'party_b',
            'contract_amount',
            'signing_date',
            'contract_officer',
            'payment_method',
            'duration',
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
            'contract_source': forms.Select(attrs={
                'class': 'form-control',
            }),
            'party_a': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入甲方名称',
            }),
            'party_b': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入乙方名称',
            }),
            'contract_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入合同金额（元）',
                'step': '0.01',
            }),
            'signing_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
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
            'duration': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入合同工期/服务期限',
                'rows': 2,
            }),
            'archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['contract_code'].disabled = True


class ProcurementForm(forms.ModelForm):
    """采购编辑表单"""
    
    class Meta:
        model = Procurement
        fields = [
            'procurement_code',
            'project_name',
            'procurement_unit',
            'winning_bidder',
            'winning_contact',
            'procurement_method',
            'procurement_category',
            'budget_amount',
            'control_price',
            'winning_amount',
            'bid_opening_date',
            'result_publicity_release_date',
            'archive_date',
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
            'winning_bidder': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入中标单位',
            }),
            'winning_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入联系人及方式',
            }),
            'procurement_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '如: 公开招标',
            }),
            'procurement_category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '如: 工程类',
            }),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'control_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'winning_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'bid_opening_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'result_publicity_release_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'archive_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['procurement_code'].disabled = True


class PaymentForm(forms.ModelForm):
    """付款编辑表单"""
    
    class Meta:
        model = Payment
        fields = [
            'payment_code',
            'payment_amount',
            'payment_date',
            'settlement_amount',
            'is_settled',
        ]
        widgets = {
            'payment_code': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
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
            }),
            'settlement_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入结算金额（可选）',
                'step': '0.01',
            }),
            'is_settled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['payment_code'].disabled = True