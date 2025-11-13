@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 重启 Django HTTPS 服务器
echo ========================================
echo.

echo [步骤 1/3] 停止现有服务器...
call server_common.bat stop_python
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已停止现有服务器
) else (
    echo [提示] 没有找到正在运行的服务器
)

echo.
echo [步骤 2/3] 检查并清理端口3500占用...
timeout /t 1 /nobreak >NUL
call server_common.bat kill_port_3500

echo.
echo [步骤 3/3] 启动 HTTPS 服务器...
timeout /t 1 /nobreak >NUL
echo.

REM 检查SSL证书是否存在
call server_common.bat ensure_ssl

REM 执行数据库迁移
call server_common.bat migrate_db

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
call server_common.bat run_https_server

echo.
echo 服务器已停止
pause
