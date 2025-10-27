#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置验证脚本（测试环境简化版）
用于检查业务常量配置是否正确设置
"""
import os
import sys
from pathlib import Path


def validate_constants():
    """验证业务常量"""
    print("\n📋 检查业务常量配置...")
    
    # 添加项目路径
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        from project.constants import BASE_YEAR, YEAR_WINDOW, DEFAULT_MONITOR_START_DATE
        
        print(f"   ✓ BASE_YEAR (基准年份): {BASE_YEAR}")
        print(f"   ✓ YEAR_WINDOW (年份窗口): {YEAR_WINDOW}")
        print(f"   ✓ DEFAULT_MONITOR_START_DATE (监控起始日): {DEFAULT_MONITOR_START_DATE}")
        
        # 验证合理性
        from datetime import datetime
        current_year = datetime.now().year
        
        if BASE_YEAR < 2000 or BASE_YEAR > current_year:
            print(f"   ⚠️  警告: BASE_YEAR ({BASE_YEAR}) 不在合理范围内")
            return False
        
        if YEAR_WINDOW < 0 or YEAR_WINDOW > 5:
            print(f"   ⚠️  警告: YEAR_WINDOW ({YEAR_WINDOW}) 不在合理范围内")
            return False
        
        print("\n   ✅ 业务常量配置正确")
        return True
        
    except Exception as e:
        print(f"   ❌ 业务常量加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 业务常量配置验证工具（测试环境版）")
    print("=" * 60)
    
    # 验证业务常量
    passed = validate_constants()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 验证结果")
    print("=" * 60)
    
    if passed:
        print("\n🎉 业务常量配置验证通过！\n")
        return 0
    else:
        print("\n⚠️  配置验证失败，请检查上述错误并修正。\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())