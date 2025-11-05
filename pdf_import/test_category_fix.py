"""测试修复后的采购类别提取"""
import sys
sys.path.insert(0, '.')

from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader

# 初始化提取器
config_loader = ConfigLoader()
extractor = FieldExtractor(config_loader)

# 测试PDF
pdf_path = 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf'

print("=" * 80)
print("测试采购类别提取（修复后）")
print("=" * 80)

# 提取数据
extracted_data = extractor.extract(pdf_path, 'procurement_notice')

print("\n提取结果:")
print("-" * 80)
for field, value in extracted_data.items():
    if value:
        print(f"{field}: {value}")

print("\n" + "=" * 80)
print("采购类别字段详情:")
print("=" * 80)
category = extracted_data.get('procurement_category')
print(f"提取值: {category}")
print(f"是否为空: {category is None or category == ''}")
print(f"是否在标准值中: {category in ['工程', '工程货物', '工程服务', '货物', '服务']}")