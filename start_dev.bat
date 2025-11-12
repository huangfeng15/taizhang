@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 启动开发服务器 (HTTP:8000)
echo ========================================
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在!
    echo [提示] 请先运行: python -m venv .venv
    pause
    exit /b 1
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 设置环境变量
set DJANGO_ENV=development

REM 检查 .env.dev 文件
if not exist ".env.dev" (
    echo [警告] .env.dev 文件不存在!
    echo [提示] 请检查项目配置
    pause
    exit /b 1
)

REM 加载 .env.dev 配置
for /f "usebackq tokens=1,* delims==" %%a in (".env.dev") do (
    set "%%a=%%b"
)

REM 显示服务信息
echo [信息] 开发环境配置:
echo   - 环境: DEVELOPMENT
echo   - 协议: HTTP
echo   - 端口: 8000
echo   - 数据库: db_dev.sqlite3
echo   - DEBUG: True
echo.
echo [访问地址]
echo   - 本机: http://127.0.0.1:8000/
echo   - 局域网: http://10.168.3.240:8000/
echo.
echo [提示] 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.

REM 启动Django开发服务器
python manage.py runserver 0.0.0.0:8000