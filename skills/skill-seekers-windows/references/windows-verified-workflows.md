# Windows Verified Workflows

## Scope

This file captures the highest-confidence Windows workflows for `skill-seekers-windows`.

- Verification basis:
  Windows local runs summarized in the source note dated `2026-04-23`
- Environment:
  Windows + PowerShell + `skill-seekers 3.5.1`
- Trust rule:
  if a generic README example conflicts with this file, prefer this file

## Table of Contents

1. baseline shell setup
2. output directory behavior
3. conservative mode
4. direct mode guidance
5. Claude Code local enhancement
6. Codex local enhancement
7. post-enhancement patch
8. API enhancement
9. common failures
10. Windows paths and cleanup
11. MCP note

## 1. Baseline Shell Setup

Run these before diagnostics or local enhancement:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
```

Reason:

- Windows consoles may default to GBK
- `skill-seekers doctor`
- `skill-seekers config --show`
- local enhancement subprocess output

can all fail or be misread if Unicode output is decoded with GBK

## 2. Output Directory Behavior

The most reliable way to control where results land is to switch into the intended output directory before running `skill-seekers`.

Before execution, the user must explicitly provide the output directory.

Do not guess the output directory from:

- the current working directory
- the Desktop
- the source file's parent directory
- any other inferred path

Recommended pattern:

```powershell
Set-Location "C:\target\parent-dir"
skill-seekers create "C:\path\to\source.pdf" --name "target-skill" --enhance-level 0
```

Why:

- on the verified Windows runs, `--output` was less reliable than the current working directory
- users may believe generation failed when output actually landed in the current directory's `output\`
- because of that behavior, asking the user for the intended output directory is mandatory on Windows

## 3. Conservative Mode

This is the default recommended Windows path.

### Base creation

```powershell
Set-Location "C:\target\parent-dir"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
skill-seekers create "C:\path\to\source.pdf" --name "target-skill" --enhance-level 0
```

Use this first to prove that scraping or extraction succeeded.

After success, verify:

- `.\output\target-skill\SKILL.md`
- `.\output\target-skill\references\`
- extracted data files or data directories

### Then enhance

Only after base creation succeeds, run the selected enhancement route.

- for `Claude Code`, use the compatibility helper
- for `Codex`, use `skill-seekers enhance` with the trusted custom agent command
- for `API`, use `skill-seekers enhance` with the confirmed provider

## 4. Direct Mode Guidance

Use direct mode only when the user explicitly accepts that it is faster but harder to debug.

Keep these controls:

- set UTF-8 environment variables first
- pin the working directory first
- quote all paths
- if the result is missing, inspect the current directory's `output\` immediately

If a direct run fails, fall back to conservative mode before changing other variables.

Special rule for `Claude Code` on the current verified versions:

- do not use raw `skill-seekers create ... --agent claude`
- use `create --enhance-level 0` and then immediately run the compatibility helper
- this is the fastest currently verified Claude path that avoids a second repair pass

## 5. Claude Code Local Enhancement

This is still the preferred local agent route on Windows, but the current high-confidence path is the compatibility helper, not the raw `skill-seekers enhance --agent claude` command.

### Verified compatibility conclusion on 2026-04-24

Real test:

- source file: `C:\Users\Chihong\Desktop\Vial 等 - 2025 - MINS Tightly coupled MultiBeam EchoSounder Inertial Navigation System for 3D bathymetric underwater.pdf`
- output directory: `C:\Users\Chihong\Desktop`
- child skill name: `mins-mbes-ins`
- versions: `skill-seekers 3.5.1`, `Claude Code 2.1.117`

Observed sequence:

1. `skill-seekers create ... --enhance-level 0` succeeded.
2. `skill-seekers enhance ".\output\mins-mbes-ins" --agent claude --timeout 900` launched Claude but did not update `SKILL.md`.
3. standalone `claude --dangerously-skip-permissions -p '只输出 OK'` succeeded.
4. rerunning the enhancement intent through the corrected `claude -p` path updated `SKILL.md` from `2377` bytes to `14057` bytes.

Practical conclusion:

- `Claude Code` itself is usable on the current machine
- the failing point was the `skill-seekers 3.5.1` Claude invocation template
- do not default to raw `skill-seekers enhance --agent claude` on this version combination
- use the compatibility helper instead

### Recommended command

Resolve the helper script path relative to this skill directory, then run:

```powershell
Set-Location "C:\target\parent-dir"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
& "<path-to-this-skill>\scripts\run-claude-compatible-enhancement.ps1" `
  -SkillDir ".\output\target-skill"
```

What this helper guarantees:

- reads `SKILL.md` plus prompt-budgeted reference excerpts before editing
- performs the main enhancement and the default quality patch in one Claude call
- keeps `references/`, `assets/`, and `scripts/` unchanged
- fails hard if `SKILL.md` hash does not change
- in the verified `mins-mbes-ins` rerun, the helper completed in about 11 minutes, so outer timeout guards should leave at least 20 minutes

### Raw command status

Keep the raw command only as a compatibility diagnostic:

```powershell
skill-seekers enhance ".\output\target-skill" --agent claude --timeout 900
```

Current status on the verified Windows machine:

- may start Claude successfully
- may still end with `Agent finished but SKILL.md was not updated`
- should not be treated as the default success path until upstream fixes the template

## 6. Codex Local Enhancement

Do not assume bare `codex` is safe on Windows.

Current highest-confidence Codex pattern for trusted directories:

```powershell
Set-Location "C:\target\parent-dir"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
skill-seekers enhance ".\output\target-skill" `
  --agent custom `
  --agent-cmd 'codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "If there is ambiguity, choose a reasonable default, modify SKILL.md directly, and do not ask clarifying questions."' `
  --timeout 1200
```

If `codex.cmd` is not on `PATH`, use the explicit path, for example:

```powershell
skill-seekers enhance ".\output\target-skill" `
  --agent custom `
  --agent-cmd 'C:/Users/Chihong/AppData/Roaming/npm/codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "If there is ambiguity, choose a reasonable default, modify SKILL.md directly, and do not ask clarifying questions."' `
  --timeout 1200
```

Why this became the preferred command:

- on the current Windows machine, the older `--full-auto` route could produce a patch-like answer but leave `SKILL.md` unchanged
- the successful rerun used `--dangerously-bypass-approvals-and-sandbox`
- after that change, `skill-seekers` reported `SKILL.md updated: 17,004 bytes`

Why this route exists:

- verified Windows logs showed bare `codex` could hit an npm shim path and fail with `WinError 5`
- even after bypassing that issue, Codex could still be blocked by its own internal sandbox
- the explicit prompt constraint reduced the “ask questions instead of writing” failure mode
- the bypass flag fixed the “agent produced content but did not write the file” failure mode

Safety rule:

- use this Codex command only in a trusted directory that the user has explicitly chosen
- do not generalize this bypass flag into an always-on recommendation for unknown workspaces

## 7. Post-Enhancement Patch

After a successful AI enhancement, run one automatic quality patch by default unless the user explicitly disables it.

Patch scope:

- patch `SKILL.md` only
- keep `references/` unchanged unless the user asks for deeper cleanup
- focus on skill usability, not on rewriting the source material

Patch goals:

- downgrade derived index files from “independent source” to “navigation index”
- broaden `description` triggers to match actual chapter coverage
- add precise chapter, page-range, and keyword anchors to `Quick Reference` or equivalent summary sections
- mark OCR noise, fake code blocks, and textbook-vs-code boundaries clearly

Route consistency rule:

- if the main enhancement used `Codex`, the patch must also use `Codex`
- if the main enhancement used `Claude Code`, the patch must also use `Claude Code`
- if the main enhancement used an `API`, the patch must stay on the same provider path
- do not silently switch routes during patching

Special rule for the Claude compatibility helper:

- the default helper run already includes the default patch goals
- if the helper succeeds and verification passes, do not run a second Claude patch
- use a second Claude pass only when the user explicitly requests extra refinement or the first result still fails validation

### Codex Patch in Trusted Directories

```powershell
Set-Location "C:\target\parent-dir\output\target-skill"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "Refine only SKILL.md. Keep references unchanged. Fix source hierarchy, broaden description triggers to actual chapter coverage, add precise chapter/page/keyword anchors to Quick Reference, mark OCR/code limitations clearly, and do not ask clarifying questions."
```

This route matches the currently verified local Codex write-back pattern on Windows.

### Claude Patch on the Same Local Route

```powershell
Set-Location "C:\target\parent-dir"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
& "<path-to-this-skill>\scripts\run-claude-compatible-enhancement.ps1" `
  -SkillDir ".\output\target-skill" `
  -PatchOnly
```

Current note:

- this helper-backed Claude patch route should stay available as the same-path default when Claude was the chosen enhancer
- on the current machine, prefer this helper path over raw `claude -p ...` so the write-back validation remains standardized

### API Patch

For API enhancement, keep the same provider route for the patch stage.

If the current environment cannot guarantee a same-provider patch call, stop and report that limitation instead of silently switching to a local agent.

## 8. API Enhancement

Use API enhancement only after confirming the relevant key exists.

Examples:

### Anthropic-compatible

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
skill-seekers enhance ".\output\target-skill"
```

### Anthropic-compatible custom endpoint

```powershell
$env:ANTHROPIC_API_KEY = "compatible-key"
$env:ANTHROPIC_BASE_URL = "https://example.com/v1"
skill-seekers enhance ".\output\target-skill"
```

### OpenAI

```powershell
$env:OPENAI_API_KEY = "sk-proj-..."
skill-seekers enhance ".\output\target-skill" --target openai
```

If the user chooses API enhancement but no key is present, stop and report the missing prerequisite instead of guessing a provider.

## 9. Common Failures

### GBK decode failure

Symptoms:

```text
UnicodeDecodeError: 'gbk' codec can't decode byte ...
Agent finished but SKILL.md was not updated
Local enhancement did not complete
```

Likely cause:

- subprocess output was decoded with GBK instead of UTF-8

Fix:

- set `PYTHONIOENCODING=utf-8`
- set `PYTHONUTF8=1`
- rerun the enhancement step

### Claude launched but did not write SKILL.md

Symptoms:

```text
Agent finished but SKILL.md was not updated
Initial: mtime=..., size=...
Final:   mtime=..., size=...
```

Possible clue:

- the last Claude output is only a greeting, help text, or a request for the task details

Verified cause on the current machine:

- `skill-seekers 3.5.1` used an outdated Claude CLI invocation template
- Claude Code itself was still healthy and writable through the corrected `-p` path

Fix:

- do not rerun the same raw `skill-seekers enhance --agent claude` command
- switch to `scripts/run-claude-compatible-enhancement.ps1`
- require the helper to report different `BEFORE_HASH` and `AFTER_HASH`

### Access denied on Codex

Symptom:

```text
[WinError 5] Access is denied
```

Likely cause:

- the workflow hit bare `codex` or an npm shim rather than `codex.cmd`

Fix:

- switch to the explicit `codex.cmd` custom agent command

### Codex produced content but SKILL.md did not change

Symptoms:

```text
Agent finished but SKILL.md was not updated
Initial: mtime=..., size=...
Final:   mtime=..., size=...
```

Possible clue:

- the last agent output may already contain a valid patch or rewritten content

Likely cause:

- Codex generated the answer but its internal sandbox blocked the final file write

Fix for trusted directories:

- rerun the same `codex.cmd exec` path with `--dangerously-bypass-approvals-and-sandbox`
- keep `--skip-git-repo-check`
- keep the “modify SKILL.md directly, and do not ask clarifying questions” instruction

### Main enhancement succeeded but quality defects remain

Symptoms:

- `SKILL.md` exists and was updated
- but it still treats a derived index as an independent source
- or `description` only covers part of the actual chapter scope
- or high-value summaries have no stable chapter/page/keyword anchors

Likely cause:

- the first enhancement produced a usable draft but did not finish the skill-quality cleanup

Fix:

- run the default automatic patch on the same AI route
- keep the patch scope limited to `SKILL.md`
- prefer targeted quality repair over a second full rewrite

### Output seems missing

Symptom:

- the command succeeds but the requested destination looks empty

Likely cause:

- output was written under the current working directory's `output\`

Fix:

- inspect the current directory immediately
- rerun after `Set-Location` into the desired parent directory

## 10. Windows Paths and Cleanup

Useful Windows locations from the verified note:

```powershell
Join-Path $env:APPDATA "skill-seekers\config.json"
Join-Path $env:LOCALAPPDATA "skill-seekers\progress"
```

If old output or cache must be removed, use PowerShell path resolution before deletion:

```powershell
$target = Resolve-Path ".\output\target-skill_data" -ErrorAction Stop
Remove-Item -LiteralPath $target.Path -Recurse -Force
```

## 11. MCP Note

Shell scripts such as `setup_mcp.sh` are not directly runnable in a normal PowerShell session.

Prefer explicit server entry points:

```powershell
python -m skill_seekers.mcp.server_fastmcp
python -m skill_seekers.mcp.server_fastmcp --transport http --port 8765
```

## Recommended Decision Order

When operating on Windows, decide in this order:

1. source type
2. output directory
3. child skill name
4. enhancement or no enhancement
5. API or local agent
6. Claude Code or Codex
7. conservative mode or direct mode

If any of these remain unclear, ask before executing.

Special rule for output directory:

- if the user has not explicitly provided it, stop and ask
- never substitute a guessed directory, even for quick tests
