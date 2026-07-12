#!/usr/bin/env python3
"""
AI-Care CRM 部署和测试脚本 - 简化版
"""
import os
import sys
import shutil
import subprocess
import time

DEPLOY_TARGET = r"E:\test-env"
PROJECT_ROOT = r"D:\claudeCode_wks\wellness-crm"
DEPLOY_DIR = os.path.join(PROJECT_ROOT, "deploy_temp")

def run_command(cmd, cwd=None):
    """运行命令"""
    print(f"执行：{cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=False)
    return result.returncode == 0

def main():
    print("=" * 50)
    print("       AI-Care CRM 部署包生成工具")
    print("=" * 50)
    print()

    # 1. 清理临时部署目录
    print("[1/7] 清理旧文件...")
    if os.path.exists(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR, ignore_errors=True)
    os.makedirs(os.path.join(DEPLOY_DIR, "src"), exist_ok=True)
    print("[完成] 清理完成")

    # 2. 复制后端文件
    print()
    print("[2/7] 复制后端文件...")

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
    print("[完成] 文件复制完成")

    # 3. 构建前端
    print()
    print("[3/7] 构建前端静态文件...")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    run_command("npm run build", cwd=frontend_dir)
    time.sleep(2)  # 等待文件释放

    # 复制前端构建文件
    frontend_dist = os.path.join(frontend_dir, "dist")
    deploy_frontend = os.path.join(DEPLOY_DIR, "src", "frontend", "dist")
    if os.path.exists(frontend_dist):
        shutil.copytree(frontend_dist, deploy_frontend, dirs_exist_ok=True)
        print("[完成] 前端构建完成")
    else:
        print("[警告] 前端构建失败，dist 目录不存在")

    # 4. 复制启动脚本
    print()
    print("[4/7] 复制启动脚本...")
    for f in ["startup.bat", "shutdown.bat", "install.bat", "README.md"]:
        src = os.path.join(DEPLOY_DIR, f)
        dst = os.path.join(DEPLOY_TARGET, f)
        # 先从 deploy 目录复制
        deploy_src = os.path.join(PROJECT_ROOT, "deploy", f)
        if os.path.exists(deploy_src):
            shutil.copy2(deploy_src, dst)
            print(f"  复制：{f}")
    print("[完成] 脚本复制完成")

    # 5. 部署到测试环境
    print()
    print(f"[5/7] 部署到测试环境 {DEPLOY_TARGET}...")
    if os.path.exists(DEPLOY_TARGET):
        try:
            shutil.rmtree(DEPLOY_TARGET, ignore_errors=True)
        except:
            time.sleep(2)
            shutil.rmtree(DEPLOY_TARGET, ignore_errors=True)
    os.makedirs(DEPLOY_TARGET, exist_ok=True)
    shutil.copytree(DEPLOY_DIR, DEPLOY_TARGET, dirs_exist_ok=True)
    print("[完成] 部署完成")

    # 6. 安装依赖
    print()
    print(f"[6/7] 安装测试环境依赖...")

    # 创建虚拟环境
    run_command("python -m venv .venv", cwd=DEPLOY_TARGET)
    time.sleep(2)

    # 安装依赖
    pip_path = os.path.join(DEPLOY_TARGET, ".venv", "Scripts", "pip.exe")
    if os.path.exists(pip_path):
        run_command(f'"{pip_path}" install -r requirements.txt -q', cwd=DEPLOY_TARGET)
        print("  安装 Python 依赖...")
        # 安装 pytest 和 playwright
        run_command(f'"{pip_path}" install pytest pytest-html pytest-playwright -q', cwd=DEPLOY_TARGET)
        print("  安装测试框架...")
    print("[完成] 依赖安装完成")

    # 7. 安装 Playwright 浏览器
    print()
    print(f"[7/7] 安装 Playwright 浏览器...")
    playwright_path = os.path.join(DEPLOY_TARGET, ".venv", "Scripts", "playwright.exe")
    if os.path.exists(playwright_path):
        run_command(f'"{playwright_path}" install chromium', cwd=DEPLOY_TARGET)
    print("[完成] 浏览器安装完成")

    # 清理临时目录
    try:
        shutil.rmtree(DEPLOY_DIR, ignore_errors=True)
    except:
        pass

    print()
    print("=" * 50)
    print("       部署包生成并安装完成!")
    print("=" * 50)
    print()
    print(f"部署位置：{DEPLOY_TARGET}")
    print()
    print("下一步:")
    print(f"1. 编辑 {DEPLOY_TARGET}\\src\\config.yaml 配置 API Key")
    print(f"2. 运行 {DEPLOY_TARGET}\\startup.bat 启动服务")
    print("3. 访问 http://localhost:8888 登录管理台")
    print()

if __name__ == "__main__":
    main()
