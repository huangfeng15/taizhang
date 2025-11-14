"""监控服务配置 - 遵循开放封闭原则（OCP）"""

# 归档规则配置
ARCHIVE_RULES = {
    'procurement': {
        'deadline_days': 40,
        'severity_thresholds': [30, 16, 1],  # 严重/中度/轻微
        'date_field': 'result_publicity_release_date',
        'archive_field': 'archive_date',
        'code_field': 'procurement_code',
        'name_field': 'project_name',
        'person_field': 'procurement_officer',
        'label': '采购'
    },
    'contract': {
        'deadline_days': 30,
        'severity_thresholds': [30, 16, 1],
        'date_field': 'signing_date',
        'archive_field': 'archive_date',
        'code_field': 'contract_code',
        'name_field': 'contract_name',
        'person_field': 'contract_officer',
        'label': '合同'
    },
    'settlement': {
        'deadline_days': 30,
        'severity_thresholds': [30, 16, 1],
        'date_field': 'completion_date',
        'archive_field': 'archive_date',
        'code_field': 'contract__contract_code',
        'name_field': 'contract__contract_name',
        'person_field': 'contract__contract_officer',
        'label': '结算'
    }
}

# 严重程度配置
SEVERITY_CONFIG = {
    'severe': {'label': '严重逾期', 'icon': '🔴', 'class': 'danger'},
    'moderate': {'label': '中度逾期', 'icon': '🟠', 'class': 'warning'},
    'minor': {'label': '轻微逾期', 'icon': '🟡', 'class': 'info'},
    'pending': {'label': '待归档', 'icon': '🔵', 'class': 'secondary'},
    'completed': {'label': '已完成', 'icon': '✅', 'class': 'success'}
}

# 更新监控规则配置
UPDATE_RULES = {
    'procurement': {
        'event_field': 'result_publicity_release_date',
        'deadline_rule': 'next_month_end',
        'code_field': 'procurement_code',
        'name_field': 'project_name',
        'person_field': 'procurement_officer',
        'label': '采购'
    },
    'contract': {
        'event_field': 'signing_date',
        'deadline_rule': 'next_month_end',
        'code_field': 'contract_code',
        'name_field': 'contract_name',
        'person_field': 'contract_officer',
        'label': '合同'
    },
    'payment': {
        'event_field': 'payment_date',
        'deadline_rule': 'next_month_end',
        'code_field': 'payment_code',
        'name_field': 'contract__contract_name',
        'person_field': 'contract__contract_officer',
        'label': '付款'
    },
    'settlement': {
        'event_field': 'completion_date',
        'deadline_rule': 'next_month_end',
        'code_field': 'contract__contract_code',
        'name_field': 'contract__contract_name',
        'person_field': 'contract__contract_officer',
        'label': '结算'
    }
}

# 工作量统计配置
WORKLOAD_CONFIG = {
    'procurement': {
        'date_field': 'result_publicity_release_date',
        'person_field': 'procurement_officer',
        'code_field': 'procurement_code',
        'name_field': 'project_name',
        'label': '采购'
    },
    'contract': {
        'date_field': 'signing_date',
        'person_field': 'contract_officer',
        'code_field': 'contract_code',
        'name_field': 'contract_name',
        'label': '合同'
    },
    'payment': {
        'date_field': 'payment_date',
        'person_field': 'contract__contract_officer',
        'code_field': 'payment_code',
        'name_field': 'contract__contract_name',
        'label': '付款'
    },
    'settlement': {
        'date_field': 'completion_date',
        'person_field': 'contract__contract_officer',
        'code_field': 'contract__contract_code',
        'name_field': 'contract__contract_name',
        'label': '结算'
    }
}

# 工作周期监控规则配置
CYCLE_RULES = {
    'procurement': {
        # 采购周期：需求书审批完成 → 结果公示完成
        'start_field': 'requirement_approval_date',
        'end_field': 'result_publicity_release_date',
        'person_field': 'procurement_officer',
        'code_field': 'procurement_code',
        'name_field': 'project_name',
        'label': '采购周期',
        # 按采购方式的规定周期（天）
        'deadline_map': {
            '直接采购': 15,
            '战采结果应用': 15,
            '单一来源': 25,
            '询价': 35,
            '竞价': 35,
            '比价': 35,
            '竞争性谈判': 35,
            '公开招标': 45,
            '邀请招标': 45,
        },
        'default_deadline': 45,  # 默认规定周期
        # 超期严重程度阈值（超期天数）
        'severity_thresholds': {
            'severe': 30,    # 超期30天以上为严重
            'moderate': 15,  # 超期15-30天为中度
            'mild': 1        # 超期1-15天为轻微
        }
    },
    'contract': {
        # 合同周期：结果公示完成 → 合同签订
        'start_field': 'procurement__result_publicity_release_date',
        'end_field': 'signing_date',
        'person_field': 'contract_officer',
        'code_field': 'contract_code',
        'name_field': 'contract_name',
        'label': '合同周期',
        'deadline_days': 30,  # 统一规定周期30天（结果公示后30天）
        # 超期严重程度阈值（超期天数）
        'severity_thresholds': {
            'severe': 30,    # 超期30天以上为严重
            'moderate': 15,  # 超期15-30天为中度
            'mild': 1        # 超期1-15天为轻微
        }
    }
}
