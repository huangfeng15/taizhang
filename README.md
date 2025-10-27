# 项目采购与成本管理系统

**版本：** v2.0
**状态：** 生产就绪
**技术栈：** Python 3.10+ | Django 4.2 | SQLite | Django Admin

---

## 🎯 重大更新 (v2.0 - 2025-10-27)

### 修复：付款导入数据丢失问题

**问题：** CSV文件153条数据只导入141条，付款编号不连续

**原因：** 批量导入编号生成逻辑缺陷导致编号冲突

**修复：**
- ✅ 优化编号生成逻辑（简单递增计数器）
- ✅ 新增数据完整性验证机制
- ✅ 增强错误处理和事务保护
- ✅ 添加数据修复工具 [`repair_payment_data.py`](scripts/repair_payment_data.py)
- ✅ 完善单元测试覆盖

**详细文档：** [付款导入问题排查指南](docs/付款导入问题排查指南.md)

---

## 📋 项目简介

项目采购与成本管理系统是一套部署在公司内部局域网的轻量级数据管理平台，旨在将分散在多个Excel文件中的采购、合同、付款、结算及供应商评价数据进行集中化、结构化管理，提供统一的数据查询与追溯能力。

### 核心特性

✅ **5大核心模块**
- 采购管理 (Procurement)
- 合同管理 (Contract)
- 付款管理 (Payment)
- 结算管理 (Settlement)
- 供应商履约评价 (Supplier Evaluation)

✅ **智能数据导入**
- 标准长表Excel批量导入
- 历史宽表自动转换导入（核心功能）
- 数据验证与错误提示

✅ **强大的查询能力**
- 全局搜索（供应商、项目、合同）
- 关联数据一键追溯
- 多维度过滤与分类

✅ **简单易维护**
- 零配置SQLite数据库
- 自动每日备份
- 一行命令启动服务

---

## 🚀 快速开始

### 环境要求

- **操作系统：** Windows 10/11 或 Windows Server 2016+
- **Python：** 3.10 或更高版本
- **内存：** 4GB+ （推荐8GB）
- **磁盘：** 50GB+ 可用空间

### 安装步骤

#### 1. 克隆项目（或解压项目包）

```bash
# 如果使用Git
git clone <repository-url>
cd procurement_system

# 如果是压缩包
# 解压到 f:\kaifa\taizhang 或其他目录
```

#### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 初始化数据库

```bash
# 创建数据库表
python manage.py makemigrations
python manage.py migrate

# 创建管理员账户
python manage.py createsuperuser
# 输入用户名、邮箱（可选）、密码
```

#### 5. 启动服务器

```bash
# 局域网访问（推荐）
python manage.py runserver 0.0.0.0:8000

# 仅本机访问
python manage.py runserver
```

#### 6. 访问系统

打开浏览器，访问：
- **管理后台：** http://服务器IP:8000/admin
- **本机访问：** http://127.0.0.1:8000/admin

使用步骤4创建的管理员账户登录。

---

## 📚 项目文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| **详细开发计划** | [`plans/2025-10-20-procurement-system-dev-plan.md`](plans/2025-10-20-procurement-system-dev-plan.md) | 2周开发时间表、技术方案、风险应对 |
| **项目结构设计** | [`plans/2025-10-20-project-structure.md`](plans/2025-10-20-project-structure.md) | 完整目录结构、核心文件说明、数据模型关系 |
| **需求文档** | [`specs/需求文档.md`](specs/需求文档.md) | 业务需求、功能规格、用户角色 |
| **技术文档** | [`specs/技术文档-简化版.md`](specs/技术文档-简化版.md) | 技术选型、实施方案、代码示例 |

---

## 🗂️ 项目结构

```
procurement_system/
├── config/              # Django配置
├── procurement/         # 采购管理应用
├── contract/            # 合同管理应用
├── payment/             # 付款管理应用
├── settlement/          # 结算管理应用
├── supplier_eval/       # 供应商评价应用
├── data/                # 数据文件（导入/导出/模板）
├── docs/                # 文档
├── scripts/             # 运维脚本（备份/恢复）
├── backups/             # 数据库备份
├── logs/                # 日志文件
├── db.sqlite3           # SQLite数据库
├── manage.py            # Django管理脚本
└── requirements.txt     # Python依赖
```

---

## 💡 常用操作

### 数据导入

#### 标准长表导入

```bash
# 导入采购数据
python manage.py import_excel data/imports/procurement.xlsx

# 导入合同数据
python manage.py import_excel data/imports/contract.xlsx
```

#### 宽表转长表导入（付款数据）

```bash
# 将历史付款宽表转换为长表并导入
python manage.py convert_wide_to_long data/imports/payment_wide.xlsx
```

### 数据备份

```bash
# 手动备份
python scripts/backup_db.py

# 恢复备份
python scripts/restore_db.py
```

### 系统维护

```bash
# 查看系统健康状态
python scripts/health_check.py

# 清理7天前的旧日志
python manage.py clearlogs
```

---

## 🔧 配置说明

### 防火墙配置（Windows）

1. 打开 **控制面板** → **Windows Defender 防火墙** → **高级设置**
2. 点击 **入站规则** → **新建规则**
3. 选择 **端口** → **TCP** → **特定本地端口：8000**
4. **允许连接** → **所有配置文件** → 命名为"Django开发服务器"

### 自动备份配置

1. 打开 **任务计划程序**
2. **创建基本任务** → 名称：每日数据库备份
3. **触发器**：每天凌晨 2:00
4. **操作**：启动程序
   - 程序：`C:\path\to\venv\Scripts\python.exe`
   - 参数：`C:\path\to\scripts\backup_db.py`
   - 起始于：`C:\path\to\procurement_system`

---

## 📊 数据模型关系

```
Procurement (采购)
    ↓ 1:N
Contract (合同)
    ├─→ Payment (付款) [1:N]
    ├─→ Settlement (结算) [1:1]
    └─→ SupplierEvaluation (评价) [1:N]
```

**关键约束：**
- 补充协议必须关联主合同
- 累计付款不超过合同金额的120%
- 一个合同只能有一条结算记录

---

## 🛠️ 技术栈

| 组件 | 技术 | 版本 |
|-----|------|------|
| **后端框架** | Django | 4.2.7 |
| **数据库** | SQLite | 3.x（Python内置） |
| **数据处理** | Pandas | 2.0.3 |
| **Excel处理** | openpyxl | 3.1.2 |
| **前端** | Django Admin | 内置 |
| **Python** | CPython | 3.10+ |

---

## 📈 开发路线图

### ✅ 阶段一：MVP（当前阶段，2周）
- [x] 需求分析与技术选型
- [x] 详细开发计划
- [x] 项目结构设计
- [ ] Django项目初始化
- [ ] 5个模型定义
- [ ] Admin后台配置
- [ ] Excel导入功能
- [ ] 宽表转长表功能
- [ ] 部署与备份

### 🔲 阶段二：标准版（可选，+3周）
- [ ] Vue3前端开发
- [ ] RESTful API
- [ ] 自定义报表
- [ ] Waitress生产服务器

### 🔲 阶段三：企业版（可选，按需）
- [ ] PostgreSQL迁移
- [ ] Nginx反向代理
- [ ] 高可用部署
- [ ] 性能优化

---

## ❓ 常见问题

### Q1：忘记管理员密码怎么办？

```bash
python manage.py changepassword admin
```

### Q2：数据库被锁定怎么办？

检查是否有多个进程同时访问数据库。修改 `config/settings.py`：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 增加超时时间
        }
    }
}
```

### Q3：局域网无法访问怎么办？

1. 确认使用 `0.0.0.0:8000` 启动
2. 检查防火墙是否开放8000端口
3. 确认 `settings.py` 中 `ALLOWED_HOSTS = ['*']`

### Q4：Excel导入失败怎么办？

1. 确保Excel是 `.xlsx` 格式（不是 `.xls`）
2. 检查列名是否与模型字段对应
3. 查看错误日志：`logs/import_*.log`

---

## 📞 支持与反馈

- **技术文档：** [`docs/`](docs/) 目录
- **问题反馈：** 创建Issue或联系系统管理员
- **开发团队：** 内部IT部门

---

## 📜 许可证

本项目为公司内部使用，仅供授权人员访问。未经许可，禁止外传或商业使用。

---

## 🎯 设计原则

本项目严格遵循以下软件工程原则：

- **KISS（简单至上）**：选择最简单的技术方案
- **YAGNI（你不需要它）**：只实现当前需要的功能
- **DRY（杜绝重复）**：代码复用，避免冗余
- **SOLID（坚实基础）**：模型单一职责，依赖抽象

---

**祝您使用愉快！** 🚀

如有任何问题，请查阅 [`docs/`](docs/) 目录下的详细文档。