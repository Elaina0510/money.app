#!/bin/bash
# Money App 一键部署脚本
# 支持两种模式：直接 Python 运行（默认）和 Docker
# 用法:
#   ./deploy.sh              # 直接 Python 部署（推荐国内服务器）
#   ./deploy.sh docker       # Docker 部署（需要能访问 Docker Hub）

set -e

MODE="${1:-python}"

echo "=========================================="
echo "  Money App 部署脚本 (模式: ${MODE})"
echo "=========================================="

# ============================================================
# 公共函数
# ============================================================

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "[ERROR] 请使用 root 用户执行此脚本"
        exit 1
    fi
}

generate_secret() {
    if [ ! -f .env ]; then
        echo "[INFO] 生成 .env 配置文件..."
        SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n/')
        cat > .env << EOF
APP_ENV=production
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=
EOF
        echo "[OK] .env 已生成"
        echo "[提示] 请编辑 .env 设置 CORS_ORIGINS 为实际访问地址(如 http://你的IP)"
    else
        echo "[OK] .env 已存在"
        # 若旧 .env 缺少 APP_ENV，补上生产标记
        if ! grep -q "^APP_ENV=" .env; then
            echo "APP_ENV=production" >> .env
            echo "[OK] 已补充 APP_ENV=production"
        fi
    fi
}

# ============================================================
# Python 直接部署模式
# ============================================================

deploy_python() {
    echo "[INFO] 使用 Python 直接部署模式"

    # 1. 检查 Python 3.11+
    echo "[INFO] 检查 Python 版本..."
    PYTHON_CMD=""
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v $cmd &> /dev/null; then
            version=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            major=$(echo $version | cut -d. -f1)
            minor=$(echo $version | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                PYTHON_CMD=$cmd
                echo "[OK] 找到 $cmd (版本 $version)"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo "[ERROR] 未找到 Python 3.10+，请先安装"
        echo "  CentOS/Alinux: yum install -y python3.11 python3.11-pip python3.11-devel"
        echo "  Ubuntu: apt install -y python3.11 python3.11-venv"
        exit 1
    fi

    # 2. 安装 venv 模块（如果没有）
    $PYTHON_CMD -m venv --help &> /dev/null || {
        echo "[INFO] 安装 venv 模块..."
        yum install -y "${PYTHON_CMD}-devel" 2>/dev/null || apt-get install -y "${PYTHON_CMD}-venv" 2>/dev/null || true
    }

    # 3. 创建虚拟环境
    if [ ! -d "backend/venv" ]; then
        echo "[INFO] 创建 Python 虚拟环境..."
        $PYTHON_CMD -m venv backend/venv
        echo "[OK] 虚拟环境已创建"
    else
        echo "[OK] 虚拟环境已存在"
    fi

    # 4. 安装依赖
    echo "[INFO] 安装 Python 依赖..."
    source backend/venv/bin/activate
    pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r backend/requirements.txt
    echo "[OK] 依赖安装完成"

    # 5. 创建数据目录
    mkdir -p backend/uploads data

    # 6. 生成 SECRET_KEY
    generate_secret

    # 7. 停止可能占用 80 端口的服务
    echo "[INFO] 检查端口 80 占用情况..."
    if lsof -i :80 | grep -q LISTEN; then
        echo "[INFO] 端口 80 被占用，尝试停止 nginx..."
        systemctl stop nginx 2>/dev/null || true
        systemctl disable nginx 2>/dev/null || true
        kill $(lsof -t -i :80) 2>/dev/null || true
        sleep 1
    fi

    # 8. 配置 supervisor
    echo "[INFO] 配置 supervisor 进程管理..."
    yum install -y supervisor 2>/dev/null || apt-get install -y supervisor 2>/dev/null || true

    VENV_PATH="$(pwd)/backend/venv"
    APP_PATH="$(pwd)/backend"

    cat > /etc/supervisord.d/money-app.ini << SUPEREOF
[program:money-app]
directory=${APP_PATH}
command=${VENV_PATH}/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/money-app.err.log
stdout_logfile=/var/log/money-app.out.log
environment=PATH="${VENV_PATH}/bin"
SUPEREOF

    systemctl start supervisord 2>/dev/null || true
    systemctl enable supervisord 2>/dev/null || true
    supervisorctl reread
    supervisorctl update
    supervisorctl restart money-app

    echo ""
    echo "=========================================="
    echo "  Python 部署完成！"
    echo "=========================================="
    echo ""
    echo "  访问地址: http://$(hostname -I | awk '{print $1}')"
    echo "  查看日志: tail -f /var/log/money-app.out.log"
    echo "  重启应用: supervisorctl restart money-app"
    echo ""
}

# ============================================================
# Docker 部署模式
# ============================================================

deploy_docker() {
    echo "[INFO] 使用 Docker 部署模式"

    # 1. 检查 Docker
    if ! command -v docker &> /dev/null; then
        echo "[INFO] Docker 未安装，正在安装..."
        curl -fsSL https://get.docker.com | sh 2>/dev/null || {
            echo "[WARN] 官方安装脚本失败，尝试国内镜像..."
            yum install -y yum-utils
            yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
            yum install -y docker-ce docker-ce-cli containerd.io
        }
        systemctl start docker
        systemctl enable docker
    fi

    # 2. 配置 Docker 镜像加速
    mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ] || ! grep -q "mirror" /etc/docker/daemon.json; then
        tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com", "https://docker.m.daocloud.io"]
}
EOF
        systemctl daemon-reload
        systemctl restart docker
    fi

    # 3. 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        echo "[INFO] 安装 Docker Compose..."
        yum install -y docker-compose-plugin 2>/dev/null || apt-get install -y docker-compose-plugin 2>/dev/null || true
    fi

    # 4. 创建数据目录
    mkdir -p data/db data/uploads

    # 5. 生成 SECRET_KEY
    generate_secret

    # 6. 构建并启动
    echo "[INFO] 构建 Docker 镜像..."
    docker compose build

    echo "[INFO] 启动容器..."
    docker compose up -d

    echo ""
    echo "=========================================="
    echo "  Docker 部署完成！"
    echo "=========================================="
    echo ""
    echo "  访问地址: http://$(hostname -I | awk '{print $1}')"
    echo "  查看日志: docker compose logs -f"
    echo "  停止服务: docker compose down"
    echo "  重启服务: docker compose restart"
    echo ""
}

# ============================================================
# 主流程
# ============================================================

check_root

case "$MODE" in
    docker)
        deploy_docker
        ;;
    python|"")
        deploy_python
        ;;
    *)
        echo "用法: $0 [python|docker]"
        exit 1
        ;;
esac
