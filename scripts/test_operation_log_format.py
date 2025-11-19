"""测试操作日志格式化输出效果"""
import sys
import os
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from project.middleware.operation_log import OperationLogMiddleware


def test_format_changes():
    """测试不同规模的变更数据格式化效果"""
    # 创建一个模拟的中间件实例，直接调用格式化方法
    class MockMiddleware:
        def _format_changes_description(self, changes):
            from project.middleware.operation_log import OperationLogMiddleware
            # 直接使用中间件的格式化方法
            return OperationLogMiddleware._format_changes_description(self, changes)
        
        def _truncate_value(self, value, max_length=30):
            from project.middleware.operation_log import OperationLogMiddleware
            return OperationLogMiddleware._truncate_value(self, value, max_length)
    
    middleware = MockMiddleware()
    
    print("=" * 80)
    print("测试场景1: 少量变更 (3个字段)")
    print("=" * 80)
    changes_small = {
        "procurement_code": {"old": "NMDY-001", "new": "NMDY-002"},
        "winning_amount": {"old": "1000000", "new": "1200000"},
        "procurement_officer": {"old": "张三", "new": "李四"}
    }
    result = middleware._format_changes_description(changes_small)
    print(f"原始变更: {len(changes_small)} 个字段")
    print(f"格式化结果:\n{result}\n")
    
    print("=" * 80)
    print("测试场景2: 中等变更 (6个字段)")
    print("=" * 80)
    changes_medium = {
        "procurement_code": {"old": "NMDY-001", "new": "NMDY-002"},
        "winning_amount": {"old": "1000000", "new": "1200000"},
        "procurement_officer": {"old": "张三", "new": "李四"},
        "procurement_method": {"old": "公开招标", "new": "竞争性谈判"},
        "winning_bidder": {"old": "A公司", "new": "B公司"},
        "archive_date": {"old": "2025-01-01", "new": "2025-01-15"}
    }
    result = middleware._format_changes_description(changes_medium)
    print(f"原始变更: {len(changes_medium)} 个字段")
    print(f"格式化结果:\n{result}\n")
    
    print("=" * 80)
    print("测试场景3: 大量变更 (15个字段)")
    print("=" * 80)
    changes_large = {
        "csrfmiddlewaretoken": {"old": "xxx", "new": "yyy"},  # 应被跳过
        "project": {"old": "项目A", "new": "项目B"},
        "procurement_code": {"old": "NMDY-001", "new": "NMDY-002"},
        "procurement_category": {"old": "货物", "new": "服务"},
        "procurement_unit": {"old": "单位A", "new": "单位B"},
        "procurement_platform": {"old": "平台A", "new": "平台B"},
        "procurement_method": {"old": "公开招标", "new": "竞争性谈判"},
        "qualification_review_method": {"old": "资格后审", "new": "资格预审"},
        "bid_evaluation_method": {"old": "综合评分法", "new": "最低评标价法"},
        "control_price": {"old": "1000000", "new": "1200000"},
        "winning_amount": {"old": "900000", "new": "1100000"},
        "procurement_officer": {"old": "张三", "new": "李四"},
        "demand_department": {"old": "部门A", "new": "部门B"},
        "winning_bidder": {"old": "A公司", "new": "B公司"},
        "archive_date": {"old": "2025-01-01", "new": "2025-01-15"}
    }
    result = middleware._format_changes_description(changes_large)
    print(f"原始变更: {len(changes_large)} 个字段 (含1个应跳过的CSRF字段)")
    print(f"格式化结果:\n{result}\n")
    
    print("=" * 80)
    print("测试场景4: 包含超长值的变更")
    print("=" * 80)
    changes_long = {
        "project_name": {"old": "短名称", "new": "龙岗区布吉街道办事处南门墩城中村改造项目意愿征集阶段服务项目制作宣传物料服务采购项目"},
        "winning_amount": {"old": "1000000", "new": "1200000"}
    }
    result = middleware._format_changes_description(changes_long)
    print(f"原始变更: {len(changes_long)} 个字段")
    print(f"格式化结果:\n{result}\n")
    
    print("=" * 80)
    print("测试场景5: 仅包含CSRF令牌的无效变更")
    print("=" * 80)
    changes_invalid = {
        "csrfmiddlewaretoken": {"old": "xxx", "new": "yyy"}
    }
    result = middleware._format_changes_description(changes_invalid)
    print(f"原始变更: {len(changes_invalid)} 个字段")
    print(f"格式化结果: '{result}' (应为空)\n")


if __name__ == "__main__":
    test_format_changes()