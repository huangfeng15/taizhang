"""
单元格检测器 - 基于pdfplumber的精确单元格识别
核心功能：识别PDF中的单元格结构，建立空间索引，支持右侧/下方键值对识别
"""
import pdfplumber
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Cell:
    """单元格数据结构"""
    text: str
    x0: float  # 左边界
    y0: float  # 上边界
    x1: float  # 右边界
    y1: float  # 下边界
    page_num: int
    
    @property
    def center_x(self) -> float:
        """中心X坐标"""
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        """中心Y坐标"""
        return (self.y0 + self.y1) / 2
    
    @property
    def width(self) -> float:
        """宽度"""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """高度"""
        return self.y1 - self.y0
    
    def __repr__(self):
        return f"Cell('{self.text[:20]}...', x={self.x0:.1f}, y={self.y0:.1f})"


class CellDetector:
    """单元格检测器 - 核心类"""
    
    def __init__(self, tolerance_x: float = 5.0, tolerance_y: float = 3.0):
        """
        初始化单元格检测器
        
        Args:
            tolerance_x: X轴对齐容差（像素）
            tolerance_y: Y轴对齐容差（像素）
        """
        self.tolerance_x = tolerance_x
        self.tolerance_y = tolerance_y
        self.cells: List[Cell] = []
        self.spatial_index: Dict[str, List[Cell]] = {}
    
    def extract_cells_from_pdf(self, pdf_path: str) -> List[Cell]:
        """
        从PDF提取所有单元格
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            单元格列表
        """
        cells = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # 方法1: 从表格提取单元格
                tables = page.extract_tables()
                if tables:
                    cells.extend(self._extract_cells_from_tables(page, tables, page_num))
                
                # 方法2: 从文本块提取单元格（补充非表格内容）
                words = page.extract_words(
                    x_tolerance=self.tolerance_x,
                    y_tolerance=self.tolerance_y
                )
                cells.extend(self._extract_cells_from_words(words, page_num))
        
        self.cells = cells
        self._build_spatial_index()
        return cells
    
    def _extract_cells_from_tables(self, page, tables: List[List[List]], 
                                   page_num: int) -> List[Cell]:
        """从表格提取单元格（带精确坐标）"""
        cells = []
        
        for table in tables:
            # 使用pdfplumber的table对象获取单元格边界
            # 注意：这里需要使用page.find_tables()来获取带坐标的表格
            pass
        
        # 简化版：从表格数据提取文本单元格
        for table in tables:
            for row_idx, row in enumerate(table):
                for col_idx, cell_text in enumerate(row):
                    if cell_text and cell_text.strip():
                        # 估算单元格位置（实际项目中应使用精确坐标）
                        # 这里我们会在后续通过words匹配来获取精确坐标
                        pass
        
        return cells
    
    def _extract_cells_from_words(self, words: List[Dict], page_num: int) -> List[Cell]:
        """从文本块提取单元格"""
        cells = []
        
        for word in words:
            cell = Cell(
                text=word['text'],
                x0=word['x0'],
                y0=word['top'],
                x1=word['x1'],
                y1=word['bottom'],
                page_num=page_num
            )
            cells.append(cell)
        
        return cells
    
    def _build_spatial_index(self):
        """构建空间索引以加速查询"""
        self.spatial_index = {
            'by_row': defaultdict(list),
            'by_col': defaultdict(list),
            'by_page': defaultdict(list)
        }
        
        for cell in self.cells:
            # 按页面索引
            self.spatial_index['by_page'][cell.page_num].append(cell)
            
            # 按行索引（Y坐标分组）
            row_key = round(cell.center_y / self.tolerance_y) * self.tolerance_y
            self.spatial_index['by_row'][row_key].append(cell)
            
            # 按列索引（X坐标分组）
            col_key = round(cell.center_x / self.tolerance_x) * self.tolerance_x
            self.spatial_index['by_col'][col_key].append(cell)
    
    def find_cell_by_text(self, text: str, fuzzy: bool = True) -> Optional[Cell]:
        """
        根据文本查找单元格
        
        Args:
            text: 要查找的文本
            fuzzy: 是否模糊匹配
            
        Returns:
            匹配的单元格，未找到返回None
        """
        for cell in self.cells:
            if fuzzy:
                if text in cell.text or cell.text in text:
                    return cell
            else:
                if cell.text == text:
                    return cell
        return None
    
    def find_right_cell(self, anchor_cell: Cell, 
                       max_distance: float = 200.0) -> Optional[Cell]:
        """
        查找右侧单元格（键值对：key在左，value在右）
        
        Args:
            anchor_cell: 锚点单元格（key）
            max_distance: 最大搜索距离
            
        Returns:
            右侧最近的单元格
        """
        candidates = []
        
        for cell in self.cells:
            # 必须在同一页
            if cell.page_num != anchor_cell.page_num:
                continue
            
            # 必须在右侧
            if cell.x0 <= anchor_cell.x1:
                continue
            
            # 检查是否在同一行（Y坐标接近）
            y_diff = abs(cell.center_y - anchor_cell.center_y)
            if y_diff > self.tolerance_y * 2:
                continue
            
            # 计算距离
            distance = cell.x0 - anchor_cell.x1
            if distance > max_distance:
                continue
            
            candidates.append((distance, cell))
        
        # 返回最近的单元格
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
    
    def find_below_cell(self, anchor_cell: Cell, 
                       max_distance: float = 100.0) -> Optional[Cell]:
        """
        查找下方单元格（键值对：key在上，value在下）
        
        Args:
            anchor_cell: 锚点单元格（key）
            max_distance: 最大搜索距离
            
        Returns:
            下方最近的单元格
        """
        candidates = []
        
        for cell in self.cells:
            # 必须在同一页
            if cell.page_num != anchor_cell.page_num:
                continue
            
            # 必须在下方
            if cell.y0 <= anchor_cell.y1:
                continue
            
            # 检查是否在同一列（X坐标接近）
            x_diff = abs(cell.center_x - anchor_cell.center_x)
            if x_diff > self.tolerance_x * 2:
                continue
            
            # 计算距离
            distance = cell.y0 - anchor_cell.y1
            if distance > max_distance:
                continue
            
            candidates.append((distance, cell))
        
        # 返回最近的单元格
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
    
    def extract_keyvalue_pair(self, key_text: str, 
                             direction: str = 'right',
                             fuzzy: bool = True) -> Optional[str]:
        """
        提取键值对（智能识别右侧或下方）
        
        Args:
            key_text: 键文本
            direction: 方向 'right'(右侧) 或 'below'(下方) 或 'auto'(自动)
            fuzzy: 是否模糊匹配key
            
        Returns:
            值文本，未找到返回None
        """
        # 1. 找到key单元格
        key_cell = self.find_cell_by_text(key_text, fuzzy=fuzzy)
        if not key_cell:
            return None
        
        # 2. 根据方向查找value单元格
        value_cell = None
        
        if direction == 'right':
            value_cell = self.find_right_cell(key_cell)
        elif direction == 'below':
            value_cell = self.find_below_cell(key_cell)
        elif direction == 'auto':
            # 自动尝试：先右侧，后下方
            value_cell = self.find_right_cell(key_cell)
            if not value_cell:
                value_cell = self.find_below_cell(key_cell)
        
        return value_cell.text if value_cell else None
    
    def extract_from_table_cell(self, table_markers: List[str],
                               row_key: str, row_value: str,
                               target_column: str) -> Optional[str]:
        """
        从表格单元格提取值（更精确的表格处理）
        
        Args:
            table_markers: 表格标识词列表
            row_key: 行标识列名
            row_value: 行标识值
            target_column: 目标列名
            
        Returns:
            目标单元格的值
        """
        # 1. 找到包含表格标记的页面
        relevant_pages = set()
        for marker in table_markers:
            for cell in self.cells:
                if marker in cell.text:
                    relevant_pages.add(cell.page_num)
        
        if not relevant_pages:
            return None
        
        # 2. 在相关页面中查找表头
        for page_num in relevant_pages:
            page_cells = self.spatial_index['by_page'][page_num]
            
            # 查找列标题单元格
            row_key_cell = None
            target_col_cell = None
            
            for cell in page_cells:
                if row_key in cell.text:
                    row_key_cell = cell
                if target_column in cell.text:
                    target_col_cell = cell
            
            if not row_key_cell or not target_col_cell:
                continue
            
            # 3. 查找行标识值所在的单元格
            row_value_cell = None
            for cell in page_cells:
                if row_value in cell.text:
                    # 检查是否在row_key列下方
                    x_diff = abs(cell.center_x - row_key_cell.center_x)
                    if x_diff < self.tolerance_x * 2 and cell.y0 > row_key_cell.y1:
                        row_value_cell = cell
                        break
            
            if not row_value_cell:
                continue
            
            # 4. 查找目标单元格（同行，target_column列）
            for cell in page_cells:
                y_diff = abs(cell.center_y - row_value_cell.center_y)
                x_diff = abs(cell.center_x - target_col_cell.center_x)
                
                if y_diff < self.tolerance_y * 2 and x_diff < self.tolerance_x * 2:
                    return cell.text
        
        return None
    
    def get_cells_in_region(self, x0: float, y0: float, 
                           x1: float, y1: float, 
                           page_num: int) -> List[Cell]:
        """获取指定区域内的所有单元格"""
        region_cells = []
        
        for cell in self.spatial_index['by_page'][page_num]:
            if (cell.x0 >= x0 and cell.x1 <= x1 and 
                cell.y0 >= y0 and cell.y1 <= y1):
                region_cells.append(cell)
        
        return region_cells
    
    def debug_print_cells(self, max_cells: int = 50):
        """调试：打印前N个单元格信息"""
        print(f"\n=== 检测到 {len(self.cells)} 个单元格 ===")
        for i, cell in enumerate(self.cells[:max_cells]):
            print(f"{i+1}. {cell}")
        if len(self.cells) > max_cells:
            print(f"... 还有 {len(self.cells) - max_cells} 个单元格")