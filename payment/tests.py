"""
付款模块单元测试
"""
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from payment.models import Payment
from payment.validators import PaymentDataValidator
from contract.models import Contract
from project.models import Project


class PaymentValidatorTests(TestCase):
    """付款数据验证器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.project = Project.objects.create(
            project_code='TEST-001',
            project_name='测试项目'
        )
        
        self.contract = Contract.objects.create(
            contract_code='TEST-HT-001',
            contract_sequence='TEST-001',
            contract_name='测试合同',
            project=self.project,
            contract_amount=Decimal('1000000.00'),
            signing_date=date.today()
        )
    
    def test_validate_complete_payment_data(self):
        """测试完整的付款数据验证"""
        payment_data = {
            'contract': self.contract,
            'payment_amount': Decimal('100000.00'),
            'payment_date': date.today(),
            'settlement_amount': Decimal('100000.00'),
            'is_settled': True,
        }
        
        is_valid, errors = PaymentDataValidator.validate_payment_data(payment_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_contract(self):
        """测试缺少合同的情况"""
        payment_data = {
            'payment_amount': Decimal('100000.00'),
            'payment_date': date.today(),
        }
        
        is_valid, errors = PaymentDataValidator.validate_payment_data(payment_data)
        self.assertFalse(is_valid)
        self.assertIn('缺少关联合同', errors)
    
    def test_validate_invalid_amount(self):
        """测试无效金额"""
        payment_data = {
            'contract': self.contract,
            'payment_amount': Decimal('-100.00'),
            'payment_date': date.today(),
        }
        
        is_valid, errors = PaymentDataValidator.validate_payment_data(payment_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('必须大于0' in err for err in errors))
    
    def test_validate_settled_without_amount(self):
        """测试已结算但无结算金额"""
        payment_data = {
            'contract': self.contract,
            'payment_amount': Decimal('100000.00'),
            'payment_date': date.today(),
            'is_settled': True,
        }
        
        is_valid, errors = PaymentDataValidator.validate_payment_data(payment_data)
        self.assertFalse(is_valid)
        self.assertIn('已标记为已结算但缺少结算金额', errors)
    
    def test_validate_batch_uniqueness(self):
        """测试批量编号唯一性验证"""
        codes = ['TEST-001-FK-001', 'TEST-001-FK-002', 'TEST-001-FK-003']
        is_unique, duplicates = PaymentDataValidator.validate_batch_uniqueness(codes)
        self.assertTrue(is_unique)
        self.assertEqual(len(duplicates), 0)
    
    def test_validate_batch_duplicates(self):
        """测试批量编号重复检测"""
        codes = ['TEST-001-FK-001', 'TEST-001-FK-002', 'TEST-001-FK-001']
        is_unique, duplicates = PaymentDataValidator.validate_batch_uniqueness(codes)
        self.assertFalse(is_unique)
        self.assertIn('TEST-001-FK-001', duplicates)
        self.assertEqual(duplicates['TEST-001-FK-001'], 2)


class PaymentModelTests(TestCase):
    """付款模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.project = Project.objects.create(
            project_code='TEST-002',
            project_name='测试项目2'
        )
        
        self.contract = Contract.objects.create(
            contract_code='TEST-HT-002',
            contract_sequence='TEST-002',
            contract_name='测试合同2',
            project=self.project,
            contract_amount=Decimal('2000000.00'),
            signing_date=date.today()
        )
    
    def test_payment_code_generation(self):
        """测试付款编号自动生成"""
        payment = Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('100000.00'),
            payment_date=date.today()
        )
        
        self.assertIsNotNone(payment.payment_code)
        self.assertTrue(payment.payment_code.startswith('TEST-002-FK-'))
    
    def test_payment_code_sequence(self):
        """测试付款编号序列"""
        # 创建3笔付款
        payments = []
        for i in range(1, 4):
            payment = Payment.objects.create(
                contract=self.contract,
                payment_amount=Decimal('100000.00'),
                payment_date=date.today() + timedelta(days=i)
            )
            payments.append(payment)
        
        # 验证编号连续
        codes = [p.payment_code for p in payments]
        expected = [f'TEST-002-FK-{i:03d}' for i in range(1, 4)]
        self.assertEqual(codes, expected)
    
    def test_payment_ordering(self):
        """测试付款按日期排序"""
        # 创建多笔付款，日期不同
        payment1 = Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('100000.00'),
            payment_date=date.today() + timedelta(days=2)
        )
        payment2 = Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('150000.00'),
            payment_date=date.today()
        )
        payment3 = Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('200000.00'),
            payment_date=date.today() + timedelta(days=1)
        )
        
        # 查询所有付款，应该按日期排序
        payments = list(self.contract.payments.all().order_by('payment_date'))
        self.assertEqual(payments[0].payment_code, 'TEST-002-FK-001')
        self.assertEqual(payments[1].payment_code, 'TEST-002-FK-002')
        self.assertEqual(payments[2].payment_code, 'TEST-002-FK-003')


class PaymentImportTests(TestCase):
    """付款导入功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.project = Project.objects.create(
            project_code='TEST-003',
            project_name='测试项目3'
        )
        
        self.contract = Contract.objects.create(
            contract_code='TEST-HT-003',
            contract_sequence='TEST-003',
            contract_name='测试合同3',
            project=self.project,
            contract_amount=Decimal('3000000.00'),
            signing_date=date.today()
        )
    
    def test_bulk_create_no_duplicates(self):
        """测试批量创建无重复"""
        # 准备批量数据
        payments_data = []
        for i in range(1, 11):
            payments_data.append({
                'contract': self.contract,
                'payment_amount': Decimal('100000.00'),
                'payment_date': date.today() + timedelta(days=i),
            })
        
        # 模拟批量创建逻辑
        created_payments = []
        existing_count = Payment.objects.filter(contract=self.contract).count()
        
        for i, data in enumerate(payments_data, start=existing_count + 1):
            payment = Payment(
                payment_code=f"TEST-003-FK-{i:03d}",
                contract=data['contract'],
                payment_amount=data['payment_amount'],
                payment_date=data['payment_date'],
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            created_payments.append(payment)
        
        # 验证编号唯一性
        codes = [p.payment_code for p in created_payments]
        self.assertEqual(len(codes), len(set(codes)), "批量数据中存在重复编号")
        
        # 批量创建
        Payment.objects.bulk_create(created_payments)
        
        # 验证数据库中的数量
        actual_count = Payment.objects.filter(contract=self.contract).count()
        self.assertEqual(actual_count, 10)
    
    def test_bulk_create_with_existing(self):
        """测试批量创建时已有数据"""
        # 先创建2笔付款
        Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('100000.00'),
            payment_date=date.today()
        )
        Payment.objects.create(
            contract=self.contract,
            payment_amount=Decimal('150000.00'),
            payment_date=date.today() + timedelta(days=1)
        )
        
        # 再批量创建3笔
        payments_data = []
        for i in range(3, 6):
            payments_data.append({
                'contract': self.contract,
                'payment_amount': Decimal('200000.00'),
                'payment_date': date.today() + timedelta(days=i),
            })
        
        # 应该从003开始编号
        created_payments = []
        existing_count = Payment.objects.filter(contract=self.contract).count()
        
        for i, data in enumerate(payments_data, start=existing_count + 1):
            payment = Payment(
                payment_code=f"TEST-003-FK-{i:03d}",
                contract=data['contract'],
                payment_amount=data['payment_amount'],
                payment_date=data['payment_date'],
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            created_payments.append(payment)
        
        Payment.objects.bulk_create(created_payments)
        
        # 验证总数
        total_count = Payment.objects.filter(contract=self.contract).count()
        self.assertEqual(total_count, 5)
        
        # 验证编号连续性
        all_payments = list(Payment.objects.filter(contract=self.contract).order_by('payment_code'))
        expected_codes = [f'TEST-003-FK-{i:03d}' for i in range(1, 6)]
        actual_codes = [p.payment_code for p in all_payments]
        self.assertEqual(actual_codes, expected_codes)