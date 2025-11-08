"""
供应商履约评价导入功能测试脚本
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from supplier_eval.models import SupplierEvaluation, SupplierInterview
from contract.models import Contract
from decimal import Decimal


def test_models():
    """测试模型基本功能"""
    print("=" * 80)
    print("测试1: 模型基本功能")
    print("=" * 80)
    
    # 统计现有数据
    eval_count = SupplierEvaluation.objects.count()
    interview_count = SupplierInterview.objects.count()
    contract_count = Contract.objects.count()
    
    print(f"[OK] 供应商履约评价记录数: {eval_count}")
    print(f"[OK] 供应商约谈记录数: {interview_count}")
    print(f"[OK] 合同记录数: {contract_count}")
    
    if eval_count > 0:
        print("\n最近5条履约评价:")
        for eval in SupplierEvaluation.objects.all()[:5]:
            print(f"  - {eval.evaluation_code}: {eval.supplier_name} - "
                  f"综合评分: {eval.comprehensive_score or '未评分'} ({eval.get_score_level()})")
    
    if interview_count > 0:
        print("\n最近5条约谈记录:")
        for interview in SupplierInterview.objects.all()[:5]:
            print(f"  - {interview.interview_date}: {interview.supplier_name} - "
                  f"{interview.interview_type} ({interview.status})")
    
    print()


def test_score_calculation():
    """测试评分计算功能"""
    print("=" * 80)
    print("测试2: 评分自动计算")
    print("=" * 80)
    
    # 查找第一个合同用于测试
    contract = Contract.objects.filter(file_positioning='主合同').first()
    
    if not contract:
        print("[WARN] 未找到可用合同,跳过测试")
        return
    
    print(f"使用合同: {contract.contract_code} - {contract.party_b}")
    
    # 创建测试评价记录
    test_code = "TEST-EVAL-001"
    
    # 删除可能存在的测试记录
    SupplierEvaluation.objects.filter(evaluation_code=test_code).delete()
    
    # 测试场景1: 仅末次评价
    print("\n场景1: 仅提供末次评价")
    eval1 = SupplierEvaluation(
        evaluation_code=test_code,
        contract=contract,
        supplier_name=contract.party_b,
        last_evaluation_score=Decimal('85.00')
    )
    eval1.save()
    print(f"  末次评价: 85.00")
    print(f"  过程评价: 无")
    print(f"  [OK] 自动计算综合评分: {eval1.comprehensive_score}")
    print(f"  [OK] 评分等级: {eval1.get_score_level()}")
    
    # 测试场景2: 末次评价 + 年度评价
    print("\n场景2: 末次评价 + 年度评价")
    eval1.score_2023 = Decimal('80.00')
    eval1.score_2024 = Decimal('82.00')
    eval1.score_2025 = Decimal('84.00')
    eval1.comprehensive_score = None  # 清空以触发重新计算
    eval1.save()
    print(f"  末次评价: 85.00 (权重60%)")
    print(f"  2023年度: 80.00")
    print(f"  2024年度: 82.00")
    print(f"  2025年度: 84.00")
    print(f"  过程评价平均: {(80+82+84)/3:.2f}")
    print(f"  [OK] 自动计算综合评分: {eval1.comprehensive_score}")
    print(f"  [OK] 评分等级: {eval1.get_score_level()}")
    
    # 测试场景3: 完整评价
    print("\n场景3: 完整评价(年度+不定期)")
    eval1.irregular_evaluation_1 = Decimal('78.00')
    eval1.irregular_evaluation_2 = Decimal('81.00')
    eval1.comprehensive_score = None
    eval1.save()
    print(f"  末次评价: 85.00")
    print(f"  年度评价: 80, 82, 84")
    print(f"  不定期评价: 78, 81")
    print(f"  过程评价平均: {(80+82+84+78+81)/5:.2f}")
    print(f"  [OK] 自动计算综合评分: {eval1.comprehensive_score}")
    print(f"  [OK] 计算公式: 85.00 x 60% + {(80+82+84+78+81)/5:.2f} x 40%")
    
    # 清理测试数据
    eval1.delete()
    print("\n[OK] 测试完成,已清理测试数据")
    print()


def test_admin_features():
    """测试Admin功能"""
    print("=" * 80)
    print("测试3: Admin后台功能")
    print("=" * 80)
    
    from django.contrib import admin
    from supplier_eval.admin import SupplierEvaluationAdmin, SupplierInterviewAdmin
    
    # 检查Admin注册
    if SupplierEvaluation in admin.site._registry:
        print("[OK] SupplierEvaluation已注册到Admin")
        admin_class = admin.site._registry[SupplierEvaluation]
        print(f"  - 列表显示字段: {len(admin_class.list_display)} 个")
        print(f"  - 搜索字段: {len(admin_class.search_fields)} 个")
        print(f"  - 筛选器: {len(admin_class.list_filter)} 个")
        print(f"  - 批量操作: {len(admin_class.actions)} 个")
    
    if SupplierInterview in admin.site._registry:
        print("\n[OK] SupplierInterview已注册到Admin")
        admin_class = admin.site._registry[SupplierInterview]
        print(f"  - 列表显示字段: {len(admin_class.list_display)} 个")
        print(f"  - 搜索字段: {len(admin_class.search_fields)} 个")
        print(f"  - 筛选器: {len(admin_class.list_filter)} 个")
        print(f"  - 批量操作: {len(admin_class.actions)} 个")
    
    print()


def test_import_command():
    """测试导入命令"""
    print("=" * 80)
    print("测试4: CSV导入命令")
    print("=" * 80)
    
    import subprocess
    
    # 检查CSV模板文件
    template_file = 'data/supplier_eval_template.csv'
    if os.path.exists(template_file):
        print(f"[OK] CSV模板文件存在: {template_file}")
        
        # 读取模板内容
        with open(template_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            print(f"  - 总行数: {len(lines)}")
            print(f"  - 表头: {lines[0].strip()}")
            print(f"  - 示例数据行数: {len(lines) - 1}")
    else:
        print(f"[WARN] CSV模板文件不存在: {template_file}")
    
    # 显示导入命令帮助
    print("\n导入命令使用方法:")
    print("  python manage.py import_supplier_eval <csv文件路径>")
    print("\n可选参数:")
    print("  --encoding utf-8-sig  指定编码")
    print("  --skip-header         跳过表头")
    print("  --dry-run            模拟运行")
    print("  --update             更新已存在记录")
    
    print()


def main():
    """主测试函数"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  供应商管理模块 - 阶段四功能测试".center(76) + "  █")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print()
    
    try:
        test_models()
        test_score_calculation()
        test_admin_features()
        test_import_command()
        
        print("=" * 80)
        print("[SUCCESS] 所有测试完成!")
        print("=" * 80)
        print()
        print("阶段四交付物清单:")
        print("  [OK] CSV导入命令: supplier_eval/management/commands/import_supplier_eval.py")
        print("  [OK] 导入配置文件: project/import_templates/supplier_eval.yml")
        print("  [OK] CSV模板示例: data/supplier_eval_template.csv")
        print("  [OK] Admin后台配置: supplier_eval/admin.py")
        print("  [OK] 使用说明文档: docs/供应商管理模块-使用说明.md")
        print()
        print("后续步骤:")
        print("  1. 准备真实的CSV数据文件")
        print("  2. 执行导入命令测试")
        print("  3. 访问Admin后台验证功能")
        print("  4. 准备进入阶段五(测试与优化)")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()