#!/bin/bash
# 小程序接口单元测试运行脚本

echo "========================================"
echo "小程序接口单元测试"
echo "========================================"
echo ""

# 检查是否在正确的目录
if [ ! -f "manage.py" ]; then
    echo "错误：请在 lsl-backend 目录下运行此脚本"
    exit 1
fi

echo "运行所有测试..."
python manage.py test customer_management.tests.test_miniapp_apis --verbosity=2

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
