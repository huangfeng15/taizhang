# 项目采购与成本管理系统 — 项目结构设计

**文档版本：** v1.0  
**编写日期：** 2025-10-20  
**关联文档：** [详细开发计划](2025-10-20-procurement-system-dev-plan.md)

---

## 1. 整体架构概览

```
项目采购与成本管理系统
├── Django后端（Python 3.10+）
│   ├── 5个业务应用（procurement, contract, payment, settlement, supplier_eval）
│   ├── SQLite数据库（文件型，零配置）
│   └── Django Admin后台（内置UI）
├── 数据导入工具（Django管理命令）
│   ├── 标准长表导入
│   └── 宽表转长表智能转换
└── 运维工具
    ├── 自动备份脚本
    └── 部署文档
```

---

## 2. 完整目录结构

```
procurement_system/                  # 项目根目录
│
├── config/                          # Django项目配置目录
│   ├── __init__.py
│   ├── settings.py                  # 核心配置文件
│   │   ├── DATABASES（SQLite配置）
│   │   ├── INSTALLED_APPS（5个业务应用）
│   │   ├── LANGUAGE_CODE = 'zh-hans'
│   │   ├── TIME_ZONE = 'Asia/Shanghai'
│   │   └── ALLOWED_HOSTS（局域网访问）
│   ├── urls.py                      # URL路由配置
│   │   └── path('admin/', admin.site.urls)
│   ├── asgi.py                      # ASGI配置（异步）
│   └── wsgi.py                      # WSGI配置（生产部署）
│
├── procurement/                     # 采购管理应用
│   ├── migrations/                  # 数据库迁移文件
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── management/                  # 自定义管理命令
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── import_excel.py      # Excel导入命令
│   │           ├── handle()         # 主执行函数
│   │           ├── validate_data()  # 数据验证
│   │           └── import_row()     # 单行导入逻辑
│   ├── __init__.py
│   ├── models.py                    # Procurement数据模型
│   │   ├── Procurement(BaseModel)
│   │   │   ├── procurement_code (PK)
│   │   │   ├── project_name（必填）
│   │   │   ├── winning_unit
│   │   │   ├── winning_amount
│   │   │   └── ... (35+字段)
│   │   └── Meta配置
│   ├── admin.py                     # Django Admin配置
│   │   ├── ProcurementAdmin
│   │   │   ├── list_display
│   │   │   ├── search_fields
│   │   │   ├── list_filter
│   │   │   └── fieldsets（字段分组）
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 单元测试
│   └── views.py                     # 视图（本阶段不使用）
│
├── contract/                        # 合同管理应用
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py                    # Contract数据模型
│   │   ├── Contract(BaseModel)
│   │   │   ├── contract_code (PK)
│   │   │   ├── contract_name（必填）
│   │   │   ├── contract_type（枚举）
│   │   │   ├── parent_contract (ForeignKey, self)
│   │   │   ├── procurement (ForeignKey)
│   │   │   └── clean()方法（业务规则验证）
│   │   └── Meta配置
│   ├── admin.py                     # ContractAdmin
│   │   ├── autocomplete_fields
│   │   └── inline展示关联数据
│   ├── apps.py
│   └── tests.py
│
├── payment/                         # 付款管理应用
│   ├── migrations/
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── convert_wide_to_long.py  # 宽表转长表（核心功能）
│   │           ├── handle()
│   │           ├── identify_date_columns()  # 识别日期列
│   │           ├── parse_month_to_date()    # 日期解析
│   │           ├── convert_wide_to_long()   # Pandas.melt()
│   │           └── import_long_data()       # 批量导入
│   ├── __init__.py
│   ├── models.py                    # Payment数据模型
│   │   ├── Payment(BaseModel)
│   │   │   ├── payment_code (PK)
│   │   │   ├── contract (ForeignKey)
│   │   │   ├── payment_amount
│   │   │   ├── payment_date
│   │   │   └── clean()方法（120%金额验证）
│   │   └── Meta配置
│   ├── admin.py                     # PaymentAdmin
│   ├── apps.py
│   └── tests.py
│
├── settlement/                      # 结算管理应用
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py                    # Settlement数据模型
│   │   ├── Settlement(BaseModel)
│   │   │   ├── settlement_code (PK)
│   │   │   ├── contract (OneToOneField)
│   │   │   ├── final_amount
│   │   │   └── completion_date
│   │   └── Meta配置
│   ├── admin.py                     # SettlementAdmin
│   ├── apps.py
│   └── tests.py
│
├── supplier_eval/                   # 供应商履约评价应用
│   ├── migrations/
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── convert_eval_wide_to_long.py
│   ├── __init__.py
│   ├── models.py                    # SupplierEvaluation数据模型
│   │   ├── SupplierEvaluation(BaseModel)
│   │   │   ├── evaluation_code (PK)
│   │   │   ├── contract (ForeignKey)
│   │   │   ├── supplier_name
│   │   │   ├── score
│   │   │   └── evaluation_type
│   │   └── Meta配置
│   ├── admin.py                     # SupplierEvaluationAdmin
│   ├── apps.py
│   └── tests.py
│
├── db.sqlite3                       # SQLite数据库文件（运行后生成）
│
├── backups/                         # 数据库备份目录
│   ├── .gitkeep
│   ├── db_backup_20251020_020000.sqlite3
│   └── db_backup_20251019_020000.sqlite3
│
├── logs/                            # 日志目录
│   ├── .gitkeep
│   ├── error.log                    # 错误日志
│   ├── import_20251020.log          # 导入日志
│   └── debug.log                    # 调试日志
│
├── data/                            # 数据文件目录
│   ├── imports/                     # 待导入的Excel文件
│   │   ├── .gitkeep
│   │   ├── procurement_raw.xlsx     # 采购原始数据
│   │   ├── contract_raw.xlsx        # 合同原始数据
│   │   ├── payment_wide.xlsx        # 付款宽表
│   │   └── evaluation_wide.xlsx    # 评价宽表
│   ├── exports/                     # 导出的数据文件
│   │   ├── .gitkeep
│   │   └── report_20251020.xlsx
│   └── templates/                   # Excel导入模板
│       ├── 采购数据导入模板.xlsx
│       ├── 合同数据导入模板.xlsx
│       ├── 付款宽表模板.xlsx
│       └── 供应商评价宽表模板.xlsx
│
├── docs/                            # 文档目录
│   ├── 部署指南.md
│   │   ├── Windows环境准备
│   │   ├── Python安装
│   │   ├── 项目初始化
│   │   ├── 防火墙配置
│   │   └── 备份脚本配置
│   ├── 用户手册.md
│   │   ├── 登录说明
│   │   ├── 数据录入
│   │   ├── 数据查询
│   │   ├── 数据导入
│   │   └── 常见问题
│   ├── 管理员手册.md
│   │   ├── 用户管理
│   │   ├── 权限配置
│   │   ├── 数据备份
│   │   └── 系统维护
│   ├── 数据字典.md
│   │   ├── 采购模块字段说明
│   │   ├── 合同模块字段说明
│   │   ├── 付款模块字段说明
│   │   ├── 结算模块字段说明
│   │   └── 评价模块字段说明
│   ├── API文档.md（阶段二需要）
│   └── 故障排查.md
│       ├── 数据库锁定
│       ├── 导入失败
│       ├── 防火墙问题
│       └── 性能优化
│
├── scripts/                         # 运维脚本目录
│   ├── backup_db.py                 # 每日自动备份脚本
│   │   ├── backup_database()
│   │   ├── cleanup_old_backups()
│   │   └── send_notification()
│   ├── restore_db.py                # 数据库恢复脚本
│   │   ├── list_backups()
│   │   ├── restore_from_backup()
│   │   └── validate_restore()
│   ├── init_db.py                   # 数据库初始化脚本
│   │   ├── create_superuser()
│   │   ├── load_sample_data()
│   │   └── verify_setup()
│   └── health_check.py              # 系统健康检查脚本
│       ├── check_db_connection()
│       ├── check_disk_space()
│       └── check_backup_status()
│
├── tests/                           # 集中式测试目录（可选）
│   ├── __init__.py
│   ├── test_models.py               # 模型测试
│   │   ├── test_procurement_model()
│   │   ├── test_contract_validation()
│   │   └── test_payment_amount_limit()
│   ├── test_import.py               # 导入功能测试
│   │   ├── test_standard_import()
│   │   └── test_wide_to_long()
│   └── test_admin.py                # Admin后台测试
│       ├── test_search_filter()
│       └── test_autocomplete()
│
├── static/                          # 静态文件目录（collectstatic后生成）
│   ├── admin/                       # Django Admin静态文件
│   └── css/                         # 自定义CSS（可选）
│
├── media/                           # 媒体文件目录（上传文件）
│   └── .gitkeep
│
├── venv/                            # 虚拟环境目录（.gitignore）
│
├── manage.py                        # Django管理脚本
├── requirements.txt                 # Python依赖列表
│   ├── Django==4.2.7
│   ├── pandas==2.0.3
│   ├── openpyxl==3.1.2
│   └── python-dateutil==2.8.2
├── requirements-dev.txt             # 开发环境依赖（可选）
│   ├── pytest==7.4.0
│   ├── pytest-django==4.5.2
│   └── black==23.7.0
├── .gitignore                       # Git忽略文件
│   ├── *.pyc
│   ├── __pycache__/
│   ├── db.sqlite3
│   ├── venv/
│   ├── backups/
│   └── logs/
├── .env.example                     # 环境变量模板
│   ├── SECRET_KEY=
│   ├── DEBUG=True
│   └── ALLOWED_HOSTS=
├── README.md                        # 项目说明文档
│   ├── 项目简介
│   ├── 快速开始
│   ├── 功能特性
│   ├── 技术栈
│   └── 联系方式
└── LICENSE                          # 许可证文件（可选）
```

---

## 3. 核心文件详细说明

### 3.1 [`config/settings.py`](config/settings.py) — 核心配置

```python
# 基础配置
SECRET_KEY = 'your-secret-key-here'
DEBUG = True
ALLOWED_HOSTS = ['*']  # 开发环境允许所有主机

# 应用注册
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 业务应用
    'procurement.apps.ProcurementConfig',
    'contract.apps.ContractConfig',
    'payment.apps.PaymentConfig',
    'settlement.apps.SettlementConfig',
    'supplier_eval.apps.SupplierEvalConfig',
]

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 防止锁定
        }
    }
}

# 国际化配置
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# 静态文件
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Admin站点自定义
ADMIN_SITE_HEADER = '项目采购与成本管理系统'
ADMIN_SITE_TITLE = '采购管理'
ADMIN_INDEX_TITLE = '欢迎使用项目采购与成本管理系统'
```

### 3.2 [`manage.py`](manage.py) — Django管理脚本

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

**常用命令：**
```bash
python manage.py runserver 0.0.0.0:8000      # 启动服务器
python manage.py makemigrations               # 创建迁移文件
python manage.py migrate                      # 执行迁移
python manage.py createsuperuser              # 创建超级用户
python manage.py import_excel data.xlsx       # 导入Excel
python manage.py convert_wide_to_long pay.xlsx  # 宽表转长表
python manage.py shell                        # Django Shell
```

### 3.3 [`requirements.txt`](requirements.txt) — 依赖管理

```txt
# 核心框架
Django==4.2.7

# 数据处理
pandas==2.0.3
openpyxl==3.1.2
python-dateutil==2.8.2

# 可选依赖
# xlrd==2.0.1           # 处理旧版.xls文件
# django-import-export  # 高级导入导出功能
```

### 3.4 [`scripts/backup_db.py`](scripts/backup_db.py) — 备份脚本

```python
"""
数据库每日自动备份脚本
配置Windows任务计划程序每日凌晨2:00执行
"""
import shutil
import datetime
import os
from pathlib import Path

def backup_database():
    """备份SQLite数据库"""
    # 项目根目录
    base_dir = Path(__file__).resolve().parent.parent
    source = base_dir / 'db.sqlite3'
    backup_dir = base_dir / 'backups'
    
    # 创建备份目录
    backup_dir.mkdir(exist_ok=True)
    
    # 生成备份文件名（带时间戳）
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'db_backup_{timestamp}.sqlite3'
    
    # 复制数据库文件
    shutil.copy2(source, backup_file)
    print(f"✓ 数据库已备份到: {backup_file}")
    
    # 清理7天前的旧备份
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
    for file in backup_dir.glob('db_backup_*.sqlite3'):
        file_time = datetime.datetime.fromtimestamp(file.stat().st_ctime)
        if file_time < cutoff_time:
            file.unlink()
            print(f"✓ 已删除旧备份: {file.name}")

if __name__ == '__main__':
    backup_database()
```

---

## 4. 数据模型关系图

```
┌─────────────────┐
│   Procurement   │ 采购信息（独立表）
│  招采编号 (PK)   │
└────────┬────────┘
         │
         │ 1:N（一个采购多个合同）
         │
         ▼
┌─────────────────┐
│    Contract     │ 合同信息
│  合同编号 (PK)   │
│  关联采购 (FK)   │────────┐
│  关联主合同 (FK) │◄───────┘ 自关联（补充协议）
└────────┬────────┘
         │
         ├──────────┐
         │          │
         │ 1:N      │ 1:1
         │          │
         ▼          ▼
┌─────────────┐  ┌─────────────┐
│   Payment   │  │ Settlement  │
│ 付款编号(PK) │  │ 结算编号(PK) │
│ 关联合同(FK) │  │ 关联合同(FK) │
└─────────────┘  └─────────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────────┐
│ SupplierEvaluation   │
│    评价编号 (PK)      │
│    关联合同 (FK)      │
└──────────────────────┘
```

**关系说明：**
- Procurement → Contract：一对多（一个采购可以有多个合同）
- Contract → Contract：自关联（一个主合同可以有多个补充协议）
- Contract → Payment：一对多（一个合同可以有多次付款）
- Contract → Settlement：一对一（一个合同只有一次结算）
- Contract → SupplierEvaluation：一对多（一个合同可以有多次评价）

---

## 5. 工作流程图

### 5.1 数据导入流程

```
开始
  │
  ├─→ 标准长表导入
  │     │
  │     ├─ 1. 读取Excel文件 (pandas)
  │     ├─ 2. 数据验证（必填字段、格式检查）
  │     ├─ 3. update_or_create（避免重复）
  │     ├─ 4. 记录成功/失败
  │     └─ 5. 输出导入报告
  │
  └─→ 宽表转长表导入
        │
        ├─ 1. 读取宽表Excel
        ├─ 2. 识别日期列（正则匹配）
        ├─ 3. Pandas.melt() 逆透视
        ├─ 4. 清理空值、无效数据
        ├─ 5. 生成业务编号
        ├─ 6. 验证关联合同存在
        ├─ 7. 批量导入数据库
        └─ 8. 输出转换报告
```

### 5.2 数据查询流程

```
用户访问Admin后台
  │
  ├─→ 列表页
  │     ├─ 搜索框输入关键字
  │     ├─ 过滤器选择条件
  │     ├─ 分页显示结果
  │     └─ 点击记录查看详情
  │
  └─→ 详情页
        ├─ 显示所有字段
        ├─ 关联数据超链接
        │   ├─ 采购 → 关联的所有合同
        │   ├─ 合同 → 关联的所有付款
        │   ├─ 合同 → 关联的结算
        │   └─ 合同 → 关联的评价
        └─ 编辑/删除按钮
```

---

## 6. 技术选型理由

| 技术 | 选型 | 理由 | 替代方案 |
|-----|------|------|---------|
| **Web框架** | Django 4.2 | 内置Admin、ORM、安全性高 | Flask（更轻量但需手写后台） |
| **数据库** | SQLite | 零配置、文件型、备份简单 | PostgreSQL（需独立安装） |
| **前端** | Django Admin | 内置、美观、功能完整 | Vue3（需额外开发3周） |
| **数据处理** | Pandas | Excel处理强大、宽表转长表 | xlrd（功能有限） |
| **服务器** | 开发服务器 | 一行命令启动 | Nginx+Gunicorn（配置复杂） |

---

## 7. 扩展性设计

### 7.1 阶段二：添加Vue前端（可选）

```
procurement_system/
├── backend/                 # 重命名原Django项目
│   ├── config/
│   ├── procurement/
│   └── ...
├── frontend/                # 新增Vue3前端
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   ├── api/            # API调用
│   │   └── router/         # 路由配置
│   ├── package.json
│   └── vite.config.js
└── docker-compose.yml       # 容器化部署（可选）
```

### 7.2 阶段三：PostgreSQL迁移（可选）

**迁移步骤：**
1. 安装PostgreSQL
2. 修改 `settings.py` 数据库配置
3. 导出SQLite数据：`python manage.py dumpdata > data.json`
4. 导入PostgreSQL：`python manage.py loaddata data.json`
5. 配置pgAdmin监控

---

## 8. 安全性设计

### 8.1 数据安全
- **业务编号主键：** 避免ID泄露业务规模
- **PROTECT删除策略：** 防止误删关联数据
- **数据验证：** Model.clean() 强制业务规则

### 8.2 系统安全
- **SECRET_KEY：** 生产环境使用环境变量
- **DEBUG=False：** 生产环境关闭调试模式
- **ALLOWED_HOSTS：** 限制访问来源
- **权限管理：** Django内置权限系统

### 8.3 备份策略
- **每日自动备份：** Windows任务计划程序
- **多版本保留：** 保留最近7天备份
- **异地备份：** 可选同步到网络存储

---

## 9. 性能优化策略

### 9.1 数据库优化
```python
# 添加索引
class Contract(models.Model):
    signing_date = models.DateField(db_index=True)  # 常用查询字段

# 查询优化
contracts = Contract.objects.select_related('procurement', 'parent_contract')
contracts = Contract.objects.prefetch_related('payments', 'evaluations')
```

### 9.2 Admin优化
```python
# 分页配置
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 50  # 避免一次加载过多数据

# 只读字段
readonly_fields = ['created_at', 'updated_at']
```

---

## 10. 开发规范

### 10.1 代码规范
- **命名：** 遵循PEP 8，使用中文注释
- **模型：** 每个字段必须有verbose_name
- **验证：** 业务规则写在Model.clean()
- **日志：** 关键操作记录日志

### 10.2 Git工作流
```bash
main                    # 生产分支（稳定版本）
  └── develop           # 开发分支
        ├── feature/procurement   # 功能分支
        ├── feature/contract
        └── bugfix/import-error
```

### 10.3 测试策略
- **单元测试：** 模型验证、数据导入
- **集成测试：** Admin后台操作
- **手动测试：** 真实数据导入测试

---

**下一步：** 此结构设计已完成，等待用户确认后可以开始实施。可以使用 `/do` 命令切换到Code模式开始编码。