"""
测试改进后的导入交互反馈功能
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from io import StringIO
from django.core.management import call_command

def test_import_with_errors():
    """测试包含错误的导入场景"""
    print("=" * 70)
    print("测试场景：导入包含错误的数据文件")
    print("=" * 70)
    
    # 创建测试CSV文件
    test_csv = """项目编码,项目名称,项目描述
TEST001,测试项目1,这是一个测试项目
TEST002,测试项目2,这是另一个测试项目
,缺少编码的项目,这行会导致错误
TEST003,测试项目3,正常项目
TEST001,重复的项目,这是重复的编码"""
    
    csv_path = 'test_data_with_errors.csv'
    with open(csv_path, 'w', encoding='utf-8-sig') as f:
        f.write(test_csv)
    
    try:
        # 捕获输出
        out = StringIO()
        
        # 执行导入命令
        call_command(
            'import_excel',
            csv_path,
            '--module=project',
            '--skip-errors',
            stdout=out,
            stderr=StringIO()
        )
        
        # 显示输出
        output = out.getvalue()
        print(output)
        
        # 验证输出包含关键信息
        assert '数据概况' in output, "应包含数据概况"
        assert '导入结果' in output, "应包含导入结果"
        assert '有效数据行' in output, "应显示有效数据行数"
        
        print("\n✓ 测试通过：导入反馈信息完整")
        
    finally:
        # 清理测试文件
        if os.path.exists(csv_path):
            os.remove(csv_path)

def test_import_success():
    """测试成功导入场景"""
    print("\n" + "=" * 70)
    print("测试场景：成功导入所有数据")
    print("=" * 70)
    
    # 创建测试CSV文件
    test_csv = """项目编码,项目名称,项目描述
SUCC001,成功项目1,这是成功的项目1
SUCC002,成功项目2,这是成功的项目2
SUCC003,成功项目3,这是成功的项目3"""
    
    csv_path = 'test_data_success.csv'
    with open(csv_path, 'w', encoding='utf-8-sig') as f:
        f.write(test_csv)
    
    try:
        # 捕获输出
        out = StringIO()
        
        # 执行导入命令
        call_command(
            'import_excel',
            csv_path,
            '--module=project',
            stdout=out,
            stderr=StringIO()
        )
        
        # 显示输出
        output = out.getvalue()
        print(output)
        
        # 验证输出
        assert '成功导入' in output, "应显示成功导入信息"
        assert '新增记录' in output or '更新记录' in output, "应显示新增或更新记录数"
        
        print("\n✓ 测试通过：成功导入反馈正确")
        
    finally:
        # 清理测试文件
        if os.path.exists(csv_path):
            os.remove(csv_path)

def test_dry_run():
    """测试预演模式"""
    print("\n" + "=" * 70)
    print("测试场景：预演模式（不实际导入）")
    print("=" * 70)
    
    test_csv = """项目编码,项目名称,项目描述
DRY001,预演项目1,这是预演项目"""
    
    csv_path = 'test_data_dry.csv'
    with open(csv_path, 'w', encoding='utf-8-sig') as f:
        f.write(test_csv)
    
    try:
        out = StringIO()
        
        call_command(
            'import_excel',
            csv_path,
            '--module=project',
            '--dry-run',
            stdout=out,
            stderr=StringIO()
        )
        
        output = out.getvalue()
        print(output)
        
        assert '预演模式' in output, "应显示预演模式标识"
        
        print("\n✓ 测试通过：预演模式工作正常")
        
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)

if __name__ == '__main__':
    print("开始测试导入交互反馈功能...\n")
    
    try:
        test_import_with_errors()
        test_import_success()
        test_dry_run()
        
        print("\n" + "=" * 70)
        print("✓ 所有测试通过！")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)