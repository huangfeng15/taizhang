"""
诊断项目导入问题的脚本
"""
import os
import csv
import sys

# 设置控制台编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def diagnose_project_csv(file_path):
    """诊断项目CSV文件的问题"""
    print('=' * 60)
    print('项目导入文件诊断工具')
    print('=' * 60)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f'[错误] 文件不存在: {file_path}')
        return False
    
    print(f'[OK] 文件存在: {file_path}')
    print(f'  文件大小: {os.path.getsize(file_path)} 字节')
    
    # 检测文件编码
    import chardet
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
    
    print(f'  检测到编码: {encoding} (置信度: {confidence:.2%})')
    
    # 读取CSV内容
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)
        
        if headers is None:
            print(f'\n[错误] 无法读取CSV表头')
            return False
        
        print(f'\n[OK] CSV读取成功')
        print(f'  列数: {len(headers)}')
        print(f'  数据行数: {len(rows)}')
        
        # 显示列名
        print(f'\n列名:')
        for i, header in enumerate(headers, 1):
            print(f'  {i}. "{header}"')
        
        # 检查必填列
        required_columns = ['项目编码', '项目名称']
        missing_columns = [col for col in required_columns if col not in headers]
        
        if missing_columns:
            print(f'\n[错误] 缺少必填列: {missing_columns}')
            return False
        else:
            print(f'\n[OK] 必填列完整')
        
        # 分析数据行
        print(f'\n数据行分析:')
        valid_rows = 0
        empty_rows = 0
        note_rows = 0
        
        for i, row in enumerate(rows, 1):
            # 检查是否为空行
            if not any(v.strip() for v in row.values() if v):
                empty_rows += 1
                continue
            
            # 检查是否为模板说明行（使用与导入命令相同的逻辑）
            is_note_row = False
            if '模板说明' in row and row['模板说明'].strip():
                # 检查关键数据列是否都为空
                key_fields = [
                    '项目编码', '招采编号', '合同编号', '付款编号', '评价编号',
                    '项目名称', '采购项目名称', '合同名称'
                ]
                has_data = False
                for field in key_fields:
                    value = row.get(field, '')
                    if str(value).strip():
                        has_data = True
                        break
                
                if not has_data:
                    is_note_row = True
                    note_rows += 1
                    print(f'  第{i+1}行: 模板说明行（将被跳过）')
                    continue
            
            # 检查项目编码和项目名称
            project_code = row.get('项目编码', '').strip()
            project_name = row.get('项目名称', '').strip()
            
            if project_code and project_name:
                valid_rows += 1
                print(f'  第{i+1}行: [OK] 有效数据')
                print(f'    - 项目编码: {project_code}')
                print(f'    - 项目名称: {project_name}')
                print(f'    - 序号: {row.get("序号", "(空)")}')
                print(f'    - 项目状态: {row.get("项目状态", "(空)")}')
            elif project_code:
                print(f'  第{i+1}行: [错误] 项目名称为空')
                print(f'    - 项目编码: {project_code}')
            elif project_name:
                print(f'  第{i+1}行: [错误] 项目编码为空')
                print(f'    - 项目名称: {project_name}')
            else:
                empty_rows += 1
        
        print(f'\n统计:')
        print(f'  有效数据行: {valid_rows}')
        print(f'  模板说明行: {note_rows}')
        print(f'  空行: {empty_rows}')
        
        if valid_rows == 0:
            print(f'\n[警告] 没有找到有效的数据行！')
            print(f'   原因可能是：')
            print(f'   1. 所有数据行的项目编码或项目名称为空')
            print(f'   2. 文件格式不正确')
            print(f'   3. 文件内容全是模板说明')
            return False
        else:
            print(f'\n[OK] 文件包含 {valid_rows} 条有效数据')
            return True
        
    except Exception as e:
        print(f'\n[错误] 读取文件时出错: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python scripts/diagnose_project_import.py <CSV文件路径>')
        print('示例: python scripts/diagnose_project_import.py "project_import_template_long .csv"')
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = diagnose_project_csv(file_path)
    
    if success:
        print('\n' + '=' * 60)
        print('[OK] 诊断完成：文件格式正确，可以导入')
        print('=' * 60)
        print('\n导入命令:')
        print(f'python manage.py import_excel "{file_path}" --module project')
    else:
        print('\n' + '=' * 60)
        print('[错误] 诊断完成：发现问题，请修复后再导入')
        print('=' * 60)
        sys.exit(1)