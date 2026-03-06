# QUICKSTART（推荐路径：Lite/Core）

> 目标：0 基础用户首次启动并在 **http://127.0.0.1:8091** 完成配置与验证。
> 说明：`5173` 仅用于前端开发热更新，不是默认使用地址。

## 📋 前置要求

## 1) 推荐启动路径（唯一推荐）：Lite/Core

本项目默认推荐 **Lite/Core 本地运行**：
- Python 本地启动
- Dashboard 默认地址 `http://127.0.0.1:8091`
- 可直接在 Dashboard 完成 Cookie 配置、状态检查与模块控制

> OpenClaw Gateway / Docker 部署属于可选方案，见文末“可选路径”。

---

## 2) 最小环境变量集

先复制模板：

```bash
cp .env.example .env
```

然后至少填写以下变量（最小可运行集合）：

```bash
# 网关模型 Key：以下至少 1 个
ANTHROPIC_API_KEY=
# 或 OPENAI_API_KEY / MOONSHOT_API_KEY / MINIMAX_API_KEY / ZAI_API_KEY / CUSTOM_GATEWAY_API_KEY

# 本地鉴权
OPENCLAW_GATEWAY_TOKEN=your-secret-token
AUTH_PASSWORD=changeme

# 闲鱼登录态
XIANYU_COOKIE_1=your_cookie_here
```

> 其余变量（如 `AI_PROVIDER/AI_API_KEY/AI_BASE_URL/AI_MODEL`）可按需后续补充，不阻塞首次启动验证。

---

## 3) 0 基础首次配置步骤

### Step A. 准备 Python 环境

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
```

### Step B. 获取并写入 Cookie

1. 浏览器打开 `https://www.goofish.com` 并登录
2. 按 `F12` → `Network`
3. 刷新页面并点任意请求
4. 在 `Request Headers` 复制整行 `Cookie:` 内容
5. 粘贴到 `.env` 的 `XIANYU_COOKIE_1`

### Step C. 启动 Dashboard（首次入口）

```bash
python -m src.dashboard_server --host 127.0.0.1 --port 8091
```

浏览器访问：**http://127.0.0.1:8091**

---

## 4) 首次验证步骤（必须做）

### 方式 1（推荐）：一条命令自动验证

```bash
bash scripts/verify-quickstart.sh
```

脚本会验证：
- `.env` 和最小环境变量是否就绪
- Dashboard 是否可启动并通过 `/healthz`
- Cookie 是否被 `/api/get-cookie` 正常读取

验证日志：`logs/verify-quickstart.log`

### 方式 2：手动验证命令链

```bash
# 1) 启动 dashboard
python -m src.dashboard_server --host 127.0.0.1 --port 8091

# 2) 新终端执行健康检查
curl -fsS http://127.0.0.1:8091/healthz

# 3) 检查 cookie 就绪
curl -fsS http://127.0.0.1:8091/api/get-cookie
```

成功标准：
- `/healthz` 返回 `{"status":"ok"}`
- `/api/get-cookie` 返回 `"success": true`

---

## 5) 可选路径（非推荐）

### 可选 A：Docker

```bash
docker compose up -d
docker compose ps

# 查看日志
docker compose logs -f

# 健康检查
curl http://localhost:8080/healthz
```

> Docker 用于容器化运维；不作为默认首启路径。

### 可选 B：OpenClaw Gateway 深度集成

如需 OpenClaw 设备配对与 Gateway 运维，可参考：
- `docs/DEPLOYMENT.md`（可选部署章节）
- `README.md` 的部署说明

---

## 6) 常见地址说明（统一口径）

- 默认业务面板：`http://127.0.0.1:8091`
- `http://127.0.0.1:5173`：仅前端开发服务（Vite dev server）
