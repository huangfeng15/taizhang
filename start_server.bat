@echo off
chcp 65001 >nul
echo ========================================
echo Starting Django HTTPS Server
echo Address: https://10.168.3.240:3500/
echo ========================================
echo.

REM Check if SSL certificates exist
if not exist "ssl_certs\server.crt" (
    echo [INFO] SSL certificate not found, generating...
    python generate_ssl_cert.py
    echo.
)

echo [INFO] Starting server...
echo.
echo Note: After server starts, visit https://10.168.3.240:3500/
echo Browser may show security warning due to self-signed certificate.
echo Please click "Continue" or "Trust this site"
echo.

REM Start HTTPS server using runserver_plus
python manage.py runserver_plus --cert-file ssl_certs/server.crt --key-file ssl_certs/server.key 10.168.3.240:3500

echo.
echo Server stopped
pause