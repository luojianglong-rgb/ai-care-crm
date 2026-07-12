# ============================================================
# AI-Care CRM PyInstaller 打包配置
# ============================================================
# 使用方法：
#   pyinstaller --clean ai_care_crm.spec
# ============================================================

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

# 项目根目录
# 注意：PyInstaller 执行 spec 文件时 __file__ 不可用，使用 os.getcwd()
ROOT_DIR = os.getcwd()
SRC_DIR = os.path.join(ROOT_DIR, 'src')
FRONTEND_DIST = os.path.join(ROOT_DIR, 'frontend', 'dist')

print(f"PyInstaller 打包配置")
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

    # ML307A 短信猫
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
    'sqlite3.dbapi2',
]

# 数据文件
# 注意：前端静态文件打包进 EXE，配置模板放在外部供用户编辑
datas = [
    (FRONTEND_DIST, 'frontend/dist'),
] + collect_data_files('serial.tools')

# 配置文件模板不打包进 EXE，放在外部 config/ 目录供用户编辑
# 用户首次启动时会自动从模板复制

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可指定 .ico 文件
)
