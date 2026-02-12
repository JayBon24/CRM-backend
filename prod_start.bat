@echo off
echo ========================================
echo 生产模式启动（无热更新）
echo ========================================
echo.

echo [步骤 1/4] 停止现有进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
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

echo [步骤 3/4] 设置生产环境变量...
set ENV=production
echo 环境变量 ENV=production 已设置
echo.

echo [步骤 4/4] 启动生产服务器（热更新已禁用）...
echo.
echo 当前 Python 版本：
python --version
echo.
echo ----------------------------------------
python main.py


