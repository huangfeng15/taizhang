# Repository Guidelines

## 项目结构与模块分工
- 核心 Django 应用分布在 `procurement/`、`contract/`、`payment/`、`settlement/` 与 `supplier_eval/`，各自维护本域模型和 Admin 配置，避免跨模块耦合，公共跨域逻辑集中在 `project/`。
- `config/` 管理全局设置与路由；`scripts/` 收录导入校验脚本（如 `prepare_import_data.py`、`check_table_data.py`）；`docs/`、`plans/` 与 `specs/` 承载业务资料，导入中间数据置于 `data/`，敏感变量参照 `.env.example`。

## 构建、测试与开发命令
```powershell
# 虚拟环境管理
python -m venv .venv         # 初始化虚拟环境
.venv\Scripts\activate       # 激活虚拟环境 (Windows)
source .venv/bin/activate    # 激活虚拟环境 (Linux/Mac)

# 依赖安装
pip install -r requirements.txt

# 数据库管理
python manage.py makemigrations  # 生成迁移文件
python manage.py migrate         # 同步数据库

# 启动服务（局域网访问）
python manage.py runserver 0.0.0.0:3500  # 局域网服务（端口3500）
python manage.py runserver               # 仅本机访问（127.0.0.1:8000）

# 用户管理
python manage.py createsuperuser         # 创建管理员
python manage.py set_staff_permission <username>  # 设置员工权限

# 测试与检查
python manage.py test           # 运行单元测试
python manage.py check          # 框架一致性自检
python manage.py check --deploy # 生产环境检查

# 数据管理
python manage.py loaddata seed.json      # 导入基线数据（如有）
python manage.py clear_all_data          # 清理所有数据（慎用）
python manage.py import_excel <file.xlsx> # Excel数据导入
```

### 数据预处理与验证
```powershell
# 预处理Excel数据（推荐在导入前使用）
python scripts\prepare_import_data.py <source.xlsx>

# 检查数据完整性
python scripts\check_table_data.py

# 交互式数据库查询
python scripts\query_database.py

# 统计数据验证
python scripts\test_procurement_dedup_statistics.py
python scripts\test_statistics_detail_consistency.py
```

## 局域网访问配置

### 服务器设置
- **默认端口**: 3500
- **监听地址**: 0.0.0.0（所有网络接口）
- **访问控制**: `ALLOWED_HOSTS = ['*']`（config/settings.py）

### 启动局域网服务
```powershell
# 启动命令
python manage.py runserver 0.0.0.0:3500

# 查看本机IP
ipconfig | findstr "IPv4"  # Windows
ip addr show               # Linux
```

### 访问地址
- **本机**: http://127.0.0.1:3500 或 http://localhost:3500
- **局域网**: http://[服务器IP]:3500（如 http://10.168.3.240:3500）
- **管理后台**: http://[服务器IP]:3500/admin/
- **数据监控**: http://[服务器IP]:3500/monitoring/
- **报表导出**: http://[服务器IP]:3500/reports/

### 防火墙配置
```cmd
# Windows防火墙开放3500端口（需管理员权限）
netsh advfirewall firewall add rule name="Django Port 3500" dir=in action=allow protocol=TCP localport=3500

# 验证规则
netsh advfirewall firewall show rule name="Django Port 3500"
```

详细配置请参考：[`docs/局域网部署说明.md`](docs/局域网部署说明.md)

## 代码风格与命名约定
- Python 代码按 PEP 8 使用四空格缩进，模块内函数保持单一职责；模型类采用 PascalCase，字段、工具函数与脚本文件使用 snake_case。
- Django 模板放在 `project/templates/` 内按业务子目录归档；管理后台自定义表单组件请单独封装在 `project/forms.py` 以利复用，避免重复逻辑。
- JavaScript 文件使用 camelCase 命名函数和变量，CSS 类名使用 kebab-case。

## 测试准则
- 默认使用 Django TestCase，测试入口统一在各应用的 `tests.py` 或 `tests/` 子包；测试函数命名为 `test_<场景>` 并覆盖成功与失败分支。
- 目前未设定强制覆盖率门槛，但提交前需至少运行 `python manage.py test`，并在 PR 描述中列出新增或受影响的测试用例。
- 涉及脚本的数据流程测试可借助 `data/fixtures/`（按需创建）存放脱敏样例，确保结果可重放。

## 提交与合并规范
- Git 历史采用动词开头的中文短语（示例：`修复高级筛选错误`、`添加供应商排名功能`），建议保持 50 字以内并描述目的而非实现细节。
- 发起 PR 前请确保通过测试、自检输出，以及说明变更范围、影响模块与手工验证步骤；若关联需求或缺陷，使用 `Refs #<编号>` 明确链接。
- 需要界面或数据示例时附上截图或关键日志片段，便于评审快速理解上下文。

## 配置与安全提示
- 生产与测试环境配置通过 `.env` 注入，切勿直接修改 `config/settings.py` 中的敏感常量；提交前确认 `.env` 未被加入版本控制。
- 数据导出、备份与临时脚本集中保存在 `backups/` 与 `logs/`，生成文件请在复核后清理，避免泄露供应商隐私。
- 当前配置 `DEBUG=True` 和 `ALLOWED_HOSTS=['*']` 仅适用于内网开发环境，不得用于公网或生产环境。

## 核心功能模块

### 1. 数据管理模块
- **采购管理** (`procurement/`): 采购计划、中标信息
- **合同管理** (`contract/`): 合同签订、补充协议、履约跟踪
- **付款管理** (`payment/`): 付款申请、审批流程
- **结算管理** (`settlement/`): 项目结算、对账
- **供应商评价** (`supplier_eval/`): 履约评分、评价记录

### 2. 监控与报表模块 (`project/services/`)
- **统计服务** (`statistics.py`): 数据汇总、金额统计、完成度分析
- **完整性监控** (`completeness.py`): 归档状态、数据完整性检查
- **排名服务** (`ranking.py`): 供应商排名、合同金额统计
- **报表生成** (`word_exporter.py`, `report_generator.py`): Word文档导出

### 3. 筛选与查询系统
- **全局筛选** (`project/filter_config.py`): 年份+项目级联筛选
- **高级筛选** (`project/utils/filters.py`): 多维度组合筛选
- **智能选择器** (`project/static/js/smart-selector.js`): 动态下拉选择

## 项目文件组织

### 配置文件
- `config/settings.py` - Django核心配置
- `config/urls.py` - 路由配置
- `.env` - 环境变量（不纳入版本控制）
- `.env.example` - 环境变量模板

### 数据文件
- `data/imports/` - 导入数据存放目录
- `data/exports/` - 导出文件存放目录
- `db.sqlite3` - SQLite数据库文件
- `backups/` - 数据库备份目录

### 文档目录
- `docs/局域网部署说明.md` - 网络配置和防火墙设置
- `docs/开发实践指南.md` - 开发规范和最佳实践
- `docs/数据模型使用手册.md` - 模型字段说明
- `docs/业务逻辑公式手册.md` - 统计和计算公式
- `docs/筛选系统使用指南.md` - 筛选功能说明
- `docs/性能优化说明.md` - 性能调优建议

## 常见问题

### Q1: 如何重置管理员密码？
```bash
python manage.py changepassword <username>
```

### Q2: 数据库被锁定怎么办？
```bash
# 关闭所有Django进程
taskkill /F /IM python.exe

# 或增加超时设置（config/settings.py）
DATABASES['default']['OPTIONS']['timeout'] = 20
```

### Q3: 局域网无法访问？
1. 确认使用 `0.0.0.0:3500` 启动
2. 检查防火墙是否开放3500端口
3. 确认 `ALLOWED_HOSTS = ['*']`

### Q4: Excel导入失败？
1. 确保使用 `.xlsx` 格式（不是 `.xls`）
2. 先运行 `python scripts\prepare_import_data.py <file.xlsx>` 预处理
3. 检查列名与模型字段对应关系

## 开发原则

本项目严格遵循以下软件工程原则：
- **KISS（简单至上）**: 选择最简单的技术方案
- **YAGNI（你不需要它）**: 只实现当前需要的功能
- **DRY（杜绝重复）**: 代码复用，避免冗余
- **SOLID（坚实基础）**: 模型单一职责，依赖抽象

## 技术栈

- **后端**: Django 4.2+ | Python 3.10+ | SQLite 3.x
- **前端**: Bootstrap 5.3 | JavaScript ES6+ | Chart.js
- **数据处理**: Pandas 2.0+ | openpyxl 3.1+
- **文档生成**: python-docx 1.1+
- **开发工具**: Git | VSCode | Django Debug Toolbar

## 相关文档

- [README.md](README.md) - 项目总览和快速开始
- [局域网部署说明](docs/局域网部署说明.md) - 详细的网络配置指南
- [开发实践指南](docs/开发实践指南.md) - 编码规范和开发流程
- [数据模型使用手册](docs/数据模型使用手册.md) - 数据库设计文档
- [筛选系统使用指南](docs/筛选系统使用指南.md) - 筛选功能使用说明

## 更新日志

### 2025-10-31
- ✅ 更新所有文档端口配置（8000 → 3500）
- ✅ 完善局域网部署说明文档
- ✅ 更新README.md，补充监控和报表功能说明
- ✅ 统一所有访问地址示例

### 2025-10-27
- ✅ 修复付款导入数据丢失问题
- ✅ 优化编号生成逻辑
- ✅ 增强数据完整性验证

---

**维护者**: 内部IT部门
**最后更新**: 2025-10-31
