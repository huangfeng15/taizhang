# 项目采购与成本管理系统 — 配置文件模板

**文档版本：** v1.0  
**编写日期：** 2025-10-20  
**用途：** 提供可复制粘贴的配置文件模板

---

## 1. requirements.txt — Python依赖

将以下内容保存为项目根目录的 `requirements.txt`：

```txt
# 核心框架
Django==4.2.7

# 数据处理
pandas==2.0.3
openpyxl==3.1.2
python-dateutil==2.8.2

# 可选：高级Excel处理
# xlrd==2.0.1

# 可选：开发工具
# django-extensions==3.2.3
# django-debug-toolbar==4.1.0
```

**安装命令：**
```bash
pip install -r requirements.txt
```

---

## 2. .gitignore — Git忽略文件

将以下内容保存为项目根目录的 `.gitignore`：

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media
/staticfiles
/static

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
*.sublime-project
*.sublime-workspace

# Environment
.env
.env.local
.env.*.local

# OS
Thumbs.db
.DS_Store

# Project specific
/backups/*
!/backups/.gitkeep
/logs/*
!/logs/.gitkeep
/data/imports/*
!/data/imports/.gitkeep
/data/exports/*
!/data/exports/.gitkeep
```

---

## 3. .env.example — 环境变量模板

```env
# Django 基础配置
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=*

# 数据库配置
DATABASE_URL=sqlite:///db.sqlite3

# 国际化
LANGUAGE_CODE=zh-hans
TIME_ZONE=Asia/Shanghai

# 日志级别
LOG_LEVEL=INFO

# 备份配置
BACKUP_RETENTION_DAYS=7
```

---

## 4. 快速启动脚本

### Windows: start.bat

```batch
@echo off
echo [*] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [*] 启动Django服务器...
python manage.py runserver 0.0.0.0:3500

echo [*] 访问地址: http://localhost:8000/admin
pause
```

### Linux/Mac: start.sh

```bash
#!/bin/bash
echo "[*] 激活虚拟环境..."
source venv/bin/activate

echo "[*] 启动Django服务器..."
python manage.py runserver 0.0.0.0:3500
```

---

**使用说明：** 在Code模式中复制上述模板内容创建对应文件。