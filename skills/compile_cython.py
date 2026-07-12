#!/usr/bin/env python3
"""
使用 Cython 编译 Python 源码为 .pyd 文件

用法:
    python compile_cython.py [source_dir] [build_dir]

示例:
    python compile_cython.py src/ compiled/
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# 需要编译的目录（核心业务代码）
COMPILE_DIRS = ["api", "ai", "channels", "playbook", "services", "tools"]

# 保留源码的文件（配置文件、入口文件等）
KEEP_SOURCE_FILES = [
    "main.py",        # 入口文件
    "config.py",      # 需要用户查看配置
    "database.py",    # 数据库配置
    "db_models.py",   # 数据模型（可能需要查看）
    "models.py",      # Pydantic 模型
    "license_manager.py",  # 授权管理（保留源码方便调试）
]

def should_compile_file(file_path: str) -> bool:
    """判断文件是否应该编译"""
    # 排除 __init__.py 和 __pycache__
    if "__pycache__" in file_path:
        return False
    if file_path.endswith("__init__.py"):
        return True  # 编译 __init__.py
    return file_path.endswith(".py")

def compile_directory(source_dir, build_dir):
    """编译目录"""
    print(f"\n开始编译：{source_dir} -> {build_dir}")

    # 创建 build 目录
    os.makedirs(build_dir, exist_ok=True)

    # 复制不需要编译的文件
    for filename in KEEP_SOURCE_FILES:
        src = os.path.join(source_dir, filename)
        if os.path.exists(src):
            shutil.copy2(src, build_dir)
            print(f"  保留源码：{filename}")

    # 编译子目录
    for subdir in COMPILE_DIRS:
        src_subdir = os.path.join(source_dir, subdir)
        if not os.path.exists(src_subdir):
            print(f"  跳过：{subdir} (不存在)")
            continue

        dst_subdir = os.path.join(build_dir, subdir)
        os.makedirs(dst_subdir, exist_ok=True)

        # 复制该目录下所有 .py 文件到临时目录准备编译
        py_files = []
        for root, dirs, files in os.walk(src_subdir):
            # 过滤 __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, src_subdir)
                    dst_file = os.path.join(dst_subdir, rel_path)
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    py_files.append(dst_file)

        if not py_files:
            continue

        # 使用 Cython 编译
        print(f"  编译：{subdir}/ ({len(py_files)} 个文件)")

        # 生成 setup.py
        setup_content = f'''
from setuptools import setup
from Cython.Build import cythonize
import os

os.environ['Cython'] = '3.0.0'

# 获取所有 .py 文件
py_files = []
for root, dirs, files in os.walk("build_src"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            py_files.append(os.path.join(root, f))

setup(
    ext_modules=cythonize(
        py_files,
        compiler_directives={{
            'language_level': '3',
            'embedsignature': True,
            'binding': False,
        }}
    )
)
'''

        # 创建临时编译目录
        temp_src = os.path.join(build_dir, "build_src", subdir)
        os.makedirs(temp_src, exist_ok=True)

        # 复制文件到临时目录
        for root, dirs, files in os.walk(src_subdir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, src_subdir)
                    dst_file = os.path.join(temp_src, rel_path)
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

        # 写入 setup.py
        setup_py = os.path.join(build_dir, "setup_temp.py")
        with open(setup_py, "w", encoding="utf-8") as f:
            f.write(setup_content)

        # 执行编译
        try:
            # 先安装 Cython
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "Cython", "-q"],
                check=True,
                capture_output=True
            )

            # 编译
            result = subprocess.run(
                [sys.executable, setup_py, "build_ext", "--inplace"],
                cwd=build_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # 查找生成的 .pyd 文件
                pyd_count = 0
                for root, dirs, files in os.walk(build_dir):
                    for file in files:
                        if file.endswith(".pyd"):
                            pyd_count += 1

                print(f"    成功：生成 {pyd_count} 个 .pyd 文件")

                # 清理临时文件
                for py_file in py_files:
                    if os.path.exists(py_file):
                        os.remove(py_file)
            else:
                print(f"    编译失败：{result.stderr[:200]}")

        except Exception as e:
            print(f"    错误：{e}")

        # 清理 setup.py 和临时目录
        if os.path.exists(setup_py):
            os.remove(setup_py)
        temp_build = os.path.join(build_dir, "build")
        if os.path.exists(temp_build):
            shutil.rmtree(temp_build, ignore_errors=True)
        if os.path.exists(os.path.join(build_dir, "build_src")):
            shutil.rmtree(os.path.join(build_dir, "build_src"), ignore_errors=True)

    print(f"编译完成：{build_dir}")

def main():
    if len(sys.argv) < 3:
        print("用法：python compile_cython.py <source_dir> <build_dir>")
        print("示例：python compile_cython.py src/ compiled/")
        sys.exit(1)

    source_dir = sys.argv[1]
    build_dir = sys.argv[2]

    if not os.path.exists(source_dir):
        print(f"错误：源目录不存在：{source_dir}")
        sys.exit(1)

    compile_directory(source_dir, build_dir)
    print("\n✅ Cython 编译完成！")

if __name__ == "__main__":
    main()
