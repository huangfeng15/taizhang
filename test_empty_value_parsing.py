"""
测试空值标记的解析
验证 "-" 和 "/" 是否正确被识别为空值
"""
import sys
import os
import django

# 设置UTF-8输出编码（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from datetime import date
from procurement.management.commands.import_excel import Command

def test_parse_decimal():
    """测试数值解析"""
    cmd = Command()
    
    test_cases = [
        # (输入值, 期望输出, 描述)
        ('100.5', Decimal('100.5'), '正常数值'),
        ('1,000.50', Decimal('1000.50'), '带千分位的数值'),
        ('/', None, '斜杠作为空值'),
        ('-', None, '减号作为空值'),
        ('—', None, '长破折号作为空值'),
        ('无', None, '中文"无"作为空值'),
        ('N/A', None, '英文N/A作为空值'),
        ('n/a', None, '小写n/a作为空值'),
        ('', None, '空字符串'),
        (None, None, 'None值'),
        ('   ', None, '空白字符'),
    ]
    
    print("=" * 60)
    print("测试数值解析 (_parse_decimal)")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for input_val, expected, desc in test_cases:
        result = cmd._parse_decimal(input_val)
        status = "[OK]" if result == expected else "[FAIL]"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {desc:20s} | 输入: {str(input_val):10s} | 期望: {str(expected):15s} | 实际: {str(result):15s}")
    
    print(f"\n通过: {passed}/{len(test_cases)}, 失败: {failed}/{len(test_cases)}")
    return failed == 0

def test_parse_date():
    """测试日期解析"""
    cmd = Command()
    
    test_cases = [
        # (输入值, 期望输出, 描述)
        ('2024-01-15', date(2024, 1, 15), '标准日期格式'),
        ('2024/01/15', date(2024, 1, 15), '斜杠日期格式'),
        ('2024年01月15日', date(2024, 1, 15), '中文日期格式'),
        ('2024-01', date(2024, 1, 1), '年月格式'),
        ('/', None, '斜杠作为空值'),
        ('-', None, '减号作为空值'),
        ('—', None, '长破折号作为空值'),
        ('无', None, '中文"无"作为空值'),
        ('N/A', None, '英文N/A作为空值'),
        ('n/a', None, '小写n/a作为空值'),
        ('', None, '空字符串'),
        (None, None, 'None值'),
        ('   ', None, '空白字符'),
    ]
    
    print("\n" + "=" * 60)
    print("测试日期解析 (_parse_date)")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for input_val, expected, desc in test_cases:
        result = cmd._parse_date(input_val)
        status = "[OK]" if result == expected else "[FAIL]"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {desc:20s} | 输入: {str(input_val):15s} | 期望: {str(expected):15s} | 实际: {str(result):15s}")
    
    print(f"\n通过: {passed}/{len(test_cases)}, 失败: {failed}/{len(test_cases)}")
    return failed == 0

if __name__ == '__main__':
    print("\n空值标记解析测试\n")
    
    decimal_ok = test_parse_decimal()
    date_ok = test_parse_date()
    
    print("\n" + "=" * 60)
    print("总体测试结果")
    print("=" * 60)
    print(f"数值解析: {'通过' if decimal_ok else '失败'}")
    print(f"日期解析: {'通过' if date_ok else '失败'}")
    
    if decimal_ok and date_ok:
        print("\n[SUCCESS] 所有测试通过！")
        sys.exit(0)
    else:
        print("\n[ERROR] 部分测试失败")
        sys.exit(1)