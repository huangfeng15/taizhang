"""调试2-21 PDF内容"""
import sys
import os
import codecs

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

pdf_path = 'docs/2-21.采购控制价OA审批（PDF导出版）.pdf'

try:
    doc = fitz.open(pdf_path)
    text = doc[0].get_text()
    
    # 查找控制价相关信息
    print("=" * 80)
    print("2-21 PDF 文本内容（前3000字符）")
    print("=" * 80)
    print(text[:3000])
    
    print("\n" + "=" * 80)
    print("查找控制价关键词")
    print("=" * 80)
    
    keywords = ['控制价', '采购控制价', '采购上限价', '预算金额']
    for keyword in keywords:
        if keyword in text:
            # 找到关键词位置
            idx = text.find(keyword)
            context = text[max(0, idx-50):min(len(text), idx+200)]
            print(f"\n找到关键词 '{keyword}':")
            print(f"上下文: {context}")
    
    doc.close()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()