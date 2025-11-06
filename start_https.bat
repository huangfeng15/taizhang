@echo off
chcp 65001 >nul
REM ============================================================================
REM 台账系统 - HTTPS模式启动脚本 (Windows)
REM 使用自签名证书启动Django开发服务器
REM ============================================================================

echo.
echo ======================================================================
echo 🚀 台账系统 - HTTPS模式启动
echo ======================================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查是否在虚拟环境中
if not defined VIRTUAL_ENV (
    echo ⚠️  警告: 未检测到虚拟环境
    echo.
    echo 建议先激活虚拟环境:
    echo    .venv\Scripts\activate
    echo.
    set /p continue="是否继续？(Y/N): "
    if /i not "%continue%"=="Y" (
        echo 操作已取消
        pause
        exit /b 0
    )
)

REM 检查证书是否存在
if not exist "ssl_certs\server.crt" (
    echo ❌ SSL证书未找到！
    echo.
    echo 正在自动生成证书...
    python generate_ssl_cert.py
    if errorlevel 1 (
        echo.
        echo ❌ 证书生成失败
        pause
        exit /b 1
    )
    echo.
    echo ✅ 证书生成成功！
    echo.
)

REM 启动HTTPS服务
echo 📦 检查依赖...
python start_https.py

if errorlevel 1 (
    echo.
    echo ❌ 启动失败
    pause
    exit /b 1
)

pause