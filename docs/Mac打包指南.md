# AI-Care CRM Mac 打包指南

## 概述

本文档说明如何在 Mac 上打包 AI-Care CRM 为可分发的应用包。

---

## 环境要求

### 系统要求
- macOS 10.15 (Catalina) 或更高版本
- 支持 Intel 和 Apple Silicon (M1/M2/M3)

### 软件要求
- Python 3.10+ (推荐 3.12)
- Node.js 18+ (用于前端构建)
- PyInstaller 6.0+

---

## 快速开始

### 步骤 1：克隆项目到 Mac
```bash
# 将项目复制到 Mac
# 可以通过 USB、网络共享或云盘传输
```

### 步骤 2：安装依赖
```bash
cd wellness-crm

# 安装 Python 依赖（使用 Mac 专用文件，排除 Windows 模块）
pip3 install -r requirements_mac.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 步骤 3：执行打包
```bash
# 添加执行权限
chmod +x build_mac.sh

# 执行打包
./build_mac.sh
```

### 步骤 4：查看输出
打包完成后，输出目录 `dist/` 包含：
```
dist/
├── AI-Care-CRM.app    # Mac 应用包
├── 用户手册.pdf       # 使用帮助
├── config/            # 配置文件
│   └── config.yaml.template
├── data/              # 数据库（运行时创建）
├── logs/              # 日志
├── startup.sh         # 启动脚本
└── shutdown.sh        # 停止脚本
```

---

## 手动打包步骤

如果自动脚本失败，可手动执行：

### 1. 构建前端
```bash
cd frontend
npm run build
cd ..
```

### 2. PyInstaller 打包
```bash
pyinstaller --clean --noconfirm ai_care_crm_mac.spec
```

### 3. 创建配置目录
```bash
mkdir -p dist/config
cp src/config.yaml.template dist/config/
mkdir -p dist/data dist/logs
```

### 4. 复制文档
```bash
cp docs/用户手册.pdf dist/
```

---

## Mac 与 Windows 差异

### 功能差异
| 功能 | Windows | Mac |
|------|---------|-----|
| 微信 RPA | ✅ 支持 | ❌ 不支持 (Windows 专用) |
| ML307A 短信猫 | ✅ 支持 | ✅ 支持 (需 USB-Serial 驱动) |
| AI 分析 | ✅ | ✅ |
| 客户管理 | ✅ | ✅ |
| 预约管理 | ✅ | ✅ |

### 端口差异
- Mac 上串口设备路径为 `/dev/tty.usbserial-*` 或 `/dev/cu.usbserial-*`
- Windows 上为 `COM3` 等

### 配置文件适配
编辑 `config.yaml`，短信猫端口配置：
```yaml
channels:
  ml307a:
    enabled: true
    port: ''           # 留空自动扫描 /dev/tty.usbserial-* 或 /dev/cu.usbserial-*
    carrier: auto
```

---

## 分发方式

### 方式 1：ZIP 压缩包
```bash
cd dist
zip -r AI-Care-CRM-Mac.zip AI-Care-CRM.app config data logs startup.sh shutdown.sh 用户手册.pdf
```

### 方式 2：DMG 安装包（推荐）
```bash
# 安装 create-dmg
brew install create-dmg

# 创建 DMG
create-dmg \
  --volname "AI-Care CRM" \
  --volicon "assets/app.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "AI-Care-CRM.app" 200 190 \
  --hide-extension "AI-Care-CRM.app" \
  --app-drop-link 600 185 \
  "AI-Care-CRM-Mac.dmg" \
  "dist/"
```

---

## 代码签名（可选）

### 签名应用
```bash
# 获取签名身份
codesign --display-signature-requirements AI-Care-CRM.app

# 签名
codesign --deep --force --verify --sign "Developer ID Application: Your Name" AI-Care-CRM.app
```

### 公证（Gatekeeper）
```bash
# 创建 ZIP 用于公证
ditto -c -k --keepParent AI-Care-CRM.app app.zip

# 上传公证
xcrun notarytool submit app.zip --apple-id "your@email.com" --team-id "TEAMID" --password "app-specific-password"

# 检查状态
xcrun notarytool history --apple-id "your@email.com" --team-id "TEAMID" --password "app-specific-password"

# 公证成功后附加票据
xcrun stapler staple AI-Care-CRM.app
```

---

## 常见问题

### Q1: 打包失败，提示找不到模块
**解决**：确保使用 `requirements_mac.txt` 安装依赖，不要使用 `requirements.txt`（包含 Windows 专用模块）。

### Q2: App 运行时闪退
**解决**：
1. 检查日志 `logs/app.log`
2. 确认 `config.yaml` 已正确配置
3. 检查端口 8888 是否被占用：`lsof -i :8888`

### Q3: 短信猫无法识别
**解决**：
1. 检查设备管理器是否显示串口设备
2. Mac 上需安装 CH340 驱动（USB-Serial）
```bash
brew install --cask usbserial-ch340
```

### Q4: Apple Silicon 运行慢
**解决**：spec 文件已配置 `target_arch='universal2'`，同时支持 Intel 和 Apple Silicon。

---

## 测试验证

打包完成后，在干净的 Mac 上测试：

1. 解压/安装应用
2. 编辑 `config/config.yaml` 配置 API Key
3. 运行 `startup.sh` 或双击 `AI-Care-CRM.app`
4. 访问 http://localhost:8888
5. 登录测试（admin / admin）
6. 测试客户管理、AI 分析等功能

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `ai_care_crm_mac.spec` | PyInstaller Mac 打包配置 |
| `build_mac.sh` | Mac 自动打包脚本 |
| `requirements_mac.txt` | Mac 专用依赖清单 |

---

## 与 Windows 打包对比

| 项目 | Windows | Mac |
|------|---------|-----|
| 打包格式 | EXE | App Bundle |
| 安装包 | Inno Setup (.exe) | DMG |
| 静态文件 | 打包进 EXE | 打包进 App |
| 配置目录 | EXE 同级 config/ | App 同级 config/ |
| 启动脚本 | startup.bat | startup.sh |
| 控制台 | 可隐藏 | 无控制台窗口 |