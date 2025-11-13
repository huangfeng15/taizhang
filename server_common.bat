@echo off
REM Common utility functions for server scripts
REM Encoding: UTF-8

IF /I "%~1"=="stop_python" GOTO :stop_python
IF /I "%~1"=="kill_port_3500" GOTO :kill_port_3500
IF /I "%~1"=="ensure_ssl" GOTO :ensure_ssl
IF /I "%~1"=="migrate_db" GOTO :migrate_db
IF /I "%~1"=="print_access" GOTO :print_access
IF /I "%~1"=="run_https_server" GOTO :run_https_server
GOTO :eof

:stop_python
  taskkill /F /IM python.exe 2>NUL
  GOTO :eof

:kill_port_3500
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3500" ^| findstr "LISTENING"') do (
      echo [INFO] 终止占用端口的进程 PID: %%a
      taskkill /F /PID %%a >NUL 2>&1
  )
  GOTO :eof

:ensure_ssl
  if not exist "ssl_certs\server.crt" (
      echo [INFO] SSL 证书不存在，正在生成...
      python generate_ssl_cert.py
      echo.
  )
  GOTO :eof

:migrate_db
  echo [INFO] Checking database migrations...
  python manage.py migrate
  echo.
  GOTO :eof

:print_access
  echo 可用的访问地址：
  echo   - 本机访问: https://127.0.0.1:3500/
  echo   - 局域网访问: https://10.168.3.240:3500/
  echo   - 其他电脑访问: https://10.168.3.240:3500/
  echo.
  GOTO :eof

:run_https_server
  python manage.py runserver_plus --cert-file ssl_certs\server.crt --key-file ssl_certs\server.key 0.0.0.0:3500
  GOTO :eof

