
# PDF智能识别提取模块 - 技术执行计划

## 📋 一、项目概述

### 1.1 核心目标
基于《PDF智能识别导入方案-最终版.md》，开发一个独立的PDF信息提取模块，实现：
- **智能识别**：自动检测5种PDF文档类型
- **精准提取**：基于键值对方法提取32个字段，准确率100%
- **独立验证**：处理5个样本PDF文件，生成结构化JSON输出

### 1.2 设计原则
- ✅ **单一数据源**：每个字段只从一个PDF提取，避免冲突
- ✅ **配置驱动**：YAML配置文件管理提取规则
- ✅ **键值对为主**：横向/纵向键值对识别，辅以正则表达式
- ✅ **独立可测**：模块自包含，可独立运行验证

---

## 🛠️ 二、技术栈选型

### 2.1 核心依赖库
```python
# PDF处理
PyMuPDF (fitz) >= 1.23.0    # 文本提取、页面解析（性能最优）
pdfplumber >= 0.10.3        # 表格提取、布局分析

# 配置管理
PyYAML >= 6.0.1             # YAML配置文件解析

# 数据处理
python-dateutil >= 2.8.2    # 智能日期解析
```

### 2.2 技术选型理由

| 库名 | 选择原因 | 替代方案 |
|------|----------|----------|
| **PyMuPDF** | 速度快、内存占用小、支持文本坐标 | PyPDF2（功能少） |
| **pdfplumber** | 表格提取准确、支持bbox定位 | camelot（依赖重） |
| **PyYAML** | 配置文件标准、可读性强 | JSON（不支持注释） |

---

## 🏗️ 三、模块架构设计

### 3.1 目录结构
```
pdf_import/                          # PDF导入模块根目录
├── config/                          # 配置文件
│   ├── field_mapping.yml           # 字段映射配置（核心）
│   └── pdf_patterns.yml            # PDF类型识别模式
├── core/                            # 核心引擎
│   ├── __init__.py
│   ├── pdf_detector.py             # PDF类型检测器
│   ├── field_extractor.py          # 字段提取引擎（核心）
│   ├── config_loader.py            # 配置加载器
│   └── data_validator.py           # 数据验证器
├── utils/                           # 工具类
│   ├── __init__.py
│   ├── text_parser.py              # 文本解析（键值对提取）
│   ├── date_parser.py              # 日期解析
│   ├── amount_parser.py            # 金额解析
│   └── enum_mapper.py              # 枚举映射
├── standalone_extract.py            # 独立运行脚本（验证用）
└── README.md                        # 模块使用说明
```

### 3.2 核心类设计

#### 3.2.1 PDFDetector（PDF类型检测器）
```python
class PDFDetector:
    """智能检测PDF文档类型"""
    
    def detect(pdf_path: str) -> Tuple[str, float, str]:
        """
        检测单个PDF类型
        Returns: (pdf_type, confidence, method)
        """
    
    def detect_batch(pdf_paths: List[str]) -> Dict[str, List]:
        """批量检测PDF类型"""
```

**检测策略**：
1. **文件名模式匹配**（权重：0.4）
   - `2-23` → `procurement_request`
   - `2-24` → `procurement_notice`
   - `2-45` → `candidate_publicity`
   - `2-47` → `result_publicity`

2. **内容标记匹配**（权重：0.6）
   - 提取前2页文本
   - 匹配关键词列表
   - 计算匹配度得分

3. **混合决策**
   - 文件名置信度 ≥ 0.8 → 直接返回
   - 内容置信度 ≥ 0.7 → 返回内容结果
   - 两者一致 → 提升置信度

#### 3.2.2 FieldExtractor（字段提取引擎）- 核心
```python
class FieldExtractor:
    """基于键值对的字段提取引擎"""
    
    def extract(pdf_path: str, pdf_type: str) -> Dict[str, Any]:
        """
        从PDF提取字段
        Args:
            pdf_path: PDF文件路径
            pdf_type: PDF类型（由detector检测）
        Returns:
            {field_name: extracted_value, ...}
        """
    
    def _extract_by_keyvalue(text: str, key_pattern: str) -> str:
        """键值对提取（核心方法）"""
    
    def _extract_from_table(pdf, table_markers: dict) -> dict:
        """从表格提取数据"""
```

**提取策略（键值对为主）**：
```python
# 横向键值对：key: value
"项目名称：深圳市某某项目" → {"project_name": "深圳市某某项目"}

# 纵向键值对：
# key
# value
"采购控制价(元)
 ￥1,234,567.00" → {"control_price": "1234567.00"}

# 表格键值对：
# | 序号 | 成交人 | 成交价(元) |
# | 1    | XX公司 | ￥100,000  |
```

#### 3.2.3 TextParser（文本解析器）- 核心工具
```python
class TextParser:
    """文本解析工具 - 键值对提取"""
    
    @staticmethod
    def extract_horizontal_kv(text: str, key: str, 
                             delimiter: str = "[：:]") -> Optional[str]:
        """
        提取横向键值对
        
        示例：
        "项目名称：深圳项目" 
        → extract_horizontal_kv(text, "项目名称") 
        → "深圳项目"
        """
    
    @staticmethod
    def extract_vertical_kv(text: str, key: str,
                           max_distance: int = 2) -> Optional[str]:
        """
        提取纵向键值对（键在上，值在下）
        
        示例：
        "采购控制价(元)\n￥1,234,567.00"
        → extract_vertical_kv(text, "采购控制价")
        → "1,234,567.00"
        """
    
    @staticmethod
    def extract_table_cell(pdf, key_text: str,
                          target_column: str) -> Optional[str]:
        """从表格中提取单元格值"""
```

#### 3.2.4 ConfigLoader（配置加载器）
```python
class ConfigLoader:
    """加载和验证YAML配置"""
    
    def load_field_mapping() -> Dict:
        """加载字段映射配置"""
    
    def load_pdf_patterns() -> Dict:
        """加载PDF识别模式"""
    
    def validate_config() -> bool:
        """验证配置完整性"""
```

#### 3.2.5 DataValidator（数据验证器）
```python
class DataValidator:
    """提取数据验证"""
    
    def validate(data: Dict, pdf_type: str) -> Dict:
        """
        验证提取的数据
        Returns:
            {
                'is_valid': bool,
                'fields': {field: {'status', 'message'}},
                'missing_required': [],
                'enum_conflicts': []
            }
        """
```

---

## 📝 四、配置文件设计

### 4.1 field_mapping.yml（字段映射配置）
```yaml
version: "1.0"
description: "采购信息PDF字段提取配置"

# 字段提取规则
fields:
  project_name:
    label: "采购项目名称"
    required: true
    data_type: "string"
    source:
      pdf_type: "procurement_notice"  # 唯一来源
      extraction:
        method: "horizontal_keyvalue"   # 提取方法：横向键值对
        key: "项目名称"
        delimiter: "[：:]"
        fallback_regex: "项目名称[：:]\s*(.+?)(?=\n项目编号)"
    validation:
      - type: "not_empty"
      - type: "max_length"
        value: 200
  
  control_price:
    label: "采购控制价(元)"
    required: false
    data_type: "decimal"
    source:
      pdf_type: "procurement_notice"
      extraction:
        method: "vertical_keyvalue"     # 纵向键值对
        key: "采购控制价"
        value_pattern: "￥([\\d,\\.]+)"
    post_process:
      - parse_amount                     # 后处理：解析金额
    validation:
      - type: "positive"
      - type: "reasonable_range"
        min: 0
        max: 100000000000
  
  winning_bidder:
    label: "中标单位"
    required: false
    data_type: "string"
    source:
      pdf_type: "result_publicity"
      extraction:
        method: "table_cell"             # 从表格提取
        table_marker: "成交结果"
        key_column: "序号"
        key_value: "1"
        target_column: "成交人"
```

### 4.2 pdf_patterns.yml（PDF识别模式）
```yaml
pdf_types:
  procurement_request:
    name: "采购请示OA审批"
    filename_patterns:
      - "2-23"
      - "采购请示"
      - "OA审批"
    content_markers:
      - "采购请示"
      - "申请人"
      - "定标方法"
      - "采购预算金额"
    confidence_threshold: 0.7
  
  procurement_notice:
    name: "采购公告"
    filename_patterns:
      - "2-24"
      - "采购公告"
      - "询价公告"
    content_markers:
      - "询价公告"
      - "项目编号"
      - "开标时间"
      - "报名截止时间"
    confidence_threshold: 0.7
  
  candidate_publicity:
    name: "中标候选人公示"
    filename_patterns:
      - "2-45"
      - "候选人公示"
    content_markers:
      - "中标候选人"
      - "第一候选人"
      - "公示结束时间"
    confidence_threshold: 0.7
  
  result_publicity:
    name: "采购结果公示"
    filename_patterns:
      - "2-47"
      - "结果公示"
      - "成交结果"
    content_markers:
      - "成交结果公示"
      - "成交人"
      - "成交价"
    confidence_threshold: 0.7
```

---

## 🔄 五、开发任务分解

### 阶段1：基础设施搭建（已部分完成）
- [x] 创建模块目录结构
- [x] 安装核心依赖（PyMuPDF, pdfplumber, PyYAML）
- [x] 编写PDFDetector基础类
- [x] 编写基础工具类（DateParser, AmountParser, EnumMapper）
- [ ] **待完成**：编写TextParser（键值对提取核心）

### 阶段2：核心引擎开发（核心任务）
- [ ] **FieldExtractor开发**（最重要）
  - [ ] 实现横向键值对提取
  - [ ] 实现纵向键值对提取
  - [ ] 实现表格单元格提取
  - [ ] 集成正则表达式降级策略
- [ ] **ConfigLoader开发**
  - [ ] 加载field_mapping.yml
  - [ ] 加载pdf_patterns.yml
  - [ ] 配置验证逻辑
- [ ] **DataValidator开发**
  - [ ] 字段完整性验证
  - [ ] 枚举值验证
  - [ ] 数据类型验证

### 阶段3：配置文件编写
- [ ] **field_mapping.yml完整版**
  - [ ] 定义全部32个字段
  - [ ] 为每个字段配置提取规则
  - [ ] 配置后处理和验证规则
- [ ] **pdf_patterns.yml**
  - [ ] 定义5种PDF类型识别模式
  - [ ] 配置文件名和内容标记

### 阶段4：独立运行脚本开发
- [ ] **standalone_extract.py**
  - [ ] 命令行参数解析
  - [ ] 批量处理PDF文件
  - [ ] 生成JSON输出
  - [ ] 错误处理和日志

### 