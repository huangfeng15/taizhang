# 常用命令
- 初始化环境：`python -m venv venv` → `venv\Scripts\activate` → `pip install -r requirements.txt`
- 数据库：`python manage.py makemigrations`，`python manage.py migrate`
- 启动服务：`python manage.py runserver`（或 `runserver 0.0.0.0:8000`）
- 测试：`python manage.py test`
- 检查：`python manage.py check`
- 数据导入：`python manage.py import_excel <路径>`，宽表转换导入 `python manage.py convert_wide_to_long <宽表.xlsx>`
- 备份恢复：`python scripts\backup_db.py`，`python scripts\restore_db.py`
- 其他脚本：`python scripts\health_check.py`，`python manage.py clearlogs`
- Windows PowerShell 常用：`dir`/`ls`，`Get-Content`，`rg`（配合项目指引的单引号外层、双引号内层写法）。