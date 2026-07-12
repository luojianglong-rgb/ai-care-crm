# ============================================================
# AI-Care CRM PyInstaller 打包配置 (Mac 版)
# ============================================================
# 使用方法：
#   pyinstaller --clean ai_care_crm_mac.spec
# ============================================================

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 项目根目录
ROOT_DIR = os.getcwd()
SRC_DIR = os.path.join(ROOT_DIR, 'src')
FRONTEND_DIST = os.path.join(ROOT_DIR, 'frontend', 'dist')

print(f"PyInstaller 打包配置 (Mac)")
print(f"  项目目录：{ROOT_DIR}")
print(f"  源码目录：{SRC_DIR}")
print(f"  前端目录：{FRONTEND_DIST}")

# 收集所有需要的模块和数据
hiddenimports = [
    # Web 框架
    'fastapi',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.staticfiles',
    'fastapi.responses',
    'uvicorn',
    'uvicorn.logging',

    # 数据验证
    'pydantic',
    'pydantic.fields',

    # 数据库
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.pool',
    'sqlite3',

    # 认证与安全
    'jose',
    'jose.backends',
    'passlib',
    'passlib.context',
    'passlib.handlers',
    'passlib.handlers.bcrypt',
    'bcrypt',
    'cryptography',

    # 配置
    'yaml',
    'pyyaml',

    # AI 大模型
    'openai',
    'openai.types',
    'openai.types.chat',

    # 定时任务
    'apscheduler',
    'apscheduler.schedulers',
    'apscheduler.schedulers.background',
    'apscheduler.triggers',
    'apscheduler.triggers.cron',

    # Excel 导出
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',

    # ML307A 短信猫（Mac 使用 USB-Serial）
    'serial',
    'serial.tools',
    'serial.tools.list_ports',

    # 其他依赖
    'email',
    'email.mime',
    'email.mime.text',
    'html',
    'http',
    'http.cookies',
    'json',
    'logging',
    'logging.handlers',
    'multiprocessing',
    'multiprocessing.spawn',
    'sqlite3.dbapi2',
]

# 数据文件
datas = [
    (FRONTEND_DIST, 'frontend/dist'),
] + collect_data_files('serial.tools')

# 收集所有子模块
for mod in ['fastapi', 'sqlalchemy', 'pydantic', 'uvicorn']:
    try:
        hiddenimports.extend(collect_submodules(mod))
    except Exception:
        pass

a = Analysis(
    [os.path.join(SRC_DIR, 'main.py')],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
        'test',
        'tests',
        'pytest',
        'nose',
        # Windows 专用模块（Mac 不需要）
        'pywinauto',
        'uiautomation',
        'comtypes',
        'win32api',
        'win32con',
        'pywin32',
        'win32',
        'windows',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI-Care-CRM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Mac 不支持 UPX
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',  # 支持 Intel + Apple Silicon
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可指定 .icns 文件路径
)

# Mac app bundle - 使用 BUNDLE 创建 .app
app = BUNDLE(
    exe,
    name='AI-Care-CRM.app',
    icon=None,
    bundle_identifier='com.ai-care.crm',
    version='1.0.0',
    info_plist={
        'CFBundleDisplayName': 'AI-Care CRM',
        'CFBundleName': 'AI-Care CRM',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15.0',
    },
)