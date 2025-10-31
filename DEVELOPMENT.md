# 开发与贡献指南

## 1. 项目结构与模块分工

本项目采用模块化的Django应用结构，旨在实现高内聚、低耦合的设计。

- **核心业务应用**:
  - `procurement/`: 采购管理
  - `contract/`: 合同管理
  - `payment/`: 付款管理
  - `settlement/`: 结算管理
  - `supplier_eval/`: 供应商评价管理
  每个应用负责其领域内的模型（`models.py`）、管理后台配置（`admin.py`）和业务规则。

- **主应用 (`project/`)**:
  - 作为系统的核心枢纽，承载所有跨模块的业务逻辑。
  - `views.py`: 包含所有自定义前端页面的视图逻辑，如监控驾驶舱、统计报表等。
  - `services/`: **核心业务逻辑层**。所有复杂的计算、统计、监控和报表生成逻辑都封装在此，与视图层解耦。
  - `templates/`: 存放所有自定义前端页面的HTML模板。
  - `static/`: 存放CSS、JavaScript等前端静态资源。

- **全局配置 (`config/`)**:
  - `settings.py`: 项目的全局配置。
  - `urls.py`: 全局URL路由。

- **脚本与数据**:
  - `scripts/`: 存放数据预处理、验证和查询等辅助脚本。
  - `data/`: 存放导入导出的数据文件。

## 2. 开发命令

### 2.1 环境设置
```powershell
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境 (Windows)
.venv\Scripts\activate
#    (Linux/macOS)
#    source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 2.2 数据库
```powershell
# 首次初始化或模型变更后执行
python manage.py makemigrations
python manage.py migrate

# 创建管理员账户
python manage.py createsuperuser
```

### 2.3 启动服务
```powershell
# 启动用于局域网访问的开发服务器
python manage.py runserver 0.0.0.0:3500
```

### 2.4 数据与测试
```powershell
# 运行单元测试
python manage.py test

# 框架一致性自检
python manage.py check

# 清理所有业务数据（慎用！）
python manage.py clear_all_data

# 从Excel导入数据
python manage.py import_excel <file.xlsx>
```

## 3. 代码风格与命名约定

- **Python**:
  - 遵循 **PEP 8** 规范，使用4个空格缩进。
  - 模型类名使用 `PascalCase` (e.g., `Contract`)。
  - 模型字段、函数、变量和文件名使用 `snake_case` (e.g., `contract_amount`, `get_total_paid()`)。
- **JavaScript**:
  - 函数和变量名使用 `camelCase` (e.g., `smartSelector`, `loadData()`)。
- **CSS**:
  - 类名使用 `kebab-case` (e.g., `smart-selector-trigger`)。

## 4. Git提交与合并规范

- **提交信息 (Commit Message)**:
  - 使用**动词开头的中文短语**，清晰描述本次提交的目的。
  - 示例: `修复：合同列表页分页错误`、`新增：供应商履约评价模块`、`优化：统计页面N+1查询`。
- **Pull Request (PR)**:
  - 在PR描述中清晰说明变更范围、实现逻辑和测试方法。
  - 如果关联到特定的Issue，使用 `Refs #<编号>` 关联。
  - 提交前必须确保所有测试用例通过 (`python manage.py test`)。

## 5. 配置与安全

- **环境变量**: 敏感配置（如 `SECRET_KEY`）应通过 `.env` 文件注入，**严禁**将 `.env` 文件提交到版本库。
- **开发环境**: 当前 `DEBUG=True` 和 `ALLOWED_HOSTS=['*']` 的配置**仅适用于内网开发环境**，不得用于公网生产环境。

## 6. 技术栈

- **后端**: Django 4.2+, Python 3.10+
- **数据库**: SQLite 3.x (开发), PostgreSQL (生产推荐)
- **前端**: Bootstrap 5.3, JavaScript (ES6+), Chart.js
- **数据处理**: Pandas 2.0+, openpyxl 3.1+
- **文档生成**: python-docx 1.1+

---
**最后更新**: 2025-10-31