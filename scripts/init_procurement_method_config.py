"""
初始化采购方式字段配置数据
从YAML配置文件读取默认配置，写入数据库
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from project.models_procurement_method_config import ProcurementMethodFieldConfig
from procurement.models import Procurement
import yaml
from pathlib import Path


def load_yaml_config():
    """从YAML文件加载默认配置"""
    config_path = Path(__file__).parent.parent / 'project' / 'configs' / 'procurement_completeness_config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)['procurement_completeness']


def init_configs():
    """初始化配置数据"""
    print("="*60)
    print("初始化采购方式字段配置")
    print("="*60)
    
    # 加载YAML配置
    yaml_config = load_yaml_config()
    
    # 映射YAML中的键名到数据库的method_type
    method_type_mapping = {
        'strategic_procurement': ProcurementMethodFieldConfig.STRATEGIC_PROCUREMENT,
        'direct_commission': ProcurementMethodFieldConfig.DIRECT_COMMISSION,
        'single_source': ProcurementMethodFieldConfig.SINGLE_SOURCE,
        'other_methods': ProcurementMethodFieldConfig.OTHER_METHODS,
    }
    
    total_created = 0
    total_updated = 0
    
    # 遍历YAML配置
    for yaml_key, config_data in yaml_config.items():
        method_type = method_type_mapping.get(yaml_key)
        if not method_type:
            continue
        
        method_label = config_data['label']
        required_fields = config_data.get('required_fields', [])
        
        print(f"\n处理：{method_label}")
        print(f"  必填字段数：{len(required_fields)}")
        
        # 为每个字段创建配置
        for idx, field_name in enumerate(required_fields):
            try:
                # 获取字段的verbose_name
                field = Procurement._meta.get_field(field_name)
                field_label = field.verbose_name
            except Exception:
                field_label = field_name
                print(f"    警告：字段 {field_name} 不存在于Procurement模型")
            
            # 创建或更新配置
            obj, created = ProcurementMethodFieldConfig.objects.update_or_create(
                method_type=method_type,
                field_name=field_name,
                defaults={
                    'field_label': field_label,
                    'is_required': True,  # YAML中列出的都是必填字段
                    'sort_order': idx
                }
            )
            
            if created:
                total_created += 1
            else:
                total_updated += 1
        
        # 统计该类型的配置
        count = ProcurementMethodFieldConfig.objects.filter(method_type=method_type).count()
        print(f"  数据库中配置数：{count}")
    
    print("\n" + "="*60)
    print(f"初始化完成！")
    print(f"  新创建：{total_created} 条")
    print(f"  已更新：{total_updated} 条")
    print("="*60)
    
    # 显示最终统计
    print("\n最终统计：")
    for method_type, method_label in ProcurementMethodFieldConfig.METHOD_TYPE_CHOICES:
        total = ProcurementMethodFieldConfig.objects.filter(method_type=method_type).count()
        required = ProcurementMethodFieldConfig.objects.filter(
            method_type=method_type,
            is_required=True
        ).count()
        print(f"  {method_label}：共 {total} 个字段，必填 {required} 个")


if __name__ == '__main__':
    init_configs()