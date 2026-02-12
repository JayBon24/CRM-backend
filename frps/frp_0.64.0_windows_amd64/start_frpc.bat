@echo off
chcp 65001 >nul
echo ========================================
echo 启动 frp 客户端（内网穿透）
echo ========================================
echo.

REM 检查配置文件是否存在（优先使用 TOML 格式）
if exist "frpc.toml" (
    set CONFIG_FILE=frpc.toml
) else if exist "frpc.ini" (
    echo [警告] ini 格式已被弃用，建议使用 TOML 格式
    set CONFIG_FILE=frpc.ini
) else (
    echo [错误] 未找到配置文件 frpc.toml 或 frpc.ini
    echo 请确保配置文件存在
    pause
    exit /b 1
)

REM 检查 frpc.exe 是否存在
if not exist "frpc.exe" (
    echo [错误] 未找到 frpc.exe
    pause
    exit /b 1
)

echo 正在启动 frp 客户端...
echo 配置文件：%CONFIG_FILE%
echo.
echo 提示：如果连接成功，客户端会保持运行状态
echo 按 Ctrl+C 可以停止客户端
echo.

REM 启动 frp 客户端（使用详细模式）
frpc.exe -c %CONFIG_FILE%

echo.
echo frp 客户端已停止
pause

