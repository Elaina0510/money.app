#!/bin/bash
# Money App 服务器首次初始化脚本
# 在全新服务器上执行，安装所有依赖
# 用法: sudo bash setup.sh

set -e

echo "=========================================="
echo "  Money App 服务器初始化"
echo "=========================================="

# 检查 root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] 请使用 root 用户执行: sudo bash setup.sh"
    exit 1
fi

# 1. 安装 Git
echo "[INFO] 安装 Git..."
if ! command -v git &> /dev/null; then
    yum install -y git 2>/dev/null || apt-get install -y git 2>/dev/null
fi
echo "[OK] Git $(git --version | awk '{print $3}')"

# 2. 安装 Python 3.11+
echo "[INFO] 检查 Python..."
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[INFO] 安装 Python 3.11..."
    yum install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || \
    apt-get install -y python3.11 python3.11-venv python3.11-dev 2>/dev/null
    PYTHON_CMD="python3.11"
fi
echo "[OK] $($PYTHON_CMD --version)"

# 3. 安装 Supervisor
echo "[INFO] 安装 Supervisor..."
if ! command -v supervisord &> /dev/null; then
    yum install -y supervisor 2>/dev/null || apt-get install -y supervisor 2>/dev/null
fi
systemctl start supervisord 2>/dev/null || true
systemctl enable supervisord 2>/dev/null || true
echo "[OK] Supervisor 已安装"

# 4. 停止 nginx（如果在占用 80 端口）
echo "[INFO] 检查端口 80..."
if lsof -i :80 2>/dev/null | grep -q LISTEN; then
    echo "[INFO] 停止 nginx..."
    systemctl stop nginx 2>/dev/null || true
    systemctl disable nginx 2>/dev/null || true
fi

# 5. 开放防火墙端口
echo "[INFO] 配置防火墙..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
fi

echo ""
echo "=========================================="
echo "  服务器初始化完成！"
echo "=========================================="
echo ""
echo "  下一步："
echo "  1. 上传项目代码到 /www/wwwroot/money-app"
echo "  2. 执行部署: cd /www/wwwroot/money-app && bash deploy.sh"
echo ""
