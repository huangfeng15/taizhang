"""
付款管理模块 - 信号处理器

实现结算信息自动同步到付款记录的功能
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='settlement.Settlement')
def sync_settlement_to_payments(sender, instance, created, **kwargs):
    """
    当结算记录保存时，自动同步结算信息到相关付款记录
    
    触发条件：
    1. 新建结算记录
    2. 更新结算记录（特别是结算价字段）
    
    同步逻辑：
    - 根据结算记录关联的主合同，找到该合同的所有付款记录
    - 将结算信息同步到这些付款记录中
    """
    # 检查是否有结算价
    if instance.final_amount is None:
        logger.info(f"结算记录 {instance.settlement_code} 未填写结算价，跳过同步")
        return
    
    # 获取关联的主合同
    main_contract = instance.main_contract
    
    if not main_contract:
        logger.warning(f"结算记录 {instance.settlement_code} 没有关联合同，跳过同步")
        return
    
    # 导入 Payment 模型（延迟导入避免循环依赖）
    from payment.models import Payment
    
    # 查找所有关联该合同的付款记录
    # 注意：付款记录可能关联主合同，也可能关联补充协议
    # 所以需要找到主合同及其所有补充协议的付款记录
    contract_codes = [main_contract.contract_code]
    
    # 获取所有补充协议的编号
    supplement_codes = list(
        main_contract.supplements.values_list('contract_code', flat=True)
    )
    contract_codes.extend(supplement_codes)
    
    # 查找所有相关付款记录
    related_payments = Payment.objects.filter(contract__contract_code__in=contract_codes)
    
    if not related_payments.exists():
        logger.info(f"合同 {main_contract.contract_code} 及其补充协议没有关联的付款记录")
        return
    
    # 批量更新付款记录的结算信息
    update_count = related_payments.update(
        is_settled=True,
        settlement_completion_date=instance.completion_date,
        settlement_archive_date=instance.created_at.date() if instance.created_at else None,  # 使用创建时间作为归档时间
        settlement_amount=instance.final_amount
    )
    
    logger.info(
        f"成功同步结算信息：合同 {main_contract.contract_code}，"
        f"更新 {update_count} 条付款记录，"
        f"结算价：{instance.final_amount} 元"
    )


@receiver(post_delete, sender='settlement.Settlement')
def clear_settlement_from_payments(sender, instance, **kwargs):
    """
    当结算记录被删除时，清除相关付款记录的结算信息
    
    注意：
    - 只有当该合同没有其他结算记录时，才清除付款记录的结算信息
    """
    main_contract = instance.main_contract
    
    if not main_contract:
        return
    
    # 导入 Settlement 和 Payment 模型
    from settlement.models import Settlement
    from payment.models import Payment
    
    # 检查该合同是否还有其他结算记录
    other_settlements = Settlement.objects.filter(
        main_contract=main_contract
    ).exclude(pk=instance.pk).exists()
    
    if not other_settlements:
        # 获取主合同及所有补充协议的编号
        contract_codes = [main_contract.contract_code]
        supplement_codes = list(
            main_contract.supplements.values_list('contract_code', flat=True)
        )
        contract_codes.extend(supplement_codes)
        
        # 如果没有其他结算记录，清除付款记录的结算信息
        update_count = Payment.objects.filter(
            contract__contract_code__in=contract_codes
        ).update(
            is_settled=False,
            settlement_completion_date=None,
            settlement_archive_date=None,
            settlement_amount=None
        )
        
        logger.info(f"已清除合同 {main_contract.contract_code} 的 {update_count} 条付款记录结算信息")
    else:
        logger.info(f"合同 {main_contract.contract_code} 还有其他结算记录，不清除付款记录结算信息")