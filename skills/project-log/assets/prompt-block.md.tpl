<!-- project-log:begin schema={{SCHEMA_VERSION}} -->
## Project Log

本项目采用仓库根目录 `.log/` 维护统一项目推进日志。`project-log` Skill 内部合同是首要规则，`.log/README.md` 是项目侧附属合同。

当任务形成可独立复核的工程或项目认知状态转移，并完成适当验证或明确未验证原因时：

1. 优先使用 `project-log` Skill，将节点写入 `.log/active.md`。
2. 优先记录目标、思路、数据与证据、判读和结论边界，以及修改正文（内容本体：≤10 行写全文，>10 行写概述 + 细节原文指针）。
3. commit、文件清单、测试命令和普通文档同步应简要克制。
4. 只在追溯历史时读取 `.log/archive/`。
5. Skill 不可用时，直接遵循 `.log/README.md`。

复杂迁移、批量补录或冲突任务由主 Agent 负责规划、证据边界和最终复核，可将文件范围不重叠的机械工作委派给子 Agents。

不要将应用运行日志、telemetry、debug 输出、原始实验产物、纯计划或敏感信息写入项目日志。
<!-- project-log:end -->
