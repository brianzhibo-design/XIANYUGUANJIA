# Xianyu Guanjia (闲鱼管家) v9.2.1

> **⚠️ 架构变更通知 (v8.1.0+)**
>
> 本项目已进行深度重构，**废弃了所有“一键安装 (.bat/.sh)”和冗余的内置 HTML 打包方式**，全面转向现代化的 **前端 (React/Vite) + 后端 (Python Asyncio)** 分离架构。
>
> 本项目旨在作为工作室内部部署和 AI Agent 自动化驱动的基础设施。不再面向无编程基础的 C端用户提供“双击启动包”。

## 🚀 核心特性

- **多级 Cookie 降级保活体系**：`闲管家 IM 直读 -> CookieCloud 实时同步 -> 本地数据库直读 -> Playwright 硬解滑块`，四级降级策略应对阿里严苛的 Web 端风控。
- **Cookie 统一持久化**：WS Transport 的所有 cookie 刷新路径均通过 `cookie_store` 原子写入 `.env`，确保进程重启后恢复最新凭证，Dashboard 健康检查始终反映实时状态。
- **现代化前后端分离**：React + TailwindCSS 构建的现代化 Dashboard 仪表盘，提供直观的状态监控与配置热更新。
- **AI 智能客服**：接入大语言模型 (DeepSeek等)，实现根据商品信息自动报价、智能上下文回复。
- **虚拟商品全自动核销**：支持卡密自动发货，自动标记已发货，状态全链路闭环。
- **闲管家深度集成**：兼容闲管家 PC 端登录状态，双重签名算法支持，降低纯 Web 协议被风控的概率。

---

## 💻 部署指南 (供开发与 AI Agent 查阅)

本项目现推荐由拥有一定开发基础的操作员或 AI 编码 Agent 进行部署。

详细的部署要求请直接参阅根目录下的：[**AGENT_DEPLOYMENT.md**](./AGENT_DEPLOYMENT.md)

### 快速一览

1. **构建前端**：
   ```bash
   cd client
   npm install
   npm run build
   ```
2. **初始化后端**：
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **配置文件**：
   复制 `.env.example` 到 `.env`，填入必需的 `XIANYU_COOKIE_1`、`DEEPSEEK_API_KEY` 等参数。
4. **启动服务**：
   ```bash
   python -m src.main
   ```

---

## 🛠 架构设计 (Architecture)

- **前端层 (`client/`)**：纯静态 SPA，编译后存放在 `client/dist/`，由后端接管路由。
- **网关/路由层 (`src/dashboard_server.py`)**：轻量级 `BaseHTTPRequestHandler` 实现的路由分发与静态文件服务。
- **业务中枢 (`src/dashboard/mimic_ops.py`)**：核心的业务操作面（God Object 正在被逐步服务化拆解），负责处理来自 Dashboard 的指令并分发到底层模块。
- **核心模块 (`src/modules/`)**：
  - `messages/`：长链接 WS 通信，心跳维护，消息接收与风控响应。
  - `orders/`：虚拟商品的履约、改价重试机制。
  - `quote/`：物流与虚拟发货的智能报价计算表。

---

## 🤝 参与贡献

欢迎提交 PR。提交代码前请确保：
1. 运行并通过所有的 1100+ 个单元测试：
   `pytest tests/ -v --cov=src`
2. 代码格式符合 Ruff 规范：
   `ruff check src/ && ruff format src/`

## 📜 许可协议 (License)

[MIT License](./LICENSE)
