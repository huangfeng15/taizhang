#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
表数据统计脚本（配置驱动版本）
使用 YAML 配置文件管理表列表，避免硬编码
"""
import os
import sys
import yaml
import argparse
from pathlib import Path

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.apps import apps


def load_config(config_path: str = None):
    """加载配置"""
    if config_path is None:
        config_path = Path(__file__).parent / 'configs' / 'table_stats.yml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_table_stats(config_path: str = None, verbose: bool = False):
    """检查表数据统计"""
    config = load_config(config_path)
    
    print('=' * 60)
    print('数据库表统计')
    print('=' * 60)
    
    total_records = 0
    
    for table_config in config['tables']:
        module_name = table_config['module']
        model_name = table_config['model']
        display_name = table_config['display_name']
        
        try:
            Model = apps.get_model(module_name, model_name)
            count = Model.objects.count()
            total_records += count
            
            status = "✓" if count > 0 else "○"
            print(f"{status} {display_name:12} : {count:6} 条")
            
            if verbose and count > 0:
                # 显示详细信息
                print(f"   表名: {table_config['name']}")
                last_record = Model.objects.last()
                if last_record:
                    print(f"   最新记录: {last_record}")
                
        except Exception as e:
            print(f"✗ {display_name:12} : 错误 - {e}")
    
    print('=' * 60)
    print(f"总计: {total_records} 条记录")
    print('=' * 60)


def main():
    parser = argparse.ArgumentParser(description='表数据统计工具（配置驱动）')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    check_table_stats(args.config, args.verbose)


if __name__ == '__main__':
    main()