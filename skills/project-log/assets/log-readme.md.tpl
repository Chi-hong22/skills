# {{PROJECT_NAME}} 项目日志

<!-- project-log:managed schema={{SCHEMA_VERSION}} -->

本目录由 `project-log` Skill 管理，用于记录可独立复核的工程或项目认知状态转移。

> 权威说明：Skill 内部 `references/log-contract.md` 是首要合同；本文是项目侧附属合同，供未安装 Skill 的 Agent 和人离线执行。

## 结构

- `active.md`：{{CURRENT_MONTH}} 当前活跃日志，日常唯一写入点。
- `archive/YYYY-MM.md`：已关闭月份，默认冻结，只在追溯历史时读取。

## 节点原则

一个节点从问题、目标或假设开始，以证据支持的结果、决策或边界结束。优先记录：

```text
目标 → 背景 → 思路 → 方法 → 数据与证据 → 结果 → 判读 → 边界
```

不要按 commit、文件、Agent 会话或普通文档同步机械拆节点。

## 类型

`implementation（功能实现）`、`bug（缺陷修复）`、`experiment（实验）`、`tuning（参数调优）`、`decision（决策）`、`no-go（否决）`、`docs（文档契约）`、`maintenance（工程维护）`、`release（发布）`。

## 证据状态

`provisional（暂定）`、`verified（已验证）`、`no-go（已否决）`、`superseded（已被取代）`、`git-backfill（Git 历史补录）`。

## 临时表述

`方案1`、`方法A` 等工作名只能暂存于 active。稳定前改为正式名称，合并有效思路、数据和判读，删除纯重复或失效文字；曾影响路线的旧方案用 `superseded（已被取代）` 或 `no-go（已否决）` 保留因果关系。

## 内容边界

- 思路、数据、判读、限制和负结果优先。
- `修改正文` 保存内容本体：≤10 行写全文，>10 行写主体概述 + 细节原文指针；`docs（文档契约）` 与 `implementation（功能实现）` 节点必填。
- 文件、commit、测试命令和普通文档更新只作简要关联。
- Git 补录不得编造未留下证据的思路或学术结论。
- 不记录应用运行日志、telemetry、debug 输出、原始实验产物或敏感信息。

## 归档索引

<!-- project-log:archive-index:begin -->
暂无归档。
<!-- project-log:archive-index:end -->

## 历史来源映射

旧日志接管和 Git 补录应在这里登记来源、覆盖范围、完整 commit hash 覆盖键、处理状态及原文保留位置。完整 hash 优先用于去重；只有标题或日期相似时不得声称已覆盖。

<!-- project-log:source-map:begin -->
暂无旧日志来源。
<!-- project-log:source-map:end -->
