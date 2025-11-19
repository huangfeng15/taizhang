"""
周报管理模块 - 单元测试
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    WeeklyReport, ProcurementProgress, WeeklyReportReminder,
    ProcurementStage, WeeklyReportStatus
)
from procurement.models import Procurement
from project.models import Project


class WeeklyReportModelTest(TestCase):
    """周报模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_weekly_report(self):
        """测试创建周报"""
        report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user,
            status=WeeklyReportStatus.DRAFT.value
        )
        
        self.assertEqual(report.report_code, 'WR2025W01')
        self.assertEqual(report.year, 2025)
        self.assertEqual(report.week, 1)
        self.assertEqual(report.recorder, self.user)
        self.assertEqual(report.status, WeeklyReportStatus.DRAFT.value)
        self.assertIsNone(report.submit_date)
    
    def test_weekly_report_validation_week_range(self):
        """测试周报周数范围验证"""
        # 测试周数大于53
        report = WeeklyReport(
            report_code='WR2025W54',
            year=2025,
            week=54,
            recorder=self.user,
            status=WeeklyReportStatus.DRAFT.value
        )
        with self.assertRaises(ValidationError):
            report.save()
        
        # 测试有效周数范围
        valid_report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user,
            status=WeeklyReportStatus.DRAFT.value
        )
        self.assertEqual(valid_report.week, 1)
        
        valid_report2 = WeeklyReport.objects.create(
            report_code='WR2025W53',
            year=2025,
            week=53,
            recorder=self.user,
            status=WeeklyReportStatus.DRAFT.value
        )
        self.assertEqual(valid_report2.week, 53)
    
    def test_weekly_report_validation_year_range(self):
        """测试周报年份范围验证"""
        # 测试年份小于2000
        report = WeeklyReport(
            report_code='WR1999W01',
            year=1999,
            week=1,
            recorder=self.user
        )
        with self.assertRaises(ValidationError) as context:
            report.full_clean()
        self.assertIn('year', context.exception.error_dict)
    
    def test_weekly_report_unique_together(self):
        """测试周报唯一性约束"""
        WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user
        )
        
        # 尝试创建相同年份、周数、记录人的周报
        with self.assertRaises(Exception):
            WeeklyReport.objects.create(
                report_code='WR2025W01_DUP',
                year=2025,
                week=1,
                recorder=self.user
            )
    
    def test_weekly_report_str(self):
        """测试周报字符串表示"""
        report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user
        )
        self.assertEqual(str(report), 'WR2025W01 - 2025年第1周')


class ProcurementProgressModelTest(TestCase):
    """采购进度模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user
        )
        self.project = Project.objects.create(
            project_code='PRJ2025001',
            project_name='测试项目'
        )
    
    def test_create_procurement_progress(self):
        """测试创建采购进度"""
        progress = ProcurementProgress.objects.create(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.PLANNING.value,
            stage_data={},
            missing_fields=[]
        )
        
        self.assertEqual(progress.progress_code, 'PP2025001')
        self.assertEqual(progress.weekly_report, self.report)
        self.assertEqual(progress.project_name, '测试采购项目')
        self.assertEqual(progress.current_stage, ProcurementStage.PLANNING.value)
        self.assertFalse(progress.is_archived)
        self.assertFalse(progress.synced_to_ledger)
    
    def test_procurement_progress_stage_order(self):
        """测试采购进度阶段顺序"""
        progress = ProcurementProgress.objects.create(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.PLANNING.value,
            stage_data={},
            missing_fields=[]
        )
        
        self.assertEqual(progress.get_stage_order(), 1)
        
        progress.current_stage = ProcurementStage.ARCHIVE.value
        self.assertEqual(progress.get_stage_order(), 7)
    
    def test_procurement_progress_can_transition(self):
        """测试采购进度阶段转换"""
        progress = ProcurementProgress.objects.create(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.PLANNING.value,
            stage_data={},
            missing_fields=[]
        )
        
        # 可以向前转换
        self.assertTrue(progress.can_transition_to(ProcurementStage.REQUIREMENT.value))
        self.assertTrue(progress.can_transition_to(ProcurementStage.ARCHIVE.value))
        
        # 不能向后转换
        self.assertFalse(progress.can_transition_to(ProcurementStage.PLANNING.value))
    
    def test_procurement_progress_validation_archived(self):
        """测试采购进度归档验证"""
        progress = ProcurementProgress(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.ARCHIVE.value,
            is_archived=True
            # 缺少 archived_date
        )
        
        with self.assertRaises(ValidationError) as context:
            progress.full_clean()
        self.assertIn('archived_date', context.exception.error_dict)
    
    def test_procurement_progress_validation_synced(self):
        """测试采购进度同步验证"""
        progress = ProcurementProgress(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.ARCHIVE.value,
            synced_to_ledger=True
            # 缺少 synced_date 和 procurement
        )
        
        with self.assertRaises(ValidationError) as context:
            progress.full_clean()
        self.assertIn('synced_date', context.exception.error_dict)
        self.assertIn('procurement', context.exception.error_dict)
    
    def test_procurement_progress_str(self):
        """测试采购进度字符串表示"""
        progress = ProcurementProgress.objects.create(
            progress_code='PP2025001',
            weekly_report=self.report,
            project_name='测试采购项目',
            current_stage=ProcurementStage.PLANNING.value,
            stage_data={},
            missing_fields=[]
        )
        self.assertIn('PP2025001', str(progress))
        self.assertIn('测试采购项目', str(progress))


class WeeklyReportReminderModelTest(TestCase):
    """周报提醒模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user
        )
    
    def test_create_reminder(self):
        """测试创建提醒"""
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报',
            reminder_type='weekly_report'
        )
        
        self.assertEqual(reminder.reminder_code, 'RMD2025001')
        self.assertEqual(reminder.target_user, self.user)
        self.assertEqual(reminder.content, '请填写本周周报')
        self.assertFalse(reminder.is_read)
        self.assertFalse(reminder.is_handled)
    
    def test_reminder_mark_as_read(self):
        """测试标记提醒为已读"""
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报'
        )
        
        self.assertFalse(reminder.is_read)
        self.assertIsNone(reminder.read_date)
        
        reminder.mark_as_read()
        
        self.assertTrue(reminder.is_read)
        self.assertIsNotNone(reminder.read_date)
    
    def test_reminder_mark_as_handled(self):
        """测试标记提醒为已处理"""
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报'
        )
        
        self.assertFalse(reminder.is_handled)
        self.assertIsNone(reminder.handled_date)
        
        reminder.mark_as_handled()
        
        self.assertTrue(reminder.is_handled)
        self.assertIsNotNone(reminder.handled_date)
    
    def test_reminder_with_related_report(self):
        """测试关联周报的提醒"""
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报',
            related_report=self.report
        )
        
        self.assertEqual(reminder.related_report, self.report)
    
    def test_reminder_str(self):
        """测试提醒字符串表示"""
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报',
            reminder_type='weekly_report'
        )
        self.assertIn('RMD2025001', str(reminder))
        self.assertIn('testuser', str(reminder))


class ProcurementModelExtensionTest(TestCase):
    """采购模型扩展测试"""
    
    def setUp(self):
        """测试前准备"""
        self.project = Project.objects.create(
            project_code='PRJ2025001',
            project_name='测试项目'
        )
    
    def test_procurement_weekly_report_fields(self):
        """测试采购模型的周报相关字段"""
        procurement = Procurement.objects.create(
            procurement_code='GC2025001',
            project_name='测试采购',
            project=self.project,
            current_stage=ProcurementStage.PLANNING.value,
            is_from_weekly_report=True
        )
        
        self.assertEqual(procurement.current_stage, ProcurementStage.PLANNING.value)
        self.assertTrue(procurement.is_from_weekly_report)
        self.assertIsNone(procurement.weekly_report_sync_date)
        self.assertEqual(procurement.stage_history, {})


class IntegrationTest(TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(
            project_code='PRJ2025001',
            project_name='测试项目'
        )
    
    def test_complete_workflow(self):
        """测试完整工作流程"""
        # 1. 创建周报
        report = WeeklyReport.objects.create(
            report_code='WR2025W01',
            year=2025,
            week=1,
            recorder=self.user,
            status=WeeklyReportStatus.DRAFT.value
        )
        
        # 2. 创建采购进度
        progress = ProcurementProgress.objects.create(
            progress_code='PP2025001',
            weekly_report=report,
            project_name='测试采购项目',
            project_code='PRJ2025001',
            current_stage=ProcurementStage.PLANNING.value,
            stage_data={},
            missing_fields=[]
        )
        
        # 3. 创建提醒
        reminder = WeeklyReportReminder.objects.create(
            reminder_code='RMD2025001',
            target_user=self.user,
            content='请填写本周周报',
            related_report=report,
            related_progress=progress
        )
        
        # 4. 验证关联关系
        self.assertEqual(progress.weekly_report, report)
        self.assertEqual(reminder.related_report, report)
        self.assertEqual(reminder.related_progress, progress)
        
        # 5. 更新进度阶段
        progress.previous_stage = progress.current_stage
        progress.current_stage = ProcurementStage.REQUIREMENT.value
        progress.save()
        
        self.assertEqual(progress.previous_stage, ProcurementStage.PLANNING.value)
        self.assertEqual(progress.current_stage, ProcurementStage.REQUIREMENT.value)
        
        # 6. 标记提醒为已处理
        reminder.mark_as_handled()
        self.assertTrue(reminder.is_handled)
        
        # 7. 提交周报
        report.status = WeeklyReportStatus.SUBMITTED.value
        report.submit_date = timezone.now()
        report.save()
        
        self.assertEqual(report.status, WeeklyReportStatus.SUBMITTED.value)
        self.assertIsNotNone(report.submit_date)
