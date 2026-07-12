# AI-Care CRM - Claude Code Project Guide

## Project Overview

AI-Care CRM is a locally-deployed AI-powered CRM for personal care businesses (TCM wellness, SPA, hair salon, nail/lash, skin care, postpartum recovery). All data stays on the merchant's machine (SQLite); AI calls use local PII masking before reaching LLM APIs.

## Tech Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0, SQLite, APScheduler
- **Frontend**: React 19, TypeScript 5.9, Vite 7, Tailwind CSS v4, axios, react-router-dom v7
- **AI**: OpenAI-compatible SDK (DeepSeek, Qwen, GLM, Kimi, Baichuan, Spark)
- **Auth**: JWT (python-jose) for admin; token-based for WAP technicians

## Directory Structure

```
wellness-crm/
├── CLAUDE.md              # Project guide (root doc only)
├── ai_care_crm.spec       # PyInstaller config
├── build.bat              # Build script
├── startup.bat            # Launch backend + frontend
├── shutdown.bat           # Stop services
├── requirements.txt       # Python dependencies
├── dist/                  # Build output (EXE)
├── docs/                  # ALL documentation files
│   ├── DEPLOYMENT.md      # Deployment guide
│   ├── API.md             # API documentation
│   └── *.md               # Other docs
├── frontend/              # React SPA
│   └── src/
│       ├── pages/         # Page components
│       ├── pages/wap/     # Mobile technician portal
│       ├── components/    # Shared components
│       ├── hooks/         # Custom hooks
│       └── types/         # TypeScript definitions
├── src/                   # Python backend
│   ├── main.py            # App entry point
│   ├── config.py          # YAML config loader
│   ├── config.yaml        # All system settings
│   ├── database.py        # SQLAlchemy engine
│   ├── db_models.py       # ORM models
│   ├── models.py          # Pydantic schemas
│   ├── api/               # REST endpoints (13 routers)
│   ├── services/          # Business logic layer
│   ├── ai/                # LLM client, analyzers
│   ├── playbook/          # Campaign engine
│   ├── channels/          # Multi-channel send
│   └── tools/             # Utilities
├── skills/                # Packaging/deploy tools
├── tests/                 # ALL test code
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── api/               # API tests
│   ├── ui/                # UI tests
│   ├── utils/             # Test utilities
│   └── conftest.py        # Pytest fixtures
├── logs/                  # Runtime logs
└── memory/                # Claude memory files
```

## File Organization Rules (CRITICAL)

**所有新文件必须按目录分类存放，严禁在根目录随意创建文件！**

| 文件类型 | 必须存放目录 | 示例 |
|---------|-------------|------|
| 文档 (.md) | `docs/` | API.md, DEPLOYMENT.md, 测试报告.md |
| 单元测试 | `tests/unit/` | test_config.py, test_quota.py |
| 集成测试 | `tests/integration/` | test_ai_flow.py, test_sms_flow.py |
| API测试 | `tests/api/` | api_tests.py |
| UI测试 | `tests/ui/` | test_full_ui.py |
| 测试工具 | `tests/utils/` | mock_llm.py, mock_db.py |
| 打包工具 | `skills/` | build_exe.py, package_deploy.py |
| 运行日志 | `logs/` | *.log 文件 |
| Claude记忆 | `memory/` | *.md 记录文件 |

**禁止行为：**
- ❌ 在根目录创建 `.md` 文档文件
- ❌ 在根目录创建测试文件
- ❌ 在根目录创建临时脚本
- ❌ 创建 `temp/`, `tmp/`, `test_tmp/` 等临时目录
- ❌ 在 `src/` 外创建 Python 模块

**例外（根目录允许）：**
- ✅ CLAUDE.md（项目指南）
- ✅ requirements.txt, build.bat, startup.bat, shutdown.bat（核心脚本）
- ✅ PyInstaller 配置文件 (.spec)
- ✅ dist/ 输出目录（打包产物）

## How to Run

```bash
# Backend (from src/ directory)
cd src && ../.venv/Scripts/python main.py
# Runs on http://localhost:8000, API docs at /docs

# Frontend (from frontend/ directory)
cd frontend && npm run dev
# Runs on http://localhost:5173

# Or use startup.bat to launch both
```

## Key URLs

- Admin console: http://localhost:5173 (default login: admin / admin)
- WAP technician portal: http://localhost:5173/wap
- API docs (Swagger): http://localhost:8000/docs

## API Route Prefixes

All APIs under `/api/v1/`:
- `/auth/*` - JWT login, admin CRUD
- `/clients/*` - Client profiles
- `/bookings/*` - Appointments
- `/inventory/*` - Stock management
- `/billing/*` - Transactions
- `/services/*` - Service items
- `/wap/*` - Mobile technician (no JWT required)
- `/config/*` - System config
- `/ai/*` - Analysis & care plans
- `/playbooks/*` - Campaign templates
- `/campaigns/*` - Marketing tasks & approval
- `/replies/*` - Client reply tracking
- `/dashboard/*` - Dashboard data

## Development Conventions

- **Language**: Code comments and UI text are in Chinese (Simplified); variable/function names are English
- **Config**: All settings in `src/config.yaml` - merchants edit only this file
- **Database**: SQLite at `src/wellness_crm.db`, auto-created on first run via `db_models.Base.metadata.create_all()`
- **Backend working dir**: Always `src/` (imports are relative to it)
- **Frontend build**: `cd frontend && npm run build` (output ~460KB JS + 38KB CSS gzipped ~123KB)
- **No git repo**: Project is not version-controlled with git
- **Version Compatibility (CRITICAL)**: 新版本必须兼容旧版本，确保客户数据安全
  - 启动时检查数据库版本号
  - 旧版数据库自动执行迁移脚本
  - 迁移前必须备份（存放在 `backups/` 目录）
  - 新字段必须设置 `nullable=True` 或 `default` 值
  - **禁止直接删除表或字段**
  - 迁移脚本存放在 `src/migrations/` 目录

## Business Tiers

- **基础版** (¥99/yr, offline collection, flexible): 50 clients, 3 staff, 10 AI/month, no RPA
- **专业版** (¥499/yr): Unlimited clients/staff/AI, custom playbooks
- **至尊版** (¥999/yr): + RPA auto-send (WeChat/SMS)

## Design Document

Full system design: `docs/System_Design_Document.md`

## Completed Phases

- Phase 1: Basic CRM (clients, appointments, inventory, billing, WAP)
- Phase 2.0-2.7: AI engine, playbooks, dashboard, admin auth (72+ API endpoints)
- Phase 3: Voice input (Web Speech API)
- Phase 4.0: Channel framework + SMS API driver
- Phase 5: Deployment packaging (automated deployment to E:\test-env)

## Deployment Packaging

### EXE Build (源码保护)

```bash
# 打包成单一 EXE 文件（约30MB）
python skills/build_exe.py

# 或使用批处理
build-exe.bat
```

输出目录：`dist/`
- `AI-Care-CRM.exe` - 主程序（二进制，源码已保护）
- `config/` - 配置文件目录
- `startup.bat` - 启动脚本
- `shutdown.bat` - 停止脚本

### Source Deploy (源码模式)

```bash
# 部署源码版本到测试环境
python skills/package_deploy.py
```

### Deployment Target

All deployments go to `E:\test-env\` with:
- Port: 8888 (production)
- Startup script: `startup.bat`
- Shutdown script: `shutdown.bat`

### Testing

```bash
cd E:\test-env
.venv\Scripts\pytest tests/ -v
```

See `docs/DEPLOYMENT.md` for full details.
