#!/usr/bin/env python
"""
数据清洗脚本 - 清理数据库中的字符串字段
用途：去除前后空白、换行符等细微差异

使用方法：
    python manage.py shell < scripts/clean_string_fields.py
    
或者在Django shell中运行：
    python manage.py shell
    >>> exec(open('scripts/clean_string_fields.py').read())
"""

import re
from django.db import transaction
from procurement.models import Procurement
from contract.models import Contract


def clean_string_value(value):
    """
    清洗字符串值
    
    Args:
        value: 原始字符串值
        
    Returns:
        清洗后的字符串值
    """
    if not value or not isinstance(value, str):
        return value
    
    # 1. 去除前后空白
    cleaned = value.strip()
    # 2. 替换所有类型的换行符为空格
    cleaned = cleaned.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    # 3. 合并多个连续空格为单个空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # 4. 再次去除前后空白
    cleaned = cleaned.strip()
    
    return cleaned


def clean_model_string_fields(model_class, model_name):
    """
    清洗指定模型的所有字符串字段
    
    Args:
        model_class: Django模型类
        model_name: 模型名称（用于日志）
    """
    print(f"\n{'='*60}")
    print(f"开始清洗 {model_name} 模型")
    print(f"{'='*60}")
    
    # 获取所有字符串字段
    string_fields = []
    for field in model_class._meta.get_fields():
        if isinstance(field, (models.CharField, models.TextField)):
            string_fields.append(field.name)
    
    print(f"找到 {len(string_fields)} 个字符串字段: {', '.join(string_fields)}")
    
    # 统计数据
    total_records = model_class.objects.count()
    updated_count = 0
    field_update_stats = {field: 0 for field in string_fields}
    
    print(f"共有 {total_records} 条记录需要检查")
    
    # 逐条检查和更新
    with transaction.atomic():
        for i, record in enumerate(model_class.objects.all(), 1):
            record_updated = False
            updated_fields = []
            
            for field_name in string_fields:
                original_value = getattr(record, field_name, None)
                
                if original_value and isinstance(original_value, str):
                    cleaned_value = clean_string_value(original_value)
                    
                    if cleaned_value != original_value:
                        setattr(record, field_name, cleaned_value)
                        record_updated = True
                        updated_fields.append(field_name)
                        field_update_stats[field_name] += 1
            
            # 如果有字段被更新，保存记录（跳过信号和验证以提高性能）
            if record_updated:
                # 使用update_fields只更新修改过的字段，跳过save()的完整验证
                record.save(update_fields=updated_fields)
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"进度: {i}/{total_records} 已处理，{updated_count} 条记录已更新")
    
    # 输出统计结果
    print(f"\n清洗完成！")
    print(f"总记录数: {total_records}")
    print(f"更新记录数: {updated_count}")
    print(f"更新比例: {updated_count/total_records*100:.2f}%")
    
    print(f"\n各字段更新统计:")
    for field_name, count in sorted(field_update_stats.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"  {field_name}: {count} 条记录")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("数据清洗脚本 - 开始执行")
    print("="*60)
    
    try:
        # 导入必要的模块
        from django.db import models
        
        # 清洗采购模型
        clean_model_string_fields(Procurement, "采购 (Procurement)")
        
        # 清洗合同模型
        clean_model_string_fields(Contract, "合同 (Contract)")
        
        print("\n" + "="*60)
        print("数据清洗完成！所有字符串字段已规范化。")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
else:
    # 当通过exec()运行时
    main()