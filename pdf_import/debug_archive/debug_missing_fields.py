"""调试缺失字段"""
import fitz
import sys
from pathlib import Path

# 设置UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

docs_dir = Path(__file__).parent.parent / 'docs'

print("="*80)
print("检查 2-24.采购公告 中的 project_name")
print("="*80)
pdf_path = docs_dir / '2-24.采购公告-特区建工采购平台（PDF导出版）.pdf'
if pdf_path.exists():
    doc = fitz.open(str(pdf_path))
    text = doc[0].get_text()
    # 查找项目名称相关内容
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '项目名称' in line:
            print(f"第{i}行: {line}")
            if i+1 < len(lines):
                print(f"第{i+1}行: {lines[i+1]}")
            if i+2 < len(lines):
                print(f"第{i+2}行: {lines[i+2]}")
    doc.close()

print("\n" + "="*80)
print("检查 2-45.中标候选人公示 中的 candidate_publicity_end_date")
print("="*80)
pdf_path = docs_dir / '2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf'
if pdf_path.exists():
    doc = fitz.open(str(pdf_path))
    text = doc[0].get_text()
    # 查找公示结束时间
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '公示' in line or '结束' in line:
            print(f"第{i}行: {line}")
    doc.close()