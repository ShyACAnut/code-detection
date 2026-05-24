#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动安装 reportlab 库的脚本
"""

import sys
import subprocess
import os

def print_banner(text):
    """打印横幅"""
    print("=" * 50)
    print(text)
    print("=" * 50)

def main():
    print_banner("安装 reportlab 库")

    # 显示当前Python信息
    print("\n[1/4] 当前Python环境:")
    print(f"  Python路径: {sys.executable}")
    print(f"  Python版本: {sys.version}")
    print(f"  当前目录: {os.getcwd()}")

    # 检查是否已安装
    print("\n[2/4] 检查 reportlab 是否已安装...")
    try:
        import reportlab
        print(f"  ✓ reportlab 已安装，版本: {reportlab.Version}")
        return 0
    except ImportError:
        print("  reportlab 未安装，开始安装...")

    # 尝试安装
    print("\n[3/4] 正在安装 reportlab...")
    print(f"  使用 pip: {sys.executable} -m pip install reportlab")
    print()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "reportlab"],
            check=True,
            capture_output=False
        )

        print("\n  ✓ pip install 完成")

    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ 安装失败，尝试使用 --user 选项...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "reportlab", "--user"],
                check=True,
                capture_output=False
            )
            print("\n  ✓ pip install --user 完成")
        except subprocess.CalledProcessError as e2:
            print("\n  ✗ 安装仍然失败！")
            print(f"  请手动执行: {sys.executable} -m pip install reportlab")
            return 1

    # 验证安装
    print("\n[4/4] 验证安装...")
    try:
        import reportlab
        print(f"  ✓ reportlab 安装成功！版本: {reportlab.Version}")
    except ImportError:
        print("  ✗ 安装验证失败！")
        return 1

    # 运行测试
    print("\n" + "=" * 50)
    print("运行 PDF 功能测试...")
    print("=" * 50)
    print()

    try:
        test_script = os.path.join(os.path.dirname(__file__), "test_pdf_generation.py")
        if os.path.exists(test_script):
            result = subprocess.run(
                [sys.executable, test_script],
                check=False,
                capture_output=False
            )
        else:
            print("  测试脚本不存在，跳过测试")
    except Exception as e:
        print(f"  测试运行失败: {e}")

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print("\n如果成功，请重启你的后端服务")
    return 0

if __name__ == "__main__":
    sys.exit(main())
