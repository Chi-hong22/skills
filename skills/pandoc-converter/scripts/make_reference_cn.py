r"""Input: pandoc 可执行文件（PATH 中）、python-docx；以 pandoc 自带 reference.docx 为基底。
Output: assets/reference_cn.docx —— 中文报告版式参考文档，供 pandoc --reference-doc 使用。
Pos: pandoc-converter 技能的中文版式唯一来源；改版式只改本脚本再重新生成，不要手改 docx。
一旦本文件被更新，务必更新开头注释与 SKILL.md 的「中文报告版式」一节。

版式取值来自 C:\Users\Chihong\Desktop\肖阳辉-20261025-周报正文.docx 的实测：
A4、左右边距 3.17 cm、上下 2.54 cm；正文宋体 + Times New Roman 12 pt、两端对齐、首行缩进 2 字符；
标题宋体加粗 22/18/13.5 pt（一级居中、二三级左对齐）；引用段楷体；题注 10.5 pt 居中加粗；表格三线无竖线。

用法：
    python scripts/make_reference_cn.py            # 生成 assets/reference_cn.docx
    python scripts/make_reference_cn.py --out X.docx
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt

FONT_HAN = "宋体"
FONT_KAI = "楷体"
FONT_LATIN = "Times New Roman"
THEME_ATTRS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")
SHADE_ATTRS = ("w:themeColor", "w:themeShade", "w:themeTint")


def get_style(doc, name: str):
    """按样式名查找，避免 python-docx 把字符串当 style_id 查询。"""
    for style in doc.styles:
        if style.name == name:
            return style
    raise KeyError(name)


def set_han_font(rpr, han: str, latin: str) -> None:
    """字体优先取 rFonts 显式属性，主题字体属性优先级更高，必须一并清掉。"""
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in THEME_ATTRS:
        rfonts.attrib.pop(qn(attr), None)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:cs"), latin)
    rfonts.set(qn("w:eastAsia"), han)


def set_color_black(rpr) -> None:
    color = rpr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rpr.append(color)
    for attr in SHADE_ATTRS:
        color.attrib.pop(qn(attr), None)
    color.set(qn("w:val"), "000000")


def three_line_borders(style) -> None:
    """三线表：上下粗线、表头下线由首行样式给出、无竖线。"""
    tbl_pr = style.element.find(qn("w:tblPr"))
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        style.element.append(tbl_pr)
    for tag in ("w:tblBorders",):
        old = tbl_pr.find(qn(tag))
        if old is not None:
            tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for tag, val, size in (
        ("w:top", "single", 8),
        ("w:left", "none", 0),
        ("w:bottom", "single", 8),
        ("w:right", "none", 0),
        ("w:insideH", "single", 4),
        ("w:insideV", "none", 0),
    ):
        el = OxmlElement(tag)
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000" if val == "single" else "auto")
        borders.append(el)
    tbl_pr.append(borders)


def build(out_path: Path) -> None:
    raw = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"],
        capture_output=True,
        check=True,
    ).stdout
    doc = Document(io.BytesIO(raw))

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)

    # 文档默认：西文 Times New Roman，中文宋体，五号（10.5 pt）即 21 半磅；正文样式再放大到小四。
    doc_defaults = doc.styles.element.find(qn("w:docDefaults"))
    rpr_default = doc_defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    set_han_font(rpr_default, FONT_HAN, FONT_LATIN)
    for tag in ("w:sz", "w:szCs"):
        el = rpr_default.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rpr_default.append(el)
        el.set(qn("w:val"), "24")

    normal = get_style(doc, "Normal")
    normal.font.size = Pt(12)
    set_han_font(normal.element.get_or_add_rPr(), FONT_HAN, FONT_LATIN)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0

    for name in ("Body Text", "First Paragraph", "Compact"):
        style = get_style(doc, name)
        style.paragraph_format.first_line_indent = Pt(24)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)

    for name, size, align, before, after in (
        ("Heading 1", 22, WD_ALIGN_PARAGRAPH.CENTER, 12, 6),
        ("Heading 2", 18, WD_ALIGN_PARAGRAPH.LEFT, 12, 6),
        ("Heading 3", 13.5, WD_ALIGN_PARAGRAPH.LEFT, 6, 3),
    ):
        style = get_style(doc, name)
        style.font.size = Pt(size)
        style.font.bold = True
        rpr = style.element.get_or_add_rPr()
        set_han_font(rpr, FONT_HAN, FONT_LATIN)
        set_color_black(rpr)
        style.paragraph_format.alignment = align
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.first_line_indent = Pt(0)

    caption = get_style(doc, "Caption")
    caption.font.size = Pt(10.5)
    caption.font.bold = True
    caption.font.italic = False
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.first_line_indent = Pt(0)
    caption.paragraph_format.space_before = Pt(6)
    caption.paragraph_format.space_after = Pt(6)  # 与 postprocess_cn_docx.py 保持一致

    block = get_style(doc, "Block Text")
    set_han_font(block.element.get_or_add_rPr(), FONT_KAI, FONT_KAI)

    table_style = get_style(doc, "Table")
    three_line_borders(table_style)
    tbl_pr = table_style.element.find(qn("w:tblPr"))
    for tag in ("w:tblInd", "w:tblCellMar"):
        old = tbl_pr.find(qn(tag))
        if old is not None:
            tbl_pr.remove(old)
    ind = OxmlElement("w:tblInd")
    ind.set(qn("w:w"), "0")
    ind.set(qn("w:type"), "dxa")
    tbl_pr.append(ind)
    mar = OxmlElement("w:tblCellMar")
    for tag, width in (("w:top", 0), ("w:left", 108), ("w:bottom", 0), ("w:right", 108)):
        el = OxmlElement(tag)
        el.set(qn("w:w"), str(width))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)

    # 兜底：模板里其余样式残留的主题字体属性一并清掉，否则 Word 会渲染成等线/Aptos。
    for rfonts in doc.styles.element.iter(qn("w:rFonts")):
        for attr in THEME_ATTRS:
            rfonts.attrib.pop(qn(attr), None)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    print(f"written: {out_path} ({out_path.stat().st_size} bytes)")


def main() -> int:
    default = Path(__file__).resolve().parent.parent / "assets" / "reference_cn.docx"
    parser = argparse.ArgumentParser(description="生成中文报告版式参考文档（pandoc --reference-doc）")
    parser.add_argument("--out", type=Path, default=default, help="输出路径，默认 assets/reference_cn.docx")
    args = parser.parse_args()
    try:
        build(args.out)
    except FileNotFoundError:
        print("pandoc not found on PATH", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
