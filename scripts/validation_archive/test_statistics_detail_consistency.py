#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统计数据一致性验证脚本

验证统计详情数据与KPI卡片显示的汇总数据是否完全匹配
"""
import os
import sys
import django
from decimal import Decimal

# 设置Windows控制台输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from project.services.statistics import (
    get_procurement_statistics,
    get_procurement_details,
    get_contract_statistics,
    get_contract_details,
    get_payment_statistics,
    get_payment_details,
    get_settlement_statistics,
    get_settlement_details,
)


def test_procurement_consistency():
    """测试采购统计数据一致性"""
    print("\n" + "="*60)
    print("测试采购统计数据一致性")
    print("="*60)
    
    # 获取统计数据和详情数据
    stats = get_procurement_statistics(year=None, project_codes=None)
    details = get_procurement_details(year=None, project_codes=None)
    
    # 验证项目数量
    detail_count = len(details)
    stats_count = stats['total_count']
    print(f"✓ 项目数量: 统计={stats_count}, 详情={detail_count}")
    assert detail_count == stats_count, f"项目数量不匹配: {detail_count} != {stats_count}"
    
    # 验证中标总额
    detail_winning_total = sum(d['winning_amount'] for d in details) / 10000  # 转换为万元
    stats_winning_total = stats['total_winning']
    print(f"✓ 中标总额: 统计={stats_winning_total:.2f}万, 详情={detail_winning_total:.2f}万")
    diff = abs(detail_winning_total - stats_winning_total)
    assert diff < 0.01, f"中标总额不匹配,差异={diff}万元"
    
    # 验证预算总额
    detail_budget_total = sum(d['budget_amount'] for d in details) / 10000
    stats_budget_total = stats['total_budget']
    print(f"✓ 预算总额: 统计={stats_budget_total:.2f}万, 详情={detail_budget_total:.2f}万")
    diff = abs(detail_budget_total - stats_budget_total)
    assert diff < 0.01, f"预算总额不匹配,差异={diff}万元"
    
    print("✅ 采购统计数据一致性验证通过!")


def test_contract_consistency():
    """测试合同统计数据一致性"""
    print("\n" + "="*60)
    print("测试合同统计数据一致性")
    print("="*60)
    
    stats = get_contract_statistics(year=None, project_codes=None)
    details = get_contract_details(year=None, project_codes=None)
    
    # 验证合同数量
    detail_count = len(details)
    stats_count = stats['total_count']
    print(f"✓ 合同数量: 统计={stats_count}, 详情={detail_count}")
    assert detail_count == stats_count, f"合同数量不匹配: {detail_count} != {stats_count}"
    
    # 验证合同总额
    detail_amount_total = sum(d['contract_amount'] for d in details) / 10000
    stats_amount_total = stats['total_amount']
    print(f"✓ 合同总额: 统计={stats_amount_total:.2f}万, 详情={detail_amount_total:.2f}万")
    diff = abs(detail_amount_total - stats_amount_total)
    assert diff < 0.01, f"合同总额不匹配,差异={diff}万元"
    
    # 验证主合同数量
    detail_main_count = sum(1 for d in details if d['file_positioning'] == '主合同')
    stats_main_count = stats['main_count']
    print(f"✓ 主合同数量: 统计={stats_main_count}, 详情={detail_main_count}")
    assert detail_main_count == stats_main_count, f"主合同数量不匹配"
    
    print("✅ 合同统计数据一致性验证通过!")


def test_payment_consistency():
    """测试付款统计数据一致性"""
    print("\n" + "="*60)
    print("测试付款统计数据一致性")
    print("="*60)
    
    stats = get_payment_statistics(year=None, project_codes=None)
    details = get_payment_details(year=None, project_codes=None)
    
    # 验证付款笔数
    detail_count = len(details)
    stats_count = stats['total_count']
    print(f"✓ 付款笔数: 统计={stats_count}, 详情={detail_count}")
    assert detail_count == stats_count, f"付款笔数不匹配: {detail_count} != {stats_count}"
    
    # 验证付款总额
    detail_amount_total = sum(d['payment_amount'] for d in details) / 10000
    stats_amount_total = stats['total_amount']
    print(f"✓ 付款总额: 统计={stats_amount_total:.2f}万, 详情={detail_amount_total:.2f}万")
    diff = abs(detail_amount_total - stats_amount_total)
    assert diff < 0.01, f"付款总额不匹配,差异={diff}万元"
    
    print("✅ 付款统计数据一致性验证通过!")


def test_settlement_consistency():
    """测试结算统计数据一致性"""
    print("\n" + "="*60)
    print("测试结算统计数据一致性")
    print("="*60)
    
    stats = get_settlement_statistics(year=None, project_codes=None)
    details = get_settlement_details(year=None, project_codes=None)
    
    # 验证结算数量
    detail_count = len(details)
    stats_count = stats['total_count']
    print(f"✓ 结算数量: 统计={stats_count}, 详情={detail_count}")
    assert detail_count == stats_count, f"结算数量不匹配: {detail_count} != {stats_count}"
    
    # 验证结算总额
    detail_amount_total = sum(d['settlement_amount'] for d in details) / 10000
    stats_amount_total = stats['total_amount']
    print(f"✓ 结算总额: 统计={stats_amount_total:.2f}万, 详情={detail_amount_total:.2f}万")
    diff = abs(detail_amount_total - stats_amount_total)
    assert diff < 0.01, f"结算总额不匹配,差异={diff}万元"
    
    print("✅ 结算统计数据一致性验证通过!")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("统计数据一致性验证测试")
    print("="*60)
    print("说明: 验证详情数据与卡片统计数据是否完全匹配")
    print("="*60)
    
    try:
        # 运行所有测试
        test_procurement_consistency()
        test_contract_consistency()
        test_payment_consistency()
        test_settlement_consistency()
        
        print("\n" + "="*60)
        print("[SUCCESS] 所有数据一致性验证测试通过!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())