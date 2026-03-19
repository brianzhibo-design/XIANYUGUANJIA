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

# 动态读取版本号
APP_VERSION="unknown"
if [ -f "src/__init__.py" ]; then
    APP_VERSION=$(python3 -c "import re; m=re.search(r'__version__\s*=\s*[\"'\''](.*?)[\"'\'']', open('src/__init__.py').read()); print(m.group(1) if m else 'unknown')" 2>/dev/null || echo "unknown")
fi

echo ""
echo "========================================="
echo "  🐟 闲鱼管家 v${APP_VERSION} - 启动中..."
echo "========================================="
echo ""

# 拉取最新代码
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
    echo "[*] 拉取最新代码..."
    if git pull --ff-only 2>/dev/null; then
        echo "[OK] 代码已更新"
    else
        echo "[!!] git pull 失败（可能有本地修改），使用当前代码继续"
    fi
    echo ""
fi

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

# 检查端口占用并释放
check_port() {
    if lsof -ti :"$1" >/dev/null 2>&1; then
        echo "[!!] 端口 $1 已被占用，尝试释放..."
        lsof -ti :"$1" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

check_port 8091
check_port 5173

PIDS=()

# 启动后端 API (8091)
echo ""
echo "[*] 启动后端 (端口 8091)..."
python3 -m src.dashboard_server --port 8091 &
PIDS+=($!)
echo "    PID: ${PIDS[-1]}"

# 启动前端 vite dev server (5173)
if [ -d "client" ] && [ -f "client/package.json" ]; then
    echo "[*] 启动前端 (端口 5173)..."
    if [ ! -d "client/node_modules" ]; then
        echo "    安装前端依赖..."
        (cd client && npm install --silent) || echo "[!!] npm install 失败"
    fi
    (cd client && npx vite --port 5173) &
    PIDS+=($!)
    echo "    PID: ${PIDS[-1]}"
    FRONTEND_URL="http://localhost:5173"
else
    echo "[!!] 未找到 client/ 目录，仅启动后端"
    FRONTEND_URL="http://localhost:8091"
fi

sleep 2

echo ""
echo "========================================="
echo "  服务已启动!"
echo "========================================="
echo ""
echo "  管理面板: $FRONTEND_URL"
echo "  后端 API: http://localhost:8091"
echo ""
echo "  关闭此窗口将停止所有服务"
echo "  按 Ctrl+C 手动停止"
echo "========================================="
echo ""

# 自动打开浏览器
if command -v open >/dev/null 2>&1; then
    sleep 3
    open "$FRONTEND_URL" 2>/dev/null || true
fi

cleanup() {
    echo ""
    echo "[*] 正在停止服务..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    echo "[OK] 服务已停止"
    exit 0
}

trap cleanup INT TERM

wait
