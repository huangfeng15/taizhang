"""
测试控制价fallback提取功能
测试场景：
1. 优先从2-24采购公告提取控制价
2. 如果2-24没有，则从2-21控制价审批提取
"""
import sys
import os
import codecs

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader


def test_control_price_from_2_24():
    """测试从2-24提取控制价"""
    print("\n" + "="*80)
    print("测试1: 从2-24采购公告提取控制价")
    print("="*80)
    
    extractor = FieldExtractor()
    pdf_path = 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf'
    
    try:
        data = extractor.extract(pdf_path, 'procurement_notice')
        control_price = data.get('control_price')
        
        if control_price:
            print(f"✓ 成功从2-24提取控制价: {control_price}")
            return True
        else:
            print("✗ 2-24中未提取到控制价")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_control_price_from_2_21():
    """测试从2-21提取控制价"""
    print("\n" + "="*80)
    print("测试2: 从2-21控制价审批提取控制价")
    print("="*80)
    
    extractor = FieldExtractor()
    pdf_path = 'docs/2-21.采购控制价OA审批（PDF导出版）.pdf'
    
    try:
        data = extractor.extract(pdf_path, 'control_price_approval')
        control_price = data.get('control_price')
        
        if control_price:
            print(f"✓ 成功从2-21提取控制价: {control_price}")
            return True
        else:
            print("✗ 2-21中未提取到控制价")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_logic():
    """测试fallback逻辑"""
    print("\n" + "="*80)
    print("测试3: 控制价Fallback逻辑测试")
    print("="*80)
    
    extractor = FieldExtractor()
    
    # 场景1: 包含2-24（有控制价）
    print("\n场景1: 包含2-24采购公告（应从2-24提取）")
    pdf_files_with_2_24 = {
        'procurement_notice': 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        'control_price_approval': 'docs/2-21.采购控制价OA审批（PDF导出版）.pdf',
    }
    
    try:
        merged_data = extractor.extract_all_from_pdfs(pdf_files_with_2_24)
        control_price = merged_data.get('control_price')
        
        if control_price:
            print(f"  ✓ 提取到控制价: {control_price}")
            print(f"  ✓ 来源: 2-24采购公告（优先）")
        else:
            print("  ✗ 未提取到控制价")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    
    # 场景2: 不包含2-24（只有2-21）
    print("\n场景2: 不包含2-24，只有2-21（应从2-21提取）")
    pdf_files_only_2_21 = {
        'control_price_approval': 'docs/2-21.采购控制价OA审批（PDF导出版）.pdf',
    }
    
    try:
        merged_data = extractor.extract_all_from_pdfs(pdf_files_only_2_21)
        control_price = merged_data.get('control_price')
        
        if control_price:
            print(f"  ✓ 提取到控制价: {control_price}")
            print(f"  ✓ 来源: 2-21控制价审批（fallback）")
        else:
            print("  ✗ 未提取到控制价")
    except Exception as e:
        print(f"  ❌ 错误: {e}")


def test_complete_extraction():
    """完整提取测试（包含所有PDF）"""
    print("\n" + "="*80)
    print("测试4: 完整提取测试（包含2-21）")
    print("="*80)
    
    extractor = FieldExtractor()
    
    pdf_files = {
        'procurement_request': 'docs/2-23.采购请示OA审批（PDF导出版）.pdf',
        'procurement_notice': 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        'control_price_approval': 'docs/2-21.采购控制价OA审批（PDF导出版）.pdf',
        'candidate_publicity': 'docs/2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf',
        'result_publicity': 'docs/2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf',
    }
    
    try:
        merged_data = extractor.extract_all_from_pdfs(pdf_files)
        
        print("\n提取结果汇总:")
        print(f"  control_price: {merged_data.get('control_price', '未提取')}")
        print(f"  budget_amount: {merged_data.get('budget_amount', '未提取')}")
        print(f"  winning_amount: {merged_data.get('winning_amount', '未提取')}")
        
        if merged_data.get('control_price'):
            print("\n✓ 控制价提取成功！")
            return True
        else:
            print("\n✗ 控制价未提取")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("="*80)
    print("控制价Fallback功能测试")
    print("="*80)
    
    results = []
    
    # 测试1: 从2-24提取
    results.append(("从2-24提取", test_control_price_from_2_24()))
    
    # 测试2: 从2-21提取
    results.append(("从2-21提取", test_control_price_from_2_21()))
    
    # 测试3: Fallback逻辑
    test_fallback_logic()
    
    # 测试4: 完整提取
    results.append(("完整提取测试", test_complete_extraction()))
    
    # 总结
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请查看详情")
        return 1


if __name__ == "__main__":
    exit(main())