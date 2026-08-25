# Agent Image Protocol v0.1 — Codex Handoff

请按以下顺序阅读：

1. `00_CONTEXT_FOR_CODEX.md` — 继承项目语境、概念谱系、已否决方向和工程偏好
2. `01_REQUIREMENTS_PRD.md` — 明确做什么 / 不做什么
3. `02_ENGINEERING_DESIGN.md` — 实现边界与模块结构
4. `03_ACCEPTANCE_CRITERIA.md` — 什么才算真正完成

优先级：

`用户最新明确指令 > 验收文档 > 工程文档 > PRD > 历史语境`

执行纪律：

- 先做 repository reconnaissance，再定 vHarness mapping。
- 协议核心不得依赖任意一个 harness 的内部数据结构。
- 首发优先：Spec → Core CLI → Hermes → OpenClaw → Hermes→OpenClaw P2 → DSH → vHarness → trained-agent demo → registry。
- 每个 phase 先写 acceptance tests。
- demo 验证后不要把 demo 补成正式架构；提取已验证知识，再按正式模块重建。
- privacy/secret 默认 fail closed。
- 状态迁移必须保留 provenance，并显式报告 preserved / transformed / redacted / unsupported / lost。
- 不要把“能打包/恢复文件”误报成“已证明技能可移植”；行为级结论必须用 fresh-restore evaluation 证明。
