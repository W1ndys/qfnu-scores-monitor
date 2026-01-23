#!/bin/bash
# QFNU 成绩监控服务 - Linux/macOS 启动脚本
# 使用方法: chmod +x start.sh && ./start.sh

set -e

echo "========================================"
echo "  QFNU 成绩监控服务启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 配置文件"
    if [ -f ".env.example" ]; then
        echo "[提示] 正在从 .env.example 创建 .env 文件..."
        cp ".env.example" ".env"
        echo "[重要] 请编辑 .env 文件，修改 ADMIN_PASSWORD 后重新运行此脚本"
        echo ""
        echo "可使用以下命令编辑："
        echo "  nano .env"
        echo "  或 vim .env"
        exit 1
    fi
fi

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "[错误] 未找到 uv 包管理器"
    echo "[提示] 请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
    echo "       Linux/macOS 安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "[1/3] 检查 Python 环境..."

echo "[2/3] 同步项目依赖..."
uv sync
if [ $? -ne 0 ]; then
    echo "[错误] 依赖安装失败"
    exit 1
fi

echo "[3/3] 启动服务..."
echo ""
echo "服务启动中，按 Ctrl+C 停止服务"
echo "========================================"
echo ""

# 启动 Flask 应用
uv run python app.py
