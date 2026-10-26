# Scripts

pandoc-converter 的三个命令行脚本，按「生成模板 → 转换 → 修补」顺序使用。

**更新提醒**：一旦本文件夹有所变化，请更新本文档。

## 文件说明

### convert.py
- **地位**：通用一次性转换入口
- **功能**：按扩展名推断格式并调用 pandoc；预处理 Obsidian 图片嵌入、补 resource path；`--check` 自检 pandoc 是否可用

### make_reference_cn.py
- **地位**：中文版式的唯一来源
- **功能**：以 pandoc 自带 reference.docx 为基底写入页面、字体、标题、引用、题注与三线表样式，生成 `assets/reference_cn.docx`；改版式改本脚本，不手改 docx

### postprocess_cn_docx.py
- **地位**：中文版式管线的第二步
- **功能**：就地修补 pandoc 不处理的局部版式——表格撑满版心、压成三线表并加粗表头，题注与图片居中，时间范围行居中
