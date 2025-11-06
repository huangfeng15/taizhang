@echo off
chcp 65001 >nul
cls
echo.
echo ================================================
echo     项目采购管理系统 - HTTPS服务器
echo ================================================
echo.
echo 正在启动...
echo 访问地址: https://10.168.3.240:3500
echo.
python manage.py runserver_plus --cert-file ssl/cert.pem --key-file ssl/key.pem 0.0.0.0:3500