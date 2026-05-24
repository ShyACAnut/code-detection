"""
PDF报告生成工具模块
=================

提供纯Python的PDF生成功能，不依赖外部Pandoc工具。
使用reportlab库生成专业的PDF报告。

功能：
- Markdown转PDF
- 纯文本转PDF
- 支持中文
- 自定义样式

作者：AI Assistant
日期：2025
"""

import os
from datetime import datetime
from typing import List, Optional

# 安全导入reportlab组件
REPORTLAB_AVAILABLE = False
_reportlab_components = {}

def _safe_import_reportlab():
    """安全地导入reportlab组件"""
    global REPORTLAB_AVAILABLE, _reportlab_components

    try:
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Image, HRFlowable, KeepTogether
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        _reportlab_components = {
            'A4': A4,
            'letter': letter,
            'getSampleStyleSheet': getSampleStyleSheet,
            'ParagraphStyle': ParagraphStyle,
            'inch': inch,
            'cm': cm,
            'TA_LEFT': TA_LEFT,
            'TA_CENTER': TA_CENTER,
            'TA_RIGHT': TA_RIGHT,
            'TA_JUSTIFY': TA_JUSTIFY,
            'colors': colors,
            'SimpleDocTemplate': SimpleDocTemplate,
            'Paragraph': Paragraph,
            'Spacer': Spacer,
            'Table': Table,
            'TableStyle': TableStyle,
            'PageBreak': PageBreak,
            'Image': Image,
            'HRFlowable': HRFlowable,
            'KeepTogether': KeepTogether,
            'pdfmetrics': pdfmetrics,
            'TTFont': TTFont,
        }

        REPORTLAB_AVAILABLE = True
        print("[PDF工具] reportlab 导入成功")

    except ImportError as e:
        REPORTLAB_AVAILABLE = False
        _reportlab_components = {}
        print(f"[PDF工具] reportlab 未安装或导入失败: {e}")
        print("[PDF工具] 请执行: pip install reportlab")
    except Exception as e:
        REPORTLAB_AVAILABLE = False
        _reportlab_components = {}
        print(f"[PDF工具] reportlab 导入异常: {e}")

# 立即尝试导入
_safe_import_reportlab()


def _get_component(name: str, default=None):
    """获取reportlab组件"""
    return _reportlab_components.get(name, default)


# 尝试注册中文字体
def _register_chinese_fonts():
    """注册中文字体，返回字体名称"""
    if not REPORTLAB_AVAILABLE:
        return "Helvetica"

    try:
        pdfmetrics = _get_component('pdfmetrics')
        TTFont = _get_component('TTFont')

        if not pdfmetrics or not TTFont:
            return "Helvetica"

        font_paths = [
            ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
            ("C:/Windows/Fonts/msyh.ttc", "MicrosoftYaHei"),
            ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
            ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WenQuanYi"),
            ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSans"),
        ]

        registered_fonts = []

        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    registered_fonts.append(font_name)
                    print(f"[PDF工具] 成功注册字体: {font_name} ({font_path})")
                except Exception as e:
                    print(f"[PDF工具] 注册字体失败 {font_path}: {e}")

        return registered_fonts[0] if registered_fonts else "Helvetica"

    except Exception as e:
        print(f"[PDF工具] 字体注册异常: {e}")
        return "Helvetica"


# 全局字体名称
CHINESE_FONT = _register_chinese_fonts()


class PDFReportGenerator:
    """
    PDF报告生成器类

    提供丰富的PDF报告生成功能，支持：
    - 标题和副标题
    - 段落文本
    - 表格
    - 代码块
    - 分页
    - 自定义样式
    """

    def __init__(self, output_path: str, title: str = "代码相似性检测报告"):
        """
        初始化PDF生成器

        Args:
            output_path: 输出PDF文件路径
            title: 报告标题
        """
        self.output_path = output_path
        self.title = title

        # 获取A4页面大小
        A4 = _get_component('A4')
        cm = _get_component('cm', 28.35)  # 默认1cm约等于28.35点

        self.pagesize = A4 if A4 else (595.27, 841.89)  # A4的点数
        self.left_margin = 2 * cm if cm else 56.69
        self.right_margin = 2 * cm if cm else 56.69
        self.top_margin = 2 * cm if cm else 56.69
        self.bottom_margin = 2 * cm if cm else 56.69

        self.styles = _get_component('getSampleStyleSheet')()
        self.story: List = []

        # 创建自定义样式
        self._create_custom_styles()

    def _create_custom_styles(self):
        """创建自定义样式"""
        if not REPORTLAB_AVAILABLE:
            return

        ParagraphStyle = _get_component('ParagraphStyle')
        colors = _get_component('colors')
        TA_CENTER = _get_component('TA_CENTER')
        TA_JUSTIFY = _get_component('TA_JUSTIFY')

        if not all([ParagraphStyle, colors, TA_CENTER, TA_JUSTIFY]):
            return

        # 标题样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontName=CHINESE_FONT,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a365d')
        ))

        # 副标题样式
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=14,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#4a5568')
        ))

        # 标题1样式
        self.styles.add(ParagraphStyle(
            name='CustomH1',
            parent=self.styles['Heading1'],
            fontName=CHINESE_FONT,
            fontSize=18,
            leading=24,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2d3748')
        ))

        # 标题2样式
        self.styles.add(ParagraphStyle(
            name='CustomH2',
            parent=self.styles['Heading2'],
            fontName=CHINESE_FONT,
            fontSize=14,
            leading=18,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#4a5568')
        ))

        # 正文样式
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=10,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8
        ))

        # 表格标题样式
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontName=CHINESE_FONT,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER
        ))

    def add_title(self, text: str, level: int = 1):
        """添加标题"""
        if not REPORTLAB_AVAILABLE:
            return

        Paragraph = _get_component('Paragraph')
        if not Paragraph:
            return

        if level == 1:
            self.story.append(Paragraph(text, self.styles['CustomTitle']))
        elif level == 2:
            self.story.append(Paragraph(text, self.styles['CustomSubtitle']))

        Spacer = _get_component('Spacer')
        if Spacer:
            self.story.append(Spacer(1, 12))

    def add_heading(self, text: str, level: int = 1):
        """添加章节标题"""
        if not REPORTLAB_AVAILABLE:
            return

        Paragraph = _get_component('Paragraph')
        if not Paragraph:
            return

        style_name = 'CustomH1' if level == 1 else 'CustomH2'
        self.story.append(Paragraph(text, self.styles[style_name]))

    def add_paragraph(self, text: str, indent: int = 0):
        """添加段落文本"""
        if not REPORTLAB_AVAILABLE:
            return

        Paragraph = _get_component('Paragraph')
        Spacer = _get_component('Spacer')
        if not Paragraph or not Spacer:
            return

        paragraphs = text.split('\n')
        for p in paragraphs:
            if p.strip():
                self.story.append(Paragraph(p, self.styles['CustomNormal']))
        self.story.append(Spacer(1, 8))

    def add_bullet_list(self, items: List[str], symbol: str = "•"):
        """添加项目符号列表"""
        if not REPORTLAB_AVAILABLE:
            return

        Paragraph = _get_component('Paragraph')
        Spacer = _get_component('Spacer')
        if not Paragraph or not Spacer:
            return

        for item in items:
            text = f"{symbol} {item}"
            self.story.append(Paragraph(text, self.styles['CustomNormal']))
        self.story.append(Spacer(1, 8))

    def add_code_block(self, code: str):
        """添加代码块"""
        if not REPORTLAB_AVAILABLE:
            return

        Paragraph = _get_component('Paragraph')
        Spacer = _get_component('Spacer')
        if not Paragraph or not Spacer:
            return

        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        self.story.append(Paragraph(f"<pre>{code}</pre>", self.styles['CustomNormal']))
        self.story.append(Spacer(1, 8))

    def add_table(self, data: List[List], col_widths: Optional[List] = None,
                  header_color: str = '#3182ce', alternate_row_color: str = '#f7fafc'):
        """添加表格"""
        if not REPORTLAB_AVAILABLE:
            return

        Table = _get_component('Table')
        TableStyle = _get_component('TableStyle')
        colors = _get_component('colors')
        TA_CENTER = _get_component('TA_CENTER')
        if not all([Table, TableStyle, colors, TA_CENTER]):
            return

        if not data:
            return

        # 计算列宽
        if col_widths is None:
            available_width = self.pagesize[0] - self.left_margin - self.right_margin
            col_count = len(data[0]) if data else 0
            col_widths = [available_width / col_count] * col_count

        table = Table(data, colWidths=col_widths)

        # 表格样式
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor(alternate_row_color)),
            ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # 交替行颜色
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.white))

        table.setStyle(TableStyle(style_commands))
        self.story.append(table)

        Spacer = _get_component('Spacer')
        if Spacer:
            self.story.append(Spacer(1, 15))

    def add_divider(self, color: str = '#e2e8f0', thickness: float = 1):
        """添加分隔线"""
        if not REPORTLAB_AVAILABLE:
            return

        HRFlowable = _get_component('HRFlowable')
        colors = _get_component('colors')
        if not HRFlowable or not colors:
            return

        self.story.append(HRFlowable(
            width="100%",
            thickness=thickness,
            color=colors.HexColor(color),
            spaceAfter=10,
            spaceBefore=10
        ))

    def add_page_break(self):
        """添加分页符"""
        if not REPORTLAB_AVAILABLE:
            return

        PageBreak = _get_component('PageBreak')
        if PageBreak:
            self.story.append(PageBreak())

    def build(self) -> bool:
        """
        生成PDF文件

        Returns:
            bool: 是否成功生成
        """
        if not REPORTLAB_AVAILABLE:
            print("[PDF工具] reportlab 未安装，无法生成PDF")
            return False

        try:
            SimpleDocTemplate = _get_component('SimpleDocTemplate')
            if not SimpleDocTemplate:
                print("[PDF工具] SimpleDocTemplate 不可用")
                return False

            doc = SimpleDocTemplate(
                self.output_path,
                pagesize=self.pagesize,
                leftMargin=self.left_margin,
                rightMargin=self.right_margin,
                topMargin=self.top_margin,
                bottomMargin=self.bottom_margin
            )

            doc.build(self.story)
            print(f"[PDF工具] PDF报告已生成: {self.output_path}")
            return True

        except Exception as e:
            print(f"[PDF工具] 生成PDF失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def markdown_to_pdf(markdown_text: str, output_path: str, title: str = "报告") -> bool:
    """
    将Markdown文本转换为PDF

    Args:
        markdown_text: Markdown格式的文本
        output_path: 输出PDF路径
        title: 报告标题

    Returns:
        bool: 是否成功转换
    """
    if not REPORTLAB_AVAILABLE:
        print("[PDF工具] reportlab 未安装，无法转换Markdown到PDF")
        return False

    try:
        generator = PDFReportGenerator(output_path, title=title)

        # 解析Markdown并添加到PDF
        lines = markdown_text.split('\n')
        in_table = False
        table_data = []
        table_col_count = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 空行处理
            if not line:
                if in_table and table_data:
                    generator.add_table(table_data)
                    table_data = []
                    in_table = False
                i += 1
                continue

            # 标题处理
            if line.startswith('# '):
                generator.add_title(line[2:], level=1)
            elif line.startswith('## '):
                generator.add_heading(line[3:], level=1)
            elif line.startswith('### '):
                generator.add_heading(line[4:], level=2)
            # 表格处理
            elif line.startswith('|'):
                # 解析表头和数据行
                cells = [cell.strip() for cell in line.split('|')[1:-1]]

                # 检查是否是分隔行
                if all(set(cell.replace('-', '').replace(':', '')) <= {'-', ':'} for cell in cells):
                    i += 1
                    continue

                if not in_table:
                    table_col_count = len(cells)
                    table_data = [cells]
                    in_table = True
                else:
                    if len(cells) == table_col_count:
                        table_data.append(cells)
            else:
                # 普通文本
                if in_table and table_data:
                    generator.add_table(table_data)
                    table_data = []
                    in_table = False

                # 处理列表
                if line.startswith('- ') or line.startswith('* '):
                    generator.add_bullet_list([line[2:]])
                # 处理普通段落
                else:
                    generator.add_paragraph(line)

            i += 1

        # 处理剩余的表格
        if in_table and table_data:
            generator.add_table(table_data)

        return generator.build()

    except Exception as e:
        print(f"[PDF工具] Markdown转PDF失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_pdf_capability() -> dict:
    """
    检查PDF生成能力

    Returns:
        dict: 包含检查结果的字典
    """
    # 重新尝试导入（以防之前失败）
    if not REPORTLAB_AVAILABLE:
        _safe_import_reportlab()

    result = {
        "reportlab_available": REPORTLAB_AVAILABLE,
        "chinese_font_available": CHINESE_FONT != "Helvetica",
        "font_name": CHINESE_FONT,
        "can_generate_pdf": REPORTLAB_AVAILABLE
    }

    if not REPORTLAB_AVAILABLE:
        result["message"] = "请安装reportlab库: pip install reportlab"
    elif CHINESE_FONT == "Helvetica":
        result["message"] = "中文字体未找到，PDF中的中文可能显示为方块"
    else:
        result["message"] = "PDF生成功能正常"

    return result


if __name__ == "__main__":
    # 测试PDF生成
    print("=" * 50)
    print("PDF报告生成工具测试")
    print("=" * 50)

    # 检查能力
    capability = check_pdf_capability()
    print(f"PDF生成能力检查: {capability}")

    if capability["can_generate_pdf"]:
        # 创建测试报告
        test_output = "test_report.pdf"
        success = markdown_to_pdf(
            """# 测试报告

## 基本信息

- 作业标题：测试作业
- 编程语言：Python
- 生成时间：2025-01-01

## 检测结果

| 提交A | 提交B | 相似度 |
|-------|-------|--------|
| 1     | 2     | 85%    |
| 3     | 4     | 72%    |
""",
            test_output,
            title="测试报告"
        )

        if success:
            print(f"✓ 测试报告已生成: {test_output}")
        else:
            print("✗ 测试报告生成失败")
    else:
        print("✗ 无法生成PDF，请安装必要的依赖")
        print(f"提示: {capability.get('message', '未知错误')}")
