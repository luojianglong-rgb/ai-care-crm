# AI-Care CRM

> 面向养生 / SPA / 美发 / 美甲 / 皮肤管理 / 产后修复行业的本地部署 AI 客户关系管理系统。
> 数据全部存放在商户本地（SQLite），AI 调用通过本地 PII 脱敏后再访问大模型。

## ✨ 功能特性

- 👤 客户档案 / 预约 / 库存 / 收银 / 服务项目 — 完整的本地 CRM 闭环
- 🤖 AI 分析与个性化养护方案（OpenAI 兼容：DeepSeek / 通义千问 / GLM / Kimi / 文心一言 / 讯飞星火）
- 📱 移动端技师工作台（WAP，免登录扫码进入）
- 📣 营销剧本（Playbook）+ 多渠道触达（短信 API / 短信 RPA / 个人微信 CLI / ML307A 4G 模组）
- 📨 客户回复解析、自动化跟进
- 📊 仪表盘 / 看板数据聚合
- 🔐 JWT 管理后台鉴权 + 许可证分级（基础 / 专业 / 至尊）
- 📦 支持 PyInstaller 打成单 EXE 部署

## 🧱 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2.0 · APScheduler · SQLite |
| 前端 | React 19 · TypeScript 5 · Vite 7 · Tailwind CSS v4 · axios · react-router-dom v7 |
| AI | OpenAI 兼容 SDK（DeepSeek / Qwen / GLM / Kimi / Baichuan / Spark） |
| 鉴权 | python-jose（JWT） |
| 打包 | PyInstaller |

## 🚀 本地启动

### 前置条件

- Python **3.14+**
- Node.js **20+**（仅开发前端时需要）
- Windows 10/11（生产部署建议），macOS / Linux 也能跑开发模式

### 1. 克隆与虚拟环境

```bash
git clone https://github.com/luojianglong-rgb/ai-care-crm.git
cd ai-care-crm

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置文件

```bash
# 复制配置模板
cp src/config.yaml.template src/config.yaml
# 用编辑器填入你的 LLM API Key、渠道参数等
```

> ⚠️ `src/config.yaml` **不会被提交**（已在 `.gitignore`），请妥善保管 API Key。

### 3. 启动后端

```bash
cd src
../.venv/Scripts/python main.py        # Windows
# 或：../.venv/bin/python main.py      # macOS / Linux
```

- 后端：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`

### 4. 启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

- 前端：`http://localhost:5173`
- 默认账号：`admin / admin`（**首次启动会被强制重置，请立即修改！**）

### 一键启动（Windows）

```bash
# 根目录
startup.bat
```

## 📁 目录结构

```
wellness-crm/
├── CLAUDE.md              # Claude Code 项目指南（开发规则）
├── README.md              # 本文件
├── LICENSE                # MIT 协议
├── ai_care_crm.spec       # PyInstaller 配置
├── requirements.txt       # 后端依赖
├── startup.bat            # 一键启动
├── shutdown.bat           # 一键停止
├── .github/workflows/     # GitHub Actions CI
├── docs/                  # 项目文档
├── frontend/              # React SPA
├── src/                   # Python 后端
│   ├── main.py
│   ├── config.yaml.template  # ✅ 入库
│   ├── config.yaml           # ❌ 不入库（含密钥）
│   ├── api/                  # REST 路由
│   ├── services/             # 业务逻辑层
│   ├── channels/             # 多渠道发送驱动
│   ├── playbook/             # 营销剧本
│   ├── ai/                   # LLM 客户端 + 分析器
│   ├── tools/                # 工具函数
│   └── migrations/           # 数据库迁移脚本
├── tests/                 # 测试代码（unit / integration / api / ui）
└── skills/                # 打包 / 部署辅助脚本
```

## 🔒 安全须知

| 项 | 说明 |
|---|---|
| 默认密码 | `admin / admin`，首次启动 `init_default_admin` 会强制重置，**生产部署前必须修改** |
| 数据库 | SQLite 存于 `src/wellness_crm.db`，**不入库**；升级前请手动备份到 `backups/` |
| API Key | 放在 `src/config.yaml`，**不入库**；如意外泄露请立即轮换 |
| 客户隐私 | 所有 PII 在送 LLM 之前做本地脱敏处理（见 `src/ai/`） |
| 数据库升级 | 新版本启动时自动执行 `src/migrations/` 中的迁移脚本，旧库自动迁移不丢数据 |

## 📦 部署打包

```bash
# 打成单 EXE（约 30MB，源码已加密）
python skills/build_exe.py

# 输出在 dist/
# dist/AI-Care-CRM.exe
```

详见 [`docs/打包发布指南.md`](docs/打包发布指南.md) 与 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)。

## 🧪 测试

```bash
# 后端
.venv\Scripts\pytest tests/ -v

# 前端
cd frontend && npm run lint && npm run build
```

CI 状态：[![CI](https://github.com/luojianglong-rgb/ai-care-crm/actions/workflows/ci.yml/badge.svg)](https://github.com/luojianglong-rgb/ai-care-crm/actions/workflows/ci.yml)

## 📚 文档

- 架构设计：[`docs/System_Design_Document.md`](docs/System_Design_Document.md)（注：完整设计稿在 `wellness-crm-design/`，未随本仓库发布）
- API 文档：启动后端后访问 `http://localhost:8000/docs`
- 部署指南：[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- ML307A 4G 模组：[`docs/ML307A 使用指南.md`](docs/ML307A%20使用指南.md)
- Mac 打包：[`docs/Mac打包指南.md`](docs/Mac打包指南.md)

## 📜 协议

[MIT](LICENSE) © luojianglong-rgb

## 🤝 贡献

欢迎 Issue 与 PR。请遵守 `CLAUDE.md` 中的目录组织规范。