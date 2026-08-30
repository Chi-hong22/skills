#!/usr/bin/env python3
"""
科研周报生成辅助脚本

功能：
- 自动定位上一份周报并解析其时间范围
- 基于历史周报与当前日志确定本次候选覆盖范围
- 输出候选范围摘要，并在交互环境中要求用户确认
- 从候选日志中提取 tags
- 生成符合当前 skill 规范的周报模板骨架

Input: 日报文件或文件夹路径，可选历史周报路径或周报根目录
Output: 周报模板 Markdown 文件
Pos: 辅助 AI 生成周报的工具脚本，负责确定性范围判定与模板骨架生成
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Tuple

import frontmatter
import yaml


TIME_RANGE_PATTERN = re.compile(
    r"(?:\*\*)?时间范围(?:\*\*)?[:：]\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})"
)
DATE_TOKEN_PATTERN = re.compile(r"(?<!\d)(\d{8}|\d{6})(?!\d)")


@dataclass
class LogInfo:
    path: Path
    date: datetime


@dataclass
class WeeklyReportInfo:
    path: Path
    start_date: datetime
    end_date: datetime


def configureConsoleEncoding() -> None:
    """
    在 Windows 终端中显式使用 UTF-8，避免中文输出乱码。
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def parseDateString(raw_value) -> Optional[datetime]:
    """
    将多种日期输入解析为 datetime（仅保留日期部分）。
    """
    if isinstance(raw_value, datetime):
        return datetime(raw_value.year, raw_value.month, raw_value.day)

    if isinstance(raw_value, date):
        return datetime(raw_value.year, raw_value.month, raw_value.day)

    if not isinstance(raw_value, str):
        return None

    normalized_value = raw_value.strip()

    date_match = re.search(r"(\d{4})[-/.](\d{2})[-/.](\d{2})", normalized_value)
    if date_match:
        year, month, day = map(int, date_match.groups())
        return datetime(year, month, day)

    digit_match = DATE_TOKEN_PATTERN.search(normalized_value)
    if not digit_match:
        return None

    token = digit_match.group(1)
    try:
        if len(token) == 8:
            return datetime.strptime(token, "%Y%m%d")
        return datetime.strptime(token, "%y%m%d")
    except ValueError:
        return None


def extractDateFromDailyLog(log_path: Path) -> Optional[datetime]:
    """
    优先从文件名提取日期，失败时再尝试从 frontmatter 读取日期。
    """
    matches = DATE_TOKEN_PATTERN.findall(log_path.stem)
    for token in reversed(matches):
        parsed_date = parseDateString(token)
        if parsed_date is not None:
            return parsed_date

    try:
        with open(log_path, "r", encoding="utf-8") as file_handle:
            post = frontmatter.load(file_handle)
    except Exception as exc:
        print(f"警告: 无法解析文件日期 {log_path}: {exc}", file=sys.stderr)
        return None

    for key in ("创建时间", "日期", "date"):
        parsed_date = parseDateString(post.metadata.get(key))
        if parsed_date is not None:
            return parsed_date

    return None


def collectDailyLogPaths(input_path: Path) -> List[Path]:
    """
    收集输入路径下的日报 Markdown 文件，排除已有周报文件。
    """
    if input_path.is_file():
        return [input_path]

    return sorted(
        [
            path
            for path in input_path.rglob("*.md")
            if not path.name.startswith("周报_")
        ]
    )


def collectLogInfos(daily_log_paths: List[Path]) -> List[LogInfo]:
    """
    收集所有带日期的日报信息。
    """
    log_infos = []

    for log_path in daily_log_paths:
        parsed_date = extractDateFromDailyLog(log_path)
        if parsed_date is None:
            print(f"警告: 无法确定日志日期，已跳过 {log_path}", file=sys.stderr)
            continue

        log_infos.append(LogInfo(path=log_path, date=parsed_date))

    return sorted(log_infos, key=lambda item: (item.date, item.path.name))


def extractTagsFromDailyLogs(daily_log_paths: List[Path]) -> Set[str]:
    """
    从日报文件中提取 tags。
    """
    all_tags = set()

    for log_path in daily_log_paths:
        if not log_path.exists():
            print(f"警告: 文件不存在 {log_path}", file=sys.stderr)
            continue

        try:
            with open(log_path, "r", encoding="utf-8") as file_handle:
                post = frontmatter.load(file_handle)

            raw_tags = post.metadata.get("tags")
            if isinstance(raw_tags, list):
                all_tags.update(raw_tags)
            elif isinstance(raw_tags, str):
                all_tags.add(raw_tags)
        except Exception as exc:
            print(f"警告: 无法解析文件 {log_path}: {exc}", file=sys.stderr)

    return all_tags


def normalizeTags(tags: Set[str]) -> List[str]:
    """
    保留 `日志/周报`，过滤其他 `日志/` 前缀标签。
    """
    filtered_tags = []

    for tag in sorted(tags):
        if tag == "日志/周报":
            continue
        if tag.startswith("日志/"):
            continue
        filtered_tags.append(tag)

    return ["日志/周报", *filtered_tags]


def extractTimeRangeFromWeeklyReport(report_path: Path) -> Optional[Tuple[datetime, datetime]]:
    """
    从历史周报正文中解析时间范围。
    """
    try:
        content = report_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"警告: 无法读取周报 {report_path}: {exc}", file=sys.stderr)
        return None

    match = TIME_RANGE_PATTERN.search(content)
    if match is None:
        return None

    start_date = datetime.strptime(match.group(1), "%Y-%m-%d")
    end_date = datetime.strptime(match.group(2), "%Y-%m-%d")
    return start_date, end_date


def findPreviousWeeklyReport(
    weekly_root: Path,
    latest_log_date: datetime,
    current_output_path: Optional[Path],
) -> Optional[WeeklyReportInfo]:
    """
    在周报根目录中查找最近一份已覆盖到当前日志日期之前的周报。
    """
    report_infos = []
    resolved_output_path = None

    if current_output_path is not None:
        try:
            resolved_output_path = current_output_path.resolve()
        except FileNotFoundError:
            resolved_output_path = current_output_path.absolute()

    for report_path in weekly_root.rglob("周报_*.md"):
        try:
            resolved_report_path = report_path.resolve()
        except FileNotFoundError:
            resolved_report_path = report_path.absolute()

        if resolved_output_path is not None and resolved_report_path == resolved_output_path:
            continue

        parsed_range = extractTimeRangeFromWeeklyReport(report_path)
        if parsed_range is None:
            continue

        start_date, end_date = parsed_range
        if end_date <= latest_log_date:
            report_infos.append(
                WeeklyReportInfo(
                    path=report_path,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

    if not report_infos:
        return None

    report_infos.sort(key=lambda item: (item.end_date, item.start_date, item.path.as_posix()))
    return report_infos[-1]


def resolveWeeklyRoot(
    weekly_root_arg: Optional[str],
    output_path: Optional[Path],
    base_path: str,
) -> Optional[Path]:
    """
    解析用于搜索历史周报的根目录。
    """
    candidate_paths = []

    if weekly_root_arg:
        candidate_paths.append(Path(weekly_root_arg))

    if output_path is not None:
        parents = list(output_path.parents)
        if len(parents) >= 3:
            candidate_paths.append(parents[2])
        if len(parents) >= 1:
            candidate_paths.append(parents[0])

    candidate_paths.append(Path(base_path))

    for candidate_path in candidate_paths:
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate_path

    return None


def calculateOutputPath(base_path: str, report_date: datetime) -> Path:
    """
    计算周报输出路径。
    """
    year = report_date.strftime("%Y")
    month = report_date.strftime("%m")
    filename = f"周报_{report_date.strftime('%y%m%d')}.md"
    return Path(base_path) / year / month / filename


def formatDateWithOrdinal(current_time: datetime) -> str:
    """
    格式化日期为 YYYY-MM-Do HH:mm:ss dddd。
    """
    day = current_time.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return f"{current_time.strftime('%Y-%m-')}{day}{suffix} {current_time.strftime('%H:%M:%S %A')}"


def summarizeLogDates(log_infos: List[LogInfo]) -> str:
    """
    将候选日志日期整理为便于核对的字符串。
    """
    unique_dates = sorted({log_info.date.strftime("%Y-%m-%d") for log_info in log_infos})
    return ", ".join(unique_dates)


def printRangeSummary(
    previous_report: Optional[WeeklyReportInfo],
    candidate_start: datetime,
    candidate_end: datetime,
    candidate_logs: List[LogInfo],
    excluded_logs: List[LogInfo],
) -> None:
    """
    输出候选范围摘要，供用户核对。
    """
    print("\n=== 周报范围核对摘要 ===")

    if previous_report is None:
        print("上一份周报: 未找到可解析的历史周报，本次回退为当前日志最小/最大日期")
    else:
        print(f"上一份周报: {previous_report.path}")
        print(
            "上一份周报时间范围: "
            f"{previous_report.start_date.strftime('%Y-%m-%d')} 至 "
            f"{previous_report.end_date.strftime('%Y-%m-%d')}"
        )

    print(
        "本次候选时间范围: "
        f"{candidate_start.strftime('%Y-%m-%d')} 至 {candidate_end.strftime('%Y-%m-%d')}"
    )
    print(f"本次候选日志数: {len(candidate_logs)}")
    print(f"本次候选日志日期: {summarizeLogDates(candidate_logs)}")

    if excluded_logs:
        print(f"已排除的更早日志数: {len(excluded_logs)}")
        print(f"已排除日志日期: {summarizeLogDates(excluded_logs)}")


def confirmCandidateRange(auto_confirm: bool) -> None:
    """
    在交互环境中要求用户确认候选范围。
    """
    if auto_confirm:
        print("已启用 --auto-confirm，跳过交互确认。")
        return

    if not sys.stdin.isatty():
        print("当前为非交互环境，请根据上述摘要在上层流程中与用户核对候选范围。")
        return

    answer = input("\n是否接受该候选范围并继续生成模板？[y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("已取消生成，请调整输入、显式指定历史周报，或重新筛选日志后再执行。", file=sys.stderr)
        sys.exit(2)


def generateWeeklyReportTemplate(
    start_date: datetime,
    end_date: datetime,
    tags: Set[str],
) -> str:
    """
    生成符合当前 skill 规范的周报模板内容。
    """
    title = f"周报_{end_date.strftime('%y%m%d')}"
    now = formatDateWithOrdinal(datetime.now())
    tags_list = normalizeTags(tags)

    frontmatter_dict = {
        "标题": title,
        "tags": tags_list,
        "创建时间": now,
        "编辑时间": now,
    }

    frontmatter_yaml = yaml.dump(
        frontmatter_dict,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    return f"""---
{frontmatter_yaml.strip()}
---

<!-- markdownlint-disable MD024 -->

# {title}

**时间范围**：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}

## 本周概述

[使用 1-3 个连续自然段，说明本周主要做了什么、课题和判断发生了什么变化、当前最关键的问题是什么。不要使用分点，不复制后文技术细节。]

---

## 主题一：[用研究问题、关键关系或判断变化命名]

### 进展与判断

- [说明为什么这是问题，本周哪些关键动作或证据推动了它，原有判断如何变化，当前如何理解。保留必要技术细节。] 【日期·分类】

### 当前问题

[明确当前属于已得到结果、合理判断、待验证假设、暂无法解释的问题或已否定方案，并说明证据缺口。]

### 下一验证

[指出下一项关键证据，以及什么结果会支持或改变当前判断。]

---

## 附图与证据索引

- **图1**：[说明图片支撑了什么判断] 【日期·分类】

![[attachments/image.png|描述]]
"""


def main():
    configureConsoleEncoding()

    parser = argparse.ArgumentParser(
        description="生成科研周报模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_weekly_report.py --input daily-logs/
  python generate_weekly_report.py --input daily-logs/2026-01/ --weekly-root weekly-reports/
  python generate_weekly_report.py --input daily-logs/ --previous-report weekly-reports/2026/01/周报_260118.md
        """,
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="日报文件或文件夹路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，默认自动计算）",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="/04_自我管理/00_日志",
        help="周报基础路径（默认: /04_自我管理/00_日志）",
    )
    parser.add_argument(
        "--weekly-root",
        type=str,
        help="历史周报根目录；未提供时尝试从输出路径或 base-path 推断",
    )
    parser.add_argument(
        "--previous-report",
        type=str,
        help="显式指定上一份周报路径，优先级高于 --weekly-root",
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="跳过交互确认，直接继续生成模板",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入路径不存在 {input_path}", file=sys.stderr)
        sys.exit(1)

    daily_log_paths = collectDailyLogPaths(input_path)
    if not daily_log_paths:
        print("错误: 未找到可用的日报文件", file=sys.stderr)
        sys.exit(1)

    print(f"找到 {len(daily_log_paths)} 个 Markdown 日志文件")

    log_infos = collectLogInfos(daily_log_paths)
    if not log_infos:
        print("错误: 未能从输入日志中解析出任何日期", file=sys.stderr)
        sys.exit(1)

    earliest_log_date = log_infos[0].date
    latest_log_date = log_infos[-1].date

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = calculateOutputPath(args.base_path, latest_log_date)

    previous_report = None

    if args.previous_report:
        previous_report_path = Path(args.previous_report)
        if not previous_report_path.exists():
            print(f"错误: 指定的上一份周报不存在 {previous_report_path}", file=sys.stderr)
            sys.exit(1)

        parsed_range = extractTimeRangeFromWeeklyReport(previous_report_path)
        if parsed_range is None:
            print(
                f"错误: 无法从指定周报中解析时间范围 {previous_report_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        previous_report = WeeklyReportInfo(
            path=previous_report_path,
            start_date=parsed_range[0],
            end_date=parsed_range[1],
        )
    else:
        weekly_root = resolveWeeklyRoot(args.weekly_root, output_path, args.base_path)
        if weekly_root is not None:
            previous_report = findPreviousWeeklyReport(weekly_root, latest_log_date, output_path)
        else:
            print("提示: 未找到可用的历史周报根目录，本次回退为当前日志最小/最大日期。")

    if previous_report is None:
        start_date = earliest_log_date
    else:
        start_date = previous_report.end_date + timedelta(days=1)

    end_date = latest_log_date

    candidate_logs = [
        log_info
        for log_info in log_infos
        if start_date <= log_info.date <= end_date
    ]
    excluded_logs = [
        log_info
        for log_info in log_infos
        if log_info.date < start_date
    ]

    printRangeSummary(previous_report, start_date, end_date, candidate_logs, excluded_logs)

    if not candidate_logs:
        print(
            "错误: 当前输入日志在上一份周报之后没有新的候选内容，请检查历史周报或输入日志范围。",
            file=sys.stderr,
        )
        sys.exit(1)

    confirmCandidateRange(args.auto_confirm)

    candidate_log_paths = [log_info.path for log_info in candidate_logs]
    tags = extractTagsFromDailyLogs(candidate_log_paths)
    print(f"提取到 {len(tags)} 个原始 tags: {sorted(tags)}")
    print(f"过滤后 tags: {normalizeTags(tags)}")

    template = generateWeeklyReportTemplate(
        start_date=start_date,
        end_date=end_date,
        tags=tags,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(template)

    print(f"\n周报模板已生成: {output_path}")
    print("\n下一步:")
    print("1. 先写自然段形式的本周概述")
    print("2. 按研究问题归并主题，补全进展与判断、当前问题、下一验证")
    print("3. 删除低价值细节，并按需格式化公式与图片索引")


if __name__ == "__main__":
    main()
