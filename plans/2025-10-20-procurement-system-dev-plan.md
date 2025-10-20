# 项目采购与成本管理系统 — 详细开发计划

**文档版本：** v1.0  
**编写日期：** 2025-10-20  
**规划周期：** 2周 MVP 阶段  
**设计原则：** KISS（简单至上）/ YAGNI（你不需要它）/ DRY（杜绝重复）

---

## 1. 项目概述

### 1.1 项目目标
开发一套部署在公司内部局域网的轻量级采购与成本管理系统，实现 **5大核心模块** 的数据集中化、结构化管理，支持历史Excel数据的平滑迁移。

### 1.2 技术方案选择（阶段一 MVP）

| 组件 | 选型 | 理由 |
|-----|------|------|
| **后端框架** | Django 4.2 | 内置ORM、Admin后台，无需写前端代码 |
| **数据库** | SQLite | 零配置，文件型，备份简单，支持10万+条数据 |
| **前端** | Django Admin | 内置美观后台，开发效率最高 |
| **服务器** | Django开发服务器 | 一行命令启动，局域网直接访问 |
| **部署环境** | Windows Server/PC | 支持Windows防火墙配置、任务计划程序自动备份 |

### 1.3 预期成果
- **功能完整性：** 5大模块核心功能 100% 完成
- **数据导入：** 支持标准长表导入 + 历史宽表智能转换
- **用户体验：** Django Admin 后台 + 搜索、过滤、关联查询
- **可维护性：** 完整的部署文档、备份策略、故障排查指南
- **交付物：** 可直接运行的 Django 项目 + 2周内上线可用

---

## 2. 需求分解

### 2.1 核心功能模块

#### 模块一：采购管理 (Procurement)
- **主键：** `招采编号`（业务编号，非数据库自增ID）
- **必填字段：** `采购项目名称`
- **关键字段：** 采购预算、控制价、中标金额、采购方式、采购类别、时间追踪字段
- **管理员操作：** 增删改查、批量导入、搜索过滤

#### 模块二：合同管理 (Contract)
- **主键：** `合同编号`
- **必填字段：** `合同名称`
- **关键关系：** 一个采购N个合同 | 一个主合同N个补充协议
- **合同分类：**
  - 采购合同：通过采购流程产生，必须关联采购项目（占绝大多数）
  - 直接签订合同：不经过采购流程，无需关联采购（极少数）
- **核心规则：**
  - 补充协议必须关联主合同，主合同不能关联其他合同
  - 采购合同必须关联采购项目，直接签订合同不能关联采购项目
  - 补充协议自动继承主合同的来源类型和采购关联
- **关键字段：** 合同类型、合同来源、甲乙方、合同金额、签订日期、支付方式

#### 模块三：付款管理 (Payment)
- **主键：** `付款编号`（格式：`[合同编号]-FK-[序号]`）
- **关键字段：** 关联合同、实付金额、付款日期
- **核心规则：** 累计付款不超过合同金额的120%
- **难点功能：** 宽表转长表导入（从"按月份列"的Excel转为独立记录）

#### 模块四：结算管理 (Settlement)
- **主键：** `结算编号`
- **关键字段：** 关联合同、最终结算金额、完成日期
- **关系特性：** 一个合同一条结算记录（OneToOne）

#### 模块五：供应商履约评价 (SupplierEvaluation)
- **主键：** `评价编号`（格式：`[合同编号]-PJ-[序号]`）
- **关键字段：** 关联合同、供应商名称、评分、评价类型、评价日期
- **难点功能：** 支持宽表转长表导入（多个评价人员、多期评价）

### 2.2 数据约束与验证

| 约束类型 | 实现位置 | 说明 |
|---------|--------|------|
| **唯一性** | 模型主键 | 业务编号作为PK，数据库级强制唯一 |
| **关联完整性** | ForeignKey + on_delete=PROTECT | 删除关联记录时保护（防止孤立数据） |
| **业务规则** | Model.clean() 方法 | 补充协议关联、付款金额上限检查、合同来源校验 |
| **空值管理** | blank=True, null=True | 除"项目名称"、"合同名称"外字段均允许为空 |
| **合同分类** | contract_source字段 | 区分采购合同和直接签订合同，支持按来源统计 |

### 2.3 数据迁移策略

#### 导入方案一：标准长表导入
- **场景：** 新数据录入、标准格式数据
- **工具：** Django 管理命令 + Pandas
- **命令：** `python manage.py import_excel data.xlsx`
- **处理流程：** 读取 → 验证 → update_or_create → 报告结果

#### 导入方案二：宽表转长表导入（关键）
- **场景：** 历史Excel台账迁移（付款、评价数据）
- **输入格式：** 宽表（第1列=合同编号，其余列=日期，单元格=金额）
- **输出格式：** 长表（每个金额→独立记录）
- **命令：** `python manage.py convert_wide_to_long payment.xlsx`
- **核心逻辑：**
  1. 识别日期列（正则匹配"年""月"）
  2. Pandas.melt() 逆透视
  3. 为每条记录自动生成编号
  4. 批量导入 + 事务管理

---

## 3. 开发阶段划分（2周时间表）

### 第1周：基础设施 + 核心功能

#### 第1天：环境搭建
- [ ] Python 3.10+ 环境配置
- [ ] 虚拟环境创建：`python -m venv venv`
- [ ] 依赖安装：Django 4.2、pandas、openpyxl
- [ ] 项目初始化：`django-admin startproject config .`
- [ ] 5个应用创建：procurement, contract, payment, settlement, supplier_eval

**验收标准：** `python manage.py runserver` 正常启动

#### 第2天：数据模型设计
- [ ] Procurement 模型完整定义（35+字段）
- [ ] Contract 模型定义（含ForeignKey关系 + contract_source字段）
- [ ] Payment、Settlement、SupplierEvaluation 模型
- [ ] 模型 clean() 方法数据验证
  - [ ] 补充协议关联主合同验证
  - [ ] 采购合同必须关联采购项目验证
  - [ ] 直接签订合同不能关联采购项目验证
  - [ ] 补充协议继承主合同来源类型验证
- [ ] 数据库迁移：`makemigrations` → `migrate`
- [ ] 创建超级用户：`createsuperuser`

**验收标准：** 数据库表成功创建，模型关系完整，业务规则验证生效

#### 第3天：Admin 基础配置
- [ ] ProcurementAdmin：list_display、search_fields、list_filter、fieldsets
- [ ] ContractAdmin：autocomplete_fields、关联关系配置、合同来源过滤器
  - [ ] 在list_display中添加contract_source显示
  - [ ] 在list_filter中添加contract_source和procurement（是否为空）过滤
  - [ ] 在fieldsets中添加合同来源分组和说明
- [ ] PaymentAdmin、SettlementAdmin、SupplierEvaluationAdmin
- [ ] 自定义Admin站点标题（中文化）

**验收标准：** Admin后台能正常增删改查5个模块，合同分类筛选功能正常

#### 第4天：Admin 高级功能
- [ ] 搜索优化（多字段搜索）
- [ ] 过滤器配置（分类、日期层级、合同来源）
- [ ] 只读字段：created_at, updated_at
- [ ] 关联快速搜索（autocomplete_fields）
- [ ] 分页配置（list_per_page）
- [ ] 自定义过滤器：按是否关联采购筛选合同

**验收标准：** Admin查询和过滤功能流畅，可快速区分两类合同

#### 第5天：标准长表导入
- [ ] 创建 `procurement/management/commands/import_excel.py`
- [ ] Pandas 读取、验证逻辑
- [ ] update_or_create 批量导入
- [ ] 错误处理 & 日志输出
- [ ] 测试：采购台账导入

**验收标准：** `python manage.py import_excel 采购台账-20251014.csv` 成功导入

### 第2周：高级功能 + 部署

#### 第6天：宽表转长表导入（核心）
- [ ] 创建 `payment/management/commands/convert_wide_to_long.py`
- [ ] 日期列识别（正则：`\d{4}\D*\d{1,2}`）
- [ ] Pandas.melt() 逆透视
- [ ] 付款编号自动生成
- [ ] 月份字符串→日期对象解析

**验收标准：** 宽表Excel转长表后，付款记录正确导入

#### 第7天：数据导入测试
- [ ] 准备测试数据（采购、合同、付款宽表）
- [ ] 批量导入采购数据
- [ ] 批量导入合同数据（包含采购合同和直接签订合同）
  - [ ] 测试采购合同导入（必须有procurement关联）
  - [ ] 测试直接签订合同导入（procurement为空）
- [ ] 转换并导入付款数据
- [ ] 验证数据完整性和关联关系
- [ ] 测试合同来源分类统计功能

**验收标准：** 历史数据平滑迁移到系统，两类合同正确区分

#### 第8天：功能完善与优化
- [ ] 搜索功能测试（跨模块搜索）
- [ ] 关联数据超链接验证
- [ ] 数据验证规则测试
- [ ] 性能优化：select_related、prefetch_related
- [ ] 界面优化（fieldsets分组）

**验收标准：** 所有核心功能正常工作

#### 第9天：部署准备
- [ ] 编写数据库备份脚本（backup_db.py）
- [ ] Windows任务计划程序配置
- [ ] Windows防火墙规则配置（端口8000）
- [ ] settings.py 生产环境配置
- [ ] ALLOWED_HOSTS 配置

**验收标准：** 系统在Windows Server上可独立运行

#### 第10天：文档与培训
- [ ] 编写用户操作手册
- [ ] 编写部署文档
- [ ] 编写故障排查指南
- [ ] 数据字典整理
- [ ] 用户培训与反馈收集

**验收标准：** 完整的文档体系交付

---

## 4. 项目目录结构

```
procurement_system/
│
├── config/                          # Django项目配置
│   ├── __init__.py
│   ├── settings.py                  # 核心配置（数据库、应用、中文设置）
│   ├── urls.py                      # 路由配置（只需admin/）
│   ├── asgi.py
│   └── wsgi.py
│
├── procurement/                     # 采购管理应用
│   ├── migrations/
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── import_excel.py      # Excel导入命令
│   ├── __init__.py
│   ├── models.py                    # Procurement模型
│   ├── admin.py                     # Admin配置
│   └── apps.py
│
├── contract/                        # 合同管理应用
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py                    # Contract模型（含ForeignKey、验证）
│   ├── admin.py                     # 高级Admin配置
│   └── apps.py
│
├── payment/                         # 付款管理应用
│   ├── migrations/
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── convert_wide_to_long.py  # 宽表转长表命令（核心）
│   ├── __init__.py
│   ├── models.py                    # Payment模型（含120%验证）
│   ├── admin.py
│   └── apps.py
│
├── settlement/                      # 结算管理应用
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py                    # Settlement模型（OneToOne）
│   ├── admin.py
│   └── apps.py
│
├── supplier_eval/                   # 供应商评价应用
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py                    # SupplierEvaluation模型
│   ├── admin.py
│   └── apps.py
│
├── db.sqlite3                       # SQLite数据库（git忽略）
│
├── backups/                         # 备份目录
│   └── .gitkeep
│
├── logs/                            # 日志目录
│   └── .gitkeep
│
├── data/                            # 数据文件目录
│   ├── imports/                     # 待导入的Excel文件
│   ├── exports/                     # 导出的数据文件
│   └── templates/                   # Excel导入模板
│
├── docs/                            # 文档目录
│   ├── 部署指南.md
│   ├── 用户手册.md
│   ├── 管理员手册.md
│   ├── 数据字典.md
│   └── 故障排查.md
│
├── scripts/                         # 脚本目录
│   ├── backup_db.py                 # 每日备份脚本
│   └── restore_db.py                # 数据恢复脚本
│
├── manage.py                        # Django管理脚本
├── requirements.txt                 # Python依赖列表
├── .gitignore                       # Git忽略文件
└── README.md                        # 项目说明
```

---

## 5. 核心代码设计框架

### 5.1 基础抽象模型（DRY原则）

```python
# 在procurement/models.py或单独的base.py中定义
from django.db import models

class BaseModel(models.Model):
    """基础模型 - 包含所有业务模型的通用审计字段"""
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.CharField('创建人', max_length=50, blank=True)
    updated_by = models.CharField('更新人', max_length=50, blank=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
```

### 5.2 宽表转长表核心算法

```python
# payment/management/commands/convert_wide_to_long.py 核心逻辑
import pandas as pd
import re
from datetime import datetime

def identify_date_columns(columns):
    """识别包含日期的列"""
    date_pattern = re.compile(r'\d{4}\D*\d{1,2}')
    return [col for col in columns if date_pattern.search(str(col))]

def parse_month_to_date(month_str):
    """将"2022年1月"转换为"2022-01-01"""
    match = re.search(r'(\d{4})\D*(\d{1,2})', str(month_str))
    if not match:
        raise ValueError(f"无法解析日期: {month_str}")
    year, month = int(match.group(1)), int(match.group(2))
    return datetime(year, month, 1).date()

def convert_wide_to_long(file_path):
    """宽表转长表主函数"""
    df = pd.read_excel(file_path)
    contract_col = df.columns[0]
    date_cols = identify_date_columns(df.columns[1:])
    
    # 逆透视
    df_long = pd.melt(
        df,
        id_vars=[contract_col],
        value_vars=date_cols,
        var_name='月份',
        value_name='金额'
    )
    
    # 清理空值
    df_long = df_long[df_long['金额'].notna() & (df_long['金额'] > 0)]
    
    return df_long
```

### 5.3 数据验证（SOLID原则 - 单一职责）

```python
# contract/models.py
from django.core.exceptions import ValidationError

class Contract(BaseModel):
    # ... 字段定义 ...
    
    def clean(self):
        """数据验证 - 业务规则检查"""
        # 规则1: 补充协议必须关联主合同
        if self.contract_type == '补充协议' and not self.parent_contract:
            raise ValidationError('补充协议必须关联主合同')
        
        # 规则2: 主合同不能关联其他合同
        if self.contract_type == '主合同' and self.parent_contract:
            raise ValidationError('主合同不能关联其他合同')
    
    def save(self, *args, **kwargs):
        self.full_clean()  # 保存前强制验证
        super().save(*args, **kwargs)
```

### 5.4 Admin配置模板

```python
# payment/admin.py
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_code', 'contract', 'payment_amount', 'payment_date']
    search_fields = ['payment_code', 'contract__contract_code', 'contract__contract_name']
    list_filter = ['payment_date', 'created_at']
    autocomplete_fields = ['contract']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('payment_code', 'contract')
        }),
        ('付款详情', {
            'fields': ('payment_amount', 'payment_date')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
```

---

## 6. 实施风险 & 应对策略

| 风险 | 等级 | 应对方案 |
|-----|------|--------|
| **日期格式解析错误** | 高 | 预编译正则表达式，测试多种格式（"2025年1月"/"2025-01"/"202501"） |
| **Excel编码问题** | 中 | Pandas指定encoding='utf-8'，提供编码转换工具 |
| **SQLite并发写入锁定** | 低 | settings.py配置timeout=20秒 |
| **主键重复导入** | 高 | 使用update_or_create而非create，数据库级唯一性约束 |
| **历史数据缺失关联** | 中 | 导入前验证：采购合同必须有关联采购；记录不存在的采购编号 |
| **合同来源误分类** | 中 | 提供清晰的字段说明和默认值；导入时进行数据校验 |
| **直接签订合同误关联采购** | 中 | Model.clean()强制验证，阻止不合规数据保存 |
| **补充协议来源不一致** | 低 | 自动继承主合同的contract_source和procurement |
| **备份文件堆积** | 低 | 备份脚本定期清理7天前的旧备份 |
| **学习曲线陡峭** | 中 | 提供详细文档、代码注释、培训支持 |

---

## 7. 成功度量指标

### 功能完整度
- [ ] 5个模块数据模型 100% 实现
- [ ] Django Admin 后台功能可用
- [ ] 标准Excel导入功能正常
- [ ] 宽表转长表转换成功
- [ ] 数据验证规则生效（包括合同来源验证）
- [ ] 合同分类统计功能正常
- [ ] 两类合同筛选功能可用
- [ ] 防火墙 + 备份脚本配置完成

### 性能指标
- 页面加载时间 < 3秒
- 列表查询响应时间 < 1秒
- 支持 10万+ 条数据无卡顿

### 可靠性
- 数据库自动每日备份
- 系统故障零数据丢失
- 7×24小时稳定运行

---

## 8. 交付物清单

| 交付物 | 格式 | 说明 |
|-------|------|------|
| Django源代码 | .py | 完整可运行项目 |
| SQLite数据库 | .sqlite3 | 初始化 + 样本数据 |
| 部署文档 | .md | 分步骤Windows部署指南 |
| 用户手册 | .md / .pdf | 功能使用说明（含截图） |
| 数据字典 | .xlsx | 所有字段定义 |
| 备份脚本 | .py + .xml | 任务计划程序配置 |
| 测试用例 | .xlsx + .md | Excel模板 + 预期结果 |
| requirements.txt | .txt | Python依赖清单 |

---

## 9. 后续优化方向（阶段二/三）

### 可选功能（不在MVP范围）
- [ ] Vue3前端自定义界面
- [ ] RESTful API（Django REST framework）
- [ ] 高级报表和数据分析
- [ ] PostgreSQL迁移
- [ ] 权限管理细化

### 性能优化（按需实施）
- [ ] Redis缓存热数据
- [ ] 数据库查询索引优化
- [ ] 前端分页虚拟滚动

---

## 10. 设计原则体现

### KISS（简单至上）
- 使用Django Admin而非自建前端 → 节省3周开发时间
- SQLite零配置 → 无需安装PostgreSQL/MySQL
- 开发服务器 → 一行命令启动

### YAGNI（你不需要它）
- 不实现审批流（需求明确不需要）
- 不实现变更管理（远期规划）
- 不引入复杂的权限系统（小团队使用）

### DRY（杜绝重复）
- BaseModel抽象通用字段 → 避免5次重复
- 统一的Admin配置模板 → 快速复制
- 宽表转长表算法复用 → 付款、评价共用

### SOLID（坚实基础）
- 单一职责：每个模型只管理自己的数据
- 开放封闭：模型扩展字段无需修改核心逻辑
- 依赖倒置：使用ForeignKey抽象关联，而非硬编码ID

---

**下一步：** 等待用户确认此计划，确认后可以使用 `/do` 命令进入Code模式开始实施。