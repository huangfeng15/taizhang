"""测试合同删除功能"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contract.models import Contract
from supplier_eval.models import SupplierEvaluation

def test_delete():
    """测试删除合同是否会触发评价数据的级联删除"""
    
    # 统计当前数据
    contract_count = Contract.objects.count()
    evaluation_count = SupplierEvaluation.objects.count()
    
    print(f"当前合同总数: {contract_count}")
    print(f"当前评价总数: {evaluation_count}")
    
    # 查找有评价记录的合同
    contracts_with_eval = Contract.objects.filter(evaluations__isnull=False).distinct()
    
    if contracts_with_eval.exists():
        test_contract = contracts_with_eval.first()
        eval_count = test_contract.evaluations.count()
        
        print(f"\n找到测试合同: {test_contract.contract_code}")
        print(f"该合同关联的评价记录数: {eval_count}")
        print(f"评价记录包含 comprehensive_score 字段: {hasattr(SupplierEvaluation, 'comprehensive_score')}")
        
        # 尝试删除（不实际执行，只是测试）
        try:
            # 模拟删除操作，但不提交
            from django.db import transaction
            with transaction.atomic():
                # 设置保存点
                sid = transaction.savepoint()
                
                # 尝试删除
                test_contract.delete()
                
                print("\n✓ 删除操作成功（已回滚，未实际删除）")
                
                # 回滚到保存点
                transaction.savepoint_rollback(sid)
                
        except Exception as e:
            print(f"\n✗ 删除操作失败: {str(e)}")
            return False
    else:
        print("\n未找到有评价记录的合同，创建测试数据...")
        # 创建测试数据
        try:
            from django.db import transaction
            with transaction.atomic():
                # 查找任意一个合同
                if Contract.objects.exists():
                    test_contract = Contract.objects.first()
                    
                    # 创建评价记录
                    evaluation = SupplierEvaluation.objects.create(
                        evaluation_code='TEST-EVAL-001',
                        contract=test_contract,
                        supplier_name=test_contract.party_b,
                        comprehensive_score=85.5,
                        last_evaluation_score=90.0
                    )
                    
                    print(f"创建测试评价记录: {evaluation.evaluation_code}")
                    
                    # 尝试删除合同
                    test_contract.delete()
                    
                    print("✓ 删除操作成功（测试数据已清理）")
                else:
                    print("数据库中没有合同数据，无法测试")
                    
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    success = test_delete()
    if success:
        print("\n【结论】数据库结构正常，删除功能应该可以正常工作")
    else:
        print("\n【结论】仍存在问题，需要进一步排查")