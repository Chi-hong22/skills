# Research Weekly Report Skill

<!--
一旦本文件夹有所变化，请更新本文档。
-->

## 架构说明

本 Skill 用于将碎片化的日报记录转换为结构化的科研周报，支持9大核心板块、自动提取tags、LaTeX公式格式化、图文联动。

**核心流程**: 日报输入 → 信息提取与聚类 → 9大板块填充 → 公式格式化 → 周报输出

## 文件清单

### SKILL.md
- **地位**: Skill 的核心定义文件
- **功能**: 定义工作流程、9大核心板块映射规则、使用说明
- **说明**: 包含完整的使用指南和快速开始示例

### scripts/
- **地位**: 辅助脚本文件夹
- **功能**: 提供自动化处理工具
- **文件**:
  - `generate_weekly_report.py`: 周报生成辅助脚本（元数据生成、tags提取、路径计算、模板生成）
  - `requirements.txt`: Python 依赖声明
  - `README.md`: 脚本使用说明

### references/
- **地位**: 参考文档文件夹
- **功能**: 提供详细的参考资料和示例
- **文件**:
  - `prompt.md`: 完整的科研周报生成提示词（Background, Profile, Skills, Goals, Constraints, Workflow, OutputFormat, Example）
  - `example_output.md`: 实际成品周报示例
  - `obsidian_template.md`: Obsidian 模板插件的周报模板
  - `README.md`: 参考文档说明

### VALIDATION.md
- **地位**: Skill 验证报告
- **功能**: 记录 Skill 结构验证结果
- **说明**: 确保 Skill 符合规范

## 使用场景

- 每周向导师汇报科研进展
- 整理多日工作记录为系统性报告
- 需要按项目/专题组织研究内容
- 涉及实验数据、论文撰写、代码开发的综合性工作

## 快速开始

1. 准备日报文件（包含 YAML frontmatter 和【日期·分类】标注）
2. 在 Cursor 中调用：`帮我生成本周的科研周报，日报内容在 @daily-logs/ 文件夹中`
3. AI 自动读取日报、提取信息、生成周报
4. 周报保存到 Obsidian Vault 指定位置

## 核心特性

- **9大核心板块**: 研究内容标题、研究方法、技术路线、核心模型、仿真结果、存在问题、难点问题、解决思路、小论文撰写任务
- **Tags 管理**: 自动从日报 frontmatter 提取并去重
- **公式格式化**: 自动转换为标准 LaTeX 格式（`$...$` 或 `$$...$$`）
- **来源追踪**: 保留【日期·分类】标注
- **图文联动**: 生成图片索引和引用
- **专业表述**: 避免草稿性质的表述

## 技术栈

- Python 3.x
- pyyaml>=6.0
- python-frontmatter>=1.0.0

## 文档更新

一旦本文件夹有所变化，请更新本 README.md 文件。
