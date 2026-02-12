@echo off
chcp 65001 >nul 2>&1
title Law Smart Link - 后端服务启动

echo.
echo ========================================
echo   Law Smart Link - 后端服务启动
echo ========================================
echo.

echo [步骤 1/4] 检查并停止占用8000端口的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo 发现8000端口被占用 (PID: %%a)，正在停止...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo [OK] 端口检查完成
echo.

echo [步骤 2/4] 激活 conda 环境 lsl...
call conda activate lsl
if errorlevel 1 (
    echo [错误] 无法激活 conda 环境 lsl
    echo 请确保已安装 conda 并创建了 lsl 环境
    pause
    exit /b 1
)
echo [OK] Conda 环境激活成功
python --version
echo.

echo [步骤 3/4] 设置环境变量...
set ENV=development
echo [OK] 环境变量 ENV=development 已设置
echo.

echo [步骤 4/4] 启动开发服务器...
echo.
echo ========================================
echo   服务启动中，请稍候...
echo ========================================
echo 访问地址: http://127.0.0.1:8000
echo API文档: http://127.0.0.1:8000/admin-api/swagger/
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

python main.py

pause

