@echo off
setlocal EnableDelayedExpansion
chcp 65001 >NUL 2>&1
echo ========================================
echo 安全部署到生产环境
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
echo.

if not "%CURRENT_BRANCH%"=="dev" (
    echo [警告] 当前不在dev分支!
    echo.
    echo 建议工作流程:
    echo   1. 在dev分支开发和测试
    echo   2. 测试通过后再部署到生产
    echo.
    echo 是否继续从当前分支(%CURRENT_BRANCH%)部署?
    set /p CONTINUE="继续(Y) 或 取消(N): "
    if /i not "!CONTINUE!"=="Y" (
        echo [取消] 部署已取消
        pause
        exit /b 0
    )
)

REM 检查是否有未提交的更改（包括未暂存和已暂存的）
git diff --quiet
set UNSTAGED=%ERRORLEVEL%
git diff --cached --quiet
set STAGED=%ERRORLEVEL%

if %UNSTAGED% NEQ 0 (
    echo [警告] 有未提交的代码更改!
    echo.
    git status --short
    echo.
    echo 建议先提交更改: git add . && git commit -m "描述"
    echo.
    set /p IGNORE="忽略并继续(Y) 或 取消(N): "
    if /i not "!IGNORE!"=="Y" (
        echo [取消] 部署已取消
        pause
        exit /b 0
    )
)

echo.
echo ========================================
echo 部署确认
echo ========================================
echo.
echo 即将执行以下操作:
echo   1. 停止生产服务
echo   2. 备份生产数据库
echo   3. 创建代码备份标签
echo   4. 合并代码到main分支
echo   5. 执行数据库迁移
echo   6. 启动生产服务
echo.
echo [警告] 这将影响生产环境!
echo.
pause

REM 1. 停止生产服务
echo.
echo [步骤1/6] 停止生产服务...
taskkill /F /IM python.exe 2>NUL
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已停止现有服务
    timeout /t 2 /nobreak >NUL
) else (
    echo [提示] 没有运行中的服务
)

REM 2. 备份生产数据库
echo.
echo [步骤2/6] 备份生产数据库...
if exist "db.sqlite3" (
    if not exist "backups" mkdir backups
    
    REM 生成时间戳
    set "timestamp=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "timestamp=!timestamp: =0!"
    
    set "backup_file=backups\db_prod_!timestamp!.sqlite3"
    copy db.sqlite3 "!backup_file!" >NUL
    
    if !ERRORLEVEL! EQU 0 (
        echo [成功] 数据库已备份: !backup_file!
    ) else (
        echo [错误] 数据库备份失败!
        pause
        exit /b 1
    )
) else (
    echo [提示] 生产数据库不存在,跳过备份
)

REM 3. 创建代码备份标签
echo.
echo [步骤3/6] 创建代码备份标签...
git tag -f v-prod-backup-latest >NUL 2>&1
echo [成功] 已创建标签: v-prod-backup-latest

REM 4. 切换到main分支并合并
echo.
echo [步骤4/6] 合并代码到生产分支(main)...

REM 保存当前分支名
set SOURCE_BRANCH=%CURRENT_BRANCH%

git checkout main >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 切换到main分支失败!
    pause
    exit /b 1
)

git merge %SOURCE_BRANCH% --no-edit >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 代码合并失败! 可能存在冲突
    echo.
    echo 请手动解决冲突后重试
    git status
    pause
    exit /b 1
)
echo [成功] 代码已合并到main分支

REM 切换到生产环境配置
echo.
echo [配置] 切换到生产环境配置...
if not exist ".env.prod" (
    echo [警告] 生产环境配置文件 .env.prod 不存在!
    echo [建议] 请先创建 .env.prod 文件
    pause
    exit /b 1
)

REM 备份当前.env
if exist ".env" (
    copy /Y .env .env.backup >NUL 2>&1
)

REM 复制生产环境配置
copy /Y .env.prod .env >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已切换到生产环境配置 (.env.prod)
) else (
    echo [错误] 环境配置切换失败!
    pause
    exit /b 1
)

REM 5. 执行数据库迁移
echo.
echo [步骤5/6] 执行数据库迁移...
set DJANGO_ENV=production
python manage.py migrate --noinput
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 数据库迁移失败!
    echo.
    echo 是否回滚?
    choice /C YN /N /M "回滚(Y) 或 继续(N): "
    if %ERRORLEVEL% EQU 1 (
        echo [回滚] 正在回滚...
        git reset --hard v-prod-backup-latest
        REM 恢复环境配置
        if exist ".env.backup" (
            copy /Y .env.backup .env >NUL 2>&1
        )
        echo [完成] 已回滚到备份版本
        pause
        exit /b 1
    )
)

REM 验证生产环境配置
echo.
echo [验证] 检查生产环境配置...
if not exist ".env" (
    echo [错误] .env 文件不存在!
    pause
    exit /b 1
)
echo [成功] 环境配置验证通过

REM 6. 启动生产服务
echo.
echo [步骤6/6] 启动生产服务...
echo.
echo ========================================
echo 部署完成!
echo ========================================
echo.
echo 生产环境访问地址:
echo   - 本机: https://127.0.0.1:3500/
echo   - 局域网: https://10.168.3.240:3500/
echo.
echo [提示] 请验证系统功能是否正常
echo [提示] 如有问题,运行 rollback_prod.bat 快速回滚
echo.
echo 按任意键启动生产服务...
pause >NUL

start_prod.bat
