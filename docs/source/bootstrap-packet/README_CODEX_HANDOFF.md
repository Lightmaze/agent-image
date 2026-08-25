# Agent Image Protocol v0.1 — Codex Handoff

建议本地 Codex 按以下顺序读取：

1. `01_REQUIREMENTS_PRD.md`
2. `02_ENGINEERING_DESIGN.md`
3. `03_ACCEPTANCE_CRITERIA.md`

执行原则：

- 先做 repository reconnaissance，再定 vHarness mapping。
- 协议核心不得依赖任意一个 harness 的内部数据结构。
- 首发优先顺序：Spec → Core CLI → Hermes → OpenClaw → Hermes→OpenClaw P2 → DSH → vHarness → trained-agent demo → registry。
- 每个 phase 先写验收测试。
- demo 验证后不要把 demo 直接补成正式架构；按正式模块重新实现。
- privacy/secret 默认 fail closed。
