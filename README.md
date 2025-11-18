# 项目采购与成本管理系统

**版本：** v3.5+
**状态：** 生产就绪
**技术栈：** Python 3.10+ | Django 5.2 | SQLite | Bootstrap 5 | Chart.js | RESTful API

---

## 优化与精简摘要（批次1-4，2025-11-13）

本轮针对冗余代码、重复逻辑与模板/静态资源进行分批精简，保持对外接口、统计口径、页面与导出行为“完全不变”。

- 累计净减少代码行数（估算）：约 2,375 行
  - 报表生成器合并及移除（删旧保新，统一入口，后移除监控中心报表生成功能）：约 -1,830 行
  - 未引用静态清理（quick-actions.css 等）：约 -488 行
  - 模板头部统一（7页替换为 include）净 -43 行（含新增片段）
  - 归档/周期统计公共化（时间分组/排序/对齐下沉）净 -70 行（含新增工具）
  - 人员聚合逻辑公共化（get_person_list 下沉）净 -41 行（含新增工具）
  - 其它零星改动：分页封装（+10）、shared utils（+32）、审计基类（+12）、导出委托（+若干）等

- 关键改动（行为不变）：
  - 统一报表导出入口：`project/services/export_service.py`（内部委托原实现）
  - 统计与归档去重：新增 `time_grouping.py`、`persons.py` 并替换原文件中重复方法体
  - 列表分页封装：`project/utils/pagination.py`，多处视图改为统一调用
  - 模板统一：新增 `templates/components/content_header_simple.html`，列表页头部统一
  - 未引用静态移除：精确扫描后只清理零引用资产
  - 审计字段基类：`project/models_base.py`（已用于 `pdf_import`/配置模型；不改字段语义）
  - 枚举映射合并：`EnumMapper` 支持从 YAML 动态合并别名（可选，失败静默）

- 验证与回滚：
  - 导出/统计/缓存键/模板渲染均保持一致；若需回滚可逐文件恢复原导入或方法体（新增工具不影响旧接口）。

## 🎯 系统简介

项目采购与成本管理系统是一套专为企业内部设计的轻量级数据管理平台。它采用 **"Django Admin + 自定义前端 + RESTful API"** 的混合架构，旨在将分散在Excel中的采购、合同、付款、结算及供应商评价数据进行集中化、结构化管理，并提供强大的数据监控与统计分析能力。

### ✨ 核心特性

- **六大业务模块**: 覆盖从采购到结算、供应商评价的全业务流程。
- **PDF智能识别**: 自动识别5种采购文档类型，提取32+个字段，成功率100%。
- **智能数据导入**: 支持Excel长/宽表格式，内置数据校验和批量导入。
- **监控驾驶舱**: 实时洞察归档进度、数据完整性与更新动态。
- **深度统计分析**: 提供多维度的数据透视、图表可视化与排名统计。
- **RESTful API**: 提供完整的API接口，支持OpenAPI/Swagger文档。
- **异步任务处理**: 支持大报表等耗时任务的后台异步处理。
- **现代化前端交互**:
  - **智能选择器**: 支持搜索、分页与级联筛选。
  - **前端编辑/新增**: 通过模态框实现流畅的数据操作体验。
  - **全局筛选**: 跨页面的年份、项目联动筛选。
  - **工作负载统计**: 可视化展示团队工作量分布。
- **多环境部署**: 支持Git分支隔离、HTTPS部署、局域网访问。
- **数据完整性**: 内置20+项完整性检查规则，支持动态配置。
- **安全性增强**: 支持CSRF保护、XSS防护、SQL注入防护。

---

## 🔒 开发/生产环境隔离

本项目采用 **Git分支管理** 实现开发和生产环境的完全隔离：

- **开发环境** (dev分支): HTTP:8000, 无证书, 随意开发测试
- **生产环境** (main分支): HTTPS:3500, 自签名证书, 稳定运行

**核心优势:**
- ✅ AI修改代码不影响生产环境
- ✅ 开发环境无HTTPS证书烦恼
- ✅ 数据库完全隔离
- ✅ 一键部署,秒级回滚

**快速开始:**
```bash
# 开发: 切换到dev分支
双击: switch_to_dev_branch.bat
访问: http://10.168.3.240:8000

# 部署: 安全部署到生产
双击: deploy_to_prod_safe.bat
访问: https://10.168.3.240:3500
```

**详细文档:**
- 📖 [Git分支环境隔离完整指南](docs/Git分支环境隔离指南.md)
- 📋 [快速参考卡片](快速参考-环境隔离.md)

---

##  快速开始

### 1. 环境要求
- **操作系统**: Windows 10/11 或 Windows Server 2016+
- **Python**: 3.10 或更高版本
- **Git**: 用于版本控制和环境隔离

### 2. 安装与启动
```bash
# 1. 克隆或解压项目代码
cd taizhang

# 2. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python manage.py migrate
python manage.py createsuperuser

# 5. 启动局域网服务（HTTPS）
# 使用 start_server.bat 启动，会自动生成SSL证书并启动HTTPS服务
start_server.bat

# 停止服务器（如需重启）
stop_server.bat

# 或者一键重启
restart_server.bat
```

### 3. 访问系统
- **查看本机IP**: 在命令行运行 `ipconfig`。
- **本机访问**: `https://127.0.0.1:3500/`
- **局域网访问**: `https://<你的IP地址>:3500/`（例如：`https://10.168.3.240:3500/`）
- **管理后台**: `https://<你的IP地址>:3500/admin/`
- **注意**: 浏览器可能显示安全警告（因为使用自签名证书），请点击"继续访问"或"信任此站点"

---

## 🗂️ 项目结构

```
taizhang/
├── config/                   # Django全局配置 (settings.py, urls.py, wsgi.py)
├── project/                  # 核心主应用（领域聚合）
│   ├── services/             # ★ 业务服务层（统计、监控、导出、安全性）
│   │   ├── export_service.py # 统一报表导出服务
│   │   ├── statistics.py     # 统计计算服务
│   │   ├── archive_monitor.py # 归档监控服务
│   │   ├── completeness.py   # 数据完整性检查
│   │   └── security/         # 安全配置（会话、密码策略）
│   ├── templates/            # ★ 自定义前端页面（Bootstrap 5 + Chart.js）
│   ├── static/               # ★ CSS/JS等静态资源
│   │   ├── css/              # 样式文件
│   │   └── js/               # JavaScript组件
│   ├── views_*.py            # 模块化视图（按业务功能拆分）
│   │   ├── views_projects.py # 项目相关视图
│   │   ├── views_monitoring.py # 监控面板视图
│   │   ├── views_statistics.py # 统计分析视图
│   │   └── views_api.py      # REST API接口
│   ├── models.py             # Project模型
│   ├── middleware/           # 自定义中间件（登录验证、性能监控）
│   └── management/commands/  # 自定义管理命令
├── procurement/              # 采购管理（Procurement模型）
├── contract/                 # 合同管理（Contract模型）
├── payment/                  # 付款管理（Payment模型）
├── settlement/               # 结算管理（Settlement模型）
├── supplier_eval/            # 供应商评价（SupplierEvaluation模型）
├── pdf_import/               # ★ PDF智能识别导入模块（独立可运行）
│   ├── core/                 # 核心引擎（检测器、提取器、配置加载器）
│   ├── config/               # YAML配置文件
│   ├── utils/                # 工具类（文本解析、日期/金额解析）
│   └── standalone_extract.py # 独立验证脚本
├── docs/                     # 项目文档和指南
├── scripts/                  # 运维和数据处理脚本
├── analytics/                # 性能分析数据
├── cache/                    # 文件缓存目录
├── ssl_certs/                # SSL证书（自签名）
├── backups/                  # 数据库备份
├── media/                    # 用户上传文件
├── logs/                     # 日志文件
├── db.sqlite3                # SQLite数据库
├── manage.py                 # Django管理入口
├── requirements.txt          # Python依赖清单
├── start_server.bat          # 启动HTTPS服务器脚本
├── stop_server.bat           # 停止服务器脚本
└── CLAUDE.md                 # Claude开发配置指南
```

---

## 📚 项目文档

| 文档 | 路径 | 说明 |
| :--- | :--- | :--- |
| **🔒 环境隔离指南** | [`docs/Git分支环境隔离指南.md`](docs/Git分支环境隔离指南.md) | **推荐阅读**。开发/生产环境隔离方案。 |
| **📋 快速参考** | [`快速参考-环境隔离.md`](快速参考-环境隔离.md) | 环境隔离快速参考卡片。 |
| **开发与贡献指南** | [`DEVELOPMENT.md`](DEVELOPMENT.md) | 项目结构、开发命令、代码规范。 |
| **系统架构分析** | [`docs/系统架构分析文档.md`](docs/系统架构分析文档.md) | 技术架构、模块设计、数据流。 |
| **数据模型手册** | [`docs/数据模型使用手册.md`](docs/数据模型使用手册.md) | 模型字段、关系图、业务规则。 |
| **环境隔离指南** | [`docs/Git分支环境隔离指南.md`](docs/Git分支环境隔离指南.md) | Git分支策略、环境管理。 |
| **HTTPS配置指南** | [`docs/HTTPS配置指南.md`](docs/HTTPS配置指南.md) | SSL证书、局域网部署说明。 |
| **PDF提取说明** | [`pdf_import/README.md`](pdf_import/README.md) | PDF智能识别模块详细文档。 |
| **PDF校验配置** | [`docs/PDF校验依赖配置说明.md`](docs/PDF校验依赖配置说明.md) | PDF提取模块安装配置。 |
| **OpenAPI使用指南** | [`docs/OpenSpec使用指南.md`](docs/OpenSpec使用指南.md) | OpenAPI测试规范。 |
| **局域网部署说明** | [`docs/局域网部署说明.md`](docs/局域网部署说明.md) | 防火墙配置、网络设置。 |
| **性能优化指南** | [`docs/性能优化说明.md`](docs/性能优化说明.md) | 查询优化、缓存策略、前端性能。 |
| **专业术语词汇表** | [`docs/专业术语词汇表.md`](docs/专业术语词汇表.md) | 统一的业务与技术术语定义。 |

---

## 💡 常用命令

### 快速开发
```bash
# 1. 安装依赖（推荐在虚拟环境中）
pip install -r requirements.txt

# 2. 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 3. 创建管理员
python manage.py createsuperuser

# 4. 启动开发服务器
python manage.py runserver 0.0.0.0:8000

# 5. 启动生产HTTPS服务器
start_server.bat
```

### PDF智能识别
```bash
# 独立验证PDF提取（无需Django运行）
python pdf_import/standalone_extract.py

# 测试PDF类型检测
python -c "from pdf_import.core import PDFDetector; d=PDFDetector(); print(d.detect('path/to/file.pdf'))"
```

### 数据导入/导出
```bash
# 从Excel导入采购数据
python manage.py import_excel data/imports/procurement.xlsx

# 下载导入模板
python manage.py download_import_template

# 导出为Word报告
python manage.py export_project_report
```

### 系统运维
```bash
# 数据库查询工具
python scripts/query_database.py

# 配置验证
python scripts/validate_config.py

# 修复付款数据
python scripts/repair_payment_data.py

# 准备导入数据
python scripts/prepare_import_data.py
```

### 测试与质量检查
```bash
# 运行所有测试
python manage.py test

# 运行特定应用测试
python manage.py test project payment

# 代码格式检查
black --check .
isort --check-only .
flake8 .

# 安全性扫描
bandit -r .
mypy .

# 系统健康检查
python manage.py check
python manage.py check --deploy
```

### 自定义管理命令
```bash
# 确保默认管理员存在
python manage.py ensure_default_admin

# 设置员工权限
python manage.py set_staff_permission

# 清理所有数据（危险！）
python manage.py clear_all_data
```

### API文档
```bash
# 访问OpenAPI/Swagger文档
# 本地: https://127.0.0.1:3500/api/docs/
# 局域网: https://10.168.3.240:3500/api/docs/
```

---

## 🔧 开发环境配置

### 推荐开发工具
- **编辑器**: VS Code + Python插件
- **Python版本**: 3.10+
- **虚拟环境**: venv或conda
- **Git**: 用于版本控制和环境隔离

### IDE配置（VS Code）
```json
{
  "python.defaultInterpreterPath": "./.venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true
}
```

### 预提交钩子
项目使用pre-commit确保代码质量：
```bash
# 安装pre-commit
pre-commit install

# 手动运行所有钩子
pre-commit run --all-files
```

### Git工作流
```bash
# 开发环境（dev分支）: HTTP:8000
# 生产环境（main分支）: HTTPS:3500

git switch dev        # 切换到开发分支
git switch main       # 切换到生产分支
git merge main        # 从main合并到dev（保持同步）
```

---

## 🚀 生产环境部署

### 安全部署流程
```bash
# 1. 创建生产备份
python manage.py backup_database

# 2. 切换到生产分支
double-click: switch_to_main_branch.bat

# 3. 安全部署到生产
double-click: deploy_to_prod_safe.bat

# 4. 验证部署
python manage.py check --deploy
```

### 端口和服务
- **应用服务**: HTTPS:3500 (Django)
- **API文档**: HTTPS:3500/api/docs/
- **数据库**: SQLite（文件级）
- **Redis**: 6379（如果使用异步任务）

### Windows服务配置
对于Windows Server：
```powershell
# 创建Windows服务（可选）
sc create "taizhang" binPath= "D:\taizhang\.venv\Scripts\python.exe D:\taizhang\manage.py runserver 0.0.0.0:3500"
```

---

## 🐛 常见问题（FAQ）

**Q: 局域网内其他电脑无法访问？**
A:
1. 确保使用 `start_server.bat` 启动服务（会自动使用 `0.0.0.0:3500` 监听所有网络接口）
2. 检查服务器的Windows防火墙是否已为TCP 3500端口添加入站规则
3. 确保使用 `https://` 协议访问，而不是 `http://`

**Q: CSRF验证失败（403错误）？**
A:
1. 检查 `config/settings.py` 中的 `CSRF_TRUSTED_ORIGINS` 配置
2. 确保请求的Origin包含在受信任列表中
3. 确认CSRF Token已正确传递（前端会自动处理）

**Q: 忘记管理员密码？**
A:
```bash
python manage.py changepassword <用户名>
# 或重置密码
python manage.py createsuperuser
```

**Q: Excel导入失败？**
A:
1. 确认文件是 `.xlsx` 格式
2. 使用 `scripts/prepare_import_data.py` 脚本预处理数据
3. 检查Excel的列名是否与系统模板一致

**Q: 数据库锁定错误（SQLite）？**
A:
1. My等待几秒钟后重试
2. 避免同时运行多个长时间查询
3. 检查 `CONN_MAX_AGE` 配置（settings.py中已设为600秒）

**Q: PDF智能识别失败？**
A:
1. 检查PDF是否为标准文本PDF（非扫描件）
2. 查看 `pdf_import/config/field_mapping.yml` 中的字段配置
3. 运行独立测试：`python pdf_import/standalone_extract.py`

---

## 📊 技术栈详情

### 后端核心技术
- **Web框架**: Django 5.2.7
- **数据库**: SQLite（生产可迁移至PostgreSQL）
- **API框架**: Django REST Framework 3.15.2
- **文档**: drf-spectacular 0.27.2（OpenAPI/Swagger）

### 前端技术
- **UI框架**: Bootstrap 5
- **图表库**: Chart.js
- **JavaScript**: 原生ES6+（无框架依赖）

### PDF处理
- **PDF解析**: PyMuPDF 1.24.14 + pdfplumber 0.11.4
- **文本提取**: 正则表达式 + 键值对算法
- **配置管理**: PyYAML 6.0.3

### 开发工具
- **代码质量**: Black（格式化）、isort（排序）、flake8（检查）
- **安全性**: bandit（漏洞扫描）
- **类型检查**: mypy（静态类型）
- **测试**: pytest（自动化测试）
- **Git钩子**: pre-commit

### 异步任务
- **任务队列**: django-rq 2.10.1
- **消息队列**: Redis 5.2.1
- **应用场景**: 大报表生成、批量数据导入

---

**最后更新：** 2025-11-18

## 📄 许可与贡献

**许可类型**: 内部项目使用

**贡献指南**:
1. 所有代码修改必须通过pull request
2. 添加新的测试用例（如适用）
3. 更新相关文档
4. 运行全部测试和质量检查通过
5. 代码审查通过后合并

**代码规范**:
- 遵循PEP 8风格指南
- 使用Black进行代码格式化
- 提交信息使用中文动词短语
- 函数和变量使用英语命名，注释使用中文

**Git工作流程**:
- `main`: 生产分支（稳定版本）
- `dev`: 开发分支（日常开发）
- `feature/*`: 功能分支（新功能开发）
- `hotfix/*`: 紧急修复分支

---
