"""测试采购类别提取"""
import fitz
import re
import sys

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = 'docs/2-24.采购公告-特区建工采购平台（PDF导出版）.pdf'

try:
    doc = fitz.open(pdf_path)
    full_text = ''
    for page in doc:
        full_text += page.get_text()
    doc.close()
    
    print("=" * 80)
    print("PDF全文（前3000字符）:")
    print("=" * 80)
    print(full_text[:3000])
    
    print("\n" + "=" * 80)
    print("搜索'项目类型'相关内容:")
    print("=" * 80)
    
    # 查找项目类型
    patterns = [
        r'项目类型[：:\s]*([^\n]+)',
        r'标段/?包分类[：:\s]*[A-Z]-[^/\n]*/\s*([^\n]+)',
        r'采购类别[：:\s]*([^\n]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            print(f"\nPattern: {pattern}")
            print(f"匹配结果: {matches}")
    
    # 搜索包含"类"的行
    print("\n" + "=" * 80)
    print("包含'类'或'类型'的行:")
    print("=" * 80)
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        if '类' in line or '类型' in line:
            print(f"行{i}: {line.strip()}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()