# Pandoc Converter Skill

基于本地 pandoc CLI 的文档格式互转技能（Markdown / Word / PDF / HTML / LaTeX / EPUB 等），并内置一套中文报告版式参考文档。

**更新提醒**：一旦本文件夹有所变化，请更新本文档。

## 文件说明

### SKILL.md
- **地位**：核心技能定义文件
- **功能**：转换路径选择（转换脚本 vs 直接 pandoc 命令）、格式对照表、中文报告版式的完整用法与已知坑

### scripts/convert.py
- **地位**：通用一次性转换入口
- **功能**：按扩展名推断格式并调用 pandoc，处理图片路径归一化；`--check` 自检 pandoc 是否可用

### scripts/make_reference_cn.py
- **地位**：中文版式唯一来源
- **功能**：以 pandoc 自带 reference.docx 为基底，用 python-docx 写入 A4 页面、边距、字体、标题、引用、题注与三线表样式，生成 `assets/reference_cn.docx`；改版式只改本脚本再重建，不手改 docx

### scripts/postprocess_cn_docx.py
- **地位**：中文版式管线第二步
- **功能**：修 pandoc 不处理的局部版式——表格撑满版心、表头加粗、单元格垂直居中、题注与图片居中、时间范围行居中

### assets/reference_cn.docx
- **地位**：`--reference-doc` 使用的版式载体（生成物）
- **功能**：固定中文报告观感：A4、左右 3.17 cm / 上下 2.54 cm、正文宋体 + Times New Roman 12 pt 首行缩进 2 字符、标题宋体加粗、引用楷体、三线表无竖线
