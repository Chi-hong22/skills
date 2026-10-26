# 自创 Skills

本目录存放自己创建的原创 Cursor Skills，用于个人项目或分享。

**更新提醒**：一旦本文件夹有所变化，请更新本文档。

## 文件夹结构

### obsidian-markdown-checker/

- **地位**：Obsidian Flavored Markdown 检查与修复技能
- **功能**：检查并修复 Obsidian 笔记内容，使其符合 OFM 规范
- **详情**：参见 [obsidian-markdown-checker/README.md](obsidian-markdown-checker/README.md)

### research-weekly-report/

- **地位**：科研周报生成技能（可评测、可迭代）
- **功能**：将零散日报提炼为面向导师的科研周报：概述报告分析形成的判断，详述用最少必要证据解释判断、当前问题与下一步；核对历史覆盖范围、内嵌图表与篇幅，配套机检脚本、评测样例与迭代入口
- **详情**：参见 [research-weekly-report/SKILL.md](research-weekly-report/SKILL.md)

### pandoc-converter/
- **地位**：文档格式互转技能（pandoc CLI），内置中文报告版式
- **功能**：Markdown/Word/PDF/HTML/LaTeX/EPUB 互转，支持 Obsidian 图片嵌入预处理与中文化版式管线
- **详情**：参见 [pandoc-converter/README.md](pandoc-converter/README.md)

### project-log/

- **地位**：项目推进日志体系技能（Git 仓库里的证据链）
- **功能**：建立、接管和维护项目日志，从 Git 历史补录缺失记录，记录功能/缺陷/实验/调参/决策/no-go，审计日志覆盖率，并向项目级 AGENTS.md 与 CLAUDE.md 注入日志规则
- **详情**：参见 [project-log/SKILL.md](project-log/SKILL.md)

### skill-seekers-windows/

- **地位**：Skill Seekers 的 Windows 编排技能
- **功能**：在 PowerShell 下先检查 python/skill-seekers/本地 agent/API Key，再确认来源、输出目录与子 skill 名称，按来源类型生成并执行工作流；支持 PDF、DOCX、EPUB、IPYNB、HTML、视频、GitHub 仓库等来源，Claude Code 默认走内置兼容脚本
- **详情**：参见 [skill-seekers-windows/SKILL.md](skill-seekers-windows/SKILL.md)
