@echo off
setlocal EnableDelayedExpansion
chcp 65001 >NUL 2>&1
echo ========================================
echo 切换到开发分支 (dev)
echo ========================================
echo.

REM 检查Git状态
git status >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 当前目录不是Git仓库!
    pause
    exit /b 1
)

REM 获取当前分支
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i

echo [信息] 当前分支: %CURRENT_BRANCH%

if "%CURRENT_BRANCH%"=="dev" (
    echo [提示] 已经在dev分支了
    echo.
    REM 验证开发环境配置
    if not exist ".env.dev" (
        echo [警告] 开发环境配置文件 .env.dev 不存在!
        echo [建议] 请先创建 .env.dev 文件
        pause
        exit /b 1
    )
    echo [验证] 开发环境配置文件存在
    echo.
    echo 是否启动开发服务器?
    choice /C YN /N /M "启动(Y) 或 取消(N): "
    if %ERRORLEVEL% EQU 1 (
        start_dev.bat
    )
    exit /b 0
)

REM 检查是否有未提交的更改（包括未暂存和已暂存的）
git diff --quiet
set UNSTAGED=%ERRORLEVEL%
git diff --cached --quiet
set STAGED=%ERRORLEVEL%

if %UNSTAGED% NEQ 0 (
    echo.
    echo [警告] 有未提交的代码更改!
    echo.
    git status --short
    echo.
    echo 选择操作:
    echo   1. 提交更改后切换
    echo   2. 放弃更改并切换
    echo   3. 暂存更改后切换 ^(git stash^)
    echo   4. 取消
    echo.
    set /p CHOICE="请输入选项 (1-4): "
    
    if "!CHOICE!"=="1" (
        echo.
        set /p COMMIT_MSG="请输入提交信息: "
        git add .
        git commit -m "!COMMIT_MSG!"
        echo [成功] 更改已提交
        goto :continue_switch
    )
    
    if "!CHOICE!"=="2" (
        git checkout -- .
        echo [成功] 更改已放弃
        goto :continue_switch
    )
    
    if "!CHOICE!"=="3" (
        git stash
        echo [成功] 更改已暂存
        goto :continue_switch
    )
    
    echo [取消] 操作已取消
    pause
    exit /b 0
)

:continue_switch
REM 切换到dev分支
echo.
echo [执行] 切换到dev分支...
git checkout dev
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 切换分支失败!
    pause
    exit /b 1
)

echo [成功] 已切换到dev分支
echo.

REM 切换到开发环境配置
echo [配置] 切换到开发环境...
if not exist ".env.dev" (
    echo [警告] 开发环境配置文件 .env.dev 不存在!
    echo [建议] 请先创建 .env.dev 文件
    pause
    exit /b 1
)

REM 备份当前.env（如果存在）
if exist ".env" (
    copy /Y .env .env.backup >NUL 2>&1
)

REM 复制开发环境配置
copy /Y .env.dev .env >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已切换到开发环境配置 (.env.dev)
) else (
    echo [错误] 环境配置切换失败!
    pause
    exit /b 1
)

echo.
echo [提示] 开发环境已就绪
echo [提示] 数据库: db.sqlite3 (开发数据库)
echo [提示] 配置: .env (已从 .env.dev 复制)
echo.
set /p START_SERVER="是否启动开发服务器? (Y/N): "
if /i "%START_SERVER%"=="Y" (
    start_dev.bat
)
