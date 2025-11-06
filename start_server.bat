@echo off
echo ========================================
echo 启动Django HTTPS服务器
echo 地址: https://10.168.3.240:3500/
echo ========================================
echo.

REM 检查SSL证书是否存在
if not exist "ssl_certs\server.crt" (
    echo [错误] SSL证书文件不存在，正在生成...
    python generate_ssl_cert.py
    echo.
)

echo [启动] 正在启动服务器...
echo.

REM 使用runserver_plus启动HTTPS服务器
python manage.py runserver_plus --cert-file ssl_certs/server.crt --key-file ssl_certs/server.key 10.168.3.240:3500

pause