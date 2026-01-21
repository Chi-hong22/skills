# Research Weekly Report - Scripts

本文件夹包含科研周报生成的辅助脚本。

## generate_weekly_report.py

周报生成辅助脚本，用于自动化处理元数据和模板生成。

### 功能

1. **元数据生成**：自动生成标题、日期范围、周次
2. **Tags 提取**：从日报文件的 frontmatter 中提取并去重 tags
3. **路径计算**：根据日期自动计算输出路径
4. **模板生成**：生成包含 9 大核心板块的周报模板结构

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

**基本用法**：

```bash
python generate_weekly_report.py --input <日报文件夹> --reporter "<汇报人姓名>"
```

**指定输出路径**：

```bash
python generate_weekly_report.py --input daily-logs/ --reporter "张三" --output my-report.md
```

**自定义 Obsidian 基础路径**：

```bash
python generate_weekly_report.py --input daily-logs/2026-01/ --reporter "李四" --base-path "/我的笔记/工作日志"
```

### 参数说明

- `--input`：日报文件或文件夹路径（必需）
- `--reporter`：汇报人姓名（默认：[姓名]）
- `--output`：输出文件路径（可选，默认自动计算）
- `--base-path`：Obsidian vault 基础路径（默认：/04_自我管理/00_日志）

### 输出

生成的周报模板包含：
- 完整的 YAML frontmatter（标题、tags、创建时间、编辑时间）
- 周报头部信息（汇报人、时间范围、周次）
- 9 大核心板块的结构
- 附图索引部分

### 工作流程

1. 扫描指定路径下的所有 Markdown 文件
2. 从每个文件的 frontmatter 提取 tags
3. 从文件名或 frontmatter 提取日期信息
4. 计算日期范围和周次
5. 生成包含所有 tags 的周报模板
6. 保存到指定路径

### 注意事项

- 确保日报文件包含有效的 YAML frontmatter
- 日报文件名建议包含日期（如：日报_260118.md）
- 输出路径会自动创建不存在的目录
- 生成的模板需要手动或使用 AI 填充内容

## requirements.txt

Python 依赖包列表：
- `pyyaml>=6.0`：YAML 解析
- `python-frontmatter>=1.0.0`：Markdown frontmatter 处理

## 文档更新

一旦本文件夹内容发生变化，请更新本 README.md 文件。
