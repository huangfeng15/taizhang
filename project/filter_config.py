"""
筛选配置辅助模块
为各个列表视图提供统一的筛选配置
"""

def get_contract_filter_config(request):
    """获取合同列表的筛选配置"""
    from .models import Project
    from contract.models import Contract
    
    # 获取多选参数
    project_values = request.GET.getlist('project')
    contract_type_values = request.GET.getlist('contract_type')
    
    # 快速筛选配置(3-5个最常用字段)
    quick_filters = [
        {
            'name': 'project',
            'type': 'select',
            'placeholder': '所有项目',
            'width': '200px',
            'current_value': project_values,  # 多选值
            'options': [
                {'value': p.project_code, 'label': p.project_name}
                for p in Project.objects.all()
            ]
        },
        {
            'name': 'contract_type',
            'type': 'select',
            'placeholder': '所有类型',
            'width': '150px',
            'current_value': contract_type_values,  # 多选值
            'options': [
                {'value': value, 'label': label}
                for value, label in Contract._meta.get_field('contract_type').choices
            ]
        },
        {
            'name': 'has_settlement',
            'type': 'select',
            'placeholder': '结算状态',
            'width': '120px',
            'current_value': request.GET.getlist('has_settlement'),
            'options': [
                {'value': 'true', 'label': '已结算'},
                {'value': 'false', 'label': '未结算'}
            ]
        }
    ]
    
    # 高级筛选配置(按类别分组)
    advanced_filter_groups = [
        {
            'title': '基本信息',
            'icon': 'fas fa-info-circle',
            'filters': [
                {
                    'name': 'contract_code',
                    'label': '合同编号',
                    'type': 'text',
                    'placeholder': '输入合同编号',
                    'current_value': request.GET.get('contract_code', '')
                },
                {
                    'name': 'contract_sequence',
                    'label': '合同序号',
                    'type': 'text',
                    'placeholder': '输入合同序号',
                    'current_value': request.GET.get('contract_sequence', '')
                },
                {
                    'name': 'contract_name',
                    'label': '合同名称',
                    'type': 'text',
                    'placeholder': '输入合同名称',
                    'current_value': request.GET.get('contract_name', '')
                },
                {
                    'name': 'contract_source',
                    'label': '合同来源',
                    'type': 'select',
                    'options': [
                        {'value': '采购合同', 'label': '采购合同'},
                        {'value': '直接签订', 'label': '直接签订'}
                    ],
                    'current_value': request.GET.getlist('contract_source')  # 多选值
                }
            ]
        },
        {
            'title': '合同方信息',
            'icon': 'fas fa-users',
            'filters': [
                {
                    'name': 'party_a',
                    'label': '甲方',
                    'type': 'text',
                    'placeholder': '输入甲方名称',
                    'current_value': request.GET.get('party_a', '')
                },
                {
                    'name': 'party_b',
                    'label': '乙方',
                    'type': 'text',
                    'placeholder': '输入乙方名称',
                    'current_value': request.GET.get('party_b', '')
                },
                {
                    'name': 'party_b_contact',
                    'label': '乙方联系人',
                    'type': 'text',
                    'placeholder': '输入联系人或电话',
                    'current_value': request.GET.get('party_b_contact', '')
                },
                {
                    'name': 'contract_officer',
                    'label': '合同签订经办人',
                    'type': 'text',
                    'placeholder': '输入经办人姓名',
                    'current_value': request.GET.get('contract_officer', '')
                }
            ]
        },
        {
            'title': '金额与付款',
            'icon': 'fas fa-money-bill-wave',
            'filters': [
                {
                    'name': 'contract_amount',
                    'label': '合同金额',
                    'type': 'number',
                    'min_value': request.GET.get('contract_amount_min', ''),
                    'max_value': request.GET.get('contract_amount_max', '')
                },
                {
                    'name': 'payment_ratio',
                    'label': '付款比例（相对合同金额%）',
                    'type': 'number',
                    'min_value': request.GET.get('payment_ratio_min', ''),
                    'max_value': request.GET.get('payment_ratio_max', ''),
                    'help_text': '输入0-100之间的百分比值'
                }
            ]
        },
        {
            'title': '日期范围',
            'icon': 'fas fa-calendar',
            'filters': [
                {
                    'name': 'signing_date',
                    'label': '签订日期',
                    'type': 'daterange',
                    'start_value': request.GET.get('signing_date_start', ''),
                    'end_value': request.GET.get('signing_date_end', '')
                },
                {
                    'name': 'performance_guarantee_return_date',
                    'label': '履约担保退回时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('performance_guarantee_return_date_start', ''),
                    'end_value': request.GET.get('performance_guarantee_return_date_end', '')
                }
            ]
        }
    ]
    
    return {
        'quick_filters': quick_filters,
        'advanced_filter_groups': advanced_filter_groups,
        'search_query': request.GET.get('q', '')
    }


def get_procurement_filter_config(request):
    """获取采购列表的筛选配置"""
    from .models import Project
    
    quick_filters = [
        {
            'name': 'project',
            'type': 'select',
            'placeholder': '所有项目',
            'width': '200px',
            'current_value': request.GET.getlist('project'),  # 多选值
            'options': [
                {'value': p.project_code, 'label': p.project_name}
                for p in Project.objects.all()
            ]
        }
    ]
    
    advanced_filter_groups = [
        {
            'title': '基本信息',
            'icon': 'fas fa-info-circle',
            'filters': [
                {
                    'name': 'procurement_code',
                    'label': '招采编号',
                    'type': 'text',
                    'placeholder': '输入招采编号',
                    'current_value': request.GET.get('procurement_code', '')
                },
                {
                    'name': 'project_name',
                    'label': '采购项目名称',
                    'type': 'text',
                    'placeholder': '输入采购项目名称',
                    'current_value': request.GET.get('project_name', '')
                },
                {
                    'name': 'procurement_unit',
                    'label': '采购单位',
                    'type': 'text',
                    'placeholder': '输入采购单位',
                    'current_value': request.GET.get('procurement_unit', '')
                },
                {
                    'name': 'procurement_category',
                    'label': '采购类别',
                    'type': 'text',
                    'placeholder': '输入采购类别',
                    'current_value': request.GET.get('procurement_category', '')
                },
                {
                    'name': 'winning_bidder',
                    'label': '中标单位',
                    'type': 'text',
                    'placeholder': '输入中标单位名称',
                    'current_value': request.GET.get('winning_bidder', '')
                }
            ]
        },
        {
            'title': '方式与审查',
            'icon': 'fas fa-tasks',
            'filters': [
                {
                    'name': 'procurement_method',
                    'label': '采购方式',
                    'type': 'text',
                    'placeholder': '输入采购方式',
                    'current_value': request.GET.get('procurement_method', '')
                },
                {
                    'name': 'qualification_review_method',
                    'label': '资格审查方式',
                    'type': 'text',
                    'placeholder': '输入资格审查方式',
                    'current_value': request.GET.get('qualification_review_method', '')
                },
                {
                    'name': 'bid_evaluation_method',
                    'label': '评标谈判方式',
                    'type': 'text',
                    'placeholder': '输入评标谈判方式',
                    'current_value': request.GET.get('bid_evaluation_method', '')
                },
                {
                    'name': 'bid_awarding_method',
                    'label': '定标方法',
                    'type': 'text',
                    'placeholder': '输入定标方法',
                    'current_value': request.GET.get('bid_awarding_method', '')
                }
            ]
        },
        {
            'title': '金额范围',
            'icon': 'fas fa-money-bill-wave',
            'filters': [
                {
                    'name': 'budget_amount',
                    'label': '采购预算金额',
                    'type': 'number',
                    'min_value': request.GET.get('budget_amount_min', ''),
                    'max_value': request.GET.get('budget_amount_max', '')
                },
                {
                    'name': 'winning_amount',
                    'label': '中标金额',
                    'type': 'number',
                    'min_value': request.GET.get('winning_amount_min', ''),
                    'max_value': request.GET.get('winning_amount_max', '')
                }
            ]
        },
        {
            'title': '日期范围',
            'icon': 'fas fa-calendar',
            'filters': [
                {
                    'name': 'announcement_release_date',
                    'label': '公告发布时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('announcement_release_date_start', ''),
                    'end_value': request.GET.get('announcement_release_date_end', '')
                },
                {
                    'name': 'registration_deadline',
                    'label': '报名截止时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('registration_deadline_start', ''),
                    'end_value': request.GET.get('registration_deadline_end', '')
                },
                {
                    'name': 'bid_opening_date',
                    'label': '开标时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('bid_opening_date_start', ''),
                    'end_value': request.GET.get('bid_opening_date_end', '')
                },
                {
                    'name': 'candidate_publicity_end_date',
                    'label': '候选人公示结束时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('candidate_publicity_end_date_start', ''),
                    'end_value': request.GET.get('candidate_publicity_end_date_end', '')
                },
                {
                    'name': 'result_publicity_release_date',
                    'label': '结果公示发布时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('result_publicity_release_date_start', ''),
                    'end_value': request.GET.get('result_publicity_release_date_end', '')
                },
                {
                    'name': 'planned_completion_date',
                    'label': '计划结束采购时间',
                    'type': 'daterange',
                    'start_value': request.GET.get('planned_completion_date_start', ''),
                    'end_value': request.GET.get('planned_completion_date_end', '')
                },
                {
                    'name': 'notice_issue_date',
                    'label': '中标通知书发放日期',
                    'type': 'daterange',
                    'start_value': request.GET.get('notice_issue_date_start', ''),
                    'end_value': request.GET.get('notice_issue_date_end', '')
                },
                {
                    'name': 'archive_date',
                    'label': '资料归档日期',
                    'type': 'daterange',
                    'start_value': request.GET.get('archive_date_start', ''),
                    'end_value': request.GET.get('archive_date_end', '')
                }
            ]
        },
        {
            'title': '其他信息',
            'icon': 'fas fa-info-circle',
            'filters': [
                {
                    'name': 'candidate_publicity_issue',
                    'label': '候选人公示期质疑情况',
                    'type': 'text',
                    'placeholder': '输入质疑情况关键词',
                    'current_value': request.GET.get('candidate_publicity_issue', '')
                },
                {
                    'name': 'non_bidding_explanation',
                    'label': '应招未招说明',
                    'type': 'text',
                    'placeholder': '输入应招未招说明关键词',
                    'current_value': request.GET.get('non_bidding_explanation', '')
                }
            ]
        }
    ]
    
    return {
        'quick_filters': quick_filters,
        'advanced_filter_groups': advanced_filter_groups,
        'search_query': request.GET.get('q', '')
    }


def get_payment_filter_config(request):
    """获取付款列表的筛选配置"""
    from .models import Project
    
    quick_filters = [
        {
            'name': 'project',
            'type': 'select',
            'placeholder': '所有项目',
            'width': '200px',
            'current_value': request.GET.getlist('project'),  # 改为多选
            'options': [
                {'value': p.project_code, 'label': p.project_name}
                for p in Project.objects.all()
            ]
        },
        {
            'name': 'is_settled',
            'type': 'select',
            'placeholder': '结算状态',
            'width': '120px',
            'current_value': request.GET.getlist('is_settled'),  # 改为多选
            'options': [
                {'value': 'true', 'label': '已结算'},
                {'value': 'false', 'label': '未结算'}
            ]
        }
    ]
    
    advanced_filter_groups = [
        {
            'title': '基本信息',
            'icon': 'fas fa-info-circle',
            'filters': [
                {
                    'name': 'payment_code',
                    'label': '付款编号',
                    'type': 'text',
                    'placeholder': '输入付款编号',
                    'current_value': request.GET.get('payment_code', '')
                },
                {
                    'name': 'contract_name',
                    'label': '合同名称',
                    'type': 'text',
                    'placeholder': '输入合同名称',
                    'current_value': request.GET.get('contract_name', '')
                }
            ]
        },
        {
            'title': '金额与日期',
            'icon': 'fas fa-calendar-dollar',
            'filters': [
                {
                    'name': 'payment_amount',
                    'label': '付款金额',
                    'type': 'number',
                    'min_value': request.GET.get('payment_amount_min', ''),
                    'max_value': request.GET.get('payment_amount_max', '')
                },
                {
                    'name': 'payment_date',
                    'label': '付款日期',
                    'type': 'daterange',
                    'start_value': request.GET.get('payment_date_start', ''),
                    'end_value': request.GET.get('payment_date_end', '')
                }
            ]
        }
    ]
    
    return {
        'quick_filters': quick_filters,
        'advanced_filter_groups': advanced_filter_groups,
        'search_query': request.GET.get('q', '')
    }
