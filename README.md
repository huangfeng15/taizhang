# 项目采购与成本管理系统

**版本：** v2.5
**状态：** 生产就绪
**技术栈：** Python 3.10+ | Django 4.2 | SQLite | Django Admin

---

## 🎯 系统简介

项目采购与成本管理系统是一套部署在公司内部局域网的轻量级数据管理平台，旨在将分散在多个Excel文件中的采购、合同、付款、结算及供应商评价数据进行集中化、结构化管理，提供统一的数据查询、监控与报表生成能力。

### 核心特性

✅ **5大核心模块**
- 📋 采购管理 (Procurement) - 采购计划与中标信息管理
- 📝 合同管理 (Contract) - 合同签订与履约跟踪
- 💰 付款管理 (Payment) - 付款申请与审批流程
- ✔️ 结算管理 (Settlement) - 项目结算与对账
- ⭐ 供应商履约评价 (Supplier Evaluation) - 供应商表现评估

✅ **智能数据导入**
- Excel标准长表批量导入（支持采购、合同、付款、供应商评价）
- 数据验证与错误提示
- 导入模板自动生成

✅ **强大的监控与报表**
- 📊 实时数据统计（采购金额、合同执行、付款进度）
- 📈 完整性监控（归档状态、数据完整度分析）
- 🏆 供应商排名（按合同金额、履约评分）
- 📄 专业报表导出（Word格式，支持综合报告）

✅ **全局筛选与查询**
- 年份+项目级联筛选
- 全局搜索（供应商、项目、合同）
- 关联数据一键追溯
- 高级筛选（多维度组合）

✅ **简单易维护**
- 零配置SQLite数据库
- 响应式界面设计
- 一行命令启动服务

---

## 🚀 快速开始

### 环境要求

- **操作系统：** Windows 10/11 或 Windows Server 2016+
- **Python：** 3.10 或更高版本
- **内存：** 4GB+ （推荐8GB）
- **磁盘：** 50GB+ 可用空间
- **网络：** 局域网环境

### 安装步骤

#### 1. 获取项目代码

```bash
# 如果使用Git
git clone <repository-url>
cd taizhang

# 如果是压缩包
# 解压到 f:\kaifa\taizhang 或其他目录
```

#### 2. 创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 初始化数据库

```bash
# 创建数据库表
python manage.py migrate

# 创建管理员账户
python manage.py createsuperuser
# 输入用户名、邮箱（可选）、密码
```

#### 5. 启动局域网服务

```bash
# 启动局域网服务（推荐）
python manage.py runserver 0.0.0.0:3500

# 仅本机访问
python manage.py runserver 127.0.0.1:3500
```

#### 6. 访问系统

**查看本机IP地址：**
```bash
# Windows
ipconfig | findstr "IPv4"

# 显示示例：IPv4 地址 . . . . . . . . . . . . : 10.168.3.240
```

**访问地址：**
- **本机访问：** http://127.0.0.1:3500 或 http://localhost:3500
- **局域网访问：** http://10.168.3.240:3500 （替换为您的实际IP）
- **管理后台：** http://10.168.3.240:3500/admin/
- **数据监控：** http://10.168.3.240:3500/monitoring/
- **报表导出：** http://10.168.3.240:3500/reports/

使用步骤4创建的管理员账户登录。

---

## 📚 项目文档

### 核心文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| **局域网部署说明** | [`docs/局域网部署说明.md`](docs/局域网部署说明.md) | 防火墙配置、网络设置、故障排查 |
| **开发实践指南** | [`docs/开发实践指南.md`](docs/开发实践指南.md) | 代码规范、测试标准、Git工作流 |
| **数据模型使用手册** | [`docs/数据模型使用手册.md`](docs/数据模型使用手册.md) | 模型字段说明、关系图、业务规则 |
| **业务逻辑公式手册** | [`docs/业务逻辑公式手册.md`](docs/业务逻辑公式手册.md) | 统计计算、数据聚合、验证规则 |
| **筛选系统使用指南** | [`docs/筛选系统使用指南.md`](docs/筛选系统使用指南.md) | 全局筛选、高级筛选、智能选择器 |

### 技术文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| **系统架构分析** | [`docs/系统架构分析文档.md`](docs/系统架构分析文档.md) | 技术架构、模块设计、数据流 |
| **性能优化说明** | [`docs/性能优化说明.md`](docs/性能优化说明.md) | 查询优化、缓存策略、并发处理 |
| **报表系统文档** | [`docs/comprehensive_report_system.md`](docs/comprehensive_report_system.md) | 报表生成、Word导出、模板配置 |

### 规范文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| **代码规范** | [`AGENTS.md`](AGENTS.md) | 项目结构、命名约定、提交规范 |
| **专业术语词汇表** | [`docs/专业术语词汇表.md`](docs/专业术语词汇表.md) | 业务术语、缩写对照 |

---

## 🗂️ 项目结构

```
taizhang/
├── config/                  # Django全局配置
│   ├── settings.py         # 核心设置（数据库、中间件、应用）
│   ├── urls.py             # 路由配置
│   └── wsgi.py             # WSGI部署入口
├── project/                 # 项目管理核心应用
│   ├── models.py           # 项目模型
│   ├── admin.py            # 管理后台配置
│   ├── views.py            # 视图逻辑（监控、报表）
│   ├── forms.py            # 表单与验证
│   ├── filter_config.py    # 筛选配置
│   ├── services/           # 业务服务层
│   │   ├── statistics.py   # 统计服务
│   │   ├── completeness.py # 完整性分析
│   │   ├── ranking.py      # 排名服务
│   │   └── word_exporter.py # Word导出
│   ├── templates/          # 前端模板
│   └── static/             # 静态资源（CSS/JS）
├── procurement/             # 采购管理应用
│   ├── models.py           # 采购模型
│   ├── admin.py            # 采购管理后台
│   └── management/commands/ # 数据导入命令
├── contract/                # 合同管理应用
├── payment/                 # 付款管理应用
├── settlement/              # 结算管理应用
├── supplier_eval/           # 供应商评价应用
├── data/                    # 数据文件
│   ├── imports/            # 导入数据存放
│   └── exports/            # 导出文件存放
├── docs/                    # 文档目录
├── scripts/                 # 运维脚本
│   ├── prepare_import_data.py  # 数据预处理
│   └── query_database.py   # 数据库查询工具
├── backups/                 # 数据库备份
├── logs/                    # 日志文件
├── db.sqlite3               # SQLite数据库
├── manage.py                # Django管理脚本
├── requirements.txt         # Python依赖
├── AGENTS.md               # 开发规范
└── README.md               # 本文件
```

---

## 💡 常用操作

### 数据导入

#### Excel数据导入

```bash
# 导入采购数据
python manage.py import_excel data/imports/procurement.xlsx

# 导入合同数据
python manage.py import_excel data/imports/contract.xlsx

# 导入付款数据
python manage.py import_excel data/imports/payment.xlsx

# 导入供应商评价数据
python manage.py import_excel data/imports/supplier_eval.xlsx
```

#### 数据预处理（推荐）

```bash
# 预处理Excel文件，检查格式和数据完整性
python scripts/prepare_import_data.py data/imports/source.xlsx
```

### 系统维护

```bash
# 查看系统状态
python manage.py check

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建管理员
python manage.py createsuperuser

# 设置员工权限
python manage.py set_staff_permission <username>

# 运行测试
python manage.py test

# 清理所有数据（慎用）
python manage.py clear_all_data
```

### 数据查询

```bash
# 使用交互式查询工具
python scripts/query_database.py

# 检查表统计信息
python scripts/test_procurement_dedup_statistics.py
```

---

## 🔧 配置说明

### 防火墙配置（Windows）

**方式一：图形界面**
1. 打开 **控制面板** → **Windows Defender 防火墙** → **高级设置**
2. 点击 **入站规则** → **新建规则**
3. 选择 **端口** → **TCP** → **特定本地端口：3500**
4. **允许连接** → **所有配置文件** → 命名为"Django项目管理系统"

**方式二：命令行（需管理员权限）**
```cmd
netsh advfirewall firewall add rule name="Django Port 3500" dir=in action=allow protocol=TCP localport=3500
```

### 环境变量配置

创建 `.env` 文件（参考 `.env.example`）：

```env
# Django配置
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*

# 数据库配置（默认使用SQLite，无需配置）
# DATABASE_URL=sqlite:///db.sqlite3
```

---

## 📊 数据模型关系

```
Project (项目基础信息)
    ↓ 1:N
Procurement (采购信息)
    ↓ 1:N
Contract (合同信息)
    ├─→ Payment (付款记录) [1:N]
    ├─→ Settlement (结算记录) [1:1]
    └─→ SupplierEvaluation (供应商评价) [1:N]
```

**关键业务规则：**
- 项目编号全局唯一，作为核心关联字段
- 补充协议必须关联主合同
- 累计付款不超过合同金额的120%（含预警机制）
- 一个合同只能有一条结算记录
- 供应商评价与合同一对多关联

---

## 🛠️ 技术栈

| 组件 | 技术 | 版本 | 用途 |
|-----|------|------|------|
| **后端框架** | Django | 4.2+ | Web框架、ORM、Admin |
| **数据库** | SQLite | 3.x | 轻量级关系数据库 |
| **数据处理** | Pandas | 2.0+ | Excel处理、数据分析 |
| **Excel操作** | openpyxl | 3.1+ | Excel读写 |
| **Word生成** | python-docx | 1.1+ | 报表文档生成 |
| **前端框架** | Bootstrap | 5.3 | 响应式UI |
| 
| **图表库** | Chart.js | 3.x | 数据可视化 |
| **Python** | CPython | 3.10+ | 运行环境 |

---

## ❓ 常见问题

### Q1：忘记管理员密码怎么办？

```bash
python manage.py changepassword admin
```

### Q2：数据库被锁定怎么办？

```bash
# 方法1：关闭所有Django进程
taskkill /F /IM python.exe

# 方法2：增加超时设置
# 在 config/settings.py 中修改：
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

1. **确认启动方式正确**
   ```bash
   python manage.py runserver 0.0.0.0:3500  # ✅ 正确
   python manage.py runserver 127.0.0.1:3500  # ❌ 错误（仅本机）
   ```

2. **检查防火墙是否开放3500端口**
   ```cmd
   netsh advfirewall firewall add rule name="Django Port 3500" dir=in action=allow protocol=TCP localport=3500
   ```

3. **确认配置正确**
   - 在 `config/settings.py` 中确认 `ALLOWED_HOSTS = ['*']`

4. **测试网络连通性**
   ```bash
   # 在客户端设备上ping服务器
   ping 10.168.3.240
   ```

### Q4：Excel导入失败怎么办？

1. **确保使用正确格式**
   - 使用 `.xlsx` 格式（不是 `.xls`）
   
2. **预处理数据**
   ```bash
   python scripts/prepare_import_data.py data/imports/source.xlsx
   ```

3. **检查列名对应关系**
   - 参考 `project/import_templates/` 目录下的模板文件
   - 确保Excel列名与模型字段一致

4. **查看错误日志**
   - 控制台会显示详细错误信息
   - 检查 `logs/` 目录下的日志文件

### Q5：如何重置所有数据？

⚠️ **警告：此操作不可恢复，请先备份数据库！**

```bash
# 清理所有数据
python manage.py clear_all_data

# 或手动删除数据库后重新初始化
del db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Q6：端口被占用怎么办？

```cmd
# 查找占用3500端口的进程
netstat -ano | findstr "3500"

# 结束进程（替换PID为实际值）
taskkill /F /PID <PID>

# 或使用其他端口
python manage.py runserver 0.0.0.0:3501
```

### Q7：如何导出数据？

1. **通过报表系统导出**
   - 访问 http://服务器IP:3500/reports/
   - 选择报表类型和导出格式
   - 系统自动生成Word文档

2. **通过管理后台导出**
   - 进入 http://服务器IP:3500/admin/
   - 选择要导出的数据
   - 使用Admin的导出功能

3. **数据库直接导出**
   ```bash
   # 导出整个数据库
   python scripts/query_database.py
   ```

---

## 🔐 安全建议

### 开发环境（当前配置）

✅ **适用场景：**
- 内部局域网部署
- 开发和测试环境
- 小型团队使用（<20人）

⚠️ **安全提示：**
- 定期更改管理员密码
- 限制管理员账户数量
- 不要暴露到公网
- 定期备份数据

### 生产环境建议

如需正式生产部署，应进行以下升级：

1. **安全配置**
   ```python
   # config/settings.py
   DEBUG = False
   ALLOWED_HOSTS = ['192.168.1.100', 'project.company.com']
   SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')  # 使用环境变量
   ```

2. **数据库升级**
   - 从SQLite迁移到PostgreSQL或MySQL
   - 支持更高并发和更好性能

3. **Web服务器**
   - 使用Gunicorn或Waitress替代开发服务器
   - 配置Nginx作为反向代理

4. **HTTPS配置**
   - 申请SSL证书
   - 配置HTTPS加密传输

5. **监控与日志**
   - 配置日志收集
   - 设置性能监控
   - 启用访问审计

---

## 📊 系统功能概览

### 数据管理

- ✅ 采购信息管理（采购计划、中标公告）
- ✅ 合同管理（主合同、补充协议）
- ✅ 付款记录管理（付款申请、审批流程）
- ✅ 结算管理（项目结算、对账记录）
- ✅ 供应商评价（履约评分、评价记录）

### 数据监控

- 📊 **统计分析** - 采购金额、合同执行、付款进度实时统计
- 📈 **完整性监控** - 归档状态、数据完整度分析
- 🏆 **供应商排名** - 按合同金额、履约评分排序
- 🔄 **更新监控** - 数据更新时间追踪

### 报表导出

- 📄 综合报告（Word格式）
- 📋 专业报表（自定义模板）
- 📊 统计图表（可视化展示）

### 筛选查询

- 🔍 全局搜索（供应商、项目、合同）
- 📅 年份+项目级联筛选
- 🎯 高级筛选（多维度组合）
- 🔗 关联数据追溯

---

## 📈 更新日志

### v2.5 (2025-10-31)
- ✅ 更新所有文档端口配置（8000 → 3500）
- ✅ 完善局域网部署说明文档
- ✅ 更新README.md，补充监控和报表功能说明
- ✅ 统一所有访问地址示例

### v2.0 (2025-10-27)
- ✅ 修复付款导入数据丢失问题
- ✅ 优化编号生成逻辑
- ✅ 增强数据完整性验证
- ✅ 添加数据修复工具

### v1.5 (2025-10-23)
- ✅ 实现数据监控系统
- ✅ 添加统计分析功能
- ✅ 完成报表导出功能
- ✅ 优化筛选系统

### v1.0 (2025-10-20)
- ✅ 完成核心数据模型设计
- ✅ 实现Excel数据导入
- ✅ 搭建Admin管理后台
- ✅ 实现全局筛选功能

---

## 📞 技术支持

### 文档资源

- **完整文档**：查看 [`docs/`](docs/) 目录
- **开发指南**：[`docs/开发实践指南.md`](docs/开发实践指南.md)
- **部署文档**：[`docs/局域网部署说明.md`](docs/局域网部署说明.md)

### 问题反馈

- 创建Issue描述问题
- 联系系统管理员
- 查看错误日志进行排查

### 开发团队

- **维护者**：内部IT部门
- **技术支持**：提供内部技术支持

---

## 📜 许可证

本项目为公司内部使用，仅供授权人员访问。未经许可，禁止外传或商业使用。

---

## 🎯 设计原则

本项目严格遵循以下软件工程原则：

- **KISS（简单至上）** - 选择最简单的技术方案
- **YAGNI（你不需要它）** - 只实现当前需要的功能
- **DRY（杜绝重复）** - 代码复用，避免冗余
- **SOLID（坚实基础）** - 模型单一职责，依赖抽象

---

**祝您使用愉快！** 🚀

如有任何问题，请查阅 [`docs/`](docs/) 目录下的详细文档或联系技术支持团队。

---

**最后更新：** 2025-10-31  
**版本：** v2.5  
**维护者：** 内部IT部门