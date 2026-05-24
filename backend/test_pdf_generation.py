"""
PDF生成功能测试脚本
==================

用于测试修复后的PDF报告生成功能是否正常工作。

使用方法：
1. 确保已安装 reportlab: pip install reportlab
2. 运行脚本: python test_pdf_generation.py
3. 查看生成的PDF文件

作者：AI Assistant
日期：2025
"""

import os
import sys

def test_pdf_generator():
    """测试PDF生成器功能"""
    print("=" * 60)
    print("PDF报告生成功能测试")
    print("=" * 60)
    print()

    # 1. 测试reportlab是否可用
    print("步骤1: 检查reportlab库...")
    try:
        import reportlab
        print(f"✓ reportlab库已安装 (版本: {reportlab.Version})")
    except ImportError:
        print("✗ reportlab库未安装")
        print()
        print("请执行以下命令安装:")
        print("  pip install reportlab")
        print()
        return False

    # 2. 测试pdf_generator模块
    print()
    print("步骤2: 测试pdf_generator模块...")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    try:
        # 重新加载模块以确保使用最新代码
        if 'pdf_generator' in sys.modules:
            del sys.modules['pdf_generator']

        from pdf_generator import markdown_to_pdf, check_pdf_capability

        capability = check_pdf_capability()
        print(f"PDF生成能力检查结果:")
        print(f"  - reportlab可用: {capability['reportlab_available']}")
        print(f"  - 中文字体可用: {capability['chinese_font_available']}")
        print(f"  - 字体名称: {capability['font_name']}")
        print(f"  - 可以生成PDF: {capability['can_generate_pdf']}")

        if not capability['can_generate_pdf']:
            print()
            print("✗ PDF生成能力不足")
            return False

    except ImportError as e:
        print(f"✗ 导入pdf_generator模块失败: {e}")
        print("请确保 pdf_generator.py 文件存在于当前目录")
        return False

    # 3. 生成测试PDF
    print()
    print("步骤3: 生成测试PDF文件...")

    test_markdown = """# 代码相似性检测报告

## 基本信息

- 作业标题：测试作业 - 排序算法
- 编程语言：Python
- 生成时间：2025-01-15 10:30:00

## 检测统计摘要

- 总比对数：15
- 平均相似度：45.23%
- 最高相似度：92%
- 高风险阈值：80%
- 高风险对数量：3

## 高风险对详情

| 提交A | 提交B | 相似度 | 分析源 | 原因(摘要) |
|-------|-------|--------|--------|-----------|
| 1     | 5     | 92     | LLM    | 代码结构完全相同 |
| 3     | 7     | 88     | LLM    | 算法实现高度相似 |
| 2     | 9     | 85     | 哈希   | 代码完全一致 |

## 建议

1. 对高相似度提交进行人工复核
2. 联系相关学生了解情况
3. 记录检测结果作为参考

---

本报告由代码相似性检测系统自动生成
"""

    output_dir = os.path.join(backend_dir, "test_output")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "test_report.pdf")

    try:
        success = markdown_to_pdf(test_markdown, output_path, title="测试报告")

        if success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ 测试PDF生成成功!")
            print(f"  文件路径: {output_path}")
            print(f"  文件大小: {file_size / 1024:.2f} KB")
            return True
        else:
            print("✗ 测试PDF生成失败")
            return False

    except Exception as e:
        print(f"✗ 生成测试PDF时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_pdf_generation():
    """测试直接PDF生成功能"""
    print()
    print("=" * 60)
    print("直接PDF生成测试")
    print("=" * 60)
    print()

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, backend_dir)

    try:
        if 'pdf_generator' in sys.modules:
            del sys.modules['pdf_generator']

        from pdf_generator import PDFReportGenerator, check_pdf_capability

        if not check_pdf_capability()['can_generate_pdf']:
            print("✗ PDF生成能力不足")
            return False

        output_dir = os.path.join(backend_dir, "test_output")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, "direct_test.pdf")

        generator = PDFReportGenerator(output_path, title="直接测试报告")

        generator.add_title("直接测试报告")
        generator.add_divider()
        generator.add_heading("1. 文本测试", level=1)
        generator.add_paragraph("这是一个测试段落。")
        generator.add_heading("2. 列表测试", level=1)
        generator.add_bullet_list(["第一项", "第二项", "第三项"])
        generator.add_heading("3. 表格测试", level=1)

        table_data = [
            ["姓名", "分数", "等级"],
            ["张三", "95", "优秀"],
            ["李四", "88", "良好"],
            ["王五", "76", "中等"],
        ]
        generator.add_table(table_data)

        success = generator.build()

        if success and os.path.exists(output_path):
            print("✓ 直接PDF生成测试成功!")
            print(f"  文件路径: {output_path}")
            return True
        else:
            print("✗ 直接PDF生成测试失败")
            return False

    except Exception as e:
        print(f"✗ 直接PDF生成测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "PDF生成功能完整测试" + " " * 23 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # 执行测试
    test1_passed = test_pdf_generator()
    test2_passed = test_direct_pdf_generation()

    # 输出总结
    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Markdown转PDF测试: {'✓ 通过' if test1_passed else '✗ 失败'}")
    print(f"直接PDF生成测试: {'✓ 通过' if test2_passed else '✗ 失败'}")
    print()

    if test1_passed and test2_passed:
        print("🎉 所有测试通过！PDF生成功能正常工作")
        print()
        print("接下来你可以:")
        print("1. 在Web界面中尝试导出PDF报告")
        print("2. 使用MCP工具生成PDF报告")
        print()
        return True
    else:
        print("⚠ 部分测试失败，请检查上述错误信息")
        print()
        print("常见问题解决方案:")
        print("1. 如果reportlab未安装: pip install reportlab")
        print("2. 如果中文字体缺失: 安装中文字体或更新系统")
        print()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
