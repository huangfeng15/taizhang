@echo off
chcp 65001 >NUL 2>&1
echo ========================================
echo 生产环境紧急回滚
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

if not "%CURRENT_BRANCH%"=="main" (
    echo [警告] 当前不在main分支!
    echo [信息] 当前分支: %CURRENT_BRANCH%
    echo.
    echo 是否切换到main分支并回滚?
    choice /C YN /N /M "继续(Y) 或 取消(N): "
    if %ERRORLEVEL% NEQ 1 (
        echo [取消] 回滚已取消
        pause
        exit /b 0
    )
    git checkout main >NUL 2>&1
)

echo [警告] 即将回滚生产环境!
echo.
echo 回滚操作:
echo   1. 停止生产服务
echo   2. 回滚代码到上一个备份版本
echo   3. (可选) 恢复数据库备份
echo   4. 重启生产服务
echo.
pause

REM 1. 停止生产服务
echo.
echo [步骤1/4] 停止生产服务...
taskkill /F /IM python.exe 2>NUL
if %ERRORLEVEL% EQU 0 (
    echo [成功] 已停止现有服务
    timeout /t 2 /nobreak >NUL
) else (
    echo [提示] 没有运行中的服务
)

REM 2. 回滚代码
echo.
echo [步骤2/4] 回滚代码...
git tag | findstr "v-prod-backup-latest" >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 找不到备份标签 v-prod-backup-latest
    echo.
    echo 可用的标签:
    git tag
    echo.
    pause
    exit /b 1
)

git reset --hard v-prod-backup-latest >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [成功] 代码已回滚到备份版本
) else (
    echo [错误] 代码回滚失败!
    pause
    exit /b 1
)

REM 3. 恢复数据库
echo.
echo [步骤3/4] 数据库恢复选项
echo.
echo 选择操作:
echo   [1] 仅回滚代码 (保留当前数据库)
echo   [2] 同时恢复数据库备份
echo.
choice /C 12 /N /M "请选择 (1或2): "

if %ERRORLEVEL% EQU 2 (
    echo.
    echo [信息] 打开备份目录,请手动选择要恢复的数据库文件
    echo.
    if exist "backups" (
        echo 最近的5个备份:
        dir /B /O-D backups\db_prod_*.sqlite3 2>NUL | findstr /N "^" | findstr "^[1-5]:"
        echo.
        echo 操作步骤:
        echo   1. 从打开的文件夹中找到要恢复的备份文件
        echo   2. 复制文件名 (例如: db_prod_20251111_143000.sqlite3)
        echo   3. 关闭文件夹窗口
        echo   4. 回到这里继续
        echo.
        explorer backups
        pause
        
        echo.
        set /p BACKUP_FILE="请输入要恢复的备份文件名: "
        
        if exist "backups\%BACKUP_FILE%" (
            copy "backups\%BACKUP_FILE%" db.sqlite3 >NUL
            if %ERRORLEVEL% EQU 0 (
                echo [成功] 数据库已恢复: %BACKUP_FILE%
            ) else (
                echo [错误] 数据库恢复失败!
            )
        ) else (
            echo [错误] 文件不存在: backups\%BACKUP_FILE%
        )
    ) else (
        echo [错误] 备份目录不存在!
    )
) else (
    echo [跳过] 保留当前数据库
)

REM 4. 重启生产服务
echo.
echo [步骤4/4] 重启生产服务...
echo.
echo ========================================
echo 回滚完成!
echo ========================================
echo.
echo 按任意键启动生产服务...
pause >NUL

start_prod.bat