"""
测试付款数据增量导入重复问题的修复
验证：重复导入相同的付款文件时不会创建重复记录
"""
import os
import sys
import django
from pathlib import Path
from datetime import date
from decimal import Decimal

# 设置Django环境
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from contract.models import Contract
from payment.models import Payment
from project.models import Project
import tempfile
import csv

def create_test_data():
    """创建测试数据"""
    print("=== 创建测试数据 ===")
    
    # 创建项目
    project, _ = Project.objects.get_or_create(
        project_code='TEST-PROJ-001',
        defaults={'project_name': '测试项目'}
    )
    print(f"✓ 项目: {project.project_code}")
    
    # 创建合同（使用直接签订来源，避免采购关联验证）
    contract, _ = Contract.objects.get_or_create(
        contract_code='TEST-CONTRACT-001',
        defaults={
            'contract_name': '测试合同',
            'project': project,
            'contract_source': '直接签订',  # 设置为直接签订，避免需要关联采购
            'party_a': '甲方',
            'party_b': '乙方',
            'contract_amount': Decimal('1000000.00'),
            'signing_date': date(2025, 1, 1),
        }
    )
    print(f"✓ 合同: {contract.contract_code}")
    
    return project, contract

def create_test_csv():
    """创建测试CSV文件"""
    print("\n=== 创建测试CSV文件 ===")
    
    # 创建临时CSV文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig', newline='')
    writer = csv.writer(temp_file)
    
    # 写入表头
    headers = [
        '项目编码', '序号', '付款编号', '关联合同编号',
        '实付金额(元)', '付款日期', '结算价（元）', '是否办理结算'
    ]
    writer.writerow(headers)
    
    # 写入测试数据（2条付款记录）
    writer.writerow([
        'TEST-PROJ-001', '1', '', 'TEST-CONTRACT-001',
        '100000.00', '2025-01-15', '', '否'
    ])
    writer.writerow([
        'TEST-PROJ-001', '2', '', 'TEST-CONTRACT-001',
        '200000.00', '2025-02-15', '', '否'
    ])
    
    temp_file.close()
    print(f"✓ CSV文件创建: {temp_file.name}")
    return temp_file.name

def test_incremental_import():
    """测试增量导入"""
    print("\n" + "="*60)
    print("开始测试增量导入重复问题")
    print("="*60)
    
    # 1. 创建测试数据
    project, contract = create_test_data()
    
    # 2. 清空现有付款记录
    Payment.objects.filter(contract=contract).delete()
    print(f"\n✓ 清空现有付款记录")
    
    # 3. 创建测试CSV
    csv_file = create_test_csv()
    
    try:
        # 4. 第一次导入
        print("\n" + "="*60)
        print("第一次导入（应该创建2条记录）")
        print("="*60)
        call_command(
            'import_excel',
            csv_file,
            '--module', 'payment',
            '--conflict-mode', 'update',
        )
        first_count = Payment.objects.filter(contract=contract).count()
        print(f"\n第一次导入后付款记录数: {first_count}")
        
        # 5. 第二次导入（重复导入）
        print("\n" + "="*60)
        print("第二次导入（应该识别为重复，不创建新记录）")
        print("="*60)
        call_command(
            'import_excel',
            csv_file,
            '--module', 'payment',
            '--conflict-mode', 'update',
        )
        second_count = Payment.objects.filter(contract=contract).count()
        print(f"\n第二次导入后付款记录数: {second_count}")
        
        # 6. 验证结果
        print("\n" + "="*60)
        print("测试结果")
        print("="*60)
        
        if first_count == 2 and second_count == 2:
            print("✅ 测试通过！")
            print(f"   - 第一次导入创建了 {first_count} 条记录")
            print(f"   - 第二次导入没有创建重复记录（仍为 {second_count} 条）")
            
            # 显示付款记录详情
            print("\n付款记录详情：")
            for payment in Payment.objects.filter(contract=contract).order_by('payment_date'):
                print(f"  {payment.payment_code}: {payment.payment_date} - {payment.payment_amount}元")
            
            return True
        else:
            print("❌ 测试失败！")
            print(f"   - 第一次导入: {first_count} 条（预期: 2）")
            print(f"   - 第二次导入: {second_count} 条（预期: 2）")
            if second_count > first_count:
                print(f"   ⚠️ 检测到重复导入：增加了 {second_count - first_count} 条重复记录")
            return False
            
    finally:
        # 清理测试文件
        if os.path.exists(csv_file):
            os.unlink(csv_file)
            print(f"\n✓ 清理临时文件: {csv_file}")

if __name__ == '__main__':
    success = test_incremental_import()
    sys.exit(0 if success else 1)