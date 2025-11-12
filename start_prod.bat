@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 启动生产服务器 (HTTPS:3500)
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

REM 设置环境变量（临时启用DEBUG以便查看详细错误）
set DJANGO_ENV=production
set DJANGO_DEBUG=True

REM 检查 .env.prod 文件
if not exist ".env.prod" (
    echo [警告] .env.prod 文件不存在!
    echo [提示] 正在从 .env.prod.example 创建...
    copy .env.prod.example .env.prod >NUL
    echo [成功] 已创建 .env.prod
    echo [提示] 请编辑 .env.prod 修改密钥等敏感配置
    echo.
)

REM 加载 .env.prod 配置
for /f "usebackq tokens=1,* delims==" %%a in (".env.prod") do (
    set "%%a=%%b"
)

REM 检查并生成SSL证书
if not exist "ssl_certs\server.crt" (
    echo [提示] SSL证书不存在，正在生成...
    python generate_ssl_cert.py
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] SSL证书生成失败!
        pause
        exit /b 1
    )
    echo [成功] SSL证书已生成
    echo.
)

REM 收集静态文件
echo [步骤] 收集静态文件...
python manage.py collectstatic --noinput --clear
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 静态文件收集失败，但将继续启动服务器
)
echo.

REM 显示服务信息
echo [信息] 生产环境配置:
echo   - 环境: PRODUCTION
echo   - 协议: HTTPS
echo   - 端口: 3500
echo   - 数据库: db.sqlite3
echo   - 静态文件: staticfiles/
echo.
echo [访问地址]
echo   - 本机: https://127.0.0.1:3500/
echo   - 局域网: https://10.168.3.240:3500/
echo.
echo [提示] 浏览器可能提示证书不安全，请点击"继续访问"
echo [提示] 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.

REM 启动Django服务器（使用 --insecure 参数在生产环境也提供静态文件）
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key --insecure 0.0.0.0:3500

REM 如果runserver_plus不可用，尝试使用标准runserver
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [警告] runserver_plus 不可用，使用标准 runserver（仅HTTP）
    echo [提示] 要使用HTTPS，请安装: pip install django-extensions Werkzeug pyOpenSSL
    echo.
    python manage.py runserver --insecure 0.0.0.0:3500
)