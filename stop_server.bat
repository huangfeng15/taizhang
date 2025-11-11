@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 停止 Django 服务器
echo ========================================
echo.

echo [INFO] 正在查找并停止所有 Python 进程...
echo.

taskkill /F /IM python.exe 2>NUL

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [成功] 所有 Python 进程已停止
    echo.
    echo 提示：现在可以重新运行 start_server.bat 启动服务器
) else (
    echo.
    echo [提示] 没有找到正在运行的 Python 进程
)

echo.
echo ========================================
pause