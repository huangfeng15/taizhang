@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 重启 Django HTTPS 服务器
echo ========================================
echo.

echo [步骤 1/3] 停止现有服务器...
taskkill /F /IM python.exe 2>NUL
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已停止现有服务器
) else (
    echo [提示] 没有找到正在运行的服务器
)

echo.
echo [步骤 2/3] 检查并清理端口3500占用...
timeout /t 1 /nobreak >NUL
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3500" ^| findstr "LISTENING"') do (
    echo [INFO] 终止占用端口的进程 PID: %%a
    taskkill /F /PID %%a >NUL 2>&1
)

echo.
echo [步骤 3/3] 启动 HTTPS 服务器...
timeout /t 1 /nobreak >NUL
echo.

REM 检查SSL证书是否存在
if not exist "ssl_certs\server.crt" (
    echo [INFO] SSL证书不存在，正在生成...
    python generate_ssl_cert.py
    echo.
)

REM 执行数据库迁移
echo [INFO] 检查数据库迁移...
python manage.py migrate
echo.

echo [INFO] 启动服务器...
echo.
echo 可用的访问地址：
echo   - 本机访问: https://127.0.0.1:3500/
echo   - 局域网访问: https://10.168.3.240:3500/
echo   - 其他电脑访问: https://10.168.3.240:3500/
echo.
echo Note: 浏览器可能显示安全警告（自签名证书），请点击"继续访问"
echo.

REM 使用0.0.0.0监听所有网络接口，端口3500
python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500

echo.
echo 服务器已停止
pause