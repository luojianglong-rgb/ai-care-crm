#!/usr/bin/env python3
"""
AI-Care CRM EXE 打包工具

用法:
    python skills/build_exe.py

功能:
    1. 编译前端
    2. 使用 PyInstaller 打包成单一 EXE
    3. 复制配置模板
    4. 生成启动/停止脚本
    5. 输出到 dist/ 目录

输出:
    dist/AI-Care-CRM.exe  (约30MB)
"""
import os
import sys
import shutil
import subprocess
import time
from datetime import datetime

# 配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
SPEC_FILE = os.path.join(PROJECT_ROOT, "ai_care_crm.spec")


def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)
    print()


def print_step(step, text):
    print(f"[{step}] {text}")


def run_command(cmd, cwd=None, capture=False):
    """运行命令"""
    print(f"  执行：{cmd}")
    if capture:
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    return result.returncode == 0


def check_requirements():
    """检查打包环境"""
    print_step("1/5", "检查打包环境...")

    # 检查 Python
    python_version = sys.version_info
    print(f"  Python: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # 检查 PyInstaller
    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

    # 检查 spec 文件
    if not os.path.exists(SPEC_FILE):
        print(f"  [错误] spec 文件不存在: {SPEC_FILE}")
        return False

    print("  [完成] 环境检查通过")
    return True


def build_frontend():
    """构建前端"""
    print_step("2/5", "构建前端...")

    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    frontend_dist = os.path.join(frontend_dir, "dist")

    # 检查是否需要构建
    if os.path.exists(frontend_dist):
        # 检查是否是最新构建（1小时内）
        dist_mtime = os.path.getmtime(frontend_dist)
        if time.time() - dist_mtime < 3600:
            print("  [跳过] 前端已是最新构建")
            return True

    # 检查 node_modules
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("  安装前端依赖...")
        run_command("npm install", cwd=frontend_dir)

    # 构建
    success = run_command("npm run build", cwd=frontend_dir)
    if success:
        print("  [完成] 前端构建成功")
    else:
        print("  [警告] 前端构建可能失败")

    return True


def build_exe():
    """使用 PyInstaller 打包"""
    print_step("3/5", "PyInstaller 打包...")

    # 获取 PyInstaller 路径
    venv_pyinstaller = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pyinstaller.exe")
    if os.path.exists(venv_pyinstaller):
        pyinstaller = venv_pyinstaller
    else:
        pyinstaller = "pyinstaller"

    print(f"  PyInstaller: {pyinstaller}")
    print(f"  Spec 文件: {SPEC_FILE}")

    # 清理旧的构建
    build_dir = os.path.join(PROJECT_ROOT, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    if os.path.exists(DIST_DIR):
        # 只删除 EXE，保留其他发布文件
        exe_file = os.path.join(DIST_DIR, "AI-Care-CRM.exe")
        if os.path.exists(exe_file):
            os.remove(exe_file)

    # 执行打包
    start_time = time.time()
    success, stdout, stderr = run_command(
        f'"{pyinstaller}" --clean --noconfirm "{SPEC_FILE}"',
        cwd=PROJECT_ROOT,
        capture=True
    )
    elapsed = time.time() - start_time

    if not success:
        print(f"  [错误] 打包失败")
        print(stderr)
        return None

    # 检查输出
    exe_path = os.path.join(DIST_DIR, "AI-Care-CRM.exe")
    if not os.path.exists(exe_path):
        print("  [错误] EXE 未生成")
        return None

    exe_size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"  [完成] EXE 生成成功")
    print(f"  文件: {exe_path}")
    print(f"  大小: {exe_size:.1f} MB")
    print(f"  耗时: {elapsed:.1f} 秒")

    return exe_path


def create_runtime_files():
    """创建运行时文件"""
    print_step("4/5", "创建运行时文件...")

    # 创建 config 目录
    config_dir = os.path.join(DIST_DIR, "config")
    os.makedirs(config_dir, exist_ok=True)

    # 复制配置模板
    config_template = os.path.join(PROJECT_ROOT, "src", "config.yaml.template")
    if os.path.exists(config_template):
        shutil.copy2(config_template, os.path.join(config_dir, "config.yaml.template"))
        print("  复制: config/config.yaml.template")

    # 复制用户手册
    manual_src = os.path.join(PROJECT_ROOT, "docs", "用户手册.html")
    if os.path.exists(manual_src):
        shutil.copy2(manual_src, os.path.join(DIST_DIR, "用户手册.html"))
        print("  复制: 用户手册.html")

    # 创建其他目录
    for dirname in ["data", "logs"]:
        os.makedirs(os.path.join(DIST_DIR, dirname), exist_ok=True)

    # 生成 startup.bat
    startup_bat = os.path.join(DIST_DIR, "startup.bat")
    startup_content = '''@echo off
title AI-Care CRM 服务

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ============================================
echo       AI-Care CRM 服务启动中...
echo ============================================
echo.

:: 检查配置文件
if not exist "config\\config.yaml" (
    if exist "config\\config.yaml.template" (
        echo [信息] 首次启动，从模板生成配置文件...
        copy "config\\config.yaml.template" "config\\config.yaml"
        echo.
        echo 配置文件已生成，请编辑 config\\config.yaml 填写 API Key
        echo.
        pause
    )
)

:: 检查是否已运行
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [警告] 服务已在运行中，端口 8888 已被占用
    echo.
    pause
    exit /b 1
)

:: 启动 EXE（后台运行）
echo [信息] 启动服务...
start "AI-Care-CRM" AI-Care-CRM.exe

:: 等待服务启动
echo [信息] 等待服务启动...
timeout /t 5 /nobreak >nul

:: 检查端口
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo       AI-Care CRM 服务启动成功!
    echo ============================================
    echo.
    echo 管理后台：http://localhost:8888/login
    echo 默认账号：admin / admin
    echo.
    echo 提示：关闭此窗口不影响服务运行
    echo       使用 shutdown.bat 停止服务
    echo.
    echo 按任意键打开浏览器...
    pause >nul
    start http://localhost:8888/login
) else (
    echo.
    echo [错误] 服务启动失败，请检查日志
    echo 日志目录：%SCRIPT_DIR%logs\\
    echo.
    pause
)
'''
    with open(startup_bat, 'wb') as f:
        f.write(startup_content.replace('\n', '\r\n').encode('gbk'))
    print("  生成: startup.bat")

    # 生成 shutdown.bat
    shutdown_bat = os.path.join(DIST_DIR, "shutdown.bat")
    shutdown_content = '''@echo off
title AI-Care CRM 服务

echo ============================================
echo       AI-Care CRM 服务关闭中...
echo ============================================
echo.

:: 方法1: 通过端口查找并终止进程
echo [信息] 查找并停止服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8888" ^| findstr "LISTENING" 2^>nul') do (
    echo [操作] 终止进程 PID=%%a
    taskkill /PID %%a /F >nul 2>&1
)

:: 方法2: 通过进程名终止
taskkill /IM "AI-Care-CRM.exe" /F >nul 2>&1

:: 等待进程退出
timeout /t 2 /nobreak >nul

:: 检查是否已关闭
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [警告] 服务可能未完全关闭，请手动检查
) else (
    echo.
    echo ============================================
    echo       AI-Care CRM 服务已关闭
    echo ============================================
)

timeout /t 2 >nul
'''
    with open(shutdown_bat, 'wb') as f:
        f.write(shutdown_content.replace('\n', '\r\n').encode('gbk'))
    print("  生成: shutdown.bat")

    print("  [完成] 运行时文件创建完成")


def print_summary():
    """打印摘要"""
    exe_path = os.path.join(DIST_DIR, "AI-Care-CRM.exe")

    print_header("打包完成!")

    if os.path.exists(exe_path):
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"输出目录: {DIST_DIR}")
        print(f"EXE 大小: {exe_size:.1f} MB")
        print()
        print("文件结构:")
        print("  ├── AI-Care-CRM.exe     # 主程序")
        print("  ├── 用户手册.html       # 使用帮助（PPT格式）")
        print("  ├── config/             # 配置文件")
        print("  │   └── config.yaml.template")
        print("  ├── data/               # 数据库（运行时创建）")
        print("  ├── logs/               # 日志")
        print("  ├── startup.bat         # 启动脚本")
        print("  └── shutdown.bat        # 停止脚本")
        print()
        print("使用方法:")
        print("  1. 编辑 config/config.yaml 配置 API Key")
        print("  2. 双击 startup.bat 启动服务")
        print("  3. 访问 http://localhost:8888")
        print()
        print("发布方式:")
        print("  - 将整个 dist 目录打包成 zip 发给用户")
        print("  - 或使用 Inno Setup 制作安装包")
        print()


def main():
    """主函数"""
    print_header(f"AI-Care CRM EXE 打包工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查环境
    if not check_requirements():
        return 1

    # 构建前端
    build_frontend()

    # 打包 EXE
    exe_path = build_exe()
    if not exe_path:
        return 1

    # 创建运行时文件
    create_runtime_files()

    # 打印摘要
    print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())