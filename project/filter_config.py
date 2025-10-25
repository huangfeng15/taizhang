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
    file_positioning_values = request.GET.getlist('file_positioning')
    
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
            'name': 'file_positioning',
            'type': 'select',
            'placeholder': '所有文件定位',
            'width': '150px',
            'current_value': file_positioning_values,  # 多选值
            'options': [
                {'value': value, 'label': label}
                for value, label in Contract._meta.get_field('file_positioning').choices
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
                    'name': 'file_positioning',
                    'label': '文件定位',
                    'type': 'select',
                    'options': [
                        {'value': '主合同', 'label': '主合同'},
                        {'value': '补充协议', 'label': '补充协议'},
                        {'value': '解除协议', 'label': '解除协议'}
                    ],
                    'current_value': request.GET.getlist('file_positioning')  # 多选值
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
                    'name': 'contract_officer',
                    'label': '合同签订经办人',
                    'type': 'text',
                    'placeholder': '输入经办人姓名',
                    'current_value': request.GET.get('contract_officer', '')
                }
            ]
        },
        {
            'title': '甲方联系信息',
            'icon': 'fas fa-user-tie',
            'filters': [
                {
                    'name': 'party_a_legal_representative',
                    'label': '甲方法定代表人',
                    'type': 'text',
                    'placeholder': '输入法定代表人信息',
                    'current_value': request.GET.get('party_a_legal_representative', '')
                },
                {
                    'name': 'party_a_contact_person',
                    'label': '甲方联系人',
                    'type': 'text',
                    'placeholder': '输入联系人信息',
                    'current_value': request.GET.get('party_a_contact_person', '')
                },
                {
                    'name': 'party_a_manager',
                    'label': '甲方负责人',
                    'type': 'text',
                    'placeholder': '输入负责人信息',
                    'current_value': request.GET.get('party_a_manager', '')
                }
            ]
        },
        {
            'title': '乙方联系信息',
            'icon': 'fas fa-user-friends',
            'filters': [
                {
                    'name': 'party_b_legal_representative',
                    'label': '乙方法定代表人',
                    'type': 'text',
                    'placeholder': '输入法定代表人信息',
                    'current_value': request.GET.get('party_b_legal_representative', '')
                },
                {
                    'name': 'party_b_contact_person',
                    'label': '乙方联系人',
                    'type': 'text',
                    'placeholder': '输入联系人信息',
                    'current_value': request.GET.get('party_b_contact_person', '')
                },
                {
                    'name': 'party_b_manager',
                    'label': '乙方负责人',
                    'type': 'text',
                    'placeholder': '输入负责人信息',
                    'current_value': request.GET.get('party_b_manager', '')
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
                    'name': 'procurement_platform',
                    'label': '采购平台',
                    'type': 'text',
                    'placeholder': '输入采购平台',
                    'current_value': request.GET.get('procurement_platform', '')
                },
                {
                    'name': 'winning_bidder',
                    'label': '中标单位',
                    'type': 'text',
                    'placeholder': '输入中标单位名称',
                    'current_value': request.GET.get('winning_bidder', '')
                },
                {
                    'name': 'winning_contact',
                    'label': '中标单位联系人及方式',
                    'type': 'text',
                    'placeholder': '输入联系人及方式',
                    'current_value': request.GET.get('winning_contact', '')
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
            'title': '人员信息',
            'icon': 'fas fa-users',
            'filters': [
                {
                    'name': 'procurement_officer',
                    'label': '采购经办人',
                    'type': 'text',
                    'placeholder': '输入经办人姓名',
                    'current_value': request.GET.get('procurement_officer', '')
                },
                {
                    'name': 'demand_department',
                    'label': '需求部门',
                    'type': 'text',
                    'placeholder': '输入需求部门',
                    'current_value': request.GET.get('demand_department', '')
                },
                {
                    'name': 'demand_contact',
                    'label': '申请人联系电话（需求部门）',
                    'type': 'text',
                    'placeholder': '输入联系人及电话',
                    'current_value': request.GET.get('demand_contact', '')
                },
                {
                    'name': 'evaluation_committee',
                    'label': '评标委员会成员',
                    'type': 'text',
                    'placeholder': '输入委员会成员关键词',
                    'current_value': request.GET.get('evaluation_committee', '')
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
                    'name': 'control_price',
                    'label': '采购控制价',
                    'type': 'number',
                    'min_value': request.GET.get('control_price_min', ''),
                    'max_value': request.GET.get('control_price_max', '')
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
            'title': '担保信息',
            'icon': 'fas fa-shield-alt',
            'filters': [
                {
                    'name': 'bid_guarantee',
                    'label': '投标担保形式及金额',
                    'type': 'text',
                    'placeholder': '输入担保信息关键词',
                    'current_value': request.GET.get('bid_guarantee', '')
                },
                {
                    'name': 'bid_guarantee_return_date',
                    'label': '投标担保退回日期',
                    'type': 'daterange',
                    'start_value': request.GET.get('bid_guarantee_return_date_start', ''),
                    'end_value': request.GET.get('bid_guarantee_return_date_end', '')
                },
                {
                    'name': 'performance_guarantee',
                    'label': '履约担保形式及金额',
                    'type': 'text',
                    'placeholder': '输入担保信息关键词',
                    'current_value': request.GET.get('performance_guarantee', '')
                }
            ]
        },
        {
            'title': '日期范围',
            'icon': 'fas fa-calendar',
            'filters': [
                {
                    'name': 'requirement_approval_date',
                    'label': '采购需求书审批完成日期（OA）',
                    'type': 'daterange',
                    'start_value': request.GET.get('requirement_approval_date_start', ''),
                    'end_value': request.GET.get('requirement_approval_date_end', '')
                },
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


def resolve_monitoring_year(request):
    """统一解析监控类页面的年份筛选，支持默认当前年与“全部”选项。"""
    from datetime import datetime
    
    current_year_local = datetime.now().year
    year_param = request.GET.get('year')
    
    available_years = list(range(2019, current_year_local + 2))
    
    if year_param == 'all':
        return {
            'current_year': current_year_local,
            'available_years': available_years,
            'selected_year_value': 'all',
            'year_filter': None,
            'display_year': '全部'
        }
    
    if year_param and year_param.isdigit():
        year_int = int(year_param)
        return {
            'current_year': current_year_local,
            'available_years': available_years,
            'selected_year_value': year_param,
            'year_filter': year_int,
            'display_year': str(year_int)
        }
    
    # 默认使用当前年度
    return {
        'current_year': current_year_local,
        'available_years': available_years,
        'selected_year_value': str(current_year_local),
        'year_filter': current_year_local,
        'display_year': str(current_year_local)
    }


def get_monitoring_filter_config(request, year_context=None):
    """获取监控中心的筛选配置"""
    from .models import Project
    
    if year_context is None:
        year_context = resolve_monitoring_year(request)
    selected_project = request.GET.get('project', '')
    project_values = request.GET.getlist('project')
    if not project_values and selected_project:
        project_values = [selected_project]
    if not project_values:
        project_values = ['']
    
    projects = list(Project.objects.all().order_by('project_name'))
    
    quick_filters = [
        {
            'name': 'year',
            'type': 'select',
            'placeholder': '选择年份',
            'width': '130px',
            'current_value': year_context['selected_year_value'],
            'options': (
                [{'value': 'all', 'label': '全部年度'}] +
                [
                    {'value': str(year), 'label': f'{year}年'}
                    for year in year_context['available_years']
                ]
            )
        },
        {
            'name': 'project',
            'type': 'select',
            'placeholder': '所有项目',
            'width': '200px',
            'current_value': project_values,
            'options': [
                {'value': '', 'label': '全部项目'}
            ] + [
                {'value': p.project_code, 'label': p.project_name}
                for p in projects
            ]
        }
    ]
    
    # 监控中心暂不需要高级筛选
    advanced_filter_groups = []
    
    return {
        'quick_filters': quick_filters,
        'advanced_filter_groups': advanced_filter_groups,
        'search_query': request.GET.get('q', ''),
        'available_years': year_context['available_years'],
        'current_year': year_context['current_year'],
        'selected_year_value': year_context['selected_year_value'],
        'display_year': year_context['display_year'],
        'projects': projects,
        'selected_project_value': selected_project,
        'year_filter': year_context['year_filter'],
    }



