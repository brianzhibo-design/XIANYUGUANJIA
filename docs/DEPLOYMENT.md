# DEPLOYMENT（统一口径）

> 本文与 `README.md`、`QUICKSTART.md` 保持一致：
> - **唯一推荐首启路径：Lite/Core**
> - **OpenClaw / Docker 为可选部署方式**
> - 默认访问地址：`http://127.0.0.1:8091`
> - `5173` 仅用于前端开发

---

## 1. 部署策略

### 1.1 推荐（默认）
**Lite/Core 本地部署**
- 适合首次安装、单机稳定运行、低门槛排障
- 启动后直接使用 Dashboard 完成配置和验证

### 1.2 可选
- **Docker Compose**：适合容器化运维
- **OpenClaw Gateway 深度模式**：适合需要 Gateway 编排能力的场景

---

## 2. 最小环境变量集

复制模板：

```bash
cp .env.example .env
```

最小必填（可启动 + 可验证）：

```bash
# 至少一个网关模型 Key
ANTHROPIC_API_KEY=
# 或 OPENAI_API_KEY / MOONSHOT_API_KEY / MINIMAX_API_KEY / ZAI_API_KEY / CUSTOM_GATEWAY_API_KEY

OPENCLAW_GATEWAY_TOKEN=your-secret-token
AUTH_PASSWORD=changeme
XIANYU_COOKIE_1=your_cookie_here
```

---

## 3. Lite/Core 部署步骤（推荐）

### Step 1: 安装依赖

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
```

### Step 2: 启动 Dashboard

```bash
python -m src.dashboard_server --host 127.0.0.1 --port 8091
```

访问：`http://127.0.0.1:8091`

### Step 3: 启动业务模块（按需）

```bash
python -m src.cli module --action start --target all --mode daemon --background --interval 5 --limit 20 --claim-limit 10 --issue-type delay --init-default-tasks
```

---

## 4. 首次 smoke 验证（已落地脚本）

推荐执行：

```bash
bash scripts/verify-quickstart.sh
```

验证项：
1. `.env` 与最小环境变量集
2. `http://127.0.0.1:8091/healthz`
3. `http://127.0.0.1:8091/api/get-cookie`（Cookie 就绪）

日志输出：`logs/verify-quickstart.log`

---

## 5. 可选部署：Docker（非默认）

```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

> 容器模式用于标准化运维，不替代 Lite/Core 作为首启路径。

---

## 6. 可选部署：OpenClaw Gateway 配对（非默认）

当出现 `pairing required` 时：

```bash
docker compose exec -it openclaw-gateway openclaw devices list
docker compose exec -it openclaw-gateway openclaw devices approve <requestId>
```

---

## 7. 地址与端口口径

- 默认面板：`http://127.0.0.1:8091`
- `5173`：仅前端开发（Vite），非生产/首启入口
