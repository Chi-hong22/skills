---
name: pandoc-converter
description: Use when converting documents between Markdown, Word, PDF, HTML, LaTeX, EPUB, and other pandoc-supported formats, especially when a local pandoc CLI workflow is preferred over manual export.
---

# Pandoc Converter

## Overview

Use this skill when a document should be converted through the local `pandoc` CLI instead of manual copy-paste or editor export.

This repaired version is a minimal, Windows-friendly skill focused on one reliable path:
- use `scripts/convert.py` for common one-shot conversions
- fall back to direct `pandoc` commands when needed
- for Chinese reports (Chinese fonts, indent, three-line tables), use the reference doc described below

For Obsidian Markdown, the helper also normalizes common wiki-style image embeds before calling `pandoc`.
If a wiki-style image path does not resolve relative to the note, the helper tries to find the asset by file name under the current working tree.

## When to Use

- Markdown to Word, PDF, HTML, EPUB, or LaTeX
- Word to Markdown for version-controlled editing
- Quick local conversion without opening GUI tools
- Reproducible document conversion inside terminal workflows
- Obsidian Markdown export where source files contain `![[image.png|caption]]` style image embeds

Do not use this skill when:
- the task is primarily about editing existing `.docx` XML internals
- the user needs advanced Word layout authoring better handled by the `docx` skill

## Prerequisites

Required:
- `pandoc`
- `Python 3.8+`

Optional:
- LaTeX distribution for PDF output via LaTeX engines

## Quick Start

### Health Check

```powershell
python scripts/convert.py --check
```

### Common Conversions

```powershell
# Markdown -> Word
python scripts/convert.py input.md output.docx

# Word -> Markdown
python scripts/convert.py input.docx output.md

# Markdown -> HTML with TOC
python scripts/convert.py input.md output.html --toc

# Markdown -> PDF
python scripts/convert.py input.md output.pdf
```

### Direct Pandoc

```powershell
pandoc input.md -o output.docx
pandoc input.docx -o output.md
```

## 中文报告版式（reference doc）

`assets/reference_cn.docx` 固定了中文报告的版式：A4、左右边距 3.17 cm、上下 2.54 cm；正文宋体 + Times New Roman 12 pt、两端对齐、首行缩进 2 字符；标题宋体加粗 22 / 18 / 13.5 pt（一级居中、二三级左对齐）；引用段楷体；题注 10.5 pt 居中加粗；表格三线无竖线。它由 `scripts/make_reference_cn.py` 从 pandoc 默认模板生成，**不要手改 docx**，改版式改脚本再重建。

```powershell
# 1) 需要调版式时重新生成模板
python scripts/make_reference_cn.py

# 2) 转换：先去掉 YAML frontmatter，Obsidian 图片嵌入换成标准语法
pandoc report.md -o report.docx --reference-doc=assets/reference_cn.docx --resource-path=<md 所在目录>

# 3) 修表格与题注（pandoc 的等分列宽会让中文表头折行）
python scripts/postprocess_cn_docx.py report.docx
```

转换前的两件必做项（`convert.py` 只归一化图片，不处理 frontmatter）：

- 删掉 YAML frontmatter，否则 `标题/tags/创建时间` 会被当成元数据吞掉或渲染进正文
- `![[attachments/x.png]]` → `![](attachments/x.png){width=14.5cm}`，版心宽 = 21 − 3.17×2 ≈ 14.66 cm

已知行为：

- 主题字体属性（`asciiTheme`/`hAnsiTheme`/`cstheme`）优先级高于显式字体，模板脚本已清除；自行改模板后若中文变成等线、西文变成 Aptos，先查这里
- pandoc 输出表格是 `tblW=auto` + 等分 `gridCol`，Word 会按等分硬排，中文列名因此折行；`postprocess_cn_docx.py` 改为 100% 版心宽 + autofit，并把表格压成三线表（上下粗线 + 表头线，行间与竖线全去）、表头加粗、题注与图片居中
- 该脚本还约定两条正文规则：以「表 N / 图 N」开头的题注段居中加粗，以「时间范围」开头的段落居中——后者是周报类文档的约定，普通报告若正好有同形段落需自行去掉
- 列表项目符号沿用 pandoc 的 Symbol 字体，PDF 里会多出 SymbolMT / ArialMT 两条内嵌记录，不影响中文正文

## Supported Workflow

`scripts/convert.py` currently supports:
- single input file -> single output file
- format inference from file extension
- `--toc`
- `--number-sections`
- metadata injection via `--title` and `--author`
- optional `--resource-path`
- `--check` to verify local environment
- automatic Obsidian image embed normalization for Markdown input
- automatic inclusion of the input file directory in pandoc resource lookup
- fallback vault-style image resolution by file name when relative Obsidian attachment paths are stale

## Implementation

Files:
- `scripts/convert.py` — 通用一次性转换
- `scripts/make_reference_cn.py` — 生成 `assets/reference_cn.docx`（中文报告版式）
- `scripts/postprocess_cn_docx.py` — 修表格宽度、表头加粗、题注与图片居中
- `assets/reference_cn.docx` — 中文版式参考文档，供 `--reference-doc` 使用

Primary helper:
- `scripts/convert.py`

Behavior:
- resolves the `pandoc` executable from PATH by default
- prints the exact command in verbose mode
- exits with a clear error when `pandoc` is missing
- rewrites Obsidian image embeds like `![[attachments/pic.png|Caption]]` into standard Markdown images before conversion
- attempts to resolve broken relative Obsidian image paths by searching the current working tree for the same file name

## Common Mistakes

- `pandoc` not installed or not on PATH
- converting to PDF without a working PDF engine
- forgetting `--resource-path` when Markdown references local assets
- expecting raw Obsidian wiki image syntax to work with plain `pandoc` without preprocessing
- assuming stale `attachments/...` paths will resolve if the asset has been moved elsewhere in the vault
- expecting advanced templates that are not included in this repaired minimal version
- 中文文档不带 `--reference-doc=assets/reference_cn.docx`，会得到蓝色标题、等线与 Aptos 字体
- 把 `![[...]]` 直接交给 pandoc，或忘记删 YAML frontmatter

## Notes

This is a repaired minimal skill intended to restore discoverability and core functionality.

其他 house style 各备一份 `assets/*.docx`，并配一个同款的生成脚本；需要批量转换时再加脚本。
