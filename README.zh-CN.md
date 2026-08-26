# Open Agent Image Protocol

[英文](README.md) | [简体中文](README.zh-CN.md)

> **模型有检查点，Agent 也需要镜像。**

> **我们没有训练模型，我们训练的是 Agent。**
>
> **不要只交付提示词，要交付 Agent 成长后的状态。**

Agent Image 是一个与 harness 无关、可检查的可移植检查点，用来保存一个经过发展的
Agent 已经成长为什么：运行时引用、身份、技能、记忆、经历、发展来源、评估、谱系、
隐私元数据，以及具有明确类型的原生状态。它不是提示词集合、技能包、模型检查点，
也不是换了名字的 profile 备份。

本仓库目前是 **v0.1 实验性 RC 候选版本**。它包含协议、schema、确定性的 `.aimg`
容器、隐私优先的验证机制，以及四个正式 adapter：Hermes Agent、OpenClaw、DSH 和
vHarness 的 P1 路径已在 Windows 上通过验证，Hermes 还在本机 WSL Linux 上通过了
验证；此外还包括 Hermes 到 OpenClaw 的 P2 语义迁移。一个独立的 clean-room
第五 adapter 证明：第三方可以通过公开入口完成注册，而无需修改 Core。本项目不作
P3 声明。

首个可公开且不包含私人状态的发展后 Agent 制品已经准备为 RC 发布制品：
`procurement-negotiator-v1.aimg`。它在全新 Hermes 环境恢复后，对 24 个新的合成决策
场景取得 `1.000000` 分；同一模型在没有实践状态时得分为 `0.481521`。公开仓库和
release URL 目前尚不存在；在获得明确发布授权之前，这组制品仍只保留在本地。

## 试用经过发展的 Agent

将以下三个 RC 制品放在同一目录中：

- `open_agent_image-0.1.0rc1-py3-none-any.whl`
- `procurement-negotiator-v1.aimg`
- `v0.1.0-rc.1.sha256`

请先确保 Hermes Agent `0.20.5` 可以通过 `hermes` 命令调用。Windows 上的最短路径是：

```powershell
python -m venv .hero-venv
.\.hero-venv\Scripts\python.exe -m pip install .\open_agent_image-0.1.0rc1-py3-none-any.whl

Get-FileHash .\procurement-negotiator-v1.aimg -Algorithm SHA256
.\.hero-venv\Scripts\agent-image.exe verify .\procurement-negotiator-v1.aimg
.\.hero-venv\Scripts\agent-image.exe inspect .\procurement-negotiator-v1.aimg

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
保密。这是 developed-state restore 的合成演示，不构成真实采购建议。Bash 命令、
准确的制品标识，以及公开衍生版本中移除了哪些内容，请参阅
[hero 使用指南](examples/procurement-negotiator/README.md)。

## 开发协议

创建可复现的开发环境，并验证安装后的 CLI：

```powershell
uv sync --locked --extra dev
uv run agent-image --help
uv run pytest
```

仓库提供标准 wheel 和源码分发包；release smoke test 会把 wheel 安装到一个
全新的虚拟环境中，且不设置 `PYTHONPATH`。

第一次真实 round-trip 使用一个具名 Hermes profile，并恢复到一个新的目标名称：

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

该 adapter 会调用 Hermes 官方的 profile export/import 命令，再执行一次 Agent Image
secret 检查，将安全的快照保存为带类型的原生状态，验证恢复后的文件不变量，并要求
Hermes 识别新的 profile。export 前后都会对源 profile 计算 hash。

私有 build 可以包含 `private` 数据项，但绝不能包含 `secret` 数据项。公开 image 通过
`redact --policy public` 创建为新的制品，不会修改源 image。未知数据默认是
private；secret 检测遵循 fail closed；不受支持的状态必须出现在操作报告中。
`inspect` 会列出每个 layer 的隐私类别、路径、大小和 digest，但不会打印数据内容。

第一条跨 harness 路径默认先执行试运行（dry run）：

```powershell
agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration-plan.json

agent-image migrate researcher.aimg `
  --to openclaw:researcher-migrated `
  --yes `
  --openclaw-binary C:\path\to\openclaw.cmd `
  --openclaw-node-binary C:\path\to\node.exe `
  --report migration.json
```

只有兼容的身份、选定记忆和技能会迁移。Hermes 原生数据库和会话状态会保留在源
image 中，并带有明确的损失状态；目标 provenance 会回指源 image digest。

第三方 adapter 通过公开的 `agent_image.adapters` entry-point group 注册。
`agent-image adapters list --json` 会报告内置及已安装 adapter 的声明，但不会把
“已经安装”误当成“已经完成运行时验证”。参阅[第三方 adapter contract](docs/adapters/THIRD_PARTY.md)
和 [clean-room package](examples/clean_room_adapter/README.md)。

静态、隐私感知的 Registry 可以在本地验证：

```powershell
agent-image registry validate registry/v0.1/index.json --json
```

Registry 的前六条记录有意使用 `withheld://`，因为对应 evidence artifact 是私有的。
第七条记录可以安全公开，但在真实 release asset URL 出现之前仍使用 `withheld://`。
Registry 元数据不会让私有状态变得可发布，也不会假装本地候选版本已经可以下载。

## 当前边界

- 当前已实现：规范/schema；`build`、`inspect`、`verify`、`redact`、`diff`、
  `restore` 和默认试运行的 `migrate`；确定性打包；归档安全；secret 检查；
  锁定版本的 Hermes、OpenClaw、DSH 和限定范围的 vHarness P1；具有 provenance 和
  完整损失报告的 Hermes 到 OpenClaw P2；通过 clean-room 第五 adapter 验证的
  公开 `agent_image.adapters` 发现机制；静态 Registry 及其 validator；Windows/Linux
  Hermes smoke automation 和安全加固 evidence；以及预注册、同模型的 Gate E 结果，
  证明任务特定的实践状态在全新 Hermes P1 restore 后得到保留。此外还有一个可公开
  的 hero 衍生版本：它在新合成场景中全新恢复后得分为 `1.0`，而同模型 fresh
  control 得分为 `0.481521`。
- 尚未实现：OCI transport 和 P3 behavioral portability。Gate E 只支持范围明确的
  同 harness 合成任务声明；它不能证明真实谈判表现或跨 harness 行为等价。

进一步资料包括：[capability matrix](docs/CAPABILITY_MATRIX.md)、
[项目状态](docs/PROJECT_STATUS.md)、
[Hermes P1 evidence](docs/evidence/hermes-p1-v0.20.5.md)、
[OpenClaw P1 evidence](docs/evidence/openclaw-p1-v2026.7.1-2.md)、
[Hermes 到 OpenClaw P2 evidence](docs/evidence/hermes-to-openclaw-p2-2026-08-25.md)、
[DSH P1 evidence](docs/evidence/dsh-p1-v0.1.0-rc.6.md)、
[vHarness P1 evidence](docs/evidence/vharness-p1-v0.1.0-alpha.1.md)、
[第五 adapter evidence](docs/evidence/clean-room-fifth-adapter-2026-08-25.md)、
[trained-agent Gate E evidence](docs/evidence/situated-negotiation-gate-e-positive-2026-08-25.md)、
[public hero restore evidence](docs/evidence/public-hero-restore-comparison-2026-08-26.md)、
[public hero operator-path evidence](docs/evidence/public-hero-operator-path-2026-08-26.md)、
[安全矩阵](docs/evidence/security-hardening-matrix-2026-08-25.md)、
[已知限制](docs/LIMITATIONS.md)、[最终复核](docs/releases/FINAL_REVIEW.md)、
[上下文继承](docs/CONTEXT_INHERITANCE.md)、[v0.1 规范](spec/v0.1/SPEC.md)、
[ADR-0001](docs/adr/0001-protocol-root-and-bootstrap.md)，以及归档的
[context pack](docs/source/context-pack/README_CODEX_HANDOFF.md)。
