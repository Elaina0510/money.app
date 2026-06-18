#!/bin/bash
# Money App 一键部署脚本
# 用法: ./deploy.sh

set -e

echo "=========================================="
echo "  Money App 部署脚本"
echo "=========================================="

# 1. 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "[INFO] Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    sudo systemctl start docker
    sudo systemctl enable docker
    echo "[OK] Docker 安装完成"
else
    echo "[OK] Docker 已安装"
fi

# 2. 检查 Docker Compose 是否可用
if ! docker compose version &> /dev/null; then
    echo "[INFO] Docker Compose 未安装，正在安装..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
    echo "[OK] Docker Compose 安装完成"
else
    echo "[OK] Docker Compose 已安装"
fi

# 3. 构建前端（frontend/dist 被 gitignore，需要本地构建）
echo "[INFO] 构建前端..."
if command -v node &> /dev/null; then
    cd frontend
    npm install
    npm run build
    cd ..
    echo "[OK] 前端构建完成"
else
    echo "[WARN] Node.js 未安装，尝试安装..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    cd frontend
    npm install
    npm run build
    cd ..
    echo "[OK] Node.js 安装并完成前端构建"
fi

# 4. 创建数据目录
echo "[INFO] 创建数据目录..."
mkdir -p data/db data/uploads
echo "[OK] 数据目录已创建"

# 5. 生成 SECRET_KEY（如果 .env 不存在）
if [ ! -f .env ]; then
    echo "[INFO] 生成 .env 配置文件..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 64 | tr -d '\n/')
    cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
EOF
    echo "[OK] .env 已生成，SECRET_KEY 已自动创建"
else
    echo "[OK] .env 已存在，跳过生成"
fi

# 6. 构建并启动容器
echo "[INFO] 构建 Docker 镜像..."
docker compose build

echo "[INFO] 启动容器..."
docker compose up -d

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://$(hostname -I | awk '{print $1}')"
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "  重启服务: docker compose restart"
echo ""
