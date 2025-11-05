# PDF单元格检测技术升级报告

## 概述

本次升级使用**pdfplumber单元格检测技术**改造了PDF文本提取模块，通过先识别单元格结构再基于空间关系匹配键值对的方式，显著提升了提取的稳定性和准确性。

## 升级时间
- 完成日期：2025-11-05
- 测试结果：**100%提取成功率** ✅

## 核心技术

### 1. 单元格检测器 (CellDetector)

**位置**: [`pdf_import/utils/cell_detector.py`](../pdf_import/utils/cell_detector.py)

**核心功能**:
- 从PDF中提取所有文本单元格及其精确坐标（x0, y0, x1, y1）
- 构建空间索引以加速查询（按页面、行、列索引）
- 基于坐标关系识别右侧/下方单元格
- 智能键值对匹配（支持自动、右侧、下方三种模式）

**关键方法**:

```python
# 提取PDF中的所有单元格
cells = detector.extract_cells_from_pdf(pdf_path)

# 查找右侧单元格（横向键值对）
value_cell = detector.find_right_cell(key_cell, max_distance=200.0)

# 查找下方单元格（纵向键值对）
value_cell = detector.find_below_cell(key_cell, max_distance=100.0)

# 智能提取键值对
value = detector.extract_keyvalue_pair(
    key_text="项目名称",
    direction='auto',  # 'right', 'below', 'auto'
    fuzzy=True
)
```

### 2. 空间索引系统

**数据结构**:
```python
@dataclass
class Cell:
    text: str           # 单元格文本
    x0, y0: float      # 左上角坐标
    x1, y1: float      # 右下角坐标
    page_num: int      # 页码
    center_x: float    # 中心X坐标
    center_y: float    # 中心Y坐标
```

**索引类型**:
- `by_page`: 按页面索引，快速定位特定页面的单元格
- `by_row`: 按行索引（Y坐标分组），快速查找同一行的单元格
- `by_col`: 按列索引（X坐标分组），快速查找同一列的单元格

### 3. 空间关系判断算法

#### 右侧单元格识别（横向键值对）
```python
def find_right_cell(anchor_cell, max_distance=200.0):
    """
    条件：
    1. 必须在同一页面
    2. X坐标在锚点右侧 (cell.x0 > anchor.x1)
    3. Y坐标对齐（中心Y坐标差 < tolerance_y * 2）
    4. 距离在范围内 (< max_distance)
    
    返回：距离最近的单元格
    """
```

#### 下方单元格识别（纵向键值对）
```python
def find_below_cell(anchor_cell, max_distance=100.0):
    """
    条件：
    1. 必须在同一页面
    2. Y坐标在锚点下方 (cell.y0 > anchor.y1)
    3. X坐标对齐（中心X坐标差 < tolerance_x * 2）
    4. 距离在范围内 (< max_distance)
    
    返回：距离最近的单元格
    """
```

## 集成方案

### FieldExtractor改造

**位置**: [`pdf_import/core/field_extractor.py`](../pdf_import/core/field_extractor.py)

**改造内容**:

1. **新增单元格检测支持**:
```python
from ..utils.cell_detector import CellDetector

self.cell_detector = None  # 延迟初始化
self._pdf_cache = {}  # 缓存已处理的PDF
```

2. **新增提取方法**: `_extract_cell_kv()`
```python
def _extract_cell_kv(self, pdf_path, extraction_config, 
                     field_config, direction='auto'):
    """基于单元格检测的键值对提取"""
    value = self.cell_detector.extract_keyvalue_pair(
        key_text=key,
        direction=direction,
        fuzzy=True
    )
    return value
```

3. **增强现有方法**:
```python
# horizontal_keyvalue: 优先单元格检测，失败则回退文本匹配
if method == 'horizontal_keyvalue':
    value = self._extract_cell_kv(pdf_path, config, field_config, 'right')
    if not value:
        value = self._extract_horizontal_kv(full_text, config, field_config)
    return value

# vertical_keyvalue: 优先单元格检测，失败则回退文本匹配
if method == 'vertical_keyvalue':
    value = self._extract_cell_kv(pdf_path, config, field_config, 'below')
    if not value:
        value = self._extract_vertical_kv(full_text, config, field_config)
    return value
```

## 技术优势

### 1. 提取稳定性提升

**问题**：原来基于纯文本正则匹配的方式容易受到以下因素干扰：
- PDF文本流顺序不固定
- 换行符位置不一致
- 多列布局识别困难

**解决**：单元格检测基于**空间坐标**而非文本顺序：
- ✅ 不受文本提取顺序影响
- ✅ 精确识别左右/上下关系
- ✅ 支持复杂表格布局

### 2. 空间关系精确识别

**横向键值对**（左右关系）：
```
[项目名称] → [深圳市某某项目]
     ↓ 找右侧单元格
```

**纵向键值对**（上下关系）：
```
[采购控制价(元)]
        ↓ 找下方单元格
    [￥1,234,567]
```

### 3. 容差机制

- `tolerance_x = 5.0`: X轴对齐容差（像素）
- `tolerance_y = 3.0`: Y轴对齐容差（像素）
- `max_distance`: 最大搜索距离控制

这些参数确保在PDF渲染误差范围内仍能正确识别关系。

### 4. 智能回退机制

```python
# 双重保障：单元格检测 + 文本匹配
value = cell_detector.extract(...)  # 优先
if not value:
    value = text_parser.extract(...)  # 回退
```

## 测试验证

### 测试脚本

**位置**: [`pdf_import/test_cell_extraction.py`](../pdf_import/test_cell_extraction.py)

**测试内容**:
1. ✅ 单元格检测器基本功能
2. ✅ 键值对提取（右侧/下方识别）
3. ✅ 字段提取器集成测试
4. ✅ 所有自动字段完整测试

### 测试结果

```
================================================================================
最终结果
================================================================================
总字段数: 23
成功: 23
失败: 0
成功率: 100.0%

🎉 恭喜！所有自动提取字段100%成功！
```

**测试覆盖的PDF**:
- ✅ 2-23.采购请示OA审批（PDF导出版）.pdf
- ✅ 2-24.采购公告-特区建工采购平台（PDF导出版）.pdf
- ✅ 2-44.采购结果OA审批（PDF导出版）.pdf
- ✅ 2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf
- ✅ 2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf

**提取字段示例**:
```
✓ project_name: 宝安区新安街道宝城43区碧海花园棚户区改造项目...
✓ procurement_unit: 深圳市天健（集团）股份有限公司
✓ procurement_method: 询价
✓ budget_amount: 400,000.00
✓ winning_bidder: 深圳市亚本传媒科技有限公司
✓ winning_amount: 340,000.00
... (共23个字段全部成功)
```

## 依赖变更

### 新增依赖

```txt
# requirements.txt
PyMuPDF==1.24.14    # 已有，保留
pdfplumber==0.11.4  # 新增
```

### 安装命令

```bash
pip install pdfplumber==0.11.4
```

## 性能优化

### 1. PDF缓存机制

```python
self._pdf_cache = {}  # 缓存已处理的PDF

if pdf_path not in self._pdf_cache:
    self.cell_detector = CellDetector()
    self.cell_detector.extract_cells_from_pdf(pdf_path)
    self._pdf_cache[pdf_path] = True
```

**优势**: 同一PDF文件的多个字段提取只需进行一次单元格检测。

### 2. 空间索引加速

通过构建by_page、by_row、by_col三重索引：
- 页面级过滤：O(1)
- 行/列级查找：O(n/k)，k为分组数

相比全表扫描提升约10-100倍。

## 使用指南

### 基本用法

```python
from pdf_import.core.field_extractor import FieldExtractor

# 初始化
extractor = FieldExtractor()

# 提取单个PDF
data = extractor.extract(
    pdf_path='docs/2-24.采购公告.pdf',
    pdf_type='procurement_notice'
)

# 提取多个PDF（合并结果）
pdf_files = {
    'procurement_request': 'path/to/2-23.pdf',
    'procurement_notice': 'path/to/2-24.pdf',
    'result_publicity': 'path/to/2-47.pdf',
}
merged_data = extractor.extract_all_from_pdfs(pdf_files)
```

### 高级用法

```python
from pdf_import.utils.cell_detector import CellDetector

# 直接使用单元格检测器
detector = CellDetector(tolerance_x=5.0, tolerance_y=3.0)
detector.extract_cells_from_pdf('document.pdf')

# 提取键值对
value = detector.extract_keyvalue_pair(
    key_text='项目名称',
    direction='auto',  # 'right', 'below', 'auto'
    fuzzy=True
)

# 调试：查看检测到的单元格
detector.debug_print_cells(max_cells=50)
```

### 配置调优

**单元格检测参数**:
```python
CellDetector(
    tolerance_x=5.0,   # X轴对齐容差，增大可识别更松散的布局
    tolerance_y=3.0    # Y轴对齐容差，减小可提高行识别精度
)
```

**搜索距离参数**:
```python
find_right_cell(anchor, max_distance=200.0)  # 横向最大搜索距离
find_below_cell(anchor, max_distance=100.0)  # 纵向最大搜索距离
```

## 后续优化方向

### 1. 表格结构识别增强
- 使用pdfplumber的`find_tables()`获取精确表格边界
- 支持合并单元格识别
- 支持跨页表格

### 2. OCR集成
- 对于扫描版PDF，集成OCR引擎（如Tesseract）
- 