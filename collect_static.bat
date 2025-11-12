@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 收集静态文件
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

echo [提示] 这将收集所有静态文件到 staticfiles/ 目录
echo [提示] 适用于生产环境部署前的准备工作
echo.
pause

REM 收集静态文件
echo [执行] 收集静态文件...
python manage.py collectstatic --noinput --clear

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [成功] 静态文件收集完成!
    echo [位置] staticfiles/
    echo.
    echo 文件统计:
    dir /s /b staticfiles\*.css 2>NUL | find /c /v "" && echo 个 CSS 文件
    dir /s /b staticfiles\*.js 2>NUL | find /c /v "" && echo 个 JS 文件
    dir /s /b staticfiles\*.png 2>NUL | find /c /v "" && echo 个 PNG 图片
) else (
    echo.
    echo [错误] 静态文件收集失败!
    echo [提示] 请检查 settings.py 中的 STATIC_ROOT 配置
)

echo.
pause