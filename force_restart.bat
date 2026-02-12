@echo off
echo ========================================
echo 强制重启Django服务器
echo ========================================
echo.

echo [1/3] 停止所有Python进程...
taskkill /F /IM python.exe 2>nul
if %ERRORLEVEL%==0 (
    echo     ✓ Python进程已停止
) else (
    echo     ✓ 没有正在运行的Python进程
)

echo.
echo [2/3] 等待端口释放...
timeout /t 3 /nobreak >nul
echo     ✓ 完成

echo.
echo [3/3] 启动Django开发服务器...
python manage.py runserver

pause

