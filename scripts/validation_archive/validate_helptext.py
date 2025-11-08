#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
帮助文案配置验证脚本
检查配置文件的完整性和占位符替换
"""
import os
import sys
from pathlib import Path

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from project.helptext import helptext_manager


def validate_config():
    """验证配置"""
    print("=" * 60)
    print("🔍 帮助文案配置验证")
    print("=" * 60)
    
    config = helptext_manager.config
    issues = []
    warnings = []
    
    # 检查联系人配置
    print("\n📋 检查联系人配置...")
    for env in ['default', 'production']:
        if env not in config.get('contacts', {}):
            issues.append(f"缺少 {env} 环境的联系人配置")
        else:
            contacts = config['contacts'][env]
            for field in ['name', 'phone', 'email']:
                if field not in contacts:
                    issues.append(f"{env} 环境缺少联系人字段: {field}")
                else:
                    print(f"   ✓ {env}.{field}: {contacts[field]}")
    
    # 检查字段配置
    print("\n📋 检查字段配置...")
    modules = ['procurement', 'contract', 'payment']
    for module in modules:
        if module not in config.get('fields', {}):
            warnings.append(f"缺少模块 {module} 的字段配置")
        else:
            field_count = len(config['fields'][module])
            print(f"   ✓ {module}: {field_count} 个字段配置")
    
    # 检查消息配置
    print("\n📋 检查消息配置...")
    if 'import' not in config.get('messages', {}):
        issues.append("缺少导入消息配置")
    else:
        import_messages = config['messages']['import']
        for module in modules:
            key = f'{module}_template'
            if key in import_messages:
                print(f"   ✓ 导入消息: {key}")
            else:
                warnings.append(f"缺少导入消息: {key}")
    
    # 检查验证消息
    print("\n📋 检查验证消息...")
    validation = config.get('validation', {})
    if validation:
        print(f"   ✓ 验证消息: {len(validation)} 条")
    else:
        warnings.append("缺少验证消息配置")
    
    # 测试占位符替换
    print("\n📋 测试占位符替换...")
    try:
        # 测试联系人占位符
        name = helptext_manager.get_contact_example('name')
        phone = helptext_manager.get_contact_example('phone')
        print(f"   ✓ 联系人示例: {name} {phone}")
        
        # 测试字段帮助文本
        help_text = helptext_manager.get_help_text('procurement', 'procurement_method')
        if help_text:
            print(f"   ✓ 采购方式帮助: {help_text[:50]}...")
        else:
            warnings.append("采购方式帮助文本为空")
        
        # 测试导入消息
        message = helptext_manager.get_message('import', 'procurement_template')
        if message:
            print(f"   ✓ 采购导入说明: {len(message)} 字符")
        else:
            warnings.append("采购导入说明为空")
            
    except Exception as e:
        issues.append(f"占位符替换测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📊 验证结果")
    print("=" * 60)
    
    if issues:
        print("\n❌ 发现以下错误：")
        for issue in issues:
            print(f"  - {issue}")
    
    if warnings:
        print("\n⚠️  发现以下警告：")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not issues and not warnings:
        print("\n✅ 配置验证通过！")
        print("\n示例文案展示：")
        print("-" * 60)
        print(f"当前环境: {helptext_manager.environment}")
        print(f"联系人: {helptext_manager.get_contact_example('name')}")
        print(f"电话: {helptext_manager.get_contact_example('phone')}")
        print(f"邮箱: {helptext_manager.get_contact_example('email')}")
        print("-" * 60)
        print(f"\n采购方式帮助文本:")
        print(f"  {helptext_manager.get_help_text('procurement', 'procurement_method')}")
        print(f"\n合同文件定位帮助文本:")
        print(f"  {helptext_manager.get_help_text('contract', 'file_positioning')}")
        print("-" * 60)
        return True
    
    return False


def main():
    """主函数"""
    try:
        success = validate_config()
        print("\n" + "=" * 60)
        if success:
            print("🎉 验证成功！帮助文案配置正确。")
        else:
            print("⚠️  验证完成，但存在问题需要修复。")
        print("=" * 60 + "\n")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()