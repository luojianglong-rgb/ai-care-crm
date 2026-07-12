# AI-Care CRM 部署打包指南

## 概述

本项目包含一个自动化部署打包工具，可以从 workspace 自动打包生成生产部署包。

## 目录结构

```
wellness-crm/
├── skills/
│   └── package_deploy.py      # 部署打包脚本
├── tests/                      # 测试脚本（会自动复制到部署包）
│   ├── api_tests.py
│   ├── ui_tests.py
│   └── conftest.py
├── deploy/                     # 部署脚本模板
│   ├── startup.bat            # 生产环境启动脚本（端口 8888）
│   ├── shutdown.bat           # 生产环境关闭脚本
│   ├── install.bat            # 安装向导
│   └── README.md              # 部署包说明
├── src/                        # 后端源码
├── frontend/                   # 前端源码
├── package-deploy.bat          # 一键打包脚本（Windows）
└── quick-build.bat             # 快速打包脚本
```

## 使用方法

### 方法一：使用 Python 脚本（推荐）

```bash
cd D:/claudeCode_wks/wellness-crm
python skills/package_deploy.py
```

### 方法二：使用批处理脚本（Windows）

```batch
cd D:/claudeCode_wks/wellness-crm
package-deploy.bat
```

## 打包流程

打包工具会自动执行以下步骤：

1. **清理临时目录** - 删除旧的打包缓存
2. **复制后端文件** - 复制 src/ 目录所有源码
3. **构建前端** - 执行 `npm run build` 并复制 dist/ 目录
4. **复制启动脚本** - 复制 startup.bat, shutdown.bat, install.bat, README.md
5. **复制测试文件** - 复制 tests/ 目录
6. **部署到目标目录** - 复制到 E:\test-env
7. **创建虚拟环境** - 创建新的 Python venv
8. **安装依赖** - 安装 requirements.txt 和测试框架
9. **安装 Playwright** - 跳过浏览器安装（使用系统 Edge）

## 部署包内容

打包完成后，`E:\test-env\` 目录包含：

```
E:\test-env\
├── .venv/                   # Python 虚拟环境
├── src/
│   ├── main.py              # 后端主程序（端口 8888）
│   ├── config.py            # 配置加载器
│   ├── config.yaml.template # 配置模板
│   ├── database.py          # 数据库配置
│   ├── db_models.py         # 数据模型
│   ├── license_manager.py   # 授权管理
│   ├── models.py            # Pydantic 模型
│   ├── frontend/dist/       # 前端静态文件
│   ├── api/                 # API 路由
│   ├── ai/                  # AI 引擎
│   ├── channels/            # 渠道驱动
│   ├── playbook/            # 运营剧本
│   ├── services/            # 业务服务
│   └── tools/               # 工具函数
├── tests/                   # 测试脚本
│   ├── api_tests.py         # API 测试（12 个用例）
│   ├── ui_tests.py          # UI 测试（7 个用例）
│   └── conftest.py          # pytest 配置
├── startup.bat              # 启动脚本
├── shutdown.bat             # 关闭脚本
├── install.bat              # 安装向导
├── README.md                # 部署说明
└── requirements.txt         # Python 依赖
```

## 使用部署包

### 1. 首次安装

```batch
cd E:\test-env
install.bat
```

### 2. 配置系统

编辑 `E:\test-env\src\config.yaml` 文件，填写：
- 大模型 API Key
- 门店信息
- 业务类型

### 3. 启动服务

```batch
E:\test-env\startup.bat
```

访问：http://localhost:8888
默认账号：`admin / admin`

### 4. 运行测试

```batch
cd E:\test-env
.venv\Scripts\pytest tests/ -v
```

### 5. 停止服务

```batch
E:\test-env\shutdown.bat
```

## 开发工作流

1. **修改代码** - 在 `D:/claudeCode_wks/wellness-crm/` 中开发
2. **运行打包** - 执行 `python skills/package_deploy.py`
3. **验证测试** - 在 `E:\test-env` 中运行测试
4. **启动验证** - 运行 `startup.bat` 验证服务正常

## 注意事项

1. **端口配置**
   - 开发环境：后端 8000，前端 5173
   - 生产部署：统一端口 8888

2. **浏览器依赖**
   - UI 测试使用系统 Microsoft Edge 浏览器
   - 如需 Chromium，手动运行：`playwright install chromium`

3. **虚拟环境**
   - 每次打包会重建虚拟环境
   - 确保依赖安装完整

4. **配置文件**
   - `config.yaml.template` 是模板文件
   - 首次启动时自动复制为 `config.yaml`
   - 用户编辑 `config.yaml` 不影响模板

## 故障排除

### 打包失败

```bash
# 清理临时目录
rm -rf D:/claudeCode_wks/wellness-crm/deploy_temp
rm -rf E:/test-env/.venv

# 重新打包
python skills/package_deploy.py
```

### 测试失败

```bash
# 检查服务是否运行
curl http://localhost:8888/api/v1/ping

# 重新启动服务
E:\test-env\shutdown.bat
E:\test-env\startup.bat
```

### 依赖安装失败

```bash
# 手动安装依赖
cd E:\test-env
.venv\Scripts\pip install -r requirements.txt
```

## 版本历史

- v1.0.0 - 初始版本
  - 支持自动打包到 E:\test-env
  - 包含 startup/shutdown/install 脚本
  - 包含完整的测试套件
  - 使用系统 Edge 浏览器进行 UI 测试
