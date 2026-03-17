#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!!]${NC} $1"; }
fail()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }
step()  { echo -e "${CYAN}==> ${NC}$1"; }

echo ""
echo "========================================="
echo "  闲鱼管家 - 一键更新"
echo "========================================="
echo ""

# Detect deployment mode
IS_DOCKER=0
if [ -f "docker-compose.yml" ] && command -v docker &>/dev/null; then
    RUNNING=$(docker compose ps --format json 2>/dev/null | head -1 || true)
    if [ -n "$RUNNING" ]; then
        IS_DOCKER=1
    fi
fi

CURRENT_VERSION="unknown"
if [ -f "src/__init__.py" ]; then
    CURRENT_VERSION=$(python3 -c "
import re, pathlib
m = re.search(r'__version__\s*=\s*[\"'\''](.*?)[\"'\'']', pathlib.Path('src/__init__.py').read_text())
print(m.group(1) if m else 'unknown')
" 2>/dev/null || echo "unknown")
fi
echo "当前版本: v${CURRENT_VERSION}"

if [ "$IS_DOCKER" = "1" ]; then
    echo "部署模式: Docker Compose"
else
    echo "部署模式: 本地运行"
fi
echo ""

# Check for uncommitted changes
if ! git diff --quiet 2>/dev/null; then
    warn "检测到本地修改的文件"
    git diff --stat
    echo ""
    read -p "是否继续更新？本地修改可能产生合并冲突 (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "已取消更新。"
        exit 0
    fi
fi

# 1. Pull latest code
step "拉取最新代码..."
if git pull --rebase 2>/dev/null; then
    info "代码更新完成"
else
    warn "git pull --rebase 失败，尝试 merge 方式..."
    git pull || fail "代码拉取失败，请手动解决冲突后重试"
    info "代码更新完成 (merge)"
fi

NEW_VERSION="unknown"
if [ -f "src/__init__.py" ]; then
    NEW_VERSION=$(python3 -c "
import re, pathlib
m = re.search(r'__version__\s*=\s*[\"'\''](.*?)[\"'\'']', pathlib.Path('src/__init__.py').read_text())
print(m.group(1) if m else 'unknown')
" 2>/dev/null || echo "unknown")
fi
echo "更新后版本: v${NEW_VERSION}"
echo ""

if [ "$IS_DOCKER" = "1" ]; then
    # Docker mode update
    step "重新构建 Docker 镜像..."
    MIRROR_ARG=""
    if [ "${MIRROR:-}" = "china" ] || [ "${CN_MIRROR:-1}" = "1" ]; then
        MIRROR_ARG="MIRROR=china"
    fi

    if [ -n "$MIRROR_ARG" ]; then
        $MIRROR_ARG docker compose build --no-cache || fail "镜像构建失败"
    else
        docker compose build --no-cache || fail "镜像构建失败"
    fi
    info "镜像构建完成"

    step "重启容器..."
    docker compose down
    docker compose up -d || fail "容器启动失败"
    info "容器已重启"

    step "等待服务就绪..."
    sleep 5
    docker compose ps
else
    # Local mode update
    step "安装 Python 依赖..."
    PIP_ARGS=""
    if [ "${CN_MIRROR:-}" = "1" ] || [ "${CHINA_MIRROR:-}" = "1" ]; then
        PIP_ARGS="-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
    fi
    pip3 install -q -r requirements.txt $PIP_ARGS 2>/dev/null && info "Python 依赖已更新" || warn "部分 Python 依赖安装失败"

    if [ -d "client" ] && [ -f "client/package.json" ]; then
        step "安装前端依赖并构建..."
        cd client
        NPM_ARGS=""
        if [ "${CN_MIRROR:-}" = "1" ] || [ "${CHINA_MIRROR:-}" = "1" ]; then
            NPM_ARGS="--registry=https://registry.npmmirror.com"
        fi
        npm install $NPM_ARGS --silent 2>/dev/null && info "前端依赖已更新" || warn "部分前端依赖安装失败"
        npm run build 2>/dev/null && info "前端构建完成" || warn "前端构建失败"
        cd "$PROJECT_ROOT"
    fi

    step "重启服务..."
    if [ -f "start.sh" ]; then
        bash start.sh
    else
        warn "未找到 start.sh，请手动重启服务"
    fi
fi

echo ""
echo "========================================="
echo "  更新完成: v${CURRENT_VERSION} -> v${NEW_VERSION}"
echo "========================================="
echo ""
