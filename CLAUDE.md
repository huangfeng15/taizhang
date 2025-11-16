# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

项目采购与成本管理系统 - 基于Django 5.2的企业内部数据管理平台，用于集中管理采购、合同、付款、结算及供应商评价数据。采用"Django Admin + 自定义前端"混合架构，支持Excel数据导入、PDF智能识别、实时监控和统计分析。

**技术栈**: Python 3.10+ | Django 5.2 | SQLite | Bootstrap 5 | Chart.js

## 常用命令

### 开发环境
```bash
# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 启动服务器（推荐方式 - HTTPS + 局域网访问）
start_server.bat

# 或手动启动HTTPS服务器
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500

# 或启动HTTP开发服务器（仅开发测试）
python manage.py runserver 0.0.0.0:3500

# 创建管理员
python manage.py createsuperuser
```

### 测试
```bash
# 运行所有测试
python manage.py test

# 运行特定应用测试
python manage.py test project
python manage.py test procurement

# 系统检查
python manage.py check
```

### PDF智能识别
```bash
# 独立验证PDF提取
python pdf_import/standalone_extract.py

# 测试PDF类型检测
python -c "from pdf_import.core import PDFDetector; d=PDFDetector(); print(d.detect('path/to/file.pdf'))"
```

### 维护脚本
```bash
# 数据库查询工具
python scripts\query_database.py

# 配置验证
python scripts\validate_config.py

# 付款数据修复
python scripts\repair_payment_data.py

# 准备导入数据
python scripts\prepare_import_data.py
```

### 自定义管理命令
```bash
# 确保默认管理员存在
python manage.py ensure_default_admin

# 设置员工权限
python manage.py set_staff_permission
```

## 核心架构

### 应用结构（Django Apps）

系统采用领域驱动设计，每个业务模块独立为Django应用：

- **project/** - 核心主应用，包含Project模型和跨域业务逻辑
  - `services/` - 业务服务层（统计、监控）
  - `templates/` - 自定义前端页面（Bootstrap 5）
  - `static/` - CSS/JS静态资源
  - `management/commands/` - 自定义管理命令
  - `utils/` - 通用工具函数

- **procurement/** - 采购管理（Procurement模型）
- **contract/** - 合同管理（Contract模型）
- **payment/** - 付款管理（Payment模型）
- **settlement/** - 结算管理（Settlement模型）
- **supplier_eval/** - 供应商评价（SupplierEvaluation模型）
- **pdf_import/** - PDF智能识别提取模块（独立可运行）

- **config/** - Django全局配置（settings.py, urls.py, wsgi.py）
- **scripts/** - 运维和数据处理脚本
- **docs/** - 项目文档

### 数据模型关系

```
Project (项目)
  ├─→ Procurement (采购) [1:N, ForeignKey, PROTECT]
  │     └─→ Contract (合同) [1:N, ForeignKey, PROTECT]
  │           ├─→ Payment (付款) [1:N, ForeignKey, PROTECT]
  │           ├─→ Settlement (结算) [1:1, OneToOneField, PROTECT]
  │           ├─→ SupplierEvaluation (供应商评价) [1:N, ForeignKey, PROTECT]
  │           ├─→ SupplierInterview (供应商约谈) [1:N, ForeignKey, SET_NULL]
  │           └─→ parent_contract (自关联) [补充协议关联主合同]
  └─→ Contract (合同) [1:N, ForeignKey, PROTECT] (直接签订合同可跳过采购)
```

**核心关联**:
- Project通过`project_code`关联所有业务数据
- Procurement通过`procurement_code`关联Contract
- Contract通过`contract_code`关联Payment和Settlement
- Contract支持两种来源：`procurement`（采购合同）和`direct`（直接签订）
- Contract通过`file_positioning`区分：主合同/补充协议/解除协议
- Settlement只能关联主合同（OneToOne关系）
- Payment自动生成编号规则：`{合同序号}-FK-{序号}`
- 所有模型包含审计字段（created_at, updated_at）

### 服务层架构（project/services/）

业务逻辑集中在服务层，视图层保持轻量：

**监控服务**:
- **archive_monitor.py** - 归档进度监控
- **archive_monitor_optimized.py** - 优化版归档监控
- **update_monitor.py** - 数据更新监控
- **completeness.py** - 数据完整性检查

**统计分析**:
- **statistics.py** - 统计分析服务
- **ranking.py** - 排名统计
- **metrics.py** - 指标计算

**数据导出**:
- **export_service.py** - 项目数据导出服务
- **word_formatter.py** - Word文档格式化工具

### PDF智能识别模块（pdf_import/）

独立的PDF信息提取引擎，基于YAML配置驱动：

**核心组件**:
- `core/pdf_detector.py` - PDF类型检测器（5种文档类型）
- `core/field_extractor.py` - 字段提取引擎（8种提取方法）
- `core/config_loader.py` - YAML配置加载器
- `utils/text_parser.py` - 键值对提取核心
- `utils/amount_parser.py` - 金额解析
- `utils/date_parser.py` - 日期解析
- `utils/enum_mapper.py` - 枚举映射
- `utils/cell_detector.py` - 单元格检测
- `config/field_mapping.yml` - 字段映射配置（v2.0，100%提取率验证版）
- `config/field_mapping_v3_universal.yml` - 通用版本
- `config/pdf_patterns.yml` - PDF类型识别模式

**支持的PDF类型**:
- procurement_request (采购请示OA审批)
- procurement_notice (采购公告)
- candidate_publicity (中标候选人公示)
- result_publicity (采购结果公示)
- control_price_approval (采购控制价OA审批)

**提取方法**: horizontal_keyvalue, vertical_keyvalue, amount, date, regex, table_first_row, multiline, fixed_value

### 前端架构

**技术栈**: Bootstrap 5 + Chart.js + 原生JavaScript

**核心特性**:
- 智能选择器（支持搜索、分页、级联筛选）
- 模态框编辑/新增（流畅的数据操作体验）
- 全局筛选（年份、项目联动）
- 响应式设计（适配桌面和移动端）

**JavaScript组件** (`project/static/js/`):
- `smart-selector.js` - 智能选择器（搜索、分页、级联筛选）
- `edit-modal.js` - 模态框编辑
- `create-modal.js` - 模态框新增
- `global-filter-component.js` - 全局筛选组件
- `global-filter-store.js` - 筛选状态管理
- `monitoring.js` - 监控功能
- `update_monitoring.js` - 更新监控
- `charts.js` - 图表渲染（Chart.js）

**模板位置**: `project/templates/`
**静态资源**: `project/static/`

### URL路由结构（config/urls.py）

**认证**: `/accounts/login/`, `/accounts/logout/`

**数据管理**:
- `/projects/`, `/procurements/`, `/contracts/`, `/payments/`, `/settlements/` - 数据列表页
- `/project/<code>/`, `/procurement/<code>/`, `/contract/<code>/`, `/payment/<code>/` - 详情页

**监控分析**:
- `/monitoring/cockpit/` - 监控驾驶舱
- `/monitoring/statistics/` - 统计分析
- `/monitoring/ranking/` - 排名统计

**API接口**:
- `/api/projects/`, `/api/procurements/`, `/api/contracts/` - 级联选择器API
- `/api/*/batch-delete/` - 批量删除API

**其他功能**:
- `/admin/` - Django Admin后台
- `/pdf-import/` - PDF智能导入
- `/supplier/` - 供应商管理

## 编码规范

**遵循原则**: KISS, YAGNI, DRY, SOLID

- Python代码遵循PEP 8，四空格缩进
- 模型类使用PascalCase，字段和函数使用snake_case
- 各Django应用保持领域内聚，跨域逻辑放在project/
- 测试使用Django TestCase，函数命名`test_<场景>`
- Git提交信息使用中文动词短语，约50字内

## 关键技术点

### 数据库配置
- **数据库**: SQLite（timeout=20防止锁定）
- **外键约束**: 启用（PRAGMA foreign_keys = ON）
- **查询优化**: 使用select_related/prefetch_related优化关联查询
- **索引字段**: project_code, procurement_code, contract_code
- **删除保护**: 所有关联使用PROTECT防止误删

### 安全配置
- SECRET_KEY通过环境变量配置（默认值仅用于开发）
- DEBUG模式通过DJANGO_DEBUG环境变量控制
- ALLOWED_HOSTS支持局域网访问（默认包含'*'）
- CSRF保护启用
- 登录认证：所有视图需要@login_required装饰器

### 局域网部署
- **启动命令**: `start_server.bat`（推荐，自动配置HTTPS）
- **HTTPS访问地址**:
  - 本机: `https://127.0.0.1:3500/`
  - 局域网: `https://10.168.3.240:3500/`
- **SSL证书**: 自签名证书（首次访问需信任）
- **防火墙**: 需配置Windows防火墙入站规则（TCP 3500端口）
- **默认管理员**: admin/admin123（首次启动自动创建）
- **依赖**: 需安装 `django-extensions` 和 `Werkzeug` 支持 `runserver_plus`

## 重要文档

- **docs/系统架构分析文档.md** - 技术架构详解
- **docs/数据模型使用手册.md** - 模型字段和关系图
- **docs/性能优化说明.md** - 查询优化和缓存策略
- **docs/专业术语词汇表.md** - 业务术语定义
- **pdf_import/README.md** - PDF提取模块文档

## 开发注意事项

1. **模型修改**: 修改models.py后必须运行makemigrations和migrate
2. **服务层优先**: 复杂业务逻辑应放在services/而非views.py
3. **PDF配置**: 新增PDF字段需修改`pdf_import/config/field_mapping.yml`
4. **测试覆盖**: 目前仅project/和payment/有测试文件，新功能需补充测试
5. **外键关系**: 所有关联使用PROTECT，删除前需先解除关联
6. **Payment编号**: 自动生成，格式为`{合同序号}-FK-{序号}`，不要手动修改
7. **Contract类型**: 注意区分file_positioning（主合同/补充协议/解除协议）
8. **Windows环境**: 使用反斜杠路径分隔符，PowerShell命令注意引号使用

## 核心依赖版本

- Django==5.2.7
- pandas==2.3.3（数据处理）
- openpyxl==3.1.5（Excel读写）
- python-docx==1.1.2（Word文档生成）
- PyMuPDF==1.24.14 + pdfplumber==0.11.4（PDF处理）
- PyYAML==6.0.3（配置管理）
- cryptography==44.0.0（HTTPS支持）
- 用户没有要求时不提交git变更。