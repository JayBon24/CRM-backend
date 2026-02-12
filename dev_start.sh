#!/bin/bash

echo ""
echo "========================================"
echo "  Law Smart Link - 开发模式启动"
echo "========================================"
echo ""

echo "[步骤 1/4] 检查端口占用..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "发现8000端口被占用，正在停止..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi
echo "✓ 端口检查完成"
echo ""

echo "[步骤 2/4] 检查虚拟环境..."
if [ -d ".conda" ]; then
    echo "检测到本地 conda 环境：.conda"
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate ./.conda
    echo "✓ Conda 环境激活成功"
elif [ -d "venv" ]; then
    echo "检测到虚拟环境：venv"
    source venv/bin/activate
    echo "✓ 虚拟环境激活成功"
else
    echo "[提示] 未检测到虚拟环境，使用当前 Python 环境"
fi
echo ""

echo "[步骤 3/4] 设置开发环境变量..."
export ENV=development
echo "✓ 环境变量 ENV=development 已设置"
echo ""

echo "[步骤 4/4] 启动开发服务器..."
python --version
echo ""
python main.py

