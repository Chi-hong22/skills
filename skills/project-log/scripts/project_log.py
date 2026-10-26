#!/usr/bin/env python3
"""Deterministic project log management with no third-party dependencies."""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA_VERSION = "2"
CONTRACT_MARKER = f"<!-- project-log:managed schema={SCHEMA_VERSION} -->"
CONTRACT_MARKER_RE = re.compile(r"<!-- project-log:managed schema=(\d+) -->")
ACTIVE_MARKER_RE = re.compile(r"<!-- project-log:active schema=(\d+) month=(\d{4}-\d{2}) -->")
PROMPT_BEGIN_RE = re.compile(r"<!-- project-log:begin(?: schema=\d+)? -->")
PROMPT_END_RE = re.compile(r"<!-- project-log:end -->")
GITIGNORE_BEGIN = "# project-log:begin"
GITIGNORE_END = "# project-log:end"
ENTRY_RE = re.compile(r"(?m)^#### (\d{4}-\d{2}-\d{2})：(.+)$")
NODE_ID_RE = re.compile(r"LOG-(\d{8})-(\d{2,})")
FULL_COMMIT_RE = re.compile(r"(?i)(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])")

TYPE_LABELS = {
    "implementation": "功能实现",
    "bug": "缺陷修复",
    "experiment": "实验",
    "tuning": "参数调优",
    "decision": "决策",
    "no-go": "否决",
    "docs": "文档契约",
    "maintenance": "工程维护",
    "release": "发布",
}

STATUS_LABELS = {
    "provisional": "暂定",
    "verified": "已验证",
    "no-go": "已否决",
    "superseded": "已被取代",
    "git-backfill": "Git 历史补录",
}

IGNORED_SCAN_DIRS = {
    ".git",
    ".log",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    "coverage",
    ".cache",
    ".turbo",
    ".vite",
    "vendor",
    "generated",
    "__pycache__",
}

LEGACY_NAME_RE = re.compile(r"dev[-_ ]?log|implementation[-_ ]?log|changelog|日志", re.IGNORECASE)
LEGACY_TEXT_SUFFIXES = {"", ".md", ".txt", ".rst", ".org", ".adoc", ".log"}
MAX_LEGACY_SOURCES = 100
MAX_LEGACY_FILE_BYTES = 2 * 1024 * 1024
MAX_LEGACY_TOTAL_BYTES = 8 * 1024 * 1024

DEFAULT_README = """{{CONTRACT_MARKER}}
# 项目日志合同

本目录是 `project-log` Skill 在仓库中的附属合同镜像；首要规则以已安装 Skill 的 `SKILL.md` 与其内部 references 为准。

- 当前活跃日志：`.log/active.md`
- 历史归档：`.log/archive/YYYY-MM.md`
- Schema：{{SCHEMA_VERSION}}
- 节点按可独立复核的工程状态或项目认知转移划分，不按 commit、文件或会话拆分。
- 核心链路：目标或问题 → 思路或假设 → 数据与证据 → 判读与决策 → 边界与未验证项。
- 应用运行日志、调试输出、遥测和生成产物不属于本目录。
"""

DEFAULT_ACTIVE = """<!-- project-log:active schema={{SCHEMA_VERSION}} month={{CURRENT_MONTH}} -->
# {{PROJECT_NAME}} 项目活跃日志：{{CURRENT_MONTH}}

> 当前月份唯一写入点。月结后由 `project-log rollover` 原子归档。
"""

DEFAULT_PROMPT = """<!-- project-log:begin schema={{SCHEMA_VERSION}} -->
## Project Log

本项目使用全局 `project-log` Skill 管理工程与研究日志。Skill 内部合同是首要规则，仓库根目录 `.log/README.md` 是便于人和 Agent 查阅的附属镜像。

任务形成可复核的工程状态、研究认知、实验结论或决策变化时，使用该 Skill 更新 `.log/active.md`；普通文档同步和文件流水账应克制合并到对应主节点。追溯历史时再读取 `.log/archive/`。不得把计划、推测、应用运行日志、生成产物或敏感信息写成已确认事实。
<!-- project-log:end -->
"""

DEFAULT_GITIGNORE_BLOCK = """# project-log:begin
!/.log/
!/.log/*.md
!/.log/archive/
!/.log/archive/**/*.md
# project-log:end"""


class ProjectLogError(RuntimeError):
    """Expected user-facing validation failure."""


@dataclass(frozen=True)
class TextFile:
    text: str
    newline: str = "\n"
    bom: bool = False


@dataclass(frozen=True)
class GitCommit:
    commit_hash: str
    commit_date: str
    author: str
    subject: str
    body: str
    files: tuple[str, ...]


def _run_git(root: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git 命令失败"
        raise ProjectLogError(message)
    return result


def resolve_project_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise ProjectLogError(f"项目根目录不存在：{root}")
        return root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ProjectLogError("当前目录不在 Git 仓库中；请显式提供 --project-root。")
    return Path(result.stdout.strip()).resolve()


def _read_text(path: Path) -> TextFile:
    raw = path.read_bytes()
    bom = raw.startswith(codecs.BOM_UTF8)
    if bom:
        raw = raw[len(codecs.BOM_UTF8) :]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectLogError(f"文件不是有效 UTF-8，拒绝修改：{path}") from exc
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return TextFile(text=text.replace("\r\n", "\n"), newline=newline, bom=bom)


def _atomic_write(path: Path, text: str, newline: str = "\n", bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = text.replace("\r\n", "\n").replace("\n", newline)
    payload = rendered.encode("utf-8")
    if bom:
        payload = codecs.BOM_UTF8 + payload
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _asset_text(name: str, fallback: str) -> str:
    path = Path(__file__).resolve().parent.parent / "assets" / name
    if not path.exists():
        return fallback
    return _read_text(path).text


def _render(template: str, project_name: str, month: str) -> str:
    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{SCHEMA_VERSION}}": SCHEMA_VERSION,
        "{{CURRENT_MONTH}}": month,
        "{{CONTRACT_MARKER}}": CONTRACT_MARKER,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template.rstrip() + "\n"


def _prompt_marker_state(text: str) -> str:
    begins = list(PROMPT_BEGIN_RE.finditer(text))
    ends = list(PROMPT_END_RE.finditer(text))
    if not begins and not ends:
        return "absent"
    if len(begins) != 1 or len(ends) != 1 or begins[0].start() >= ends[0].start():
        return "invalid"
    return "valid"


def _inject_prompt(original: TextFile | None, block: str) -> TextFile:
    if original is None:
        return TextFile(block.rstrip() + "\n")
    state = _prompt_marker_state(original.text)
    if state == "invalid":
        raise ProjectLogError("project-log 托管标记残缺、重复或顺序错误，拒绝修改。")
    if state == "absent":
        if original.text:
            separator = "\n" if original.text.endswith("\n") else "\n\n"
            text = original.text + separator + block.rstrip() + "\n"
        else:
            text = block.rstrip() + "\n"
    else:
        begin = PROMPT_BEGIN_RE.search(original.text)
        end = PROMPT_END_RE.search(original.text)
        assert begin is not None and end is not None
        text = original.text[: begin.start()] + block.rstrip() + original.text[end.end() :]
        if not text.endswith("\n"):
            text += "\n"
    return TextFile(text=text, newline=original.newline, bom=original.bom)


def _gitignore_marker_state(text: str) -> str:
    begin_count = text.count(GITIGNORE_BEGIN)
    end_count = text.count(GITIGNORE_END)
    if begin_count == 0 and end_count == 0:
        return "absent"
    if begin_count != 1 or end_count != 1 or text.index(GITIGNORE_BEGIN) >= text.index(GITIGNORE_END):
        return "invalid"
    return "valid"


def _inject_gitignore(original: TextFile | None) -> TextFile:
    if original is None:
        return TextFile(DEFAULT_GITIGNORE_BLOCK + "\n")
    state = _gitignore_marker_state(original.text)
    if state == "invalid":
        raise ProjectLogError(".gitignore 中 project-log 托管标记残缺或重复，拒绝修改。")
    if state == "absent":
        if original.text:
            separator = "\n" if original.text.endswith("\n") else "\n\n"
            text = original.text + separator + DEFAULT_GITIGNORE_BLOCK + "\n"
        else:
            text = DEFAULT_GITIGNORE_BLOCK + "\n"
    else:
        start = original.text.index(GITIGNORE_BEGIN)
        end = original.text.index(GITIGNORE_END) + len(GITIGNORE_END)
        text = original.text[:start] + DEFAULT_GITIGNORE_BLOCK + original.text[end:]
        if not text.endswith("\n"):
            text += "\n"
    return TextFile(text=text, newline=original.newline, bom=original.bom)


def _preflight_log_directory(root: Path) -> None:
    log_dir = root / ".log"
    if log_dir.exists() and not log_dir.is_dir():
        raise ProjectLogError(f"{log_dir} 已存在但不是目录。")
    if not log_dir.exists():
        return
    children = list(log_dir.iterdir())
    readme = log_dir / "README.md"
    managed = readme.is_file() and bool(CONTRACT_MARKER_RE.search(_read_text(readme).text))
    if children and not managed:
        raise ProjectLogError("检测到未受 project-log 管理的 .log 目录，可能是应用运行日志；拒绝接管。")
    if managed:
        allowed_top_level = {"README.md", "active.md", "archive"}
        unexpected = [item.name for item in children if item.name not in allowed_top_level]
        archive = log_dir / "archive"
        if archive.exists() and not archive.is_dir():
            unexpected.append("archive（不是目录）")
        elif archive.is_dir():
            unexpected.extend(
                str(item.relative_to(log_dir)).replace("\\", "/")
                for item in archive.rglob("*")
                if item.is_dir() or item.suffix.lower() != ".md"
            )
        if unexpected:
            raise ProjectLogError(".log 中存在合同外内容，可能属于应用运行日志；拒绝修改：" + "、".join(unexpected[:8]))


def _managed_log(root: Path) -> None:
    readme = root / ".log" / "README.md"
    if not readme.is_file() or not CONTRACT_MARKER_RE.search(_read_text(readme).text):
        raise ProjectLogError("项目尚未由 project-log setup 初始化。")


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _active_month(root: Path) -> str:
    active = root / ".log" / "active.md"
    if not active.is_file():
        raise ProjectLogError("缺少 .log/active.md。")
    match = ACTIVE_MARKER_RE.search(_read_text(active).text)
    if not match:
        raise ProjectLogError("active.md 缺少有效月份标记。")
    return match.group(2)


def _scan_project_candidates(root: Path) -> tuple[list[str], list[str]]:
    legacy_candidates: list[str] = []
    nested_prompts: list[str] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in IGNORED_SCAN_DIRS)
        files.sort()
        current_path = Path(current)
        for directory in directories:
            if LEGACY_NAME_RE.search(directory):
                legacy_candidates.append(str((current_path / directory).relative_to(root)).replace("\\", "/"))
        for filename in files:
            path = current_path / filename
            relative = str(path.relative_to(root)).replace("\\", "/")
            if filename in {"AGENTS.md", "CLAUDE.md"} and path.parent != root:
                nested_prompts.append(relative)
            if LEGACY_NAME_RE.search(filename):
                legacy_candidates.append(relative)
    return sorted(set(legacy_candidates)), sorted(set(nested_prompts))


def _legacy_candidate_files(root: Path, candidates: Sequence[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    resolved_root = root.resolve()
    for relative in candidates:
        candidate = root / relative
        if candidate.is_symlink():
            continue
        if candidate.is_file():
            possible = [candidate]
        elif candidate.is_dir():
            possible = []
            for current, directories, names in os.walk(candidate):
                directories[:] = sorted(name for name in directories if name not in IGNORED_SCAN_DIRS)
                names.sort()
                possible.extend(Path(current) / name for name in names)
        else:
            continue
        for path in possible:
            if path.is_symlink() or path.suffix.lower() not in LEGACY_TEXT_SUFFIXES:
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(resolved_root)
            except ValueError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return sorted(files)[:MAX_LEGACY_SOURCES]


def _legacy_hashes(root: Path) -> tuple[list[str], set[str], int, int]:
    candidates, _ = _scan_project_candidates(root)
    source_files = _legacy_candidate_files(root, candidates)
    readable_sources: list[str] = []
    hashes: set[str] = set()
    skipped_size = 0
    skipped_encoding = 0
    total_bytes = 0
    for path in source_files:
        try:
            size = path.stat().st_size
        except OSError:
            skipped_encoding += 1
            continue
        if size > MAX_LEGACY_FILE_BYTES or total_bytes + size > MAX_LEGACY_TOTAL_BYTES:
            skipped_size += 1
            continue
        try:
            raw = path.read_bytes()
            if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
                text = raw.decode("utf-16")
            else:
                text = raw.decode("utf-8-sig")
        except (OSError, UnicodeDecodeError):
            skipped_encoding += 1
            continue
        total_bytes += size
        readable_sources.append(str(path.relative_to(root)).replace("\\", "/"))
        hashes.update(match.group(1).lower() for match in FULL_COMMIT_RE.finditer(text))
    return readable_sources, hashes, skipped_size, skipped_encoding


def _legacy_readme_section(root: Path) -> str:
    candidates, _ = _scan_project_candidates(root)
    lines = [
        "## 旧日志来源",
        "",
        "旧日志原文保留在原位置；本节只登记自动扫描发现的候选来源，不复制或改写原文。",
        "",
    ]
    if candidates:
        lines.extend(f"- `{relative}`" for relative in candidates[:MAX_LEGACY_SOURCES])
        if len(candidates) > MAX_LEGACY_SOURCES:
            lines.append(f"- 另有 {len(candidates) - MAX_LEGACY_SOURCES} 个候选未在此展开。")
    else:
        lines.append("- 未发现旧日志候选。")
    lines.extend(
        [
            "",
            "> Git 补录会先按旧日志中的完整 40 位 commit hash 去重；旧日志的语义迁移、节点合并和研究判读仍需主 Agent 审核。",
        ]
    )
    return "\n".join(lines)


def inspect_project(root: Path) -> dict[str, object]:
    log_dir = root / ".log"
    managed = False
    foreign = False
    if log_dir.is_dir():
        readme = log_dir / "README.md"
        managed = readme.is_file() and bool(CONTRACT_MARKER_RE.search(_read_text(readme).text))
        foreign = any(log_dir.iterdir()) and not managed
    prompts: dict[str, str] = {}
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        prompts[name] = _prompt_marker_state(_read_text(path).text) if path.exists() else "absent"
    git = _run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0
    default_ref = _default_ref(root) if git else None
    shallow = False
    if git:
        shallow_result = _run_git(root, ["rev-parse", "--is-shallow-repository"], check=False)
        shallow = shallow_result.returncode == 0 and shallow_result.stdout.strip().lower() == "true"
    legacy_candidates, nested_prompts = _scan_project_candidates(root)
    return {
        "project_root": str(root),
        "git_repository": git,
        "log_directory": "managed" if managed else "foreign" if foreign else "absent",
        "active_month": _active_month(root) if managed and (log_dir / "active.md").exists() else None,
        "prompt_blocks": prompts,
        "default_ref": default_ref,
        "shallow_history": shallow,
        "legacy_log_candidates": legacy_candidates[:100],
        "legacy_log_candidates_truncated": len(legacy_candidates) > 100,
        "nested_prompt_files": nested_prompts[:100],
        "nested_prompt_files_truncated": len(nested_prompts) > 100,
    }


def setup(root: Path, dry_run: bool = False) -> dict[str, object]:
    _preflight_log_directory(root)
    month = _current_month()
    project_name = root.name
    log_dir = root / ".log"
    archive_dir = log_dir / "archive"
    readme_path = log_dir / "README.md"
    active_path = log_dir / "active.md"

    if active_path.exists() and not ACTIVE_MARKER_RE.search(_read_text(active_path).text):
        raise ProjectLogError("现有 .log/active.md 缺少有效受管标记，拒绝覆盖或部分升级。")

    prompt_template = _render(_asset_text("prompt-block.md.tpl", DEFAULT_PROMPT), project_name, month)
    if _prompt_marker_state(prompt_template) != "valid":
        raise ProjectLogError("Skill 内部 prompt-block 模板缺少有效托管标记，拒绝写入项目。")
    planned: list[tuple[Path, TextFile]] = []

    # Read and validate every managed file before performing the first write.
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        original = _read_text(path) if path.exists() else None
        planned.append((path, _inject_prompt(original, prompt_template)))

    gitignore_path = root / ".gitignore"
    gitignore_original = _read_text(gitignore_path) if gitignore_path.exists() else None
    planned.append((gitignore_path, _inject_gitignore(gitignore_original)))

    readme = _render(_asset_text("log-readme.md.tpl", DEFAULT_README), project_name, month)
    if CONTRACT_MARKER not in readme:
        readme = CONTRACT_MARKER + "\n" + readme
    readme = readme.rstrip() + "\n\n" + _legacy_readme_section(root).rstrip() + "\n"
    if readme_path.exists():
        readme_original = _read_text(readme_path)
        planned.append((readme_path, TextFile(readme, readme_original.newline, readme_original.bom)))
    else:
        planned.append((readme_path, TextFile(readme)))
    if not active_path.exists():
        active = _render(_asset_text("active.md.tpl", DEFAULT_ACTIVE), project_name, month)
        if not ACTIVE_MARKER_RE.search(active):
            active = f"<!-- project-log:active schema={SCHEMA_VERSION} month={month} -->\n" + active
        planned.append((active_path, TextFile(active)))
    else:
        active_original = _read_text(active_path)
        active_marker = ACTIVE_MARKER_RE.search(active_original.text)
        assert active_marker is not None
        if active_marker.group(1) != SCHEMA_VERSION:
            upgraded = ACTIVE_MARKER_RE.sub(
                f"<!-- project-log:active schema={SCHEMA_VERSION} month={active_marker.group(2)} -->",
                active_original.text,
                count=1,
            )
            planned.append((active_path, TextFile(upgraded, active_original.newline, active_original.bom)))

    changed = [str(path.relative_to(root)) for path, content in planned if not path.exists() or _read_text(path) != content]
    if dry_run:
        return {"status": "dry-run", "would_change": changed, "would_create_directory": str(archive_dir.relative_to(root))}

    archive_dir.mkdir(parents=True, exist_ok=True)
    for path, content in planned:
        if path.exists() and _read_text(path) == content:
            continue
        _atomic_write(path, content.text, content.newline, content.bom)
    return {"status": "ok", "changed": changed, "active_month": month}


def _all_log_files(root: Path) -> list[Path]:
    log_dir = root / ".log"
    files = []
    active = log_dir / "active.md"
    if active.is_file():
        files.append(active)
    archive = log_dir / "archive"
    if archive.is_dir():
        files.extend(sorted(archive.glob("*.md")))
    return files


def _next_node_id(root: Path, day: str) -> str:
    prefix = day.replace("-", "")
    maximum = 0
    for path in _all_log_files(root):
        for match in NODE_ID_RE.finditer(_read_text(path).text):
            if match.group(1) == prefix:
                maximum = max(maximum, int(match.group(2)))
    return f"LOG-{prefix}-{maximum + 1:02d}"


def _field(label: str, value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return f"- **{label}**：{value.strip()}"


def _content_field(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    lines = [line.rstrip() for line in value.strip().splitlines()]
    if len(lines) == 1:
        return f"- **修改正文**：{lines[0].strip()}"
    body = "\n".join(f"  > {line}" if line else "  >" for line in lines)
    return "- **修改正文**：\n" + body


def build_entry(
    root: Path,
    day: str,
    title: str,
    node_type: str,
    evidence_status: str,
    values: dict[str, str | None],
    node_id: str | None = None,
) -> str:
    if node_type not in TYPE_LABELS:
        raise ProjectLogError(f"未知类型：{node_type}；允许值：{', '.join(TYPE_LABELS)}")
    if evidence_status not in STATUS_LABELS:
        raise ProjectLogError(f"未知证据状态：{evidence_status}；允许值：{', '.join(STATUS_LABELS)}")
    try:
        parsed_day = date.fromisoformat(day)
    except ValueError as exc:
        raise ProjectLogError(f"日期格式无效：{day}") from exc
    node_id = node_id or _next_node_id(root, parsed_day.isoformat())
    lines: list[str | None] = [
        f"#### {day}：{title.strip()}",
        "",
        f"- **节点 ID**：{node_id}",
        f"- **类型**：{node_type}（{TYPE_LABELS[node_type]}）",
        f"- **证据状态**：{evidence_status}（{STATUS_LABELS[evidence_status]}）",
        _field("目标或问题", values.get("target")),
        _field("背景与基线", values.get("baseline")),
        _field("思路或假设", values.get("idea")),
        _field("实施或方法", values.get("method")),
        _content_field(values.get("content")),
        _field("数据与证据", values.get("data")),
        _field("结果", values.get("result")),
        _field("判读与决策", values.get("decision")),
        _field("边界与未验证项", values.get("boundaries")),
        _field("关联", values.get("relations")),
        _field("研究含义", values.get("research_meaning")),
    ]
    return "\n".join(line for line in lines if line is not None).rstrip() + "\n"


def _append_entry(path: Path, entry: str) -> None:
    current = _read_text(path)
    text = current.text.rstrip() + "\n\n" + entry.rstrip() + "\n"
    _atomic_write(path, text, current.newline, current.bom)


def record(root: Path, args: argparse.Namespace) -> dict[str, object]:
    _managed_log(root)
    day = args.date or date.today().isoformat()
    month = _active_month(root)
    if not day.startswith(month + "-"):
        raise ProjectLogError(f"记录日期 {day} 不属于活跃月份 {month}；请先 rollover 或使用 backfill。")
    values = {
        "target": args.target,
        "baseline": args.baseline,
        "idea": args.idea,
        "method": args.method,
        "content": args.content,
        "data": args.data,
        "result": args.result,
        "decision": args.decision,
        "boundaries": args.boundaries,
        "relations": args.relations,
        "research_meaning": args.research_meaning,
    }
    core_values = {
        "target": args.target,
        "idea": args.idea,
        "data": args.data,
        "decision": args.decision,
        "boundaries": args.boundaries,
    }
    missing = [name for name, value in core_values.items() if not value or not value.strip()]
    if missing:
        raise ProjectLogError("标准节点必须显式提供目标、思路、数据、判读和边界；缺少：" + ", ".join(missing))
    if args.evidence_status == "superseded":
        relation = values["relations"] or ""
        if not re.search(r"正式替代|替代节点|被.+替代|取代|superseded by", relation, re.IGNORECASE):
            raise ProjectLogError("superseded 节点必须通过 --relations 指明正式替代关系。")
    entry = build_entry(root, day, args.title, args.type, args.evidence_status, values)
    node_id = NODE_ID_RE.search(entry)
    _append_entry(root / ".log" / "active.md", entry)
    return {
        "status": "ok",
        "node_id": node_id.group(0) if node_id else None,
        "type": f"{args.type}（{TYPE_LABELS[args.type]}）",
        "evidence_status": f"{args.evidence_status}（{STATUS_LABELS[args.evidence_status]}）",
    }


def _next_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    if number == 12:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{number + 1:02d}"


def rollover(root: Path, new_month: str | None) -> dict[str, object]:
    _managed_log(root)
    old_month = _active_month(root)
    new_month = new_month or _next_month(old_month)
    if not re.fullmatch(r"\d{4}-\d{2}", new_month):
        raise ProjectLogError("--new-month 必须是 YYYY-MM。")
    if new_month <= old_month:
        raise ProjectLogError("新活跃月份必须晚于当前月份。")
    active = root / ".log" / "active.md"
    archive = root / ".log" / "archive" / f"{old_month}.md"
    if archive.exists():
        raise ProjectLogError(f"同月归档已存在，拒绝覆盖：{archive}")

    active_original = _read_text(active)
    template = _asset_text("active.md.tpl", DEFAULT_ACTIVE)
    new_content = _render(template, root.name, new_month)
    fd, temp_name = tempfile.mkstemp(prefix=".active.", suffix=".tmp", dir=active.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        _atomic_write(temp_path, new_content, active_original.newline, active_original.bom)
        os.replace(active, archive)
        try:
            os.replace(temp_path, active)
        except BaseException:
            os.replace(archive, active)
            raise
    finally:
        temp_path.unlink(missing_ok=True)
    return {"status": "ok", "archived": str(archive.relative_to(root)), "active_month": new_month}


def _default_ref(root: Path) -> str:
    remote = _run_git(root, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], check=False)
    if remote.returncode == 0 and remote.stdout.strip():
        return remote.stdout.strip()
    return "HEAD"


def _git_commits(root: Path, ref: str) -> list[GitCommit]:
    separator = "\x1e"
    field = "\x1f"
    fmt = f"%H%x1f%ad%x1f%an%x1f%s%x1f%b%x1e"
    result = _run_git(root, ["log", "--reverse", "--date=short", f"--format={fmt}", ref])
    commits: list[GitCommit] = []
    for raw_record in result.stdout.split(separator):
        record = raw_record.strip("\r\n")
        if not record:
            continue
        parts = record.split(field, 4)
        if len(parts) != 5:
            raise ProjectLogError("无法解析 Git 历史输出。")
        commit_hash, commit_date, author, subject, body = parts
        files_result = _run_git(root, ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit_hash])
        files = tuple(line.strip().replace("\\", "/") for line in files_result.stdout.splitlines() if line.strip())
        commits.append(GitCommit(commit_hash, commit_date, author, subject, body.strip(), files))
    return commits


def _existing_commits(root: Path) -> set[str]:
    hashes: set[str] = set()
    for path in _all_log_files(root):
        hashes.update(match.group(1).lower() for match in FULL_COMMIT_RE.finditer(_read_text(path).text))
    return hashes


def _infer_type(subject: str) -> str:
    match = re.match(r"(?i)^([a-z]+)(?:\([^)]*\))?!?:", subject)
    prefix = match.group(1).lower() if match else ""
    return {
        "feat": "implementation",
        "fix": "bug",
        "perf": "bug",
        "test": "maintenance",
        "docs": "docs",
        "refactor": "maintenance",
        "build": "maintenance",
        "ci": "maintenance",
        "chore": "maintenance",
        "release": "release",
    }.get(prefix, "maintenance")


def _is_log_only(commit: GitCommit) -> bool:
    if not commit.files:
        return False
    if all(path == ".log" or path.startswith(".log/") for path in commit.files):
        return True
    allowed_setup_paths = {"AGENTS.md", "CLAUDE.md", ".gitignore"}
    only_managed_paths = all(
        path == ".log" or path.startswith(".log/") or path in allowed_setup_paths
        for path in commit.files
    )
    setup_subject = re.search(
        r"project[-_ ]?log|log\s+setup|setup\s+log|初始化日志|日志体系|日志治理",
        commit.subject,
        re.IGNORECASE,
    )
    return only_managed_paths and bool(setup_subject)


def _archive_header(root: Path, month: str) -> str:
    return (
        f"<!-- project-log:archive schema={SCHEMA_VERSION} month={month} -->\n"
        f"# {root.name} 项目日志归档：{month}\n\n"
        "> 本文件包含人工日志与 Git 历史补录。git-backfill 节点只陈述提交中可确认的信息。\n"
    )


def _append_many(path: Path, header: str, entries: Iterable[str]) -> None:
    if path.exists():
        original = _read_text(path)
        text = original.text.rstrip()
        newline, bom = original.newline, original.bom
    else:
        text = header.rstrip()
        newline, bom = "\n", False
    new_entries = [entry.rstrip() for entry in entries]
    if not new_entries:
        return
    first_match = ENTRY_RE.search(text)
    if first_match:
        prefix = text[: first_match.start()].rstrip()
        blocks = [block for _, _, block in _entry_blocks(text)] + new_entries
    else:
        prefix = text.rstrip()
        blocks = new_entries

    def sort_key(block: str) -> tuple[str, int, str]:
        heading = ENTRY_RE.search(block)
        day = heading.group(1) if heading else "9999-99-99"
        node = NODE_ID_RE.search(block)
        sequence = int(node.group(2)) if node else 999999
        return day, sequence, heading.group(2) if heading else block

    blocks.sort(key=sort_key)
    merged = prefix + "\n\n" + "\n\n".join(blocks)
    _atomic_write(path, merged.rstrip() + "\n", newline, bom)


def backfill(root: Path, ref: str | None, dry_run: bool = False) -> dict[str, object]:
    _managed_log(root)
    if _run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode != 0:
        raise ProjectLogError("backfill/sync 需要 Git 仓库。")
    ref = ref or _default_ref(root)
    shallow_result = _run_git(root, ["rev-parse", "--is-shallow-repository"], check=False)
    shallow = shallow_result.returncode == 0 and shallow_result.stdout.strip().lower() == "true"
    existing = _existing_commits(root)
    legacy_sources, legacy_commits, legacy_skipped_size, legacy_skipped_encoding = _legacy_hashes(root)
    active_month = _active_month(root)
    grouped: dict[str, list[str]] = {}
    skipped_log_only = 0
    skipped_log_duplicate = 0
    skipped_legacy_duplicate = 0
    next_by_day: dict[str, int] = {}

    # Seed counters once so generated IDs stay unique without writing between entries.
    for path in _all_log_files(root):
        for match in NODE_ID_RE.finditer(_read_text(path).text):
            next_by_day[match.group(1)] = max(next_by_day.get(match.group(1), 0), int(match.group(2)))

    for commit in _git_commits(root, ref):
        if commit.commit_hash.lower() in existing:
            skipped_log_duplicate += 1
            continue
        if commit.commit_hash.lower() in legacy_commits:
            skipped_legacy_duplicate += 1
            continue
        if _is_log_only(commit):
            skipped_log_only += 1
            continue
        day_key = commit.commit_date.replace("-", "")
        next_by_day[day_key] = next_by_day.get(day_key, 0) + 1
        node_id = f"LOG-{day_key}-{next_by_day[day_key]:02d}"
        visible_files = "、".join(commit.files[:8]) if commit.files else "提交未列出文件"
        if len(commit.files) > 8:
            visible_files += f" 等 {len(commit.files)} 个文件"
        values = {
            "target": f"补录提交 `{commit.subject}` 的可确认工程变更。",
            "baseline": f"来源为 Git 提交元数据；作者：{commit.author}。",
            "idea": "无法从 Git 历史恢复当时的思路或假设。",
            "method": f"提交涉及：{visible_files}。",
            "data": f"完整 commit：`{commit.commit_hash}`。",
            "result": "仅确认该提交及其文件差异存在。",
            "decision": "无法从 Git 历史恢复当时的判读与决策。",
            "boundaries": "历史提交未提供可独立核验的验证记录、当时假设或学术结论；不得据此补推。",
            "relations": f"commit `{commit.commit_hash}`",
            "research_meaning": None,
        }
        entry = build_entry(
            root,
            commit.commit_date,
            commit.subject or commit.commit_hash[:12],
            _infer_type(commit.subject),
            "git-backfill",
            values,
            node_id=node_id,
        )
        grouped.setdefault(commit.commit_date[:7], []).append(entry)

    summary = {
        "status": "dry-run" if dry_run else "ok",
        "ref": ref,
        "shallow_history": shallow,
        "warning": "当前为 shallow clone，补录范围不完整。" if shallow else None,
        "new_entries": sum(len(entries) for entries in grouped.values()),
        "months": {month: len(entries) for month, entries in sorted(grouped.items())},
        "legacy_source_count": len(legacy_sources),
        "legacy_hash_count": len(legacy_commits),
        "legacy_skipped_size": legacy_skipped_size,
        "legacy_skipped_encoding": legacy_skipped_encoding,
        "skipped_log_duplicate": skipped_log_duplicate,
        "skipped_legacy_duplicate": skipped_legacy_duplicate,
        "skipped_manual_log": skipped_legacy_duplicate,
        "skipped_duplicate": skipped_log_duplicate + skipped_legacy_duplicate,
        "skipped_log_only": skipped_log_only,
    }
    if dry_run:
        return summary
    for month, entries in sorted(grouped.items()):
        if month == active_month:
            path = root / ".log" / "active.md"
            header = ""
        else:
            path = root / ".log" / "archive" / f"{month}.md"
            header = _archive_header(root, month)
        _append_many(path, header, entries)
    return summary


def _entry_blocks(text: str) -> list[tuple[str, str, str]]:
    matches = list(ENTRY_RE.finditer(text))
    blocks: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1), match.group(2).strip(), text[match.start() : end].strip()))
    return blocks


def _content_stats(block: str) -> tuple[bool, int]:
    match = re.search(r"^- \*\*修改正文\*\*：(.*)$", block, re.MULTILINE)
    if not match:
        return False, 0
    if match.group(1).strip():
        return True, 1
    count = 0
    for line in block[match.end() :].splitlines():
        if line.startswith("  >"):
            if line[3:].strip():
                count += 1
        elif line.strip():
            break
    return True, count


def _audit_prompt(path: Path, issues: list[dict[str, str]]) -> None:
    if not path.exists():
        issues.append({"severity": "error", "code": "prompt-missing", "path": path.name, "message": "缺少项目级提示词文件。"})
        return
    state = _prompt_marker_state(_read_text(path).text)
    if state != "valid":
        issues.append({"severity": "error", "code": "prompt-marker", "path": path.name, "message": f"托管块状态为 {state}。"})


def audit(root: Path) -> dict[str, object]:
    issues: list[dict[str, str]] = []
    log_dir = root / ".log"
    required = [log_dir / "README.md", log_dir / "active.md", log_dir / "archive"]
    for path in required:
        if not path.exists():
            issues.append({"severity": "error", "code": "structure", "path": str(path.relative_to(root)), "message": "缺少必需路径。"})
    if (log_dir / "README.md").is_file():
        readme_marker = CONTRACT_MARKER_RE.search(_read_text(log_dir / "README.md").text)
        if not readme_marker:
            issues.append({"severity": "error", "code": "contract-marker", "path": ".log/README.md", "message": "缺少受管合同标记。"})
        elif readme_marker.group(1) != SCHEMA_VERSION:
            issues.append({"severity": "warning", "code": "schema-outdated", "path": ".log/README.md", "message": f"合同 Schema 为 {readme_marker.group(1)}，当前为 {SCHEMA_VERSION}；请运行 setup 升级。"})
    if (log_dir / "active.md").is_file():
        active_match = ACTIVE_MARKER_RE.search(_read_text(log_dir / "active.md").text)
        if not active_match:
            issues.append({"severity": "error", "code": "active-marker", "path": ".log/active.md", "message": "活跃日志月份或 Schema 标记无效。"})
        elif active_match.group(1) != SCHEMA_VERSION:
            issues.append({"severity": "warning", "code": "active-schema-outdated", "path": ".log/active.md", "message": f"活跃日志 Schema 为 {active_match.group(1)}，当前为 {SCHEMA_VERSION}；请运行 setup 升级。"})
    for name in ("AGENTS.md", "CLAUDE.md"):
        _audit_prompt(root / name, issues)

    gitignore = root / ".gitignore"
    if not gitignore.exists() or _gitignore_marker_state(_read_text(gitignore).text) != "valid":
        issues.append({"severity": "error", "code": "gitignore-marker", "path": ".gitignore", "message": "缺少有效 project-log 例外块。"})
    if _run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0 and (log_dir / "active.md").exists():
        ignored = _run_git(root, ["check-ignore", "-q", ".log/active.md"], check=False)
        if ignored.returncode == 0:
            issues.append({"severity": "error", "code": "git-ignored", "path": ".log/active.md", "message": "活跃日志仍被 Git 忽略。"})

    seen_commits: dict[str, str] = {}
    temp_re = re.compile(r"方案\s*\d+|方法\s*[A-Za-zＡ-Ｚａ-ｚ]|临时")
    for path in _all_log_files(root):
        relative = str(path.relative_to(root)).replace("\\", "/")
        text = _read_text(path).text
        blocks = _entry_blocks(text)
        dates = [item[0] for item in blocks]
        if dates != sorted(dates):
            issues.append({"severity": "error", "code": "date-order", "path": relative, "message": "节点日期不是升序。"})
        for entry_date, title, block in blocks:
            node_match = NODE_ID_RE.search(block)
            if not node_match or node_match.group(1) != entry_date.replace("-", ""):
                issues.append({"severity": "error", "code": "node-id", "path": relative, "message": f"节点“{title}”缺少与日期一致的节点 ID。"})
            type_match = re.search(r"^- \*\*类型\*\*：([a-z-]+)（([^）]+)）", block, re.MULTILINE)
            if not type_match or TYPE_LABELS.get(type_match.group(1)) != type_match.group(2):
                issues.append({"severity": "error", "code": "type", "path": relative, "message": f"节点“{title}”类型或中文含义无效。"})
            status_match = re.search(r"^- \*\*证据状态\*\*：([a-z-]+)（([^）]+)）", block, re.MULTILINE)
            status = status_match.group(1) if status_match else None
            if not status_match or STATUS_LABELS.get(status) != status_match.group(2):
                issues.append({"severity": "error", "code": "evidence-status", "path": relative, "message": f"节点“{title}”证据状态或中文含义无效。"})
            for core_label in ("目标或问题", "思路或假设", "数据与证据", "判读与决策", "边界与未验证项"):
                field_match = re.search(rf"^- \*\*{re.escape(core_label)}\*\*：\s*(.+)$", block, re.MULTILINE)
                if not field_match or not field_match.group(1).strip():
                    issues.append({"severity": "error", "code": "core-field", "path": relative, "message": f"节点“{title}”缺少核心字段“{core_label}”。"})
            node_type = type_match.group(1) if type_match else None
            has_content, content_lines = _content_stats(block)
            if node_type in {"docs", "implementation"} and status != "git-backfill":
                if not has_content:
                    issues.append({"severity": "warning", "code": "content-missing", "path": relative, "message": f"节点“{title}”为 {node_type}（{TYPE_LABELS[node_type]}）类型，缺少修改正文。"})
                elif content_lines > 10:
                    issues.append({"severity": "warning", "code": "content-too-long", "path": relative, "message": f"节点“{title}”修改正文 {content_lines} 行，超过 10 行，建议改为主体概述 + 细节原文指针。"})
            if status in {"verified", "no-go"} and temp_re.search(block):
                issues.append({"severity": "warning", "code": "temporary-wording", "path": relative, "message": f"正式节点“{title}”仍含方案1、方法A或临时等中间表述。"})
            if status == "superseded" and not re.search(r"正式替代|替代节点|被.+替代|取代|superseded by", block, re.IGNORECASE):
                issues.append({"severity": "error", "code": "superseded-relation", "path": relative, "message": f"节点“{title}”未说明正式替代关系。"})
            for commit_hash in {match.group(1).lower() for match in FULL_COMMIT_RE.finditer(block)}:
                if commit_hash in seen_commits:
                    issues.append({"severity": "error", "code": "duplicate-commit", "path": relative, "message": f"commit {commit_hash} 已在 {seen_commits[commit_hash]} 记录。"})
                else:
                    seen_commits[commit_hash] = f"{relative}:{title}"
    if _run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0:
        try:
            missing_commits = [
                commit.commit_hash
                for commit in _git_commits(root, _default_ref(root))
                if not _is_log_only(commit) and commit.commit_hash.lower() not in seen_commits
            ]
        except ProjectLogError as exc:
            issues.append({"severity": "warning", "code": "git-coverage-unavailable", "path": ".git", "message": str(exc)})
        else:
            if missing_commits:
                issues.append({"severity": "warning", "code": "git-unrecorded", "path": ".git", "message": f"存在 {len(missing_commits)} 个尚未由完整 hash 关联的提交；可运行 sync。"})
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {"status": "ok" if errors == 0 else "failed", "errors": errors, "warnings": warnings, "issues": issues}


def _add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", "--repo", dest="project_root", help="项目根目录；省略时通过 git rev-parse 识别。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="统一项目日志治理工具")
    _add_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inspect", help="只读识别项目日志状态")
    setup_parser = subparsers.add_parser("setup", help="初始化或幂等升级日志体系")
    setup_parser.add_argument("--dry-run", action="store_true")

    record_parser = subparsers.add_parser("record", help="记录当前月份的标准节点")
    record_parser.add_argument("--title", required=True)
    record_parser.add_argument("--type", required=True, choices=sorted(TYPE_LABELS))
    record_parser.add_argument("--evidence-status", required=True, choices=sorted(STATUS_LABELS))
    record_parser.add_argument("--date")
    for option in ("target", "idea", "data", "decision", "boundaries"):
        record_parser.add_argument(f"--{option}", required=True)
    for option in ("baseline", "method", "content", "result", "relations", "research-meaning"):
        record_parser.add_argument(f"--{option}", dest=option.replace("-", "_"))

    rollover_parser = subparsers.add_parser("rollover", help="原子归档当前月份并创建新 active")
    rollover_parser.add_argument("--new-month")

    for command in ("backfill", "sync"):
        history_parser = subparsers.add_parser(command, help="从 Git 历史补录尚未记录的节点")
        history_parser.add_argument("--ref")
        history_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("audit", help="审计结构、节点合同、Git 覆盖与临时表述")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = resolve_project_root(args.project_root)
        if args.command == "inspect":
            result = inspect_project(root)
        elif args.command == "setup":
            result = setup(root, args.dry_run)
        elif args.command == "record":
            result = record(root, args)
        elif args.command == "rollover":
            result = rollover(root, args.new_month)
        elif args.command in {"backfill", "sync"}:
            result = backfill(root, args.ref, args.dry_run)
        elif args.command == "audit":
            result = audit(root)
        else:
            parser.error(f"未知命令：{args.command}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "audit" and result.get("status") == "failed" else 0
    except ProjectLogError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
