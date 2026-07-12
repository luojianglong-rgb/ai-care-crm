# AI-Care CRM 系统安装手册

> 本手册面向运维人员，涵盖系统部署、配置、启动、维护的完整流程。

---

## 目录

1. [系统要求](#1-系统要求)
2. [环境准备](#2-环境准备)
3. [安装步骤](#3-安装步骤)
4. [配置说明](#4-配置说明)
5. [启动与停止](#5-启动与停止)
6. [数据备份与恢复](#6-数据备份与恢复)
7. [常见问题排查](#7-常见问题排查)
8. [系统升级](#8-系统升级)
9. [安全建议](#9-安全建议)

---

## 1. 系统要求

### 1.1 硬件要求

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 10 GB | 50 GB+ (SSD) |
| 网络 | 局域网 | 千兆局域网 |

### 1.2 软件要求

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| 操作系统 | Windows 10/11 或 Windows Server 2016+ | 支持 Linux (Ubuntu 20.04+) |
| Python | 3.10+ | 推荐 3.11 或 3.12 |
| Node.js | 18.0+ | 推荐 20.x LTS |
| npm | 9.0+ | 随 Node.js 安装 |
| Git | 最新版 | 用于代码更新 |

### 1.3 网络要求

- 后端服务端口：`8000`（可配置）
- 前端开发服务端口：`5173`（生产环境无需）
- 局域网内其他设备需能访问服务器 IP

---

## 2. 环境准备

### 2.1 安装 Python

**Windows 系统：**

1. 下载 Python 安装包：https://www.python.org/downloads/
2. 运行安装程序，**勾选 "Add Python to PATH"**
3. 打开命令提示符验证：
   ```cmd
   python --version
   pip --version
   ```

### 2.2 安装 Node.js

1. 下载 Node.js LTS 版本：https://nodejs.org/
2. 运行安装程序，使用默认选项
3. 验证安装：
   ```cmd
   node --version
   npm --version
   ```

### 2.3 创建虚拟环境（推荐）

```cmd
# 进入项目目录
cd D:\wellness-crm

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 激活虚拟环境（Linux/Mac）
source .venv/bin/activate
```

---

## 3. 安装步骤

### 3.1 获取代码

**方式一：直接解压部署包**

```cmd
# 解压到目标目录，例如
D:\wellness-crm\
```

**方式二：从 Git 克隆**

```cmd
git clone <仓库地址> D:\wellness-crm
cd D:\wellness-crm
```

### 3.2 安装后端依赖

```cmd
cd D:\wellness-crm

# 激活虚拟环境
.venv\Scripts\activate

# 安装 Python 依赖
pip install -r requirements.txt
```

**主要依赖包：**

| 包名 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| pydantic | 数据验证 |
| sqlalchemy | ORM 数据库操作 |
| python-jose | JWT 认证 |
| passlib + bcrypt | 密码加密 |
| pyyaml | YAML 配置解析 |
| openai | AI 大模型调用 |
| apscheduler | 定时任务调度 |
| openpyxl | Excel 导出 |
| pywinauto | Windows UI 自动化（微信 RPA） |
| uiautomation | Windows UI 自动化（微信 RPA） |
| python-multipart | 文件上传支持 |

### 3.3 安装前端依赖

```cmd
cd D:\wellness-crm\frontend
npm install
```

### 3.4 构建生产版本

```cmd
cd D:\wellness-crm\frontend
npm run build
```

构建产物位于 `frontend/dist/` 目录。

### 3.5 初始化数据库

系统首次启动时会自动创建 SQLite 数据库文件 `src/wellness_crm.db`，并初始化：

- 默认管理员账号：`admin` / `admin`
- 系统预设剧本（7 个）
- 服务项目示例

---

## 4. 配置说明

### 4.1 配置文件位置

```
D:\wellness-crm\src\config.yaml
```

### 4.2 核心配置项

#### 4.2.1 门店信息

```yaml
store:
  name: "您的门店名称"           # 门店名称
  business_type: tcm_wellness   # 业态类型
```

**可选业态类型：**

| 值 | 说明 |
|----|------|
| `tcm_wellness` | 养生馆（中医体质辨识） |
| `spa` | SPA 水疗（肤质分析） |
| `hair_salon` | 美发沙龙（发质分析） |
| `nail_lash` | 美甲美睫（甲型适配） |
| `skin_care` | 皮肤管理（皮肤诊断） |
| `postpartum` | 产后修复（体质评估） |
| `general` | 通用模式 |

#### 4.2.2 授权激活码

```yaml
license:
  key: "CARE-XXXX-XXXX-XXXX-XXXX"  # 激活码
```

**激活码等级：**

| 等级 | 定价 | 功能权限 |
|------|------|----------|
| 基础版 | ¥99/年（线下收取，可灵活减免） | 基础 CRM（50 客户，10 次 AI 分析/月） |
| 专业版 | ¥499/年 | 无限 AI，自定义剧本 |
| 至尊版 | ¥999/年 | + RPA 自动发送 |

#### 4.2.3 AI 大模型配置

```yaml
llm:
  mode: direct                    # direct=直连, proxy=代理
  provider: deepseek              # 大模型提供商
  api_key: "sk-xxxxxxxx"          # API Key
  model: "deepseek-chat"          # 模型名称
  temperature: 0.3                # 温度参数
  max_tokens: 2000                # 最大输出 Token
```

**支持的提供商：**

| Provider | Base URL | 默认模型 |
|----------|----------|----------|
| deepseek | https://api.deepseek.com/v1 | deepseek-chat |
| qwen | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus |
| glm | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| kimi | https://api.moonshot.cn/v1 | moonshot-v1-8k |

#### 4.2.4 触达渠道配置

```yaml
channels:
  default: wechat_rpa
  wechat_rpa:
    enabled: true
    method: pc_rpa               # PC 端微信自动化
  sms_rpa:
    enabled: false
    method: clipboard            # adb / clipboard
  sms_api:
    enabled: false
    mode: direct
    provider: aliyun
    api_key: ""
    api_secret: ""
    sign_name: ""
```

#### 4.2.5 剧本引擎配置

```yaml
playbook:
  scan_hour: 6                   # 每日扫描时间（点）
  send_interval_min: 10          # 发送队列检查间隔（分钟）
  send_delay_min: 30             # 发送间隔最小值（秒）
  send_delay_max: 90             # 发送间隔最大值（秒）
  daily_send_limit: 100          # 每日发送上限
  consecutive_failure_threshold: 5  # 连续失败阈值
  blacklist_phones: []           # 黑名单手机号
  sensitive_keywords: []         # 敏感词列表
```

### 4.3 服务器配置

```yaml
server:
  host: "0.0.0.0"                # 监听地址
  port: 8000                     # 监听端口
  debug: false                   # 调试模式
```

---

## 5. 启动与停止

### 5.1 开发环境启动

**方式一：分别启动前后端**

```cmd
# 终端1：启动后端
cd D:\wellness-crm\src
.venv\Scripts\activate
python main.py

# 终端2：启动前端开发服务器
cd D:\wellness-crm\frontend
npm run dev
```

**方式二：使用启动脚本**

```cmd
# 双击运行
D:\wellness-crm\startup.bat

# 或命令行
cd D:\wellness-crm
startup.bat
```

### 5.2 生产环境启动

**仅启动后端（前端已构建为静态文件）：**

```cmd
cd D:\wellness-crm\src
python main.py
```

前端静态文件由 FastAPI 在 `/` 路径下提供服务。

### 5.3 停止服务

```cmd
# 双击运行
D:\wellness-crm\shutdown.bat

# 或按 Ctrl+C 停止运行中的进程
```

### 5.4 后台服务（Linux）

```bash
# 使用 nohup 后台运行
cd /opt/wellness-crm/src
nohup python main.py > /var/log/wellness-crm.log 2>&1 &

# 使用 systemd（推荐）
# 创建服务文件 /etc/systemd/system/wellness-crm.service
```

**systemd 服务配置示例：**

```ini
[Unit]
Description=AI-Care CRM Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/wellness-crm/src
ExecStart=/opt/wellness-crm/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable wellness-crm
sudo systemctl start wellness-crm
sudo systemctl status wellness-crm
```

### 5.5 Windows 服务（可选）

使用 NSSM 将应用注册为 Windows 服务：

```cmd
# 下载 NSSM
# 安装服务
nssm install WellnessCRM "D:\wellness-crm\.venv\Scripts\python.exe" "D:\wellness-crm\src\main.py"
nssm start WellnessCRM
```

---

## 6. 数据备份与恢复

### 6.1 数据库备份

**手动备份：**

```cmd
# 复制数据库文件
copy D:\wellness-crm\src\wellness_crm.db D:\backup\wellness_crm_20240101.db
```

**自动备份脚本（backup.bat）：**

```batch
@echo off
set BACKUP_DIR=D:\backup\wellness-crm
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%
set TIME=%time:~0,2%%time:~3,2%

if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%

copy D:\wellness-crm\src\wellness_crm.db %BACKUP_DIR%\wellness_crm_%DATE%_%TIME%.db

echo Backup completed: wellness_crm_%DATE%_%TIME%.db
```

**添加到 Windows 任务计划程序，每日自动执行。**

### 6.2 数据恢复

```cmd
# 1. 停止服务
shutdown.bat

# 2. 恢复数据库
copy D:\backup\wellness_crm_20240101.db D:\wellness-crm\src\wellness_crm.db

# 3. 重启服务
startup.bat
```

### 6.3 备份内容清单

| 文件/目录 | 说明 | 备份频率 |
|-----------|------|----------|
| `src/wellness_crm.db` | SQLite 数据库 | 每日 |
| `src/config.yaml` | 系统配置 | 变更时 |
| `frontend/dist/` | 前端构建产物 | 更新时 |

---

## 7. 常见问题排查

### 7.1 后端启动失败

**问题：端口被占用**

```cmd
# 查看端口占用
netstat -ano | findstr :8000

# 结束占用进程
taskkill /PID <进程ID> /F
```

**问题：依赖包缺失**

```cmd
# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

**问题：数据库锁定**

```cmd
# 确保没有其他进程访问数据库
# 删除可能的锁文件
del D:\wellness-crm\src\wellness_crm.db-journal
```

### 7.2 前端页面空白

**检查项：**

1. 后端是否正常运行：访问 http://127.0.0.1:8000/api/v1/ping
2. 浏览器控制台是否有错误（按 F12 查看）
3. 是否正确登录（未登录会重定向到登录页）

**重新构建前端：**

```cmd
cd D:\wellness-crm\frontend
npm run build
```

### 7.3 AI 分析失败

**检查项：**

1. `config.yaml` 中是否配置了正确的 API Key
2. 网络是否能访问大模型 API
3. 查看后端日志中的错误信息

**测试 API 连接：**

```cmd
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### 7.4 微信 RPA 发送失败

**检查清单：**

- [ ] 微信 PC 版已登录并保持运行
- [ ] 客户档案中已填写微信别名
- [ ] 微信中已添加该客户为好友
- [ ] 激活码为 Business 等级

**查看 RPA 日志：**

```cmd
# 后端日志会显示详细的 RPA 操作过程
# 查看 src/logs/ 目录或控制台输出
```

### 7.5 登录失败

**重置管理员密码：**

```cmd
cd D:\wellness-crm\src
python -c "
from database import SessionLocal
from db_models import AdminUser
import bcrypt

db = SessionLocal()
admin = db.query(AdminUser).filter(AdminUser.username == 'admin').first()
if admin:
    admin.password_hash = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.commit()
    print('密码已重置为: admin')
else:
    print('未找到 admin 用户')
db.close()
"
```

---

## 8. 系统升级

### 8.1 升级前准备

1. **备份数据库**
   ```cmd
   copy D:\wellness-crm\src\wellness_crm.db D:\backup\wellness_crm_pre_upgrade.db
   ```

2. **备份配置文件**
   ```cmd
   copy D:\wellness-crm\src\config.yaml D:\backup\config.yaml.bak
   ```

### 8.2 升级步骤

```cmd
# 1. 停止服务
shutdown.bat

# 2. 更新代码
git pull origin main
# 或解压新版本覆盖

# 3. 更新依赖
.venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install

# 4. 重新构建前端
npm run build

# 5. 检查配置文件差异
# 对比新旧 config.yaml，合并新配置项

# 6. 启动服务
startup.bat
```

### 8.3 数据库迁移

如果新版本包含数据库结构变更：

```cmd
# 系统启动时会自动添加新字段
# 如需手动迁移：
cd D:\wellness-crm\src
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///./wellness_crm.db')
with engine.connect() as conn:
    # 添加新列示例
    try:
        conn.execute(text('ALTER TABLE clients ADD COLUMN new_field TEXT'))
        conn.commit()
        print('迁移成功')
    except:
        print('字段已存在或迁移失败')
"
```

---

## 9. 安全建议

### 9.1 账号安全

- [ ] 首次登录后立即修改默认密码
- [ ] 定期更换管理员密码（建议 90 天）
- [ ] 不同人员使用不同账号
- [ ] 离职员工账号及时禁用

### 9.2 网络安全

- [ ] 仅在局域网内开放服务
- [ ] 使用防火墙限制访问 IP
- [ ] 如需外网访问，配置 HTTPS
- [ ] 定期检查登录日志

### 9.3 数据安全

- [ ] 定期备份数据库
- [ ] 备份文件存储在独立位置
- [ ] 敏感配置（API Key）不要提交到版本控制
- [ ] 定期检查 AI 调用额度

### 9.4 系统安全

- [ ] 及时更新操作系统补丁
- [ ] 定期更新 Python 依赖包
- [ ] 关闭不必要的服务和端口
- [ ] 启用系统日志记录

---

## 附录

### A. 目录结构

```
wellness-crm/
├── src/                      # 后端源码
│   ├── main.py               # 主入口
│   ├── config.yaml           # 配置文件
│   ├── wellness_crm.db       # SQLite 数据库
│   ├── api/                  # API 路由
│   ├── services/             # 业务逻辑
│   ├── ai/                   # AI 模块
│   ├── channels/             # 渠道驱动
│   ├── playbook/             # 剧本引擎
│   └── tools/                # 工具脚本
├── frontend/                 # 前端源码
│   ├── src/
│   ├── dist/                 # 构建产物
│   └── package.json
├── startup.bat               # 启动脚本
├── shutdown.bat              # 停止脚本
├── requirements.txt          # Python 依赖
└── README.md                 # 说明文档
```

### B. 默认账号

| 账号类型 | 用户名 | 密码 | 说明 |
|----------|--------|------|------|
| 管理后台 | admin | admin | 请及时修改 |
| WAP 技师端 | 技师手机号 | 初始密码 | 在员工管理中设置 |

### C. API 端点列表

| 路径 | 说明 |
|------|------|
| `/api/v1/ping` | 健康检查 |
| `/api/v1/auth/login` | 登录认证 |
| `/api/v1/clients/` | 客户管理 |
| `/api/v1/billing/` | 财务收银 |
| `/api/v1/bookings/` | 预约管理 |
| `/api/v1/staff/` | 员工管理 |
| `/api/v1/inventory/` | 库存管理 |
| `/api/v1/ai/analyze` | AI 分析 |
| `/api/v1/playbooks/` | 剧本管理 |
| `/api/v1/campaigns/` | 营销任务 |
| `/api/v1/replies/` | 客户回复 |
| `/api/v1/config/` | 系统配置 |

### D. 技术支持

- **系统版本**：v4.1
- **技术支持**：Claude AI
- **文档更新**：2024 年

---

*本文档最后更新于 2024 年*