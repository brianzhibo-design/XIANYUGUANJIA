#!/usr/bin/env bash
# 闲鱼管家 - macOS 双击启动
# 将此文件拖到桌面或 Dock，双击即可启动所有服务

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 从 Finder 双击时 PATH 不完整，补充常见路径
for p in /opt/homebrew/bin /opt/homebrew/sbin /usr/local/bin "$HOME/.nvm/versions/node"/*/bin; do
  [ -d "$p" ] && case ":$PATH:" in *:"$p":*) ;; *) export PATH="$p:$PATH" ;; esac
done
[ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" 2>/dev/null || true

echo ""
echo "========================================="
echo "  🐟 闲鱼管家 v9.1.0 - 启动中..."
echo "========================================="
echo ""

# 激活 Python 虚拟环境
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "[OK] Python 虚拟环境已激活"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "[OK] Python 虚拟环境已激活 (venv)"
else
    echo "[!!] 未找到虚拟环境，使用系统 Python"
    echo "     建议先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi

# 确保必要目录存在
mkdir -p data logs config

# 检查配置文件
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[INFO] 已从模板创建 .env，请编辑填入配置"
    fi
fi
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config.example.yaml" ]; then
        cp config/config.example.yaml config/config.yaml
        echo "[INFO] 已从模板创建 config/config.yaml"
    fi
fi

# 检查端口占用
check_port() {
    if lsof -ti :"$1" >/dev/null 2>&1; then
        echo "[!!] 端口 $1 已被占用，尝试释放..."
        lsof -ti :"$1" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

check_port 8091
check_port 5173

# 启动后端
echo ""
echo "[*] 启动 Python 后端 (端口 8091)..."
python3 -m src.dashboard_server --port 8091 &
BACKEND_PID=$!
echo "    PID: $BACKEND_PID"

# 等待后端就绪
sleep 2

# 启动前端
FRONTEND_PID=""
if [ -d "client" ] && [ -f "client/package.json" ]; then
    if command -v node >/dev/null 2>&1; then
        echo "[*] 启动前端 (端口 5173)..."
        cd client && npx vite --host &
        FRONTEND_PID=$!
        echo "    PID: $FRONTEND_PID"
        cd "$PROJECT_ROOT"
    else
        echo "[!!] 未找到 Node.js，跳过前端启动"
        echo "     可直接访问后端: http://localhost:8091"
    fi
fi

echo ""
echo "========================================="
echo "  服务已启动!"
echo "========================================="
echo ""
echo "  管理面板: http://localhost:5173"
echo "  后端 API: http://localhost:8091"
echo ""
echo "  关闭此窗口将停止所有服务"
echo "  按 Ctrl+C 手动停止"
echo "========================================="
echo ""

# 自动打开浏览器
if command -v open >/dev/null 2>&1; then
    sleep 3
    open "http://localhost:5173" 2>/dev/null || true
fi

cleanup() {
    echo ""
    echo "[*] 正在停止服务..."
    kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    echo "[OK] 服务已停止"
    exit 0
}

trap cleanup INT TERM

wait
