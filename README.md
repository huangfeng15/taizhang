# 项目采购与成本管理系统

**版本：** v3.0
**状态：** 生产就绪
**技术栈：** Python 3.10+ | Django 4.2 | SQLite | Bootstrap 5 | Chart.js

---

## 🎯 系统简介

项目采购与成本管理系统是一套专为企业内部设计的轻量级数据管理平台。它采用 **“Django Admin + 自定义前端”** 的混合架构，旨在将分散在Excel中的采购、合同、付款、结算及供应商评价数据进行集中化、结构化管理，并提供强大的数据监控、统计分析与报表生成能力。

### ✨ 核心特性

- **五大核心模块**: 覆盖从采购到结算的全业务流程。
- **智能数据导入**: 支持Excel长/宽表格式，内置数据校验。
- **监控驾驶舱**: 实时洞察归档进度、数据完整性与更新动态。
- **深度统计分析**: 提供多维度的数据透视与图表可视化。
- **专业报表导出**: 一键生成结构化的Word格式周报、月报、年报。
- **现代化前端交互**:
  - **智能选择器**: 支持搜索、分页与级联筛选。
  - **前端编辑/新增**: 通过模态框实现流畅的数据操作体验。
  - **全局筛选**: 跨页面的年份、项目联动筛选。

---

## 🚀 快速开始

### 1. 环境要求
- **操作系统**: Windows 10/11 或 Windows Server 2016+
- **Python**: 3.10 或更高版本

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

# 5. 启动局域网服务
python manage.py runserver 0.0.0.0:3500
```

### 3. 访问系统
- **查看本机IP**: 在命令行运行 `ipconfig`。
- **访问地址**: `http://<你的IP地址>:3500`
- **管理后台**: `http://<你的IP地址>:3500/admin/`

---

## 🗂️ 项目结构

```
taizhang/
├── config/              # Django全局配置 (settings.py, urls.py)
├── project/             # 核心主应用
│   ├── services/        # ★ 业务服务层 (统计、监控、报表逻辑)
│   ├── templates/       # ★ 自定义前端页面
│   ├── static/          # ★ CSS/JS等静态资源
│   ├── views.py         # 视图函数
│   └── models.py        # 项目模型
├── procurement/         # 采购应用
├── contract/            # 合同应用
├── payment/             # 付款应用
├── settlement/          # 结算应用
├── supplier_eval/       # 供应商评价应用
├── docs/                # 项目文档
├── scripts/             # 辅助脚本
├── db.sqlite3           # 数据库文件
├── manage.py            # Django管理入口
├── requirements.txt     # Python依赖
└── DEVELOPMENT.md       # ★ 开发与贡献指南
```

---

## 📚 项目文档

| 文档 | 路径 | 说明 |
| :--- | :--- | :--- |
| **开发与贡献指南** | [`DEVELOPMENT.md`](DEVELOPMENT.md) | **必读**。项目结构、开发命令、代码规范。 |
| **系统架构分析** | [`docs/系统架构分析文档.md`](docs/系统架构分析文档.md) | 技术架构、模块设计、数据流。 |
| **数据模型手册** | [`docs/数据模型使用手册.md`](docs/数据模型使用手册.md) | 模型字段、关系图、业务规则。 |
| **局域网部署说明** | [`docs/局域网部署说明.md`](docs/局域网部署说明.md) | 防火墙配置、网络设置。 |
| **性能优化指南** | [`docs/性能优化说明.md`](docs/性能优化说明.md) | 查询优化、缓存策略、前端性能。 |
| **专业术语词汇表** | [`docs/专业术语词汇表.md`](docs/专业术语词汇表.md) | 统一的业务与技术术语定义。 |

---

## 💡 常用命令

### 数据导入
```bash
# 导入采购数据 (支持 .xlsx 和 .csv)
python manage.py import_excel data/imports/procurement.xlsx
```

### 系统维护
```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 清理所有数据 (危险操作，会清空数据库！)
python manage.py clear_all_data
```

---

## ❓ 常见问题

**Q: 局域网其他电脑无法访问？**
A: 1. 确保启动命令是 `python manage.py runserver 0.0.0.0:3500`。 2. 检查服务器的Windows防火墙是否已为TCP 3500端口添加入站规则。

**Q: 忘记管理员密码？**
A: 运行 `python manage.py changepassword <你的管理员用户名>`。

**Q: Excel导入失败？**
A: 1. 确认文件是 `.xlsx` 格式。 2. 使用 `scripts/prepare_import_data.py` 脚本预处理数据。 3. 检查Excel的列名是否与 `project/import_templates/` 下的模板一致。

---

**最后更新：** 2025-10-31