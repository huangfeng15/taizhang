@echo off
chcp 65001 >nul
echo ========================================
echo Starting Django HTTPS Server
echo ========================================
echo.

REM 检查SSL证书是否存在
if not exist "ssl_certs\server.crt" (
    echo [INFO] SSL certificate not found, generating...
    python generate_ssl_cert.py
    echo.
)

REM 执行数据库迁移
echo [INFO] Checking database migrations...
python manage.py migrate
echo.

echo [INFO] Starting server...
echo.
echo 可用的访问地址：
echo   - 本机访问: https://127.0.0.1:3500/
echo   - 局域网访问: https://10.168.3.240:3500/
echo   - 其他电脑访问: https://10.168.3.240:3500/
echo.
echo Note: Browser may show security warning due to self-signed certificate.
echo Please click "Continue" or "Trust this site"
echo.

REM 使用0.0.0.0监听所有网络接口（支持本地和局域网访问），端口3500
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500

echo.
echo Server stopped
pause