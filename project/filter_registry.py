"""
筛选器注册中心
动态管理各模块的筛选器配置
遵循 OCP 原则：对扩展开放，对修改封闭
"""
from typing import Dict, List, Any
from project.enums import (
    ProcurementMethod,
    ContractSource,
    FilePositioning,
    ProcurementCategory,
    QualificationReviewMethod,
    BidEvaluationMethod,
    BidAwardingMethod
)


class FilterRegistry:
    """筛选器注册中心"""
    
    def __init__(self):
        self._filters = {}
    
    def register(self, module_name: str, filters: List[Dict[str, Any]]):
        """
        注册筛选器
        
        Args:
            module_name: 模块名称
            filters: 筛选器配置列表
        """
        self._filters[module_name] = filters
    
    def get_filters(self, module_name: str) -> List[Dict[str, Any]]:
        """获取指定模块的筛选器配置"""
        return self._filters.get(module_name, [])
    
    def get_all_modules(self) -> List[str]:
        """获取所有已注册的模块"""
        return list(self._filters.keys())


# 全局注册实例
filter_registry = FilterRegistry()


# 注册采购模块筛选器
filter_registry.register('procurement', [
    {
        'key': 'procurement_method',
        'label': '采购方式',
        'type': 'select',
        'enum': ProcurementMethod,
        'field': 'procurement_method'
    },
    {
        'key': 'procurement_category',
        'label': '采购类别',
        'type': 'select',
        'enum': ProcurementCategory,
        'field': 'procurement_category'
    },
    {
        'key': 'qualification_review_method',
        'label': '资格审查方式',
        'type': 'select',
        'enum': QualificationReviewMethod,
        'field': 'qualification_review_method'
    },
    {
        'key': 'bid_evaluation_method',
        'label': '评标谈判方式',
        'type': 'select',
        'enum': BidEvaluationMethod,
        'field': 'bid_evaluation_method'
    },
    {
        'key': 'bid_awarding_method',
        'label': '定标方法',
        'type': 'select',
        'enum': BidAwardingMethod,
        'field': 'bid_awarding_method'
    },
    {
        'key': 'budget_amount',
        'label': '预算金额',
        'type': 'range',
        'field': 'budget_amount',
        'data_type': 'decimal'
    },
    {
        'key': 'winning_amount',
        'label': '中标金额',
        'type': 'range',
        'field': 'winning_amount',
        'data_type': 'decimal'
    },
    {
        'key': 'result_publicity_release_date',
        'label': '结果公示发布时间',
        'type': 'date_range',
        'field': 'result_publicity_release_date'
    }
])


# 注册合同模块筛选器
filter_registry.register('contract', [
    {
        'key': 'file_positioning',
        'label': '文件定位',
        'type': 'select',
        'enum': FilePositioning,
        'field': 'file_positioning'
    },
    {
        'key': 'contract_source',
        'label': '合同来源',
        'type': 'select',
        'enum': ContractSource,
        'field': 'contract_source'
    },
    {
        'key': 'contract_amount',
        'label': '合同金额',
        'type': 'range',
        'field': 'contract_amount',
        'data_type': 'decimal'
    },
    {
        'key': 'signing_date',
        'label': '签订日期',
        'type': 'date_range',
        'field': 'signing_date'
    },
    {
        'key': 'has_settlement',
        'label': '结算状态',
        'type': 'boolean',
        'field': 'has_settlement',
        'options': [
            {'value': 'true', 'label': '已结算'},
            {'value': 'false', 'label': '未结算'}
        ]
    }
])


# 注册付款模块筛选器
filter_registry.register('payment', [
    {
        'key': 'is_settled',
        'label': '结算状态',
        'type': 'boolean',
        'field': 'is_settled',
        'options': [
            {'value': 'true', 'label': '已结算'},
            {'value': 'false', 'label': '未结算'}
        ]
    },
    {
        'key': 'payment_amount',
        'label': '付款金额',
        'type': 'range',
        'field': 'payment_amount',
        'data_type': 'decimal'
    },
    {
        'key': 'payment_date',
        'label': '付款日期',
        'type': 'date_range',
        'field': 'payment_date'
    }
])