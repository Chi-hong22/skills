#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FORMAT_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".docx": "docx",
    ".html": "html",
    ".htm": "html",
    ".tex": "latex",
    ".ltx": "latex",
    ".pdf": "pdf",
    ".epub": "epub",
    ".rst": "rst",
    ".txt": "plain",
}


def infer_format(path: Path) -> str | None:
    return FORMAT_MAP.get(path.suffix.lower())


def resolve_pandoc(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() else shutil.which(explicit)
    return shutil.which("pandoc")


def looks_like_markdown(fmt: str | None, path: Path) -> bool:
    return (fmt == "markdown") or path.suffix.lower() in {".md", ".markdown"}


def find_resource_by_name(file_name: str, search_root: Path) -> Path | None:
    matches = [path for path in search_root.rglob(file_name) if path.is_file()]
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_obsidian_target(target: str, input_path: Path, search_root: Path) -> str:
    candidate = Path(target)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    relative = input_path.parent / candidate
    if relative.exists():
        return target

    discovered = find_resource_by_name(candidate.name, search_root)
    if discovered:
        return discovered.as_posix()

    return target


def preprocess_obsidian_markdown(input_path: Path, search_root: Path) -> Path:
    text = input_path.read_text(encoding="utf-8")

    def replace_image(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        if "|" in inner:
            target, alt = inner.split("|", 1)
            target = target.strip()
            alt = alt.strip()
        else:
            target = inner
            alt = ""
        resolved = resolve_obsidian_target(target, input_path, search_root)
        return f"![{alt}]({resolved})"

    def replace_link(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        if "|" in inner:
            target, label = inner.split("|", 1)
            target = target.strip()
            label = label.strip()
        else:
            target = inner
            label = inner

        if any(sep in target for sep in ("/", "\\", ".")):
            resolved = resolve_obsidian_target(target, input_path, search_root)
            return f"[{label}]({resolved})"
        return label

    text = re.sub(r"!\[\[([^\]]+)\]\]", replace_image, text)
    text = re.sub(r"(?<!!)\[\[([^\]]+)\]\]", replace_link, text)

    temp_dir = Path(tempfile.mkdtemp(prefix="pandoc_converter_"))
    temp_file = temp_dir / input_path.name
    temp_file.write_text(text, encoding="utf-8")
    return temp_file


def run_command(command: list[str], verbose: bool) -> int:
    if verbose:
        print("RUN:", subprocess.list2cmdline(command))
    completed = subprocess.run(command, check=False)
    return completed.returncode


def perform_check(pandoc_cmd: str) -> int:
    print(f"PANDOC={pandoc_cmd}")
    version = subprocess.run([pandoc_cmd, "--version"], check=False, capture_output=True, text=True)
    if version.returncode != 0:
        sys.stderr.write(version.stderr or "Failed to run pandoc --version\n")
        return version.returncode
    first_line = version.stdout.splitlines()[0] if version.stdout else "pandoc available"
    print(first_line)
    print("STATUS=OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Minimal pandoc wrapper for single-file document conversion."
    )
    parser.add_argument("input", nargs="?", help="Input file path")
    parser.add_argument("output", nargs="?", help="Output file path")
    parser.add_argument("--check", action="store_true", help="Verify pandoc is available")
    parser.add_argument("--pandoc", help="Explicit pandoc executable path or command name")
    parser.add_argument("--from-format", dest="from_format", help="Override inferred input format")
    parser.add_argument("--to-format", dest="to_format", help="Override inferred output format")
    parser.add_argument("--toc", action="store_true", help="Include table of contents")
    parser.add_argument("--number-sections", action="store_true", help="Number headings")
    parser.add_argument("--title", help="Document title metadata")
    parser.add_argument("--author", help="Document author metadata")
    parser.add_argument("--resource-path", help="Pandoc resource path for linked assets")
    parser.add_argument("--verbose", action="store_true", help="Print generated pandoc command")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pandoc_cmd = resolve_pandoc(args.pandoc)
    if not pandoc_cmd:
        sys.stderr.write("pandoc not found. Install pandoc or pass --pandoc.\n")
        return 2

    if args.check:
        return perform_check(pandoc_cmd)

    if not args.input or not args.output:
        parser.error("input and output are required unless --check is used")

    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()

    if not input_path.exists():
        sys.stderr.write(f"Input file not found: {input_path}\n")
        return 2

    from_format = args.from_format or infer_format(input_path)
    to_format = args.to_format or infer_format(output_path)
    actual_input = input_path

    if looks_like_markdown(from_format, input_path):
        actual_input = preprocess_obsidian_markdown(input_path, Path.cwd())

    command = [pandoc_cmd, str(actual_input), "-o", str(output_path)]

    if from_format:
        command.extend(["-f", from_format])
    if to_format and to_format != "pdf":
        command.extend(["-t", to_format])
    if args.toc:
        command.append("--toc")
    if args.number_sections:
        command.append("--number-sections")
    if args.title:
        command.extend(["-M", f"title={args.title}"])
    if args.author:
        command.extend(["-M", f"author={args.author}"])
    resource_parts: list[str] = []
    if args.resource_path:
        resource_parts.append(args.resource_path)
    input_parent = str(input_path.parent)
    if input_parent not in resource_parts:
        resource_parts.append(input_parent)
    if resource_parts:
        command.extend(["--resource-path", os.pathsep.join(resource_parts)])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return run_command(command, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
