"""简单测试采购类别提取"""
import sys
sys.path.insert(0, '.')

from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader

config_loader = ConfigLoader()
extractor = FieldExtractor(config_loader)

pdf_path = 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf'
extracted = extractor.extract(pdf_path, 'procurement_notice')

category = extracted.get('procurement_category')
print(f"采购类别提取结果: {category}")
print(f"是否为标准值: {category in ['工程', '工程货物', '工程服务', '货物', '服务']}")
print(f"测试状态: {'成功' if category == '服务' else '失败'}")