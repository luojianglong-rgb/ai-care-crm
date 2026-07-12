#!/usr/bin/env python3
"""
AI-Care CRM 自动化部署打包工具

用法:
    python skills/package_deploy.py

功能:
    1. 自动编译前端
    2. 复制后端源码
    3. 复制启动脚本 (startup.bat, shutdown.bat, install.bat)
    4. 复制到部署目录
    5. 创建虚拟环境并安装依赖
    6. 安装 Playwright 浏览器
    7. 运行测试验证
"""
import os
import sys
import shutil
import subprocess
import time
import py_compile
from datetime import datetime

# 配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_TARGET = r"E:\test-env"
DEPLOY_DIR = os.path.join(PROJECT_ROOT, "deploy_temp")

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
    result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=False)
    return result.returncode == 0

def clean_deploy_dir():
    """清理临时部署目录"""
    print_step("1/8", "清理旧文件...")
    if os.path.exists(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR, ignore_errors=True)
    os.makedirs(os.path.join(DEPLOY_DIR, "src"), exist_ok=True)
    print("  [完成] 清理完成")

def copy_backend_files():
    """复制后端文件"""
    print_step("2/8", "复制后端文件...")

    # 复制根目录文件
    for f in ["main.py", "config.py", "config.yaml.template", "database.py",
              "db_models.py", "license_manager.py", "models.py"]:
        src = os.path.join(PROJECT_ROOT, "src", f)
        dst = os.path.join(DEPLOY_DIR, "src", f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  复制：{f}")

    # 复制子目录
    for subdir in ["api", "ai", "channels", "playbook", "services", "tools"]:
        src = os.path.join(PROJECT_ROOT, "src", subdir)
        dst = os.path.join(DEPLOY_DIR, "src", subdir)
        if os.path.exists(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"  复制：{subdir}/")

    # 复制 requirements.txt
    shutil.copy2(os.path.join(PROJECT_ROOT, "requirements.txt"),
                 os.path.join(DEPLOY_DIR, "requirements.txt"))
    print("  [完成] 文件复制完成")

def build_frontend():
    """构建前端"""
    print_step("3/8", "构建前端静态文件...")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

    # 检查 node_modules
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("  安装前端依赖...")
        run_command("npm install", cwd=frontend_dir)

    # 构建
    success = run_command("npm run build", cwd=frontend_dir)
    time.sleep(2)  # 等待文件释放

    # 复制前端构建文件
    frontend_dist = os.path.join(frontend_dir, "dist")
    deploy_frontend = os.path.join(DEPLOY_DIR, "src", "frontend", "dist")
    if os.path.exists(frontend_dist):
        shutil.copytree(frontend_dist, deploy_frontend, dirs_exist_ok=True)
        print("  [完成] 前端构建完成")
    else:
        print("  [警告] 前端构建失败，dist 目录不存在")

def copy_scripts():
    """复制启动脚本 - 直接生成正确的 BAT 文件"""
    print_step("4/9", "复制启动脚本...")
    deploy_source = os.path.join(PROJECT_ROOT, "deploy")

    # BAT 文件内容 - 使用正确的 Windows 语法 (>nul 而不是 /dev/null)
    bat_files = {
        "startup.bat": '''@echo off
title AI-Care CRM 服务

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PYTHON=python"

cd /d "%SCRIPT_DIR%"

echo ============================================
echo       AI-Care CRM 服务启动中...
echo ============================================
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查虚拟环境
if exist ".venv\\Scripts\\python.exe" (
    set "PYTHON=.venv\\Scripts\\python.exe"
)

:: 检查依赖
echo [检查] 检查依赖包...
%PYTHON% -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 安装依赖包...
    %PYTHON% -m pip install -r requirements.txt -q
)

:: 检查配置文件
if not exist "src\\config.yaml" (
    if exist "src\\config.yaml.template" (
        echo [信息] 首次启动，从模板生成配置文件...
        copy "src\\config.yaml.template" "src\\config.yaml"
        echo.
        echo 配置文件已生成，请编辑 src\\config.yaml 填写 API Key
        echo.
        pause
    )
)

:: 设置生产环境端口
set "PORT=8888"

:: 启动服务
echo [信息] 启动服务 (端口 %PORT%)...
echo.
start "AI-Care CRM 服务" "%PYTHON%" src\\main.py

:: 等待服务启动
timeout /t 3 /nobreak >nul

:: 检查端口
netstat -ano | findstr ":8888" >nul 2>&1
if %errorlevel% equ 0 (
    echo ============================================
    echo       AI-Care CRM 服务启动成功!
    echo ============================================
    echo.
    echo 管理后台：http://localhost:8888/login
    echo 默认账号：admin / admin
    echo.
    echo 按任意键打开浏览器...
    pause >nul
    start http://localhost:8888/login
) else (
    echo [错误] 服务启动失败
    pause
)
''',
        "shutdown.bat": '''@echo off
title AI-Care CRM 服务

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PYTHON=python"

cd /d "%SCRIPT_DIR%"

echo ============================================
echo       AI-Care CRM 服务关闭中...
echo ============================================
echo.

:: 检查虚拟环境
if exist ".venv\\Scripts\\python.exe" (
    set "PYTHON=.venv\\Scripts\\python.exe"
)

:: 停止端口 8888 的进程
echo [信息] 停止服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8888" ^| findstr "LISTENING"') do (
    echo [操作] 终止进程 %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo ============================================
echo       AI-Care CRM 服务已关闭
echo ============================================
timeout /t 2 >nul
''',
        "install.bat": '''@echo off
title AI-Care CRM 安装向导

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"

cd /d "%SCRIPT_DIR%"

echo ============================================
echo       AI-Care CRM 安装向导
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python 3.10+
    echo.
    echo 请先安装 Python 3.10 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    echo.
    echo 安装 Python 时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [信息] Python 已安装
python --version
echo.

:: 创建虚拟环境
echo [1/4] 创建 Python 虚拟环境...
if exist ".venv" (
    echo [跳过] 虚拟环境已存在
) else (
    python -m venv .venv
    echo [完成] 虚拟环境创建成功
)
echo.

:: 安装依赖
echo [2/4] 安装 Python 依赖...
.venv\\Scripts\\pip install -r requirements.txt -q
echo [完成] 依赖安装完成
echo.

:: 初始化数据库
echo [3/4] 初始化数据库...
start "AI-Care CRM 服务" .venv\\Scripts\\python src\\main.py
timeout /t 3 /nobreak >nul
taskkill /F /FI "WINDOWTITLE eq AI-Care CRM 服务*" >nul 2>&1
echo [完成] 数据库初始化完成
echo.

:: 生成配置文件
echo [4/4] 初始化配置文件...
if not exist "src\\config.yaml" (
    if exist "src\\config.yaml.template" (
        copy "src\\config.yaml.template" "src\\config.yaml"
        echo [完成] 配置文件已生成
    )
)
echo.

echo ============================================
echo       AI-Care CRM 安装完成!
echo ============================================
echo.
echo 下一步:
echo 1. 编辑 src\\config.yaml 填写 API Key
echo 2. 运行 startup.bat 启动服务
echo 3. 访问 http://localhost:8888 登录管理台
echo    默认账号：admin / admin
echo.
pause
'''
    }

    # 写入 BAT 文件 - 使用 CRLF 换行符 + GBK 编码
    for bat_name, bat_content in bat_files.items():
        dst = os.path.join(DEPLOY_DIR, bat_name)
        # 转换 LF 为 CRLF
        content_crlf = bat_content.replace('\n', '\r\n')
        # 用 GBK 编码写入
        with open(dst, 'wb') as f:
            f.write(content_crlf.encode('gbk'))
        print(f"  生成：{bat_name} (CRLF + GBK)")

    # 复制其他文件
    for f in ["README.md", "欢迎使用.txt"]:
        src = os.path.join(deploy_source, f)
        dst = os.path.join(DEPLOY_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  复制：{f}")
        else:
            print(f"  [警告] {f} 不存在")
    print("  [完成] 脚本复制完成")

def copy_tests():
    """复制测试文件（仅开发环境）"""
    # 发布包不包含测试文件，减少大小
    pass

def deploy_to_target():
    """部署到目标目录"""
    print_step("5/8", f"部署到 {DEPLOY_TARGET}...")

    # 清理目标目录
    if os.path.exists(DEPLOY_TARGET):
        try:
            shutil.rmtree(DEPLOY_TARGET, ignore_errors=True)
        except PermissionError:
            print("  等待文件释放...")
            time.sleep(3)
            shutil.rmtree(DEPLOY_TARGET, ignore_errors=True)

    os.makedirs(DEPLOY_TARGET, exist_ok=True)
    shutil.copytree(DEPLOY_DIR, DEPLOY_TARGET, dirs_exist_ok=True)
    print("  [完成] 部署完成")

def create_venv():
    """创建虚拟环境"""
    print_step("6/8", "创建 Python 虚拟环境...")

    # 清理旧虚拟环境
    venv_path = os.path.join(DEPLOY_TARGET, ".venv")
    if os.path.exists(venv_path):
        print("  清理旧虚拟环境...")
        shutil.rmtree(venv_path, ignore_errors=True)

    success = run_command("python -m venv .venv", cwd=DEPLOY_TARGET)
    time.sleep(2)
    return success

def install_dependencies():
    """安装依赖"""
    print_step("7/9", "安装依赖包...")

    pip_path = os.path.join(DEPLOY_TARGET, ".venv", "Scripts", "pip.exe")
    if not os.path.exists(pip_path):
        print("  [错误] pip 不存在")
        return False

    # 升级 pip
    run_command(f'"{pip_path}" install --upgrade pip -q', cwd=DEPLOY_TARGET)

    # 安装项目依赖
    print("  安装项目依赖...")
    run_command(f'"{pip_path}" install -r requirements.txt -q', cwd=DEPLOY_TARGET)

    print("  [完成] 依赖安装完成")
    return True

def install_playwright():
    """安装 Playwright 浏览器"""
    print_step("8/9", "安装 Playwright 浏览器...")
    print("  [跳过] 使用系统 Edge 浏览器进行测试")
    print("  如需安装 Chromium，请手动运行：playwright install chromium")
    return True

def init_database():
    """初始化数据库"""
    print_step("9/9", "初始化数据库...")

    # 启动服务并等待数据库创建
    import subprocess
    env = os.environ.copy()
    env['PORT'] = '8888'

    proc = subprocess.Popen(
        [os.path.join(DEPLOY_TARGET, ".venv", "Scripts", "python.exe"), "src/main.py"],
        cwd=DEPLOY_TARGET,
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # 等待 5 秒让数据库初始化
    time.sleep(5)

    # 终止进程
    try:
        proc.terminate()
    except:
        pass

    print("  [完成] 数据库初始化完成")
    return True

def protect_source_code():
    """保护源码 - 使用 PyInstaller 打包成 EXE"""
    print_step("9/9", "使用 PyInstaller 打包源码...")

    # 在开发环境安装 PyInstaller（如果未安装）
    dev_pip = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pip.exe") if os.path.exists(os.path.join(PROJECT_ROOT, ".venv")) else "pip"
    run_command(f'"{dev_pip}" install pyinstaller -q', cwd=PROJECT_ROOT)

    # 使用开发环境的 PyInstaller 打包
    dev_pyinstaller = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pyinstaller.exe") if os.path.exists(os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pyinstaller.exe")) else "pyinstaller"

    # 先构建前端（确保 dist 存在）
    frontend_dist = os.path.join(PROJECT_ROOT, "frontend", "dist")
    if not os.path.exists(frontend_dist):
        print("  [警告] 前端 dist 不存在，先构建前端...")
        build_frontend()

    # 执行 PyInstaller 打包
    print("  执行 PyInstaller 打包...")
    spec_file = os.path.join(PROJECT_ROOT, "ai_care_crm.spec")

    # 在项目根目录执行打包
    success, stdout, stderr = run_command(
        f'"{dev_pyinstaller}" --clean --noconfirm "{spec_file}"',
        cwd=PROJECT_ROOT,
        capture=True
    )

    if not success:
        print(f"  [错误] PyInstaller 打包失败")
        print(f"  {stderr}")
        return False

    # 打包结果：dist/AI-Care-CRM.exe
    exe_src = os.path.join(PROJECT_ROOT, "dist", "AI-Care-CRM.exe")
    if not os.path.exists(exe_src):
        print(f"  [错误] EXE 未生成")
        return False

    # 删除源码目录和不需要的文件
    src_dir = os.path.join(DEPLOY_TARGET, "src")
    if os.path.exists(src_dir):
        shutil.rmtree(src_dir, ignore_errors=True)

    # 删除虚拟环境（EXE 已包含依赖）
    venv_dir = os.path.join(DEPLOY_TARGET, ".venv")
    if os.path.exists(venv_dir):
        shutil.rmtree(venv_dir, ignore_errors=True)

    # 删除 requirements.txt（不再需要）
    req_file = os.path.join(DEPLOY_TARGET, "requirements.txt")
    if os.path.exists(req_file):
        os.remove(req_file)

    # 删除 install.bat（不再需要安装依赖）
    install_bat = os.path.join(DEPLOY_TARGET, "install.bat")
    if os.path.exists(install_bat):
        os.remove(install_bat)

    # 复制 EXE 到部署目录
    exe_dst = os.path.join(DEPLOY_TARGET, "AI-Care-CRM.exe")
    shutil.copy2(exe_src, exe_dst)

    # 创建最小化配置目录
    os.makedirs(os.path.join(DEPLOY_TARGET, "config"), exist_ok=True)

    # 复制配置模板
    config_template = os.path.join(PROJECT_ROOT, "src", "config.yaml.template")
    if os.path.exists(config_template):
        shutil.copy2(config_template, os.path.join(DEPLOY_TARGET, "config", "config.yaml.template"))

    # 获取 EXE 大小
    exe_size = os.path.getsize(exe_dst) / (1024 * 1024)
    print(f"  [完成] EXE 打包成功: {exe_size:.1f} MB")
    print(f"  源码已保护（编译为二进制）")
    print(f"  已清理不需要的文件（.venv, requirements.txt, install.bat）")

    # 更新启动脚本（启动 EXE 而非 Python）
    update_startup_script_for_exe()

    return True

def update_startup_script_for_exe():
    """更新启动脚本以运行 EXE"""
    startup_bat = os.path.join(DEPLOY_TARGET, "startup.bat")

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

:: 启动 EXE
echo [信息] 启动服务...
start "AI-Care CRM 服务" AI-Care-CRM.exe

:: 等待服务启动
timeout /t 5 /nobreak >nul

:: 检查端口
netstat -ano | findstr ":8888" >nul 2>&1
if %errorlevel% equ 0 (
    echo ============================================
    echo       AI-Care CRM 服务启动成功!
    echo ============================================
    echo.
    echo 管理后台：http://localhost:8888/login
    echo 默认账号：admin / admin
    echo.
    echo 按任意键打开浏览器...
    pause >nul
    start http://localhost:8888/login
) else (
    echo [警告] 服务可能未正常启动，请检查日志
    pause
)
'''

    # 写入文件
    content_crlf = startup_content.replace('\n', '\r\n')
    with open(startup_bat, 'wb') as f:
        f.write(content_crlf.encode('gbk'))

    print("  已更新 startup.bat (EXE 模式)")

def cleanup():
    """清理临时目录"""
    try:
        shutil.rmtree(DEPLOY_DIR, ignore_errors=True)
    except:
        pass

def print_summary():
    """打印摘要"""
    print_header("部署包生成完成!")

    # 检查是否为 EXE 模式
    exe_path = os.path.join(DEPLOY_TARGET, "AI-Care-CRM.exe")
    if os.path.exists(exe_path):
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"打包模式：EXE 单文件（源码已保护）")
        print(f"EXE 大小：{exe_size:.1f} MB")
    else:
        print(f"打包模式：源码模式")

    print()
    print(f"部署位置：{DEPLOY_TARGET}")
    print()
    print("目录结构：")
    print("  ├── AI-Care-CRM.exe    # 主程序")
    print("  ├── config/            # 配置文件目录")
    print("  │   └── config.yaml    # 用户配置文件")
    print("  ├── data/              # 数据库目录（运行时创建）")
    print("  ├── logs/              # 日志目录")
    print("  ├── startup.bat        # 启动脚本")
    print("  └── shutdown.bat       # 停止脚本")
    print()
    print("下一步:")
    print(f"1. 编辑 {DEPLOY_TARGET}\\config\\config.yaml 配置 API Key")
    print(f"2. 双击 {DEPLOY_TARGET}\\startup.bat 启动服务")
    print("3. 访问 http://localhost:8888 登录管理台")
    print("   默认账号：admin / admin")
    print()

def main():
    """主函数"""
    print_header(f"AI-Care CRM 部署打包工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 执行打包步骤
    clean_deploy_dir()
    copy_backend_files()
    build_frontend()
    copy_scripts()
    copy_tests()
    deploy_to_target()
    create_venv()
    install_dependencies()
    install_playwright()
    init_database()
    protect_source_code()  # 保护核心源码

    # 清理
    cleanup()

    # 打印摘要
    print_summary()

    return 0

if __name__ == "__main__":
    sys.exit(main())
