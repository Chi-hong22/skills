# 项目提示词注入规则

`project-log` 向仓库根级 `AGENTS.md` 和 `CLAUDE.md` 注入同源、平台中立的最小提示块，使没有主动触发 Skill 的 Agent 也能发现项目日志合同。

## 1. 权威关系

优先级如下：

1. `project-log` Skill 内部 `references/log-contract.md`。
2. 项目 `.log/README.md` 附属合同。
3. `AGENTS.md` / `CLAUDE.md` 中的发现和操作提示块。

提示块不能复制完整合同，也不能引入与 Skill 冲突的另一套字段或路径。

## 2. 托管标记

使用固定标记：

```markdown
<!-- project-log:begin schema={{SCHEMA_VERSION}} -->
...
<!-- project-log:end -->
```

只允许修改两个标记之间的内容。第二次使用同一 Skill 版本执行注入时，必须产生零 diff。

## 3. 注入内容

提示块至少表达：

- 项目采用根目录 `.log/` 体系。
- Skill 内部合同优先，`.log/README.md` 是项目侧附属合同。
- 实际工程或研究状态转移形成后更新 `.log/active.md`。
- 思路、数据、判读和边界优先，commit/文件/文档同步克制。
- 仅追溯历史时读取 `.log/archive/`。
- 应使用 `project-log` Skill；Skill 不可用时按 `.log/README.md` 降级执行。
- 不将运行日志、telemetry、debug 输出、原始实验结果或敏感信息写入项目日志。
- 复杂迁移、批量补录或冲突任务由主 Agent 规划和复核，可将不重叠的机械工作委派给子 Agents。

使用 `assets/prompt-block.md.tpl` 作为唯一模板来源，确保两种 Agent 文件内容一致。

## 4. 文件处理

- 默认只处理仓库根级 `AGENTS.md` 和 `CLAUDE.md`。
- 文件缺失时创建只含托管块的最小文件。
- 文件存在时保留托管块外原文、编码、BOM、换行和末尾换行习惯。
- 嵌套目录中的 `AGENTS.md` 或 `CLAUDE.md` 只报告，不自动注入。
- 不改写项目已有的语言、框架、测试、编码、提交或其他工作流规则。

## 5. 冲突处理

发现以下情况时停止注入，不产生部分写入：

- 只有 begin 或 end 的残缺标记。
- 多个重复托管块。
- 托管块嵌套。
- 项目已有规则要求另一日志路径、格式或互斥工作流。
- 文件编码无法安全保留。

对普通的旧日志提示词，先输出冲突位置和建议迁移映射。只有能够明确判定为同一职责的操作性规则，才在用户确认或 setup 接管范围内定点替换；不要全局修改历史文档中的旧路径。

## 6. `.gitignore` 配合

目录名 `.log` 可能被 `*.log` 规则整体忽略。注入前后检查：

```powershell
git check-ignore -v .log/README.md .log/active.md
```

若被忽略，只添加允许跟踪 Markdown 合同和日志所需的最小例外，不放开真正的运行时 `*.log` 文件。修改前先展示拟议规则，并保持项目原有忽略意图。

## 7. 验证

注入后验证：

1. 两个文件各有且仅有一个完整托管块。
2. 两个托管块除必要上下文外内容一致。
3. 再运行一次注入产生零 diff。
4. 托管块外文本哈希或逐字比较不变。
5. `.log/README.md` 和 `.log/active.md` 可被 Git 跟踪。
6. 项目已有非日志规则未改变。
