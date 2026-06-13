#!/bin/bash

echo "========================================"
echo "   Money App - 个人记账程序启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 查找 Python
PYTHON=""
for py in python python3; do
    if command -v "$py" &> /dev/null; then
        PYTHON="$py"
        break
    fi
done

# 如果找不到，尝试常见路径
if [ -z "$PYTHON" ]; then
    for py in \
        "/c/Users/$USER/AppData/Local/Programs/Python/Python312/python.exe" \
        "/c/Users/$USER/AppData/Local/Programs/Python/Python312/python3.exe" \
        "/c/Python312/python.exe"; do
        if [ -f "$py" ]; then
            PYTHON="$py"
            export PATH="$(dirname "$py"):$PATH"
            break
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo -e "\033[31m[错误] 未找到 Python，请先安装 Python 3.12+\033[0m"
    exit 1
fi

echo -e "\033[32m[检查] Python: $($PYTHON --version)\033[0m"

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo -e "\033[33m[检查] 安装前端依赖...\033[0m"
    cd frontend
    npm install
    cd ..
fi

# 构建前端
echo -e "\033[32m[1/2] 构建前端...\033[0m"
cd frontend
npx vite build
cd ..

# 检查后端虚拟环境
if [ ! -d "backend/venv" ]; then
    echo -e "\033[33m[检查] 创建后端虚拟环境...\033[0m"
    cd backend
    $PYTHON -m venv venv
    source venv/Scripts/activate 2>/dev/null || source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# 获取本机IP（简化版）
IP=$(ipconfig 2>/dev/null | grep -oP '192\.\d+\.\d+\.\d+' | head -1)

echo ""
echo -e "\033[32m[2/2] 启动后端服务...\033[0m"
echo ""
echo "========================================"
echo -e "\033[32m   Money App 已启动！\033[0m"
echo "========================================"
echo "   本机访问: http://localhost:8000"
if [ -n "$IP" ]; then
    echo "   手机访问: http://$IP:8000"
fi
echo "   API文档:  http://localhost:8000/docs"
echo "========================================"
echo ""
echo -e "\033[90m按 Ctrl+C 停止服务\033[0m"
echo ""

# 启动后端
cd backend
source venv/Scripts/activate 2>/dev/null || venv/Scripts/activate

# 检查端口是否被占用
if netstat -ano 2>/dev/null | grep -q ":8000 .*LISTENING"; then
    echo -e "\033[31m[错误] 端口 8000 已被占用，请先关闭占用该端口的程序\033[0m"
    echo ""
    netstat -ano 2>/dev/null | grep ":8000 .*LISTENING"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 如果 uvicorn 异常退出，显示错误信息
echo ""
echo -e "\033[31m[错误] 后端服务已停止\033[0m"
read -p "按回车键退出..."
