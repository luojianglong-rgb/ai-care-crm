@echo off
chcp 65001 >nul
title AI-Care CRM 一键打包工具

echo ============================================
echo       AI-Care CRM 一键打包工具
echo ============================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行：python -m venv .venv
    pause
    exit /b 1
)

:: 检查前端目录
if not exist "frontend\dist\index.html" (
    echo [信息] 前端未编译，开始编译...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

:: PyInstaller 打包
echo.
echo [信息] 开始 PyInstaller 打包...
.venv\Scripts\pyinstaller --clean --noconfirm ai_care_crm.spec

if %errorlevel% neq 0 (
    echo.
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

:: 检查打包结果
if not exist "dist\AI-Care-CRM.exe" (
    echo.
    echo [错误] 未找到打包后的 EXE 文件
    pause
    exit /b 1
)

echo.
echo ============================================
echo          PyInstaller 打包完成!
echo ============================================
echo.
echo 生成文件：dist\AI-Care-CRM.exe
echo.
echo 下一步:
echo 1. 测试打包后的 EXE 是否正常运行
echo 2. 使用 Inno Setup 创建安装包 (可选)
echo.
pause
