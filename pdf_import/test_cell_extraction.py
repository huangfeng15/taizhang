"""
单元格检测提取测试脚本
测试基于pdfplumber单元格检测的键值对提取效果
"""
import sys
import os
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader
from pdf_import.utils.cell_detector import CellDetector
import json


def test_cell_detector_basic():
    """测试单元格检测器基本功能"""
    print("\n" + "="*80)
    print("测试1: 单元格检测器基本功能")
    print("="*80)
    
    # 测试PDF路径
    test_pdfs = [
        "docs/2-23.采购请示OA审批（PDF导出版）.pdf",
        "docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf",
        "docs/2-44.采购结果OA审批（PDF导出版）.pdf",
    ]
    
    for pdf_path in test_pdfs:
        if not Path(pdf_path).exists():
            print(f"❌ PDF不存在: {pdf_path}")
            continue
        
        print(f"\n📄 处理文件: {pdf_path}")
        
        try:
            # 初始化检测器
            detector = CellDetector(tolerance_x=5.0, tolerance_y=3.0)
            
            # 提取单元格
            cells = detector.extract_cells_from_pdf(pdf_path)
            print(f"✓ 检测到 {len(cells)} 个单元格")
            
            # 显示前10个单元格
            print("\n前10个单元格:")
            for i, cell in enumerate(cells[:10]):
                print(f"  {i+1}. '{cell.text[:30]}...' at ({cell.x0:.1f}, {cell.y0:.1f})")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()


def test_keyvalue_extraction():
    """测试键值对提取"""
    print("\n" + "="*80)
    print("测试2: 键值对提取（右侧/下方识别）")
    print("="*80)
    
    test_cases = [
        {
            "pdf": "docs/2-23.采购请示OA审批（PDF导出版）.pdf",
            "tests": [
                {"key": "申请人", "direction": "right", "expected_contains": ""},
                {"key": "部门", "direction": "right", "expected_contains": ""},
                {"key": "采购预算", "direction": "auto", "expected_contains": ""},
            ]
        },
        {
            "pdf": "docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf",
            "tests": [
                {"key": "项目名称", "direction": "auto", "expected_contains": ""},
                {"key": "采购方式", "direction": "right", "expected_contains": ""},
                {"key": "采购控制价", "direction": "below", "expected_contains": ""},
            ]
        },
    ]
    
    for case in test_cases:
        pdf_path = case["pdf"]
        
        if not Path(pdf_path).exists():
            print(f"\n❌ PDF不存在: {pdf_path}")
            continue
        
        print(f"\n📄 测试文件: {Path(pdf_path).name}")
        
        try:
            detector = CellDetector(tolerance_x=5.0, tolerance_y=3.0)
            detector.extract_cells_from_pdf(pdf_path)
            
            for test in case["tests"]:
                key = test["key"]
                direction = test["direction"]
                
                value = detector.extract_keyvalue_pair(key, direction=direction)
                
                if value:
                    print(f"  ✓ {key}: {value}")
                else:
                    print(f"  ❌ {key}: 未找到")
                    
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()


def test_field_extractor_integration():
    """测试字段提取器集成"""
    print("\n" + "="*80)
    print("测试3: 字段提取器集成测试（100%提取率验证）")
    print("="*80)
    
    # 定义测试用的PDF文件
    pdf_files = {
        'procurement_request': 'docs/2-23.采购请示OA审批（PDF导出版）.pdf',
        'procurement_notice': 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        'result_approval': 'docs/2-44.采购结果OA审批（PDF导出版）.pdf',
        'candidate_publicity': 'docs/2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf',
        'result_publicity': 'docs/2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf',
    }
    
    # 初始化提取器
    config_loader = ConfigLoader()
    extractor = FieldExtractor(config_loader)
    
    # 统计结果
    total_fields = 0
    extracted_fields = 0
    failed_fields = []
    
    print("\n开始提取所有自动提取字段...")
    
    for pdf_type, pdf_path in pdf_files.items():
        if not Path(pdf_path).exists():
            print(f"\n⚠️  跳过不存在的文件: {pdf_path}")
            continue
        
        print(f"\n📄 处理 {pdf_type}: {Path(pdf_path).name}")
        
        try:
            # 提取字段
            extracted = extractor.extract(pdf_path, pdf_type)
            
            # 统计结果
            for field_name, value in extracted.items():
                total_fields += 1
                if value is not None and str(value).strip():
                    extracted_fields += 1
                    print(f"  ✓ {field_name}: {value}")
                else:
                    failed_fields.append(f"{pdf_type}.{field_name}")
                    print(f"  ❌ {field_name}: 未提取")
                    
        except Exception as e:
            print(f"  ❌ 提取错误: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印统计结果
    print("\n" + "="*80)
    print("提取结果统计")
    print("="*80)
    print(f"总字段数: {total_fields}")
    print(f"成功提取: {extracted_fields}")
    print(f"提取失败: {len(failed_fields)}")
    print(f"提取成功率: {extracted_fields/total_fields*100:.1f}%" if total_fields > 0 else "N/A")
    
    if failed_fields:
        print("\n失败字段列表:")
        for field in failed_fields:
            print(f"  - {field}")
    
    return extracted_fields == total_fields


def test_all_auto_fields():
    """测试所有自动提取字段（最终验证）"""
    print("\n" + "="*80)
    print("测试4: 所有自动提取字段完整测试")
    print("="*80)
    
    # 所有需要自动提取的字段
    auto_extract_fields = [
        'project_name',
        'procurement_unit',
        'procurement_category',
        'procurement_platform',
        'procurement_method',
        'qualification_review_method',
        'bid_evaluation_method',
        'bid_awarding_method',
        'budget_amount',
        'control_price',
        'winning_amount',
        'procurement_officer',
        'demand_department',
        'demand_contact',
        'winning_bidder',
        'planned_completion_date',
        'requirement_approval_date',
        'announcement_release_date',
        'registration_deadline',
        'bid_opening_date',
        'candidate_publicity_end_date',
        'result_publicity_release_date',
    ]
    
    pdf_files = {
        'procurement_request': 'docs/2-23.采购请示OA审批（PDF导出版）.pdf',
        'procurement_notice': 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        'result_approval': 'docs/2-44.采购结果OA审批（PDF导出版）.pdf',
        'candidate_publicity': 'docs/2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf',
        'result_publicity': 'docs/2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf',
    }
    
    config_loader = ConfigLoader()
    extractor = FieldExtractor(config_loader)
    
    # 合并提取所有PDF
    print("\n合并提取所有PDF文件...")
    merged_data = extractor.extract_all_from_pdfs(pdf_files)
    
    # 验证所有自动字段
    print("\n" + "="*80)
    print("字段提取验证")
    print("="*80)
    
    success_count = 0
    fail_count = 0
    
    for field in auto_extract_fields:
        value = merged_data.get(field)
        if value and str(value).strip():
            print(f"✓ {field}: {value}")
            success_count += 1
        else:
            print(f"❌ {field}: 未提取")
            fail_count += 1
    
    # 最终统计
    total = len(auto_extract_fields)
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    print("\n" + "="*80)
    print("最终结果")
    print("="*80)
    print(f"总字段数: {total}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 恭喜！所有自动提取字段100%成功！")
    else:
        print(f"\n⚠️  还有 {fail_count} 个字段需要优化")
    
    return success_rate == 100


def main():
    """主测试函数"""
    print("="*80)
    print("PDF单元格检测提取测试")
    print("="*80)
    
    try:
        # 测试1: 基本单元格检测
        test_cell_detector_basic()
        
        # 测试2: 键值对提取
        test_keyvalue_extraction()
        
        # 测试3: 字段提取器集成
        test_field_extractor_integration()
        
        # 测试4: 所有自动字段完整测试
        all_success = test_all_auto_fields()
        
        print("\n" + "="*80)
        print("测试完成")
        print("="*80)
        
        if all_success:
            print("✓ 所有测试通过！")
            return 0
        else:
            print("⚠️  部分测试未通过，请查看上方详情")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())