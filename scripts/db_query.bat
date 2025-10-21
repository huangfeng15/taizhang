@echo off
chcp 65001 >nul
echo 数据库查询工具
echo ================
echo.

if "%1"=="" (
    echo 用法:
    echo   db_query.bat "SQL语句" [格式]
    echo   db_query.bat --list-tables
    echo   db_query.bat --describe 表名
    echo   db_query.bat --count 表名
    echo.
    echo 示例:
    echo   db_query.bat "SELECT * FROM contract_contract LIMIT 10"
    echo   db_query.bat "SELECT * FROM contract_contract LIMIT 10" json
    echo   db_query.bat --list-tables
    echo   db_query.bat --describe contract_contract
    echo   db_query.bat --count contract_contract
    echo.
    echo 或者直接运行进入交互模式:
    echo   db_query.bat
    echo.
    pause
    exit /b
)

python scripts/query_database.py %*