"""
采购记录齐全性检查工具
根据采购方式分类检查必填字段的完整性
"""
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from decimal import Decimal


class ProcurementCompletenessChecker:
    """采购记录齐全性检查器"""
    
    def __init__(self, use_database=True):
        """
        初始化并加载配置
        
        Args:
            use_database: 是否从数据库加载配置（默认True），False则从YAML文件加载
        """
        self.use_database = use_database
        if use_database:
            self.config = self._load_config_from_db()
        else:
            self.config = self._load_config_from_yaml()
    
    def _load_config_from_db(self) -> dict:
        """从数据库加载齐全性配置"""
        from project.models_procurement_method_config import ProcurementMethodFieldConfig
        
        config = {}
        
        # 遍历所有采购方式类型
        for method_type, method_label in ProcurementMethodFieldConfig.METHOD_TYPE_CHOICES:
            # 获取该类型的必填字段
            required_fields = ProcurementMethodFieldConfig.get_required_fields(method_type)
            
            # 获取该类型对应的采购方式值（从YAML配置映射）
            yaml_config = self._load_config_from_yaml()
            procurement_method_values = yaml_config.get(method_type, {}).get('procurement_method_values', [])
            
            config[method_type] = {
                'label': method_label,
                'procurement_method_values': procurement_method_values,
                'required_fields': required_fields
            }
        
        return config
    
    def _load_config_from_yaml(self) -> dict:
        """从YAML文件加载齐全性配置（备用方案）"""
        config_path = Path(__file__).parent.parent / 'configs' / 'procurement_completeness_config.yml'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)['procurement_completeness']
        except Exception as e:
            raise RuntimeError(f"无法加载采购齐全性配置文件: {e}")
    
    def get_procurement_type(self, procurement_method: str) -> str:
        """
        根据采购方式判断采购类型
        
        Args:
            procurement_method: 采购方式字符串
            
        Returns:
            采购类型键名: strategic_procurement, direct_commission, single_source, other_methods
        """
        if not procurement_method:
            return 'other_methods'
        
        # 遍历所有配置，查找匹配的采购方式
        for type_key, type_config in self.config.items():
            if procurement_method in type_config['procurement_method_values']:
                return type_key
        
        # 默认归类为其他采购方式
        return 'other_methods'
    
    def get_type_label(self, type_key: str) -> str:
        """
        获取采购类型的显示标签
        
        Args:
            type_key: 采购类型键名
            
        Returns:
            显示标签
        """
        return self.config.get(type_key, {}).get('label', type_key)
    
    def get_required_fields(self, type_key: str) -> List[str]:
        """
        获取指定采购类型的必填字段列表
        
        Args:
            type_key: 采购类型键名
            
        Returns:
            必填字段名列表
        """
        return self.config.get(type_key, {}).get('required_fields', [])
    
    def check_field_filled(self, value) -> bool:
        """
        检查字段值是否已填写
        
        Args:
            value: 字段值
            
        Returns:
            True表示已填写，False表示未填写
        """
        # None 或空字符串视为未填写
        if value is None or value == '':
            return False
        
        # 数值类型的0也视为已填写（因为可能是有效的业务数据）
        if isinstance(value, (int, float, Decimal)):
            return True
        
        # 字符串去空格后判断
        if isinstance(value, str):
            return value.strip() != ''
        
        # 其他类型（日期、布尔等）只要不是None就算已填写
        return True
    
    def check_completeness(self, procurement_obj) -> Dict[str, any]:
        """
        检查单条采购记录的齐全性
        
        Args:
            procurement_obj: Procurement模型实例
            
        Returns:
            字典包含:
            - type_key: 采购类型键名
            - type_label: 采购类型显示标签
            - required_count: 必填字段总数
            - filled_count: 已填写字段数
            - completeness_rate: 齐全率(0-100)
            - missing_fields: 缺失字段列表
        """
        # 判断采购类型
        type_key = self.get_procurement_type(procurement_obj.procurement_method)
        type_label = self.get_type_label(type_key)
        
        # 获取必填字段
        required_fields = self.get_required_fields(type_key)
        required_count = len(required_fields)
        
        # 检查每个字段
        filled_count = 0
        missing_fields = []
        
        for field_name in required_fields:
            try:
                value = getattr(procurement_obj, field_name, None)
                if self.check_field_filled(value):
                    filled_count += 1
                else:
                    missing_fields.append(field_name)
            except AttributeError:
                # 字段不存在也算缺失
                missing_fields.append(field_name)
        
        # 计算齐全率
        completeness_rate = (filled_count / required_count * 100) if required_count > 0 else 100.0
        
        return {
            'type_key': type_key,
            'type_label': type_label,
            'required_count': required_count,
            'filled_count': filled_count,
            'completeness_rate': round(completeness_rate, 2),
            'missing_fields': missing_fields,
        }
    
    def calculate_type_statistics(self, procurement_queryset) -> Dict[str, Dict]:
        """
        计算各采购类型的齐全性统计
        
        Args:
            procurement_queryset: Procurement查询集
            
        Returns:
            字典格式:
            {
                'strategic_procurement': {
                    'label': '战采结果应用',
                    'total_count': 10,
                    'total_required': 80,
                    'total_filled': 72,
                    'completeness_rate': 90.0,
                    'records': [...]  # 明细记录
                },
                ...
                'overall': {
                    'total_count': 50,
                    'total_required': 500,
                    'total_filled': 450,
                    'completeness_rate': 90.0
                }
            }
        """
        # 初始化各类型的统计
        stats = {}
        for type_key, type_config in self.config.items():
            stats[type_key] = {
                'type_key': type_key,
                'label': type_config['label'],
                'total_count': 0,
                'total_required': 0,
                'total_filled': 0,
                'completeness_rate': 0.0,
                'records': []
            }
        
        # 遍历所有采购记录
        overall_count = 0
        overall_required = 0
        overall_filled = 0
        
        for procurement in procurement_queryset:
            result = self.check_completeness(procurement)
            type_key = result['type_key']
            
            # 累加到对应类型
            if type_key in stats:
                stats[type_key]['total_count'] += 1
                stats[type_key]['total_required'] += result['required_count']
                stats[type_key]['total_filled'] += result['filled_count']
                stats[type_key]['records'].append({
                    'procurement_code': procurement.procurement_code,
                    'project_name': procurement.project_name,
                    'procurement_method': procurement.procurement_method,
                    'completeness_rate': result['completeness_rate'],
                    'missing_fields': result['missing_fields']
                })
            
            # 累加到总体统计
            overall_count += 1
            overall_required += result['required_count']
            overall_filled += result['filled_count']
        
        # 计算各类型的齐全率
        for type_key in stats:
            if stats[type_key]['total_required'] > 0:
                rate = (stats[type_key]['total_filled'] / stats[type_key]['total_required']) * 100
                stats[type_key]['completeness_rate'] = round(rate, 2)
        
        # 添加总体统计
        overall_rate = (overall_filled / overall_required * 100) if overall_required > 0 else 100.0
        stats['overall'] = {
            'label': '总体',
            'total_count': overall_count,
            'total_required': overall_required,
            'total_filled': overall_filled,
            'completeness_rate': round(overall_rate, 2)
        }
        
        return stats
    
    def get_all_type_keys(self) -> List[str]:
        """获取所有采购类型的键名列表"""
        return list(self.config.keys())
    
    def get_all_type_labels(self) -> List[str]:
        """获取所有采购类型的显示标签列表"""
        return [config['label'] for config in self.config.values()]