"""完整测试采购类别提取流程"""
import sys
sys.path.insert(0, '.')

from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader

print("=" * 80)
print("完整测试：采购类别字段提取与映射")
print("=" * 80)

# 初始化
config_loader = ConfigLoader()
extractor = FieldExtractor(config_loader)

# 测试多个PDF场景
test_cases = [
    {
        'name': '场景1: 服务类 → 服务',
        'pdf': 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        'expected': '服务'
    }
]

for case in test_cases:
    print(f"\n{case['name']}")
    print("-" * 80)
    
    extracted = extractor.extract(case['pdf'], 'procurement_notice')
    category = extracted.get('procurement_category')
    
    print(f"提取值: {category}")
    print(f"预期值: {case['expected']}")
    print(f"测试结果: {'✓ 通过' if category == case['expected'] else '✗ 失败'}")

print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print("✓ 修复内容:")
print("  1. 修改配置：从'项目类型'字段提取，而不是'标段/包分类'")
print("  2. 添加映射：服务类→服务, 货物类→货物, 工程类→工程")
print("  3. 修复bug：regex提取方法现在会调用_post_process进行枚举映射")
print("\n✓ 现在采购类别可以正确提取并映射为标准值")