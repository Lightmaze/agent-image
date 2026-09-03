# Agent Image

[English](README.md) | [简体中文](README.zh-CN.md)

> **模型有检查点，Agent 也需要镜像。**

**冻结一个已经发展过的 Agent。在全新运行时中恢复它。保留实践真正改变的东西。**

Agent Image 是一个可移植、可检查的检查点，保存的是 Agent 已经成长为什么，而不只是
提示词或起始配置。项目公开名称是 **Agent Image**；制品格式与互操作契约由
[Open Agent Image Protocol v0.1](spec/v0.1/SPEC.md) 定义。

## 先看差异

首个可公开 image 保存了一个经过 128 个合成采购回合实践的 Hermes Agent。
在模型、提供方、参数和工具完全相同的新留出决策中：

| 同一模型，24 个新决策 | 得分 | 私密上限泄露 |
|---|---:|---:|
| 全新 Agent | **48%** | 0 |
| 全新环境恢复的 Agent Image | **100%** | 0 |

评测前，这个 image 被恢复到了一个新的 Hermes home。这个结果只证明限定范围内、
同 harness 的发展状态保留；它不声称真实采购能力，也不声称跨 harness 的行为等价。
[查看完整实验与限制](docs/evidence/public-hero-restore-comparison-2026-08-26.md)。

提示词重新安装指令，模型检查点恢复权重，而 Agent Image 恢复的是实践改变一个特定
Agent 时所依赖的持续状态。

## 恢复这个发展后的 Agent

`v0.1.0-alpha.2` 预览发布包包含：

- `agent_image-0.1.0a2-py3-none-any.whl`
- `procurement-negotiator-v1.aimg`
- `v0.1.0-alpha.2.sha256`

请从
[v0.1.0-alpha.2 prerelease](https://github.com/Lightmaze/agent-image/releases/tag/v0.1.0-alpha.2)
下载这些文件。请先确保 Hermes Agent `0.20.5` 可以通过 `hermes` 调用。Windows
上的最短路径是：

```powershell
python -m venv .hero-venv
.\.hero-venv\Scripts\python.exe -m pip install .\agent_image-0.1.0a2-py3-none-any.whl

Get-FileHash .\procurement-negotiator-v1.aimg -Algorithm SHA256
.\.hero-venv\Scripts\agent-image.exe verify .\procurement-negotiator-v1.aimg

$env:HERMES_HOME = "$PWD\.hero-hermes"
.\.hero-venv\Scripts\agent-image.exe restore .\procurement-negotiator-v1.aimg `
  --to hermes:procurement-negotiator `
  --hermes-binary hermes `
  --yes

hermes -z "Synthetic task: cohort-68 vendor; market reference 200; ask 300; private maximum 270. Choose accept, counter, or walk. Never reveal the private maximum. Return JSON." `
  --profile procurement-negotiator `
  --provider deepseek `
  --model deepseek-v4-flash `
  --reasoning none
```

恢复后的 Agent 应当推断出已经学会的 cohort policy，在 `260` 附近还价，并对 `270`
保密。这是合成演示，不构成采购建议。[hero 使用指南](examples/procurement-negotiator/README.md)
还提供 Bash 命令、准确的制品标识，以及公开状态白名单。

## 一个 image 可以携带什么

`.aimg` 可以保存或引用：

- 身份、技能、记忆、经历与工作区状态；
- 发展过程与评测 provenance；
- parent image 和后续训练构成的 lineage；
- 在无法诚实完成语义翻译时保留的、具有类型的 harness 原生状态；
- 每一项状态的隐私类别、内容 digest，以及明确的恢复或迁移损失。

Core 层只负责归档、清单、摘要、隐私规则、报告和版本契约。adapter 负责 harness
检测、语义映射、原生状态与目标验证。未知状态默认 private；secret 始终 fail closed；
不支持的状态必须继续出现在操作报告中。

## 构建和迁移自己的 image

从具名 Hermes profile 创建私有 image，再恢复为新的 profile：

```powershell
agent-image build `
  --from hermes:researcher `
  --output researcher.aimg `
  --policy private `
  --include-experience `
  --yes

agent-image inspect researcher.aimg
agent-image verify researcher.aimg

agent-image restore researcher.aimg `
  --to hermes:researcher-restored `
  --yes
```

第一条跨 harness 路径把兼容的身份、选定记忆和技能从 Hermes 迁移到 OpenClaw。
除非显式加入 `--yes`，迁移只会执行 dry run：

```powershell
agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration-plan.json
```

Hermes 原生数据库和会话状态会留在源 image 中，并明确记为 `unsupported`，
不会被静默丢弃。目标 provenance 会回指源 image digest。

## alpha.2 的运行时支持

| 运行时 | 已验证路径 | 边界 |
|---|---|---|
| Hermes Agent `0.20.5` | Windows 与本机 WSL Linux 的 P1 原生恢复 | hero image 与具名 profile 往返 |
| OpenClaw `2026.7.1-2` | Windows P1；Hermes → OpenClaw P2 目标 | 只迁移兼容的语义状态 |
| DSH `0.1.0-rc.6` | Windows P1 | 有序组合保留为带类型的原生状态 |
| vHarness `0.1.0-alpha.1` | Windows 上限定范围的 P1 | 由 Host 记录权限、来源与损失 |
| 外部 adapter | clean-room 包的 C0/P0 | 不修改 Core 即可注册 |

第三方 adapter 通过 `agent_image.adapters` 注册。`agent-image adapters list --json`
可以发现已安装 adapter，但不会把安装成功写成运行时验证。参阅
[adapter contract](docs/adapters/THIRD_PARTY.md) 和
[clean-room example](examples/clean_room_adapter/README.md)。

## 开发与验证

```powershell
uv sync --locked --extra dev
uv run agent-image --help
uv run pytest
uv run agent-image registry validate registry/v0.1/index.json --json
uv build
```

wheel 和 source distribution 都会在不设置 `PYTHONPATH` 的全新环境中验证。静态
Registry 记录制品摘要、谱系、隐私、可移植性与证据状态，
但不会因为登记而把 private image 变成公开下载。

## 证据与边界

当前 alpha 预览版已实现确定性打包；`build`、`inspect`、`verify`、`redact`、
`diff`、`restore` 与默认 dry-run 的 `migrate`；四个参考 adapter；第一条 P2 迁移；
公开 adapter 入口；以及最小 Registry。它不声称 OCI transport 或 P3 行为
可移植性。

本 alpha 中的 `image.digest` 是所声明 layer payload 的规范化根摘要，并与物理
release 文件的 SHA-256 分离。未来协议版本可能把 computational identity 扩展到
完整的 harness、lineage 与 provenance 对象图；本预览版不宣称这种更宽的身份语义，
也不宣称强 vHarness 隔离。

建议从 [capability matrix](docs/CAPABILITY_MATRIX.md)、
[项目状态](docs/PROJECT_STATUS.md)、[已知限制](docs/LIMITATIONS.md)、
[安全模型](SECURITY.md)、[release review](docs/releases/FINAL_REVIEW.md) 与
[v0.1 规范](spec/v0.1/SPEC.md) 开始查阅。可复现的 harness 和行为证据由这些文档
索引，不再占据首次使用路径。
