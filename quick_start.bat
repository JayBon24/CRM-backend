@echo off
echo ========================================
echo 快速启动 Django 服务器
echo ========================================
echo.

echo [步骤 1/3] 停止现有进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo.

echo [步骤 2/3] 激活 conda 环境...
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
echo 当前 Python 版本：
python --version
echo.

echo [步骤 3/3] 启动服务器...
echo.
echo ----------------------------------------
python main.py

