# 快速开始

5 分钟内启动闲鱼管家。

---

## 前提条件

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.10+ | Python 后端运行时 |
| Node.js | 18+ | Node.js 后端和 React 前端 |
| npm | 随 Node.js 安装 | 包管理器 |
| Chrome / Edge | 任意版本 | Cookie 自动获取需要本机浏览器 |

---

## 一键启动（推荐）

```bash
# macOS / Linux
bash quick-start.sh

# Windows
quick-start.bat
```

脚本会自动完成：环境检查 → 依赖安装 → 配置校验 → 服务启动 → 首次使用引导。

> 还有精简版一键启动脚本 `start.sh` / `start.bat`，功能相同但无交互引导。

---

## 项目文件结构

```
xianyu-openclaw/
├── quick-start.sh / .bat  # 交互式快速启动（带引导）
├── start.sh / start.bat   # 精简版一键启动
├── setup.sh               # 仅安装依赖（不启动服务）
│
├── config/                # 配置文件
│   ├── config.yaml        # 主配置（报价规则、关键词、快递参数等）
│   ├── config.example.yaml# 配置模板
│   ├── rules.yaml         # 自定义回复规则
│   ├── categories/        # 品类配置（快递/票务/虚拟商品等）
│   └── templates/         # 消息模板
│
├── src/                   # Python 后端源码
│   ├── dashboard_server.py# Dashboard 入口（端口 8091）
│   ├── core/              # 核心模块
│   │   ├── config.py      #   配置加载
│   │   ├── config_models.py#  配置模型定义
│   │   ├── browser_client.py# 浏览器客户端（Cookie 获取）
│   │   ├── cookie_grabber.py# Cookie 自动获取
│   │   ├── crypto.py      #   加密工具
│   │   ├── error_handler.py#  错误处理
│   │   └── logger.py      #   日志
│   ├── dashboard/         # Dashboard 服务层
│   │   ├── router.py      #   API 路由
│   │   ├── config_service.py# 配置服务
│   │   ├── repository.py  #   数据仓储
│   │   └── module_console.py# 模块控制台
│   ├── modules/           # 业务模块
│   │   ├── messages/      #   消息处理（核心）
│   │   │   ├── service.py #     消息服务（报价、AI 回复）
│   │   │   ├── reply_engine.py# 回复引擎（意图规则库）
│   │   │   ├── workflow.py#     会话工作流
│   │   │   └── setup.py   #     模块初始化
│   │   ├── quote/         #   报价模块
│   │   │   ├── engine.py  #     报价计算引擎
│   │   │   ├── geo_resolver.py# 地理位置解析
│   │   │   ├── cost_table.py#   价格表
│   │   │   └── models.py  #     数据模型
│   │   ├── accounts/      #   账户管理
│   │   ├── orders/        #   订单管理
│   │   ├── content/       #   AI 内容生成
│   │   ├── listing/       #   商品管理
│   │   ├── analytics/     #   数据分析
│   │   ├── ticketing/     #   票务模块
│   │   ├── virtual_goods/ #   虚拟商品
│   │   ├── media/         #   媒体处理
│   │   ├── operations/    #   运营工具
│   │   ├── growth/        #   增长工具
│   │   ├── followup/      #   跟单
│   │   └── compliance/    #   合规检查
│   └── integrations/      # 第三方集成
│       └── xianguanjia/   #   闲管家集成
│
├── server/                # Node.js 后端
│   ├── src/
│   │   ├── app.js         #   入口（端口 3001）
│   │   ├── config/        #   配置
│   │   ├── middleware/    #   中间件
│   │   ├── models/        #   数据模型
│   │   ├── routes/        #   API 路由
│   │   └── services/      #   服务层
│   └── data/
│       ├── system_config.json # 前端管理的系统配置（AI、通知等）
│       └── cookie_cloud/  #   CookieCloud 数据
│
├── client/                # React 前端（管理面板）
│   ├── src/
│   │   ├── App.tsx        #   应用入口
│   │   ├── main.tsx       #   渲染入口
│   │   ├── api/           #   API 调用层
│   │   ├── components/    #   通用组件
│   │   ├── pages/         #   页面
│   │   │   ├── Dashboard.tsx  # 仪表盘
│   │   │   ├── Orders.tsx     # 订单管理
│   │   │   ├── accounts/      # 账户管理
│   │   │   ├── products/      # 商品管理
│   │   │   ├── messages/      # 消息/对话沙盒
│   │   │   ├── analytics/     # 数据分析
│   │   │   └── config/        # 系统配置
│   │   ├── contexts/      #   React Context
│   │   ├── hooks/         #   自定义 Hooks
│   │   └── styles/        #   样式文件
│   ├── vite.config.js     #   Vite 构建配置
│   └── tsconfig.json      #   TypeScript 配置
│
├── data/                  # 运行时数据（自动生成）
│   ├── express_faq.json   #   FAQ 知识库
│   ├── unmatched_messages.jsonl # 未匹配消息日志
│   ├── quote_costs/       #   快递价格表
│   ├── geo/               #   地理数据
│   ├── *.db               #   SQLite 数据库
│   └── brand_assets/      #   品牌素材
│
├── tests/                 # 测试
│   ├── test_reply_comprehensive.py # 161条自动回复测试
│   └── test_dashboard_services.py  # 服务层测试
│
├── scripts/               # 工具脚本
│   ├── backup_data.sh     #   数据备份
│   ├── unix/              #   Unix 辅助脚本
│   ├── windows/           #   Windows 辅助脚本
│   ├── macos/             #   macOS 辅助脚本
│   └── qa/                #   质量检查
│
├── docs/                  # 文档
├── docker-compose.yml     # Docker 编排
├── Dockerfile.python      # Python 镜像
├── requirements.txt       # Python 依赖
├── .env / .env.example    # 环境变量
└── README.md              # 项目说明
```

### 关键配置文件说明

| 文件 | 作用 | 修改场景 |
|------|------|---------|
| `.env` | 环境变量（Cookie、端口） | 更换 Cookie、修改端口 |
| `config/config.yaml` | 报价规则、快递参数、关键词 | 调整价格、新增快递线路 |
| `server/data/system_config.json` | 前端管理的配置（AI、通知） | 通过管理面板修改 |
| `data/express_faq.json` | AI 回复参考的 FAQ 知识库 | 新增常见问题 |
| `config/rules.yaml` | 自定义回复规则 | 定制特殊回复 |

---

## 手动启动（分步骤）

### 第 1 步：安装依赖

```bash
# Python 依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Node.js 依赖
cd server && npm install && cd ..
cd client && npm install && cd ..
```

> Windows 用虚拟环境用 `.venv\Scripts\activate` 替代 `source .venv/bin/activate`。

### 第 2 步：配置

```bash
# 复制环境变量模板
cp .env.example .env

# 复制配置模板（如没有 config.yaml）
cp config/config.example.yaml config/config.yaml
```

编辑 `.env` 填入闲鱼 Cookie。AI 配置可稍后在管理面板中设置。

### 第 3 步：分别启动三个服务

```bash
# 终端 1 - Python 后端
source .venv/bin/activate
python3 -m src.dashboard_server --port 8091

# 终端 2 - Node.js 后端
cd server && node src/app.js

# 终端 3 - React 前端
cd client && npx vite --host
```

### 第 4 步：验证启动

| 服务 | 地址 | 预期结果 |
|------|------|---------|
| 管理面板 | http://localhost:5173 | 管理面板首页 |
| Python API | http://localhost:8091 | Dashboard 页面 |
| Node.js API | http://localhost:3001/health | 健康状态 JSON |

---

## Docker 模式

```bash
cp .env.example .env    # 编辑 .env 填入配置
docker compose up -d    # 启动
docker compose ps       # 查看状态
```

| 容器 | 端口 | 说明 |
|------|------|------|
| xianyu-node-backend | 3001 | Node.js 后端 |
| xianyu-python-backend | 8091 | Python 后端 |
| xianyu-react-frontend | 5173 | React 前端 |

---

## 首次使用指南

```
1. 打开 http://localhost:5173 → 管理面板
2. 账户页 → 粘贴闲鱼 Cookie 或点击「自动获取」
3. 系统配置 → AI 配置 → 选择百炼千问 (Qwen) → 填入 API Key
4. 消息页 → 对话沙盒 → 测试自动回复效果
5. 确认无误后 → 开启自动回复
```

### 获取闲鱼 Cookie

1. Chrome 打开 https://www.goofish.com 并登录
2. **F12** 打开开发者工具 → **Network** 标签
3. **F5** 刷新 → 点击任意请求 → **Request Headers** 找到 `Cookie:` 行
4. 全部复制 → 粘贴到管理面板或 `.env` 文件

Cookie 有效期 7-30 天。过期后通过管理面板在线更新。

### AI 配置推荐

| 提供商 | 模型 | 适合场景 |
|--------|------|---------|
| 百炼千问 (Qwen) | qwen-plus-latest | **推荐** 中文电商，性价比高 |
| DeepSeek | deepseek-chat | 通用场景 |
| OpenAI | gpt-4o-mini | 英文/多语言 |

---

## 常见问题

### 端口被占用

```bash
# macOS/Linux - 查看并杀掉占用进程
lsof -ti :5173 | xargs kill -9
lsof -ti :3001 | xargs kill -9
lsof -ti :8091 | xargs kill -9
```

### Cookie 失效

1. 保持本机 Chrome 登录闲鱼，系统自动读取最新 Cookie
2. 或通过管理面板 → 账户页手动更新
3. 多次失败可能需要在闲鱼 App 完成安全验证

### npm install 失败

```bash
node -v                    # 确认 >= 18
npm cache clean --force    # 清除缓存
npm install                # 重试
```

### pip install 失败（国内用户）

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 停止服务

```bash
# 一键启动模式：Ctrl+C 即可停止所有服务

# Docker 模式
docker compose down       # 停止（保留数据）
docker compose down -v    # 停止并删除数据卷（谨慎）
```

---

## 启动脚本对比

| 脚本 | 平台 | 特点 |
|------|------|------|
| `quick-start.sh` | macOS/Linux | 交互式引导、彩色输出、状态检查 |
| `quick-start.bat` | Windows | 交互式引导、状态检查 |
| `start.sh` | macOS/Linux | 精简版，直接启动 |
| `start.bat` | Windows | 精简版，直接启动 |
| `setup.sh` | macOS/Linux | 仅安装依赖，不启动服务 |

---

## 下一步

- 详细使用指南：[USER_GUIDE.md](USER_GUIDE.md)
- 完整功能说明：[README.md](README.md)
- CLI 命令参考：`python -m src.cli --help`
- 参与开发：[CONTRIBUTING.md](CONTRIBUTING.md)
