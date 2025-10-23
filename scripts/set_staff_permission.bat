@echo off
chcp 65001 >nul
echo ========================================
echo    设置用户Staff权限工具
echo ========================================
echo.

REM 切换到项目根目录
cd /d "%~dp0.."

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [1/3] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [1/3] 激活虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo 警告：未找到虚拟环境，使用系统Python
)

echo.
echo [2/3] 获取当前用户列表...
echo ----------------------------------------
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); [print(f'{u.username} | Staff={u.is_staff} | Superuser={u.is_superuser}') for u in User.objects.all()]"
echo ----------------------------------------
echo.

REM 获取用户输入
set /p username="请输入要设置staff权限的用户名: "

if "%username%"=="" (
    echo 错误：用户名不能为空
    pause
    exit /b 1
)

echo.
echo [3/3] 正在为用户 "%username%" 设置staff权限...
python manage.py set_staff_permission "%username%"

echo.
echo ========================================
echo 操作完成！
echo ========================================
echo.
echo 提示：现在您可以使用该用户登录Admin后台，
echo      然后在前端页面使用删除等功能。
echo.
pause