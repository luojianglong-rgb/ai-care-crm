#!/usr/bin/env python3
"""
AI-Care CRM 源码保护脚本
- 将核心代码编译为 .pyc 字节码
- 删除 .py 源码文件
- 保留配置文件

用法:
    python skills/protect_source.py <source_dir>
"""
import os
import sys
import py_compile
import shutil

# 保留源码的文件（配置相关、需要用户查看的）
KEEP_SOURCE_FILES = {
    "main.py",           # 入口文件（需要修改端口等）
    "config.py",         # 配置加载器
    "database.py",       # 数据库配置
}

# 需要保留 .py 的文件（用户可能需要修改配置）
CONFIG_FILES = {
    "config.yaml",
    "config.yaml.template",
}

def protect_directory(directory):
    """保护目录中的 Python 文件"""
    print(f"\n开始保护：{directory}")

    protected_count = 0
    removed_count = 0

    for root, dirs, files in os.walk(directory):
        # 跳过 __pycache__
        if "__pycache__" in root:
            continue

        # 移除子目录中的 __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            file_path = os.path.join(root, file)

            # 只处理 .py 文件
            if not file.endswith(".py"):
                continue

            # 检查是否应该保留源码
            if file in KEEP_SOURCE_FILES:
                print(f"  保留源码：{file}")
                continue

            try:
                # 1. 编译为 .pyc
                py_compile.compile(file_path, doraise=True)

                # 2. 删除 .py 文件
                os.remove(file_path)

                protected_count += 1
                removed_count += 1

                print(f"  已保护：{file} → .pyc")

            except py_compile.PyCompileError as e:
                print(f"  编译失败：{file} - {e}")
            except Exception as e:
                print(f"  错误：{file} - {e}")

    # 清理 __pycache__ 目录（可选，保留可以让加载更快）
    # for root, dirs, files in os.walk(directory):
    #     if "__pycache__" in dirs:
    #         pycache_path = os.path.join(root, "__pycache__")
    #         shutil.rmtree(pycache_path, ignore_errors=True)
    #         print(f"  清理：__pycache__/")

    print(f"\n保护完成:")
    print(f"  - 编译并删除：{protected_count} 个文件")
    print(f"  - 保留源码：{len(KEEP_SOURCE_FILES)} 个文件")

def main():
    if len(sys.argv) < 2:
        print("用法：python protect_source.py <source_dir>")
        print("示例：python protect_source.py E:/test-env/src")
        sys.exit(1)

    source_dir = sys.argv[1]

    if not os.path.exists(source_dir):
        print(f"错误：目录不存在：{source_dir}")
        sys.exit(1)

    confirm = input(f"确认要保护 {source_dir} 中的源码吗？\n此操作将删除大部分 .py 文件（可恢复）\n输入 y 确认：")
    if confirm.lower() != 'y':
        print("已取消")
        sys.exit(0)

    protect_directory(source_dir)
    print("\n✅ 源码保护完成！\n\n注意:")
    print("- 已被保护的代码仍然可以正常运行")
    print("- .pyc 文件在 __pycache__ 目录中")
    print("- 如需恢复，重新复制源码即可")

if __name__ == "__main__":
    main()
