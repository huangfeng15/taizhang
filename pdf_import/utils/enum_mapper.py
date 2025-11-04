"""枚举映射工具"""
from typing import Dict, Any


class EnumMapper:
    """枚举值映射器"""
    
    def __init__(self):
        """初始化映射器"""
        self.alias_map = {
            # 采购类别
            '地产营销': '服务',
            '服务类': '服务',
            
            # 采购方式
            '询价': '公开询价',
            '公开竞争性谈判': '公开谈判',
            
            # 评标方式
            '综合评估法': '综合评分法',
            '最低评标价法': '最低价法',
        }
    
    def map(self, field_name: str, value: str) -> Dict[str, Any]:
        """
        映射枚举值
        
        Args:
            field_name: 字段名
            value: 原始值
            
        Returns:
            映射结果字典
        """
        if not value:
            return {
                'value': None,
                'original': value,
                'confidence': 0.0,
                'requires_manual': True,
                'suggestions': [],
                'mapping_method': 'failed'
            }
        
        # 精确匹配
        if value not in self.alias_map:
            return {
                'value': value,
                'original': value,
                'confidence': 1.0,
                'requires_manual': False,
                'suggestions': [],
                'mapping_method': 'exact'
            }
        
        # 别名映射
        mapped_value = self.alias_map[value]
        return {
            'value': mapped_value,
            'original': value,
            'confidence': 0.95,
            'requires_manual': False,
            'suggestions': [],
            'mapping_method': 'alias'
        }