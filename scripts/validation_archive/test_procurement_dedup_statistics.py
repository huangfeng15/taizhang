"""
测试采购统计去重逻辑

验证按采购项目名称去重，并取预算金额、中标金额、控制价的最大值
"""
import os
import sys
import django

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 配置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from procurement.models import Procurement
from project.services.statistics import get_procurement_statistics


def test_procurement_dedup():
    """测试采购统计去重逻辑"""
    
    print("=" * 80)
    print("测试采购统计按项目名称去重功能")
    print("=" * 80)
    
    # 1. 查询所有采购项目
    all_procurements = Procurement.objects.all()
    print(f"\n数据库中总采购记录数: {all_procurements.count()}")
    
    # 2. 统计重复的采购项目名称
    project_names = {}
    for proc in all_procurements:
        name = proc.project_name
        if not name:
            continue
        
        if name not in project_names:
            project_names[name] = []
        
        project_names[name].append({
            'code': proc.procurement_code,
            'budget': proc.budget_amount or Decimal('0'),
            'winning': proc.winning_amount or Decimal('0'),
            'control': proc.control_price or Decimal('0'),
        })
    
    # 3. 找出重复的项目名称
    duplicate_names = {name: records for name, records in project_names.items() if len(records) > 1}
    
    print(f"\n唯一采购项目名称数: {len(project_names)}")
    print(f"重复的采购项目名称数: {len(duplicate_names)}")
    
    if duplicate_names:
        print("\n重复项目示例（前5个）：")
        print("-" * 80)
        for i, (name, records) in enumerate(list(duplicate_names.items())[:5]):
            print(f"\n{i+1}. 项目名称: {name}")
            print(f"   重复次数: {len(records)}")
            
            # 显示每条记录的金额
            for j, record in enumerate(records):
                print(f"   记录 {j+1}: 编号={record['code']}, "
                      f"预算={float(record['budget'])/10000:.2f}万元, "
                      f"中标={float(record['winning'])/10000:.2f}万元, "
                      f"控制价={float(record['control'])/10000:.2f}万元")
            
            # 计算最大值
            max_budget = max(r['budget'] for r in records)
            max_winning = max(r['winning'] for r in records)
            max_control = max(r['control'] for r in records)
            
            print(f"   应统计值: 预算={float(max_budget)/10000:.2f}万元, "
                  f"中标={float(max_winning)/10000:.2f}万元, "
                  f"控制价={float(max_control)/10000:.2f}万元")
    
    # 4. 调用统计函数验证
    print("\n" + "=" * 80)
    print("调用统计函数验证")
    print("=" * 80)
    
    stats = get_procurement_statistics(year=None, project_codes=None)
    
    print(f"\n统计结果：")
    print(f"  采购项目数（去重后）: {stats['total_count']}")
    print(f"  预算总额: {stats['total_budget']:.2f} 万元")
    print(f"  中标总额: {stats['total_winning']:.2f} 万元")
    print(f"  控制价总额: {stats['total_control_price']:.2f} 万元")
    print(f"  节约金额: {stats['savings_amount']:.2f} 万元")
    print(f"  节约率: {stats['savings_rate']:.2f}%")
    print(f"  归档数量: {stats['archived_count']}")
    print(f"  归档率: {stats['archive_rate']:.2f}%")
    
    # 5. 验证采购方式分布
    if stats['method_distribution']:
        print("\n采购方式分布（去重后）：")
        for method_info in stats['method_distribution']:
            print(f"  {method_info['method']}: "
                  f"{method_info['count']}项 ({method_info['percentage']:.2f}%), "
                  f"金额 {method_info['amount']:.2f}万元")
    
    # 6. 对比验证
    print("\n" + "=" * 80)
    print("对比验证")
    print("=" * 80)
    
    # 手动计算去重后的统计
    manual_count = len(project_names)
    manual_budget = sum(max(r['budget'] for r in records) for records in project_names.values())
    manual_winning = sum(max(r['winning'] for r in records) for records in project_names.values())
    manual_control = sum(max(r['control'] for r in records) for records in project_names.values())
    
    print(f"\n手动计算（用于对比）：")
    print(f"  项目数: {manual_count}")
    print(f"  预算总额: {float(manual_budget)/10000:.2f} 万元")
    print(f"  中标总额: {float(manual_winning)/10000:.2f} 万元")
    print(f"  控制价总额: {float(manual_control)/10000:.2f} 万元")
    
    # 验证是否一致
    print(f"\n验证结果：")
    count_match = stats['total_count'] == manual_count
    budget_match = abs(stats['total_budget'] - float(manual_budget)/10000) < 0.01
    winning_match = abs(stats['total_winning'] - float(manual_winning)/10000) < 0.01
    control_match = abs(stats['total_control_price'] - float(manual_control)/10000) < 0.01
    
    print(f"  项目数一致: {'[OK]' if count_match else '[FAIL]'}")
    print(f"  预算总额一致: {'[OK]' if budget_match else '[FAIL]'}")
    print(f"  中标总额一致: {'[OK]' if winning_match else '[FAIL]'}")
    print(f"  控制价总额一致: {'[OK]' if control_match else '[FAIL]'}")
    
    if count_match and budget_match and winning_match and control_match:
        print("\n[SUCCESS] 所有验证通过！采购统计去重逻辑正确。")
    else:
        print("\n[FAILED] 验证失败！请检查统计逻辑。")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    test_procurement_dedup()