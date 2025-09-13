#!/usr/bin/env python3
"""
简化的发布脚本，用于手动发布到PyPI
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, check=True):
    """运行命令并返回结果"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def main():
    # 检查当前目录
    if not Path("pyproject.toml").exists():
        print("Error: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 清理旧的构建
    print("🧹 清理旧的构建文件...")
    run_command("rm -rf dist/ build/ *.egg-info/", check=False)
    
    # 构建包
    print("🔨 构建包...")
    run_command("python -m build")
    
    # 检查包
    print("✅ 检查包...")
    run_command("twine check dist/*")
    
    # 显示包信息
    print("📦 包信息:")
    run_command("ls -la dist/")
    
    print("\n🚀 发布选项:")
    print("1. 发布到TestPyPI (测试): twine upload --repository testpypi dist/*")
    print("2. 发布到PyPI (正式): twine upload dist/*")
    print("\n注意: 需要先配置API token:")
    print("- TestPyPI: https://test.pypi.org/manage/account/token/")
    print("- PyPI: https://pypi.org/manage/account/token/")
    
    # 询问是否发布
    choice = input("\n是否现在发布到TestPyPI? (y/N): ").lower().strip()
    if choice == 'y':
        print("发布到TestPyPI...")
        run_command("twine upload --repository testpypi dist/*")
        print("✅ 发布成功!")
        print("📦 包地址: https://test.pypi.org/project/leakage-buster/")
    else:
        print("跳过发布。可以稍后手动运行发布命令。")

if __name__ == "__main__":
    main()
