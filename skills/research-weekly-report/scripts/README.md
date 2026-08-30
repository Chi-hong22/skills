# Scripts

<!--
一旦本文件夹内容发生变化，请更新本文档。
-->

科研周报生成的辅助脚本，用于处理日报元数据等确定性、重复性任务。

## 文件说明

| 文件 | 功能 |
|------|------|
| `generate_weekly_report.py` | 解析上一份周报时间范围、筛选本次候选日志、提取 tags、生成周报模板骨架 |
| `requirements.txt` | Python 依赖：`pyyaml>=6.0`、`python-frontmatter>=1.0.0` |

## generate_weekly_report.py

**定位**：辅助 AI 生成周报的工具脚本，负责确定性的“范围判定 + 候选日志筛选 + 模板骨架生成”任务，不负责最终内容填充。

**安装**：

```bash
pip install -r requirements.txt
```

**使用**：

```bash
# 基本用法
python generate_weekly_report.py --input daily-logs/

# 指定历史周报根目录
python generate_weekly_report.py --input daily-logs/2026-01/ --weekly-root weekly-reports/

# 显式指定上一份周报
python generate_weekly_report.py --input daily-logs/ --previous-report weekly-reports/2026/01/周报_260118.md

# 指定输出并跳过交互确认
python generate_weekly_report.py --input daily-logs/ --output report.md --auto-confirm
```

**参数**：

- `--input`：日报文件夹路径（必需）
- `--output`：输出路径（可选，默认自动计算）
- `--base-path`：周报基础路径（默认：`/04_自我管理/00_日志`）
- `--weekly-root`：历史周报根目录；未提供时尝试从输出路径或 `base-path` 推断
- `--previous-report`：显式指定上一份周报路径，优先级高于 `--weekly-root`
- `--auto-confirm`：跳过终端交互确认，直接继续生成模板

**范围判定规则**：

1. 优先读取上一份周报正文中的 `时间范围`。
2. 本次候选开始日期 = 上次结束日期 + 1 天。
3. 本次候选结束日期 = 当前输入日志中的最近日期。
4. 若未找到可解析的历史周报，则退回为当前输入日志的最小/最大日期。
5. 脚本会输出候选范围摘要；在交互终端中会要求用户确认后再继续。

**输出骨架**：

脚本生成“前短后详”的模板骨架：

1. `本周概述`：使用连续自然段，让导师快速理解本周工作与变化。
2. `主题`：按研究问题组织，而不是按文件或任务组织。
3. 主题内部最多包含 `进展与判断`、`当前问题`、`下一验证`。

**边界**：该脚本只生成模板骨架与候选范围摘要，不负责重要性过滤、主题归并和内容填充；这些工作仍由 AI 根据 `SKILL.md` 完成。
