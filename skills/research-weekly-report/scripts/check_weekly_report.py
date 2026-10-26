#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周报机检：篇幅硬上限、必填小节、概述科普首段、状态词、过程叙述、表图编号与图片数。

用法：python check_weekly_report.py <周报.md> [--json]
退出码：0 无阻断问题；1 存在 ERR。
口径：正文 = 去掉 frontmatter、标题行、引用块、表格、图题表题、代码块后的汉字数。
图片只计真实图片文件（![[x.png]] 或 ![](x.png)），不把笔记嵌入算作图。

Input: 周报 Markdown 路径（UTF-8），可选 --json
Output: 人读检查结果或 JSON；退出码 0 无阻断，1 有 ERR
Pos: 交付前机检脚本，只报机械可判问题，不替代内容验收
一旦文件被更新，务必更新开头注释及所属文件夹的 README.md。
"""
import json
import re
import sys

LIMITS = {"body_cjk": 1500, "quote_cjk": 400, "total_cjk": 2600, "figures": 4, "lede": 120, "theme_lead": 40}
IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp|svg|bmp|tiff?)$", re.IGNORECASE)
CJK = re.compile(r"[\u4e00-\u9fff]")
CAPTION = re.compile(r"^(\*\*|[-*]\s+\*\*)(图|表)\s*(\d+)")
PROCESS = [("第一步", r"第一步"), ("先…再…式步骤", r"先[^。；\n]{0,12}再"),
           ("冻结参数或种子", r"冻结[^。；\n]{0,8}(参数|种子|配置)"), ("排期", r"排期"),
           ("拟于或计划在", r"(拟于|计划在)")]
STATUS = ["定稿", "已证明", "完全解决"]
STATUS_LOOSE = re.compile(r"(?<![未不有])完成(?!率|度)|(?<![未已不经有])证明")


def cjk(text):
    return len(CJK.findall(text))


def split_frontmatter(lines):
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[: i + 1], lines[i + 1 :]
    return [], lines


def collect(body):
    kept, quote, table, caption = [], [], [], []
    in_code = False
    for line in body:
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^\s*>", line):
            quote.append(line)
            continue
        if s.startswith("|"):
            table.append(line)
            continue
        if CAPTION.match(s):
            caption.append(s)
            continue
        if s.startswith("#") or s.startswith("![["):
            continue
        kept.append(line)
    return kept, quote, table, caption


def first_paragraph_after(lines, start):
    for i in range(start + 1, len(lines)):
        s = lines[i].strip()
        if not s or s.startswith("#"):
            continue
        return s, i
    return "", start


def countFigures(text):
    """只计真实图片文件：wikilink 嵌入与标准 Markdown 图片，排除笔记嵌入。"""
    figures = 0
    for raw in re.findall(r"!\[\[([^\]]+)\]\]", text):
        target = raw.split("|")[0].split("#")[0].strip()
        if IMAGE_EXT.search(target):
            figures += 1
    for raw in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", text):
        if IMAGE_EXT.search(raw.strip("<>")):
            figures += 1
    return figures


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("用法: python check_weekly_report.py <周报.md> [--json]")
        return 2
    path = sys.argv[1]
    as_json = "--json" in sys.argv
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    _, body = split_frontmatter(lines)
    kept, quote, table, caption = collect(body)

    body_text = "\n".join(kept)
    body_cjk, quote_cjk, total_cjk = cjk(body_text), cjk("\n".join(quote)), cjk(text)
    results = []

    def add(level, name, detail):
        results.append({"level": level, "name": name, "detail": detail})

    add("ERR" if body_cjk > LIMITS["body_cjk"] else "OK", "正文汉字", "%d / %d" % (body_cjk, LIMITS["body_cjk"]))
    add("ERR" if quote_cjk > LIMITS["quote_cjk"] else "OK", "引用块汉字", "%d / %d" % (quote_cjk, LIMITS["quote_cjk"]))
    add("ERR" if total_cjk > LIMITS["total_cjk"] else "OK", "全篇汉字", "%d / %d" % (total_cjk, LIMITS["total_cjk"]))

    if not any("时间范围" in l for l in body):
        add("ERR", "时间范围", "缺少 **时间范围** 行")
    if not re.search(r"##\s*\d*\s*本周概述", text):
        add("ERR", "概述小节", "缺少 本周概述 小节")
    try:
        idx = next(i for i, l in enumerate(lines) if "本周概述" in l and l.strip().startswith("##"))
        lede, _ = first_paragraph_after(lines, idx)
        lede_n = cjk(lede)
        add("ERR" if lede_n > LIMITS["lede"] else "OK", "概述科普首段", "%d / %d 汉字" % (lede_n, LIMITS["lede"]))
    except StopIteration:
        pass

    for i, line in enumerate(lines):
        s = line.strip()
        if not (s.startswith("## ") and not s.startswith("### ")):
            continue
        if "概述" in s or "文献" in s or "附图" in s or "问题与" in s:
            continue
        lead, _ = first_paragraph_after(lines, i)
        lead = re.sub(r"^[-*]\s+", "", lead)
        n = cjk(lead)
        if n > LIMITS["theme_lead"]:
            add("WARN", "主题定位句", "第 %d 行后首段 %d 汉字，建议压到 %d 以内" % (i + 1, n, LIMITS["theme_lead"]))

    for word in STATUS:
        if word in body_text:
            add("WARN", "状态词", "出现 %s，确认不是把初稿写成定稿、把未验证写成已证明" % word)
    loose = STATUS_LOOSE.search(body_text)
    if loose:
        add("WARN", "状态词", "出现 %s，确认不是把未完成写成已完成、把未验证写成已证明" % loose.group(0))

    for name, pattern in PROCESS:
        if re.search(pattern, body_text):
            add("WARN", "过程叙述", "出现 %s，周报只写进展与结果" % name)

    figs, tabs = [], []
    for c in caption:
        m = CAPTION.match(c)
        if not m:
            continue
        (figs if m.group(2) == "图" else tabs).append(int(m.group(3)))
    for kind, nums in (("图", figs), ("表", tabs)):
        if nums and nums != list(range(1, len(nums) + 1)):
            add("ERR", "编号顺序", "%s编号 %s，应按出现顺序从 1 连续" % (kind, nums))
    n_img = countFigures(text)
    add("ERR" if n_img > LIMITS["figures"] else "OK", "图片数", "%d / %d" % (n_img, LIMITS["figures"]))
    if n_img < 2:
        add("WARN", "图片数下限", "仅 %d 张，规则期望 2–4 张；确有理由可保留" % n_img)

    summary = {"path": path, "body_cjk": body_cjk, "quote_cjk": quote_cjk, "total_cjk": total_cjk,
               "figures": n_img, "tables": len(tabs), "results": results}
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print("%-4s %-8s %s" % (r["level"], r["name"], r["detail"]))
        print("-> 正文 %d 字，引用块 %d 字，全篇 %d 字，图 %d 张，表 %d 张"
              % (body_cjk, quote_cjk, total_cjk, n_img, len(tabs)))
    return 1 if any(r["level"] == "ERR" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
