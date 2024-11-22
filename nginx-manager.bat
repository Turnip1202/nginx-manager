@echo off
chcp 65001
cls

:: Set Nginx Path
set NGINX_PATH=S:\Nginx\nginx-1.27.2
set NGINX_CONF=%NGINX_PATH%\conf\my-nginx.conf

:menu
cls
echo ================================
echo         Nginx Manager
echo ================================
echo 1. Start Nginx (Custom Config)
echo 2. Start Nginx (Default Config)
echo 3. Stop Nginx
echo 4. Reload Config
echo 5. Test Config
echo 6. Check Status
echo 7. View Error Log
echo 8. View Access Log
echo 9. Exit
echo ================================

choice /c 123456789 /n /m "Please select [1-9]: "

if errorlevel 9 goto end
if errorlevel 8 goto access_log
if errorlevel 7 goto error_log
if errorlevel 6 goto status
if errorlevel 5 goto test
if errorlevel 4 goto reload
if errorlevel 3 goto stop
if errorlevel 2 goto start_default
if errorlevel 1 goto start_custom

:start_custom
cd /d %NGINX_PATH%
start /b nginx.exe -c conf/my-nginx.conf
echo Starting Nginx with custom config...
timeout /t 3
goto menu

:start_default
cd /d %NGINX_PATH%
start /b nginx.exe
echo Starting Nginx with default config...
timeout /t 3
goto menu

:stop
cd /d %NGINX_PATH%
nginx.exe -s stop
echo Stopping Nginx...
timeout /t 3
goto menu

:reload
cd /d %NGINX_PATH%
nginx.exe -s reload
echo Reloading config...
timeout /t 3
goto menu

:test
cd /d %NGINX_PATH%
nginx.exe -t
pause
goto menu

:status
cls
echo.
echo Nginx Process Status:
echo ================================
echo Found Nginx processes:
tasklist /fi "imagename eq nginx.exe" /fo list | findstr /i "PID: Image Name:"
echo.
echo Note:
echo - Usually there are two processes:
echo   1. Master Process
echo   2. Worker Process
echo ================================
echo.
pause
goto menu

:error_log
cls
echo.
echo Recent Error Logs:
echo ================================
type %NGINX_PATH%\logs\error.log
echo ================================
echo.
pause
goto menu

:access_log
cls
echo.
echo Recent Access Logs:
echo ================================
type %NGINX_PATH%\logs\access.log
echo ================================
echo.
pause
goto menu

:end
cls
echo Exiting...
timeout /t 1
exit