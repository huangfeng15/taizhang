@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 切换到开发分支
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
    echo 是否启动开发服务器?
    choice /C YN /N /M "启动(Y) 或 取消(N): "
    if %ERRORLEVEL% EQU 1 (
        start_dev.bat
    )
    exit /b 0
)

REM 检查是否有未提交的更改
git diff --quiet
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [警告] 有未提交的代码更改!
    echo.
    git status --short
    echo.
    echo 选择操作:
    echo   1. 提交更改后切换
    echo   2. 暂存更改后切换 (git stash)
    echo   3. 放弃更改并切换
    echo   4. 取消
    echo.
    set /p CHOICE="请输入选项 (1-4): "
    
    if "%CHOICE%"=="1" (
        echo.
        set /p COMMIT_MSG="请输入提交信息: "
        git add .
        git commit -m "!COMMIT_MSG!"
        echo [成功] 更改已提交
    ) else if "%CHOICE%"=="2" (
        git stash
        echo [成功] 更改已暂存
    ) else if "%CHOICE%"=="3" (
        git checkout -- .
        echo [成功] 更改已放弃
    ) else (
        echo [取消] 操作已取消
        pause
        exit /b 0
    )
)
    

REM 切换到dev分支
echo.
echo [执行] 切换到dev分支...
git checkout dev
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已切换到dev分支
    echo.
    set /p START_SERVER="是否启动开发服务器? (Y/N): "
    if /i "%START_SERVER%"=="Y" (
        start_dev.bat
    )
) else (
    echo [错误] 切换分支失败!
    pause
    exit /b 1
)