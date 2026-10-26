---
name: project-log
description: 为任意 Git 项目建立、接管和维护统一的项目推进日志体系。只要用户要初始化项目日志、规范旧日志、从 Git 历史补录缺失记录、记录功能/缺陷/实验/调参/决策/no-go、归档当前日志、审计日志覆盖率，或向项目级 AGENTS.md 与 CLAUDE.md 注入日志规则，就应使用本 Skill；即使用户只说“整理项目日志”“把过去工作补进日志”“记录这次研发结论”也应触发。不要用于应用运行日志、服务日志、telemetry、debug logging、训练控制台输出、实验原始输出或 Python/Java 等 logging 框架配置。
compatibility: 需要 Python 3、Git 和可写的项目工作区；优先在 Git 仓库中运行。
---

# Project Log

把项目日志维护成可复核的推进证据链，而不是 commit、文件和文档更新流水账。日志同时服务于三类读者：恢复上下文的 Agent、进行工程审计的人，以及后续从项目历史中提炼论文动机、方法演化、实验结果和限制的研究者。

## 权威来源

Skill 内部文档是规则权威：

- 记录、整理或审核节点时，读取 `references/log-contract.md`。
- 从 Git 历史补录时，同时读取 `references/git-backfill.md`。
- 注入或升级项目提示词时，读取 `references/prompt-injection.md`。
- 任务涉及多来源接管、批量历史、冲突或语义裁决时，读取 `references/agent-workflow.md`。

项目中的 `.log/README.md` 是由 Skill 生成的附属合同，方便没有安装 Skill 的 Agent 和人读取。它不得反向覆盖 Skill 内部规则；Schema 升级时，以 Skill 内部合同重新生成其托管内容。

## 管理范围

管理以下内容：

- 独立功能或工程能力的形成。
- Bug、性能问题、根因和回归验证。
- 实验、A/B、消融、参数调优及数据判读。
- 架构、接口、研究口径和 no-go 决策。
- 会改变工程合同、验证策略、论文 claim 或复现入口的文档工作。
- Git 历史中可以由证据可靠恢复的既往推进事实。

不要管理：

- 应用或服务运行日志、telemetry、debug 输出、崩溃转储。
- 训练控制台输出、原始实验数据、生成图表和大型二进制结果。
- 纯计划、未经验证的完成声明、会话聊天记录。
- 密钥、令牌、个人数据或其他敏感信息。

这些内容应留在项目既有运行日志、结果目录或外部存储中；项目日志只链接关键证据入口。

## 固定项目结构

在仓库根目录维护：

```text
.log/
├── README.md
├── active.md
└── archive/
    └── YYYY-MM.md
```

- `.log/README.md`：附属合同、Schema、阅读顺序和归档索引。
- `.log/active.md`：当前月份唯一可持续编辑的日志。
- `.log/archive/YYYY-MM.md`：已关闭月份，默认冻结。

不要把运行时 `.log` 文件搬入该目录。若 `.log/` 已被项目用于其他用途，先停止并报告路径冲突，不覆盖现有内容。

## 复杂任务的 Agent 工作流

以下情况属于复杂任务，应先读取 `references/agent-workflow.md`：

- 迁移旧日志或接管多种历史格式。
- 回填多个月份或大量 commit。
- 处理 AGENTS.md、CLAUDE.md 或旧日志提示词冲突。
- 合并多个临时节点、正式术语和相互矛盾的判读。
- 更正已归档节点或重建历史因果。
- 升级 Schema、模板或项目侧附属合同。

主 Agent 承担 orchestrator 与 deep reasoning：确定证据边界、规划、拆解、架构判断、冲突裁决和最终综合，不陷入可委派的低层体力工作。子 Agents 只承担边界清晰的机械检索、Git 提取、定点写入、验证和简要独立 review；尽量并行，但不得修改重叠文件或替主 Agent 作语义裁决。

主 Agent 委派前应明确目标、输入、允许修改范围、禁止事项、输出格式和验证方式；子 Agent 返回后必须复核事实、diff、冲突、遗漏和结论边界，再决定采纳、修改或丢弃。简单任务仍由主 Agent 直接完成，不为使用 subagent 而拆分。

## 标准工作流

### 1. 检查项目状态

先运行：

```powershell
python scripts/project_log.py --project-root <项目根目录> inspect
```

确认：

- 项目根目录和 Git 状态。
- `.log/` 是否存在、是否与其他用途冲突。
- 旧日志位置和格式。
- 根级 `AGENTS.md`、`CLAUDE.md` 是否存在。
- `.gitignore` 是否会忽略 `.log/` 或其中 Markdown 文件。
- 是否为 shallow clone、默认分支能否识别。

根据证据分类：

- 空项目：无 `.log/`，无可补录 Git 历史。
- 历史项目：无 `.log/`，但有 Git 历史。
- 旧日志项目：有其他位置或格式的项目日志。
- 已接入项目：存在受管 `.log/README.md`。
- 冲突项目：`.log/` 已有非本 Skill 内容，或托管块损坏。

### 2. 预览搭建或接管

对空项目、历史项目和旧日志项目，先 dry-run：

```powershell
python scripts/project_log.py --project-root <项目根目录> setup --dry-run
```

检查预览是否：

- 只创建或更新约定路径。
- 保留已有人工日志和项目提示词的非托管内容。
- 正确识别需要补录的 Git 范围。
- 没有把运行日志、结果文件或普通文档误认为项目日志。

确认后运行不带 `--dry-run` 的 `setup`。若旧日志迁移需要人为判断，先报告映射，不要强行转换。

### 3. 记录推进节点

读取 `references/log-contract.md`，先判断是否形成了一个可独立复核的状态转移。满足条件时使用：

```powershell
python scripts/project_log.py --project-root <项目根目录> record `
  --title <正式节点名称> `
  --type <英文类型> `
  --evidence-status <英文证据状态> `
  --target <目标或问题> `
  --idea <思路或假设> `
  --data <数据与证据> `
  --decision <判读与决策> `
  --boundaries <边界与未验证项>
```

可按需补充 `--date`、`--baseline`、`--method`、`--content`、`--result`、`--relations`、`--research-meaning`。`--content` 填写 `修改正文`：`docs（文档契约）` 与 `implementation（功能实现）` 节点必填，内容本体 ≤10 行写全文（多行用单引号 here-string 传入，脚本渲染为缩进引用块），>10 行写 3-5 句主体概述 + 细节原文指针（`路径 §位置 @ commit`）。不要为了填满字段而编造信息；缺失项应明确为未记录或不可恢复。

### 4. 整理 active 中间过程

开发中的 `方案1`、`方法A`、`临时路径` 等表述只能暂存于 `.log/active.md`。在功能稳定、形成正式文档或归档前，执行一次语义收口：

1. 为稳定概念确定正式名称。
2. 修改仅有措辞差异的临时表述。
3. 将成为正式工程或研究概念的内容升级为正式节点。
4. 合并多个临时记录中的有效目标、思路、数据和判读。
5. 删除纯重复、失效且未影响决策的临时表述。
6. 对曾影响路线的旧方案保留因果关系，标记为 `superseded（已被取代）` 或 `no-go（已否决）`，并关联替代节点。

不要把“改了表述”“合并了笔记”本身写成流水账。日志要保存项目认知如何变化，而不是文字编辑过程。

### 5. 同步 Git 历史

读取 `references/git-backfill.md`。先预览：

```powershell
python scripts/project_log.py --project-root <项目根目录> backfill --dry-run
```

已接入项目日常使用：

```powershell
python scripts/project_log.py --project-root <项目根目录> sync --dry-run
```

确认范围后再执行。可用 `--ref <引用>` 限定 Git 引用。人工日志优先；Git 只补可确认事实，不能补写当时没有留下证据的思路、数据解释或学术结论。

### 6. 月结归档

归档前完成 active 语义收口和审计，然后运行：

```powershell
python scripts/project_log.py --project-root <项目根目录> rollover
```

可用 `--new-month YYYY-MM` 指定新月份。归档应将完整 active 原子移动到 `.log/archive/YYYY-MM.md`，再创建新的 `active.md`；不要复制后留下两个活跃副本。

### 7. 审计

运行：

```powershell
python scripts/project_log.py --project-root <项目根目录> audit
```

至少检查：

- 结构、Schema 和模板是否一致。
- 日期、节点 ID、类型和证据状态是否合法。
- Git commit 关联是否重复或遗漏。
- active 是否残留无解释的 `方案1`、`方法A` 等临时命名。
- 归档是否被静默改写。
- 托管提示词是否漂移或损坏。
- `.log/**/*.md` 是否被 Git 忽略。
- 是否存在占位符、敏感信息模式或明显的完成声明越界。

## 节点边界

一个节点表示一次可独立复核的工程或认知状态转移：从问题、目标或假设开始，以证据支持的结果、决策或边界结束。

以下情况通常拆成不同节点：

- 从实现进入实验，从实验进入根因诊断，从诊断进入裁决。
- 定向验证升级为全量、真实数据或更高等级验证。
- `provisional（暂定）` 变为 `verified（已验证）`、`no-go（已否决）` 或 `superseded（已被取代）`。
- 出现值得独立保留的负结果、反证或根因发现。
- 两部分工作成功标准不同，或一部分已验证而另一部分仍是假设。

以下情况通常合并在主节点中：

- 同一功能产生多个 commit 或修改多个文件。
- RED、GREEN、回归属于同一个实现切片。
- README、索引、AGENTS.md、CLAUDE.md 随功能同步。
- 没有改变设计、证据或结论的临时编译修正。

## 内容优先级

优先保存：

```text
目标或问题
→ 背景与基线
→ 思路或假设
→ 方法或实现
→ 修改正文
→ 数据与证据
→ 结果
→ 判读与决策
→ 边界、no-go 或重开条件
```

`修改正文` 保存内容本体（论文定稿文字、代码核心逻辑/含义），使命中日志脱离原项目也能梳理核心变化；短则全文、长则主体概述 + 细节原文指针。文件列表、commit、命令和文档同步只是关联证据，应简要记录。普通文档同步不单独建节点；只有它改变工程合同、验证策略、架构语义、论文 claim 或复现路径时，才使用 `docs（文档契约）` 节点。

## 安全与最小修改

- 默认先 dry-run，再写入。
- 保留原文件编码、BOM、换行和托管块外内容。
- 不删除已有人工历史；冲突时输出报告并等待裁决。
- 不改写已归档的历史因果；使用修正、关联和 `superseded（已被取代）`。
- 不自动安装依赖；脚本只依赖 Python 标准库和 Git。
- 不把未提交工作推断成已完成节点。
- 只修改 `.log/`、根级提示词托管块，以及为跟踪 Markdown 所必需的最小 `.gitignore` 例外。

## 完成交付

说明：

- 创建、迁移、补录或更新了哪些日志。
- 采用了哪些证据来源，哪些信息无法恢复。
- 提示词注入和 Git 跟踪是否通过幂等检查。
- audit 结果及仍需人工裁决的冲突。
- 未验证、未补录或因 shallow clone 等原因不完整的范围。
