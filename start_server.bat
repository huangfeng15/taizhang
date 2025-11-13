@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo Starting Django HTTPS Server
echo ========================================
echo.

REM 检查并终止占用3500端口的进程
echo [INFO] 检查端口3500占用情况...
call server_common.bat kill_port_3500
echo.

REM 检查SSL证书是否存在
call server_common.bat ensure_ssl

REM 执行数据库迁移
call server_common.bat migrate_db

echo [INFO] Starting server...
echo.
call server_common.bat print_access
echo Note: Browser may show security warning due to self-signed certificate.
echo Please click "Continue" or "Trust this site"
echo.

REM 使用0.0.0.0监听所有网络接口（支持本地和局域网访问），端口3500
call server_common.bat run_https_server

echo.
echo Server stopped
pause
