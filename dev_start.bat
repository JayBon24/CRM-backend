@echo off
chcp 65001 >nul 2>&1
title Law Smart Link - 开发服务器

echo.
echo ========================================
echo   Law Smart Link - 开发模式启动
echo ========================================
echo.

echo [步骤 1/4] 检查端口占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo 发现8000端口被占用 (PID: %%a)，正在停止...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo ✓ 端口检查完成
echo.

echo [步骤 2/4] 激活 conda 环境...
if exist ".conda\" (
    echo 检测到本地 conda 环境：.conda
    call conda activate .\.conda
    if errorlevel 1 (
        echo [警告] 激活本地环境失败，尝试使用系统 Python
    ) else (
        echo ✓ Conda 环境激活成功
    )
) else (
    echo [提示] 未检测到 .conda 环境，使用当前 Python 环境
)
echo.

echo [步骤 3/4] 设置开发环境变量...
set ENV=development
echo ✓ 环境变量 ENV=development 已设置
echo.

echo [步骤 4/4] 启动开发服务器...
python --version
echo.
python main.py


