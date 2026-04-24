---
name: skill-seekers-windows
description: >-
  在 Windows 和 PowerShell 环境下安全调用 Skill Seekers，先检查 python、skill-seekers、本地
  agent 与 API Key，再与用户确认目标来源、输出目录、子 skill 名称、是否启用 AI 增强、采用
  API 还是 local agent、选择 Claude Code 还是 Codex，并按来源类型生成和执行高可信 PowerShell
  工作流。针对 Claude Code，在当前已验证的 Windows 版本组合下默认改走内置兼容脚本，而不是
  原生 `skill-seekers enhance --agent claude`，以避免 Claude 会话启动成功但 `SKILL.md`
  未写回；启用 AI 增强时默认执行一次沿用同路径的 `SKILL.md` 质量补丁。用户提到 Skill Seekers、
  skill-seekers、在 Windows 生成 skill、从 PDF、DOCX、EPUB、
  IPYNB、HTML、视频、本地目录、GitHub 仓库或文档站创建 skill、配置本地增强、Claude Code、
  Codex、codex.cmd、输出目录或子 skill 名称时使用本 skill。
---

# Skill Seekers Windows

## Overview

在 Windows / PowerShell 下编排 Skill Seekers 的环境检查、交互确认、命令生成与结果验证。优先采用本地已验证成功的 Windows 工作流；官方 README 仅作为补充，不覆盖本技能内置的高可信流程。

## Non-Negotiable Rules

- 只使用 PowerShell 语法，不照抄 Bash 示例。
- 正式执行前，必须先根据来源给出 2-3 个子 skill 名称建议，再与用户确认最终采用哪个名称。
- 正式执行前，必须与用户确认目标来源、输出目录、子 skill 名称。
- 未确认输出目录时，禁止执行 `Set-Location`、`skill-seekers create`、`skill-seekers video` 或 `skill-seekers enhance`。
- 不得默认使用当前工作目录、桌面目录、源文件同级目录或任意推断目录作为输出目录。
- 不得替用户直接决定是否启用 AI 增强；必须先问。
- 涉及 AI 增强时，必须确认是 `API` 还是 `local agent`。
- 若选择 `local agent`，必须继续确认 `Claude Code` 还是 `Codex`。
- 只要启用了 AI 增强，默认自动执行一次增强补丁；补丁阶段必须沿用与主增强相同的 AI 路径。
- 不得在主增强使用 `API` 时偷偷切换到本地 agent，也不得在主增强使用 `Claude Code` 时偷偷切到 `Codex`，反之亦然。
- 默认提供双模式：`保守型` 与 `直跑型`，并让用户明确选择。
- 路径包含空格或中文时必须加引号。
- 运行 `skill-seekers`、`doctor`、`config --show` 或本地增强前，先设置 UTF-8 环境变量。
- Windows 下优先通过切换执行目录控制输出位置，不盲信 `--output`。
- 当官方文档与本技能内置的 Windows 实测记录冲突时，优先参考 `references/windows-verified-workflows.md`。
- Codex 路线不要默认使用裸 `codex`；优先使用 `codex.cmd` 的自定义命令模板。
- 在当前已验证版本组合下，`Claude Code` 默认不要执行原生 `skill-seekers enhance --agent claude` 或 `skill-seekers create --agent claude`；改用本 skill 内置的兼容脚本。
- `Claude Code` 兼容脚本默认把“主增强 + 自动补丁 + 写回校验”合并在一次调用内；校验通过前，不要再重复执行第二次 Claude 补丁。

## Required Inputs

执行前必须确认以下字段；缺任一关键项时先问，不猜：

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| 目标来源 | 是 | 文档站 URL、GitHub 仓库、本地目录、本地文件、视频 URL 或视频文件 |
| 输出目录 | 是 | Windows 目录路径；必须由用户明确提供，优先切换到该目录再执行 |
| 子 skill 名称建议 | 是 | 先根据来源生成 2-3 个候选名称，供用户选择或修改 |
| 子 skill 名称 | 是 | 由 Skill Seekers 生成的目标 skill 名称 |
| 是否 AI 增强 | 是 | 不增强则只生成基础 skill |
| 增强方式 | 条件必需 | 仅当启用增强时需要：`API` 或 `local agent` |
| 本地 agent | 条件必需 | 仅当增强方式为 `local agent` 时需要：`Claude Code` 或 `Codex` |
| 增强补丁 | 否 | 默认自动开启；仅在用户明确要求关闭时才跳过 |
| 执行模式 | 是 | `保守型` 或 `直跑型` |

## Child Skill Naming

在询问用户最终名称前，先基于来源生成 2-3 个候选名称。

命名规则：

- 使用小写短横线风格
- 优先保留主题词，不要机械照抄超长文件名
- 如果来源是论文，优先提取主题或方法名，而不是作者和年份全拼
- 如果来源是文档站或仓库，优先使用产品或框架名

示例：

- 输入文件：`Active Bathymetric SLAM for autonomous underwater explorationLing et al2023.pdf`
- 可建议：
  - `active-bathymetric-slam`
  - `bathymetric-slam-exploration`
  - `auv-active-bslam`

必须先把这些建议发给用户，再让用户选择或改名，不能直接替用户定名。

## Source Routing

先识别来源，再决定命令形态：

- 视频 URL 或本地视频文件：使用 `skill-seekers video`
- GitHub 仓库：支持 `owner/repo` 或 `https://github.com/owner/repo`
- 文档站 URL：使用 `skill-seekers create "<url>"`
- 本地目录：使用 `skill-seekers create "<directory>"`
- 本地文件：根据扩展名走 `skill-seekers create "<file>"`

常见本地文件类型：

- 文档类：`.pdf`、`.docx`、`.epub`、`.adoc`
- 笔记与规范：`.ipynb`、`.html`、`.htm`、`.yaml`、`.yml`
- 订阅与 man page：`.rss`、`.xml`、`.1`
- 演示类：`.pptx`

## Workflow

### Step 1: Check Environment

优先运行 `scripts/check-environment.ps1`，读取以下状态：

- `python` 是否可调用
- `skill-seekers` 是否已安装，以及版本
- `claude` 是否可调用
- `codex.cmd` 是否可调用
- 是否存在可用 API Key
- `PYTHONIOENCODING` 与 `PYTHONUTF8` 是否已设为推荐值
- Windows 用户配置与进度目录位置

如果用户允许代为配置环境，先补齐缺口再进入后续步骤；如果不允许，清楚列出阻塞点并停止。

### Step 2: Confirm Execution Plan

按下面顺序与用户确认：

1. 目标来源是什么
2. 输出目录是什么
3. 先给出 2-3 个子 skill 名称建议
4. 用户最终选择哪个子 skill 名称
5. 是否需要 AI 增强
6. 若增强，采用 `API` 还是 `local agent`
7. 若为本地增强，选择 `Claude Code` 还是 `Codex`
8. 是否接受默认自动执行“增强补丁”（不提则视为接受）
9. 采用 `保守型` 还是 `直跑型`

如果用户还没有给出输出目录，立即停下并追问；不要把“当前目录”“桌面”“源文件同级目录”当作默认答案。

确认后，先向用户回显完整计划，再执行命令。

### Step 3: Prepare the Shell Session

Windows 下先设置 UTF-8，再切换目录：

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location "C:\target\output-dir"
```

只有在用户已经明确给出输出目录后，才能执行 `Set-Location`。

如果输出目录不存在，先与用户确认是否创建；得到确认后再创建。

不要自行把以下位置当作输出目录：

- 当前工作目录
- 桌面目录
- 源文件所在目录
- 任何“看起来合理”的临时目录

### Step 4: Execute by Mode

#### Mode A: 保守型

适用于 Windows 默认主流程。先生成基础 skill，再单独增强。

基础创建模板：

```powershell
skill-seekers create "C:\path\to\source.pdf" --name "target-skill" --enhance-level 0
```

视频模板：

```powershell
skill-seekers video --url "https://example.com/video" --name "target-skill"
```

保守型增强模板：

- `Claude Code`

```powershell
& "scripts/run-claude-compatible-enhancement.ps1" `
  -SkillDir ".\output\target-skill"
```

该脚本位于本 skill 的 `scripts/` 目录下，默认会在一次 Claude 调用中完成：

- 读取 `SKILL.md` 与预算内的 `references/*.md` 摘录
- 执行主增强
- 内置默认质量补丁目标
- 校验 `SKILL.md` 的内容哈希必须变化
- 外层总超时建议至少预留 20 分钟，不要用过短的包装层超时提前截断

若脚本返回成功，就不要再额外跑一次 Claude 补丁。

- `Codex`

```powershell
skill-seekers enhance ".\output\target-skill" `
  --agent custom `
  --agent-cmd 'codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "If there is ambiguity, choose a reasonable default, modify SKILL.md directly, and do not ask clarifying questions."' `
  --timeout 1200
```

仅在可信目录中使用上述 `Codex` 命令，因为它显式关闭了 Codex 自身的内部审批和沙箱。

- `API`

先按用户提供的方案设置所需 API Key，再运行：

```powershell
skill-seekers enhance ".\output\target-skill"
```

#### Mode B: 直跑型

适用于用户明确接受“更快但更难排障”的路径。保持 UTF-8 环境和固定执行目录，然后一次完成创建与增强。

- `API` 路线：先设置对应 API Key，再直接执行 `skill-seekers create`
- `Claude Code` 路线：在当前已验证版本上，不使用原生 `create --agent claude`；统一改为 `create --enhance-level 0` 后立刻执行兼容脚本，这就是当前 Windows 上最快且不返工的 Claude 直达路径
- `Codex` 路线：在可信目录中优先使用 `--agent custom --agent-cmd 'codex.cmd exec --dangerously-bypass-approvals-and-sandbox ...'`

如果用户没有明确接受排障成本，仍然推荐回到 `保守型`。

### Step 5: AI Enhancement Patch

仅在用户启用了 AI 增强，且没有明确关闭自动补丁时执行。

补丁阶段的目标不是“再做一遍完整增强”，而是对生成后的 `SKILL.md` 做一次定向质量修补。默认只修改 `SKILL.md`，不要修改 `references/`，除非用户明确要求。

例外规则：

- 若主增强走的是 `scripts/run-claude-compatible-enhancement.ps1` 的默认模式，则该次调用已经内置默认补丁目标
- 只要该脚本校验通过，就不要再追加第二次 Claude 补丁
- 只有在用户明确要求二次精修，或首次结果校验未达标时，才继续走同一路径的 Claude `PatchOnly` 模式

补丁阶段必须沿用主增强的同一路径：

- 主增强是 `local agent + Claude Code`，补丁也必须继续用 `Claude Code`
- 主增强是 `local agent + Codex`，补丁也必须继续用 `Codex`
- 主增强是 `API`，补丁也必须继续使用同一类 `API` provider 或同一路由

若当前环境无法保证“补丁与主增强同路径”，停止并告知用户，而不是私自切换路径。

补丁检查清单：

1. 修正把派生索引误写成独立来源的表述
2. 扩大 `description` 触发范围，使其覆盖实际章节能力
3. 给 `Quick Reference` 或等价高价值摘要补 `章节 + 页段 + 关键词` 锚点
4. 明确标出 OCR 噪声、伪代码块和资料边界
5. 防止把教材型资料误写成源码仓库或厂商 API 文档

在可信目录中的本地补丁命令模板：

- `Codex`

```powershell
Set-Location ".\output\target-skill"
codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "Refine only SKILL.md. Keep references unchanged. Fix source hierarchy, broaden description triggers to actual chapter coverage, add precise chapter/page/keyword anchors to Quick Reference, mark OCR/code limitations clearly, and do not ask clarifying questions."
```

- `Claude Code`

```powershell
& "scripts/run-claude-compatible-enhancement.ps1" `
  -SkillDir ".\output\target-skill" `
  -PatchOnly
```

若使用 `API` 路线，补丁也应继续使用同一 provider；当前若无法在该环境中确定同 provider 的补丁调用方式，不要偷偷切换到本地 agent。

### Step 6: Verify Results

不要只看命令退出码；至少检查以下内容：

- `output/<skill-name>/SKILL.md` 是否存在
- `output/<skill-name>/references/` 是否生成
- 对文件型来源，确认 `*_extracted.json` 或原始数据目录是否存在
- 若执行了增强，确认 `SKILL.md` 的内容或大小确实发生变化，而不是停留在基础版
- 若执行的是 Claude 兼容脚本，确认脚本输出的 `BEFORE_HASH` 与 `AFTER_HASH` 不同
- 若执行了增强补丁，确认 `description`、来源层级、`Quick Reference` 锚点和 OCR/边界说明至少有一项被实质改善

若命令成功但用户指定目录没有结果，优先检查当前执行目录下的 `output\` 文件夹。

## Agent Selection Rules

### API

- 仅在用户已经明确可用 API Key 时选择
- 若涉及 Claude 兼容端点，允许同时设置 `ANTHROPIC_BASE_URL`
- 未确认 provider 时，先问，不猜

### Claude Code

- 作为 Windows 本地增强的默认优先路线
- 在当前已验证版本上，这条路线默认指的是内置兼容脚本，不是原生 `skill-seekers enhance --agent claude`
- 当前高可信原因不是“原生命令更稳”，而是兼容脚本已经规避了 `skill-seekers 3.5.1` 的 Claude 调用兼容问题
- 仍然必须先设置 UTF-8 环境变量
- 如果当前机器上的 Claude 账号或本地 hook 状态异常，把该次失败记为“待复测”，不要武断归因为单一问题
- 若主增强使用了 Claude，默认自动补丁也继续使用 Claude，不切换到 Codex

### Codex

- 只有在用户明确要求 Codex 时才走这条路
- 先检查 `codex.cmd` 是否可调用；若只有裸 `codex` 或 npm shim 不可靠，先告知风险
- 在可信目录中的当前高可信写法是 `codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check ...`
- 默认不要只用 `--full-auto`，因为它可能让 Codex 生成补丁却不写盘
- agent 命令里要明确写入“直接选择合理默认值，不要反问用户”的约束
- 若主增强使用了 Codex，默认自动补丁也继续使用 Codex，不切换到 Claude

## Failure Handling

优先按下面顺序定位：

1. 命令是否在预期输出目录执行
2. UTF-8 环境变量是否已设置
3. `skill-seekers` 是否可调用且版本合理
4. 本地 agent 是否可调用
5. API Key 是否存在
6. 目标路径是否加引号

常见 Windows 症状：

- `UnicodeDecodeError: 'gbk' codec can't decode byte ...`
- `Agent finished but SKILL.md was not updated`
- `[WinError 5] Access is denied`
- 指定了 `--output`，结果却仍写入当前工作目录的 `output\`
- 主增强成功了，但 `SKILL.md` 仍保留伪多源、过窄 description、缺失锚点等明显质量问题
- `skill-seekers enhance --agent claude` 启动了 Claude，但最后只输出问候语或帮助信息，`SKILL.md` 完全没变化

出现这些问题时，优先读取 `references/windows-verified-workflows.md` 中的对应案例。

如果 `Codex` 输出了补丁或完整改写内容，但 `SKILL.md` 的时间戳和大小都没有变化，优先判断为 Codex 内部沙箱阻止写盘，而不是先怀疑提示词失效。

如果原生 `Claude` 增强只启动了会话却没有写回，优先判断为当前 `skill-seekers` 与 Claude CLI 的兼容问题；不要重复执行同一条原生命令，直接切换到 `scripts/run-claude-compatible-enhancement.ps1`。

## Resources

按需加载，不必每次全部读取：

| 资源 | 何时读取 | 用途 |
| --- | --- | --- |
| `references/skill-seekers-source-note.md` | 需要补充 Skill Seekers 通用命令、来源类型、导出目标时 | 作为本地备份说明与通用能力速查 |
| `references/windows-verified-workflows.md` | 需要选择 Windows 工作流、排查增强失败、决定 Claude/Codex 路线时 | 作为最高可信度的 Windows 实测参考 |
| `scripts/check-environment.ps1` | 正式执行前 | 输出环境状态与建议操作 |
| `scripts/run-claude-compatible-enhancement.ps1` | 用户选择 `Claude Code` 本地增强，或原生 Claude 路径已知不可靠时 | 以单次 Claude 调用完成主增强、默认补丁与写回校验 |

## Output Contract

完成任务时，给用户回报以下内容：

1. 已确认的输入参数
2. 提供过哪些子 skill 名称建议，以及用户最终选择了哪个名称
3. 是否启用 AI 增强，以及用户选择了哪条增强方案
4. 用户明确给出的输出目录，以及是否发生过“目录不存在后由用户确认创建”的动作
5. 实际执行的 PowerShell 命令
6. 生成结果目录
7. 是否完成 AI 增强
8. 是否执行了默认自动补丁，以及补丁沿用了哪条 AI 路径
9. 若失败，明确卡点和下一步建议
