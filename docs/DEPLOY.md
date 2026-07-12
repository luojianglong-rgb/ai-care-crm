# AI-Care CRM 部署指南

## 部署包结构

```
AI-Care-CRM/
├── install.bat         # 安装脚本（首次运行）
├── startup.bat         # 启动服务
├── shutdown.bat        # 关闭服务
├── requirements.txt    # Python 依赖清单
├── src/
│   ├── main.py                # 主程序入口
│   ├── config.py              # 配置加载模块
│   ├── config.yaml.template   # 配置模板
│   ├── database.py            # 数据库配置
│   ├── db_models.py           # 数据库模型
│   ├── license_manager.py     # 授权管理
│   ├── models.py              # 数据模型
│   ├── api/                   # API 路由模块
│   ├── ai/                    # AI 模块
│   ├── channels/              # 渠道模块
│   ├── playbook/              # 剧本引擎
│   ├── services/              # 服务模块
│   └── tools/                 # 工具模块
└── logs/              # 日志目录（运行时自动生成）
```

---

## 部署步骤

### 步骤 1：准备环境

确保目标服务器已安装：
- **Python 3.10 或更高版本**
- **pip**（通常随 Python 一起安装）

验证 Python 安装：
```cmd
python --version
```

### 步骤 2：解压部署包

将部署包解压到目标目录，例如：
```
C:\AI-Care-CRM\
```

### 步骤 3：运行安装脚本

双击 `install.bat`，脚本会自动：
1. 创建 Python 虚拟环境（`.venv` 目录）
2. 安装所有 Python 依赖
3. 生成配置文件

### 步骤 4：配置系统

编辑 `src\config.yaml` 文件，填写必填项：

```yaml
# 门店基础信息
store:
  name: "您的门店名称"              # [必填] 修改为您的门店名称
  business_type: tcm_wellness       # 业态类型

# AI 大模型配置
llm:
  api_key: "sk-xxxxxxxx"            # [必填] 大模型 API Key
  provider: deepseek                # 推荐：DeepSeek（性价比高）
  model: "deepseek-chat"
```

### 步骤 5：启动服务

双击 `startup.bat` 启动服务。

首次启动时，系统会自动：
- 创建数据库（`src\wellness_crm.db`）
- 创建默认管理员账号（admin / admin）
- 生成日志目录（`logs/`）

### 步骤 6：登录系统

打开浏览器访问：
```
http://localhost:8000/login
```

使用默认账号登录：
- 用户名：`admin`
- 密码：`admin`

---

## 服务管理

### 启动服务
```cmd
双击 startup.bat
```

### 关闭服务
```cmd
双击 shutdown.bat
```

### 查看运行状态
打开任务管理器，查找进程：
- `python.exe` 运行 `main.py`

### 查看日志
日志文件位于：`logs\app.log`

---

## 常见问题

### 1. 端口 8000 被占用

**症状**：启动时提示 "Address already in use" 或 "端口被占用"

**解决**：
1. 编辑 `src\config.yaml`
2. 修改 `server.port` 为其他端口，例如：
   ```yaml
   server:
     port: 8080
   ```
3. 重启服务

### 2. 忘记管理员密码

**解决**：
1. 关闭服务
2. 删除 `src\wellness_crm.db`
3. 重启服务，系统会自动重建默认账号（admin / admin）

### 3. Python 未找到

**症状**：运行时提示 "python 不是内部或外部命令"

**解决**：
1. 下载安装 Python：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"

### 4. 依赖包安装失败

**症状**：install.bat 运行时提示 pip 安装错误

**解决**：
```cmd
# 手动运行安装命令
.venv\Scripts\pip install -r requirements.txt
```

---

## 高级配置

### 开机自动启动

1. 按 `Win+R`，输入 `shell:startup`，打开启动文件夹
2. 创建 `startup.bat` 的快捷方式
3. 将快捷方式放入启动文件夹

### 局域网访问

1. 编辑 `src\config.yaml`
2. 确保 `server.host` 为 `0.0.0.0`（允许局域网访问）
3. 在防火墙中开放 8000 端口

其他电脑访问地址：
```
http://<服务器 IP>:8000/login
```

### 配置 ML307A 短信猫

编辑 `src\config.yaml`：
```yaml
channels:
  ml307a:
    enabled: true
    port: 'COM3'           # 串口号，留空自动扫描
    baudrate: 115200
```

---

## 升级说明

### 从旧版本升级

1. 关闭服务（运行 `shutdown.bat`）
2. 备份配置文件 `src\config.yaml`
3. 备份数据库 `src\wellness_crm.db`
4. 删除旧版本文件（保留 `config.yaml` 和 `wellness_crm.db`）
5. 解压新版本
6. 将备份的配置文件和数据库复制回 `src/` 目录
7. 启动服务

---

## 技术支持

如有问题，请联系技术支持，提供以下信息：
- 操作系统版本
- Python 版本
- 日志文件内容（`logs\app.log`）
