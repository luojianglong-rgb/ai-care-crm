#!/bin/bash
# ============================================================
# AI-Care CRM Mac 打包脚本
# ============================================================
# 用法：
#   chmod +x build_mac.sh
#   ./build_mac.sh
# ============================================================

set -e

echo ""
echo "============================================"
echo "       AI-Care CRM Mac 打包工具"
echo "============================================"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"

# 步骤 1：检查环境
echo "[1/5] 检查打包环境..."

# Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "  Python: $PYTHON_VERSION"

# 检查 PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "  安装 PyInstaller..."
    pip3 install pyinstaller
fi
PYINSTALLER_VERSION=$(python3 -c "import PyInstaller; print(PyInstaller.__version__)")
echo "  PyInstaller: $PYINSTALLER_VERSION"

# 步骤 2：构建前端
echo "[2/5] 构建前端..."

FRONTEND_DIR="$PROJECT_ROOT/frontend"
FRONTEND_DIST="$FRONTEND_DIR/dist"

if [ -d "$FRONTEND_DIST" ]; then
    # 检查是否是最新构建（1小时内）
    DIST_MTIME=$(stat -f %m "$FRONTEND_DIST" 2>/dev/null || stat -c %Y "$FRONTEND_DIST")
    NOW=$(date +%s)
    if [ $((NOW - DIST_MTIME)) -lt 3600 ]; then
        echo "  [跳过] 前端已是最新构建"
    else
        echo "  构建前端..."
        cd "$FRONTEND_DIR"
        npm run build
    fi
else
    echo "  构建前端..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
fi

cd "$PROJECT_ROOT"

# 步骤 3：PyInstaller 打包
echo "[3/5] PyInstaller 打包..."

# 清理旧的构建
rm -rf "$PROJECT_ROOT/build"
rm -rf "$DIST_DIR/AI-Care-CRM.app"

# 执行打包
pyinstaller --clean --noconfirm ai_care_crm_mac.spec

# 检查输出
APP_PATH="$DIST_DIR/AI-Care-CRM.app"
if [ ! -d "$APP_PATH" ]; then
    echo "  [错误] App 未生成"
    exit 1
fi

APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
echo "  [完成] App 生成成功"
echo "  文件: $APP_PATH"
echo "  大小: $APP_SIZE"

# 步骤 4：创建运行时文件
echo "[4/5] 创建运行时文件..."

# 创建 config 目录
mkdir -p "$DIST_DIR/config"

# 复制配置模板
CONFIG_TEMPLATE="$PROJECT_ROOT/src/config.yaml.template"
if [ -f "$CONFIG_TEMPLATE" ]; then
    cp "$CONFIG_TEMPLATE" "$DIST_DIR/config/config.yaml.template"
    echo "  复制: config/config.yaml.template"
fi

# 复制用户手册
MANUAL_SRC="$PROJECT_ROOT/docs/用户手册.pdf"
if [ -f "$MANUAL_SRC" ]; then
    cp "$MANUAL_SRC" "$DIST_DIR/用户手册.pdf"
    echo "  复制: 用户手册.pdf"
fi

# 创建其他目录
mkdir -p "$DIST_DIR/data"
mkdir -p "$DIST_DIR/logs"

# 生成 startup.sh
cat > "$DIST_DIR/startup.sh" << 'STARTUP_EOF'
#!/bin/bash
# AI-Care CRM 启动脚本 (Mac)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "       AI-Care CRM 服务启动中..."
echo "============================================"
echo ""

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config.yaml.template" ]; then
        echo "[信息] 首次启动，从模板生成配置文件..."
        cp "config/config.yaml.template" "config/config.yaml"
        echo ""
        echo "配置文件已生成，请编辑 config/config.yaml 填写 API Key"
        echo ""
        read -p "按回车继续..."
    fi
fi

# 检查是否已运行
if lsof -i :8888 > /dev/null 2>&1; then
    echo "[警告] 服务已在运行中，端口 8888 已被占用"
    exit 1
fi

# 启动 App
echo "[信息] 启动服务..."
open "$SCRIPT_DIR/AI-Care-CRM.app"

# 等待服务启动
echo "[信息] 等待服务启动..."
sleep 5

# 检查端口
if lsof -i :8888 > /dev/null 2>&1; then
    echo ""
    echo "============================================"
    echo "       AI-Care CRM 服务启动成功!"
    echo "============================================"
    echo ""
    echo "管理后台：http://localhost:8888/login"
    echo "默认账号：admin / admin"
    echo ""
    echo "提示：关闭此窗口不影响服务运行"
    echo "      使用 shutdown.sh 停止服务"
    echo ""
    read -p "按回车打开浏览器..."
    open "http://localhost:8888/login"
else
    echo ""
    echo "[错误] 服务启动失败，请检查日志"
    echo "日志目录：$SCRIPT_DIR/logs/"
fi
STARTUP_EOF

chmod +x "$DIST_DIR/startup.sh"
echo "  生成: startup.sh"

# 生成 shutdown.sh
cat > "$DIST_DIR/shutdown.sh" << 'SHUTDOWN_EOF'
#!/bin/bash
# AI-Care CRM 关闭脚本 (Mac)

echo "============================================"
echo "       AI-Care CRM 服务关闭中..."
echo "============================================"
echo ""

# 方法1: 通过端口查找并终止进程
echo "[信息] 查找并停止服务..."
PID=$(lsof -ti :8888 2>/dev/null)
if [ -n "$PID" ]; then
    echo "[操作] 终止进程 PID=$PID"
    kill $PID 2>/dev/null
fi

# 方法2: 通过进程名终止
pkill -f "AI-Care-CRM" 2>/dev/null

# 等待进程退出
sleep 2

# 检查是否已关闭
if lsof -i :8888 > /dev/null 2>&1; then
    echo "[警告] 服务可能未完全关闭，请手动检查"
else
    echo ""
    echo "============================================"
    echo "       AI-Care CRM 服务已关闭"
    echo "============================================"
fi
SHUTDOWN_EOF

chmod +x "$DIST_DIR/shutdown.sh"
echo "  生成: shutdown.sh"

echo "  [完成] 运行时文件创建完成"

# 步骤 5：打印摘要
echo ""
echo "============================================"
echo "       打包完成!"
echo "============================================"
echo ""
echo "输出目录: $DIST_DIR"
echo ""
echo "文件结构:"
echo "  ├── AI-Care-CRM.app    # Mac 应用包"
echo "  ├── 用户手册.pdf       # 使用帮助"
echo "  ├── config/            # 配置文件"
echo "  │   └── config.yaml.template"
echo "  ├── data/              # 数据库（运行时创建）"
echo "  ├── logs/              # 日志"
echo "  ├── startup.sh         # 启动脚本"
echo "  └── shutdown.sh        # 停止脚本"
echo ""
echo "使用方法:"
echo "  1. 编辑 config/config.yaml 配置 API Key"
echo "  2. 双击 startup.sh 或 AI-Care-CRM.app 启动"
echo "  3. 访问 http://localhost:8888"
echo ""
echo "发布方式:"
echo "  - 将 dist 目录打包成 dmg 或 zip 发给用户"
echo "  - 或使用 create-dmg 工具制作 DMG 安装包"
echo ""