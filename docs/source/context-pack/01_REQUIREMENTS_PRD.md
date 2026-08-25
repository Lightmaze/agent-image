# Agent Image Protocol v0.1 — 需求文档（PRD）

**状态**：Draft for Implementation  
**目标读者**：本地 Codex / 核心实现者 / 早期贡献者  
**首发窗口**：协议优先，目标在 2–4 周内形成可公开、可运行、可扩展的 v0.1  
**项目定位**：Open Agent Image Initiative 的第一批开源基础设施  
**首发支持对象**：Hermes Agent、OpenClaw、DeepSeek Harness（DSH）、vHarness

---

## 0. 一句话定义

**Agent Image 是“一个已经发展过的 Agent 的可移植检查点（portable checkpoint of a developed agent）”。**

它不是 prompt bundle，不是 skill pack，也不只是 harness profile 的压缩包。它要能够描述并携带：

1. Agent 的运行时依赖与身份配置；
2. 可发布的技能、记忆、经验与工作状态；
3. Agent 是如何发展到当前状态的 provenance；
4. 该状态的 lineage、评测与隐私边界；
5. 原生 harness 无法通用解释的 opaque/native layers；
6. 在相同 harness 上恢复，以及在不同 harness 之间做受控语义迁移的能力。

核心口号：

> **Models have checkpoints. Agents need images.**  
> **We didn't train the model. We trained the agent.**  
> **Don't ship only prompts. Ship what the agent has become.**

---

# 1. 背景与问题

当前 Agent 生态已经出现多个“持久 Agent”实现，但分发单位仍高度碎片化：

- Hermes 已支持 profile、skills、memory、sessions、state，以及 profile distribution / export；
- OpenClaw 已有 workspace、identity/bootstrap 文件、memory、skills，并支持从 Hermes / Codex / Claude Code 导入部分 memory；
- DSH 将运行时组织为 profile + ordered bundles + Cordis patches，几乎所有能力都是插件；
- vHarness 需要表达可切换、可冻结、可恢复的 harness/runtime 状态；
- 不同生态都在接近“whole agent distribution”，但缺少一个 harness-neutral 的“developed agent artifact”抽象。

现状的根本缺口不是“无法复制文件”，而是：

> **没有一个开放协议明确回答：一个 Agent 经过数小时、数天、数周训练/实践/生活以后，什么状态构成“它已经变成的样子”，这些状态如何被保存、审计、分享、恢复、继续训练与迁移。**

如果这个语义层不被尽快公开定义，各 harness 很可能分别形成不兼容的事实标准。

---

# 2. 产品目标

## G1. 抢占 Agent 分发协议的语义层

v0.1 必须公开定义以下概念：

- Agent Image
- Image Manifest
- Logical Layers
- Native/Opaque Layer
- Development Provenance
- Lineage
- Privacy/Redaction Policy
- Portability Level
- Adapter Contract

协议必须是 **harness-neutral**，不能把 vHarness 数据结构直接升格为标准。

---

## G2. 证明协议能覆盖真实、异构的 Agent harness

首发必须至少支持：

1. **Hermes Agent**
2. **OpenClaw**
3. **DeepSeek Harness（DSH）**
4. **vHarness**

“支持”在 v0.1 的最低定义是：

- 能探测本地 source；
- 能导出一个符合协议的 Agent Image；
- 能 inspect / verify；
- 能在原 harness 上 native restore 或明确标注为 archive-only；
- adapter 的 unsupported surface 必须被显式记录，不允许静默丢失。

---

## G3. 证明“发展状态”是一等对象

Agent Image 必须能够表达：

- base image / parent image；
- 训练或实践来源；
- habitat / training ground（如存在）；
- duration / episode count（如可获得）；
- before / after evaluation（如存在）；
- experience traces / session provenance；
- development notes；
- image lineage。

协议不能把这些信息降格成 README 自由文本。

---

## G4. 安全地分发，而不是简单 tar 全目录

v0.1 必须默认保护：

- API keys
- OAuth/token files
- `.env`
- credentials
- 明确标记的 secret layers
- 用户私人记忆
- conversation history
- 商业机密
- 本地绝对路径与机器身份信息（能清理时清理）

默认策略：

> **Private by default; publishing is an explicit action.**

---

## G5. 为社区 Registry 提供最小可聚合元数据

首发不要求搭建中心化服务。

只需：

- 一个 `awesome-agent-images` / registry GitHub 页面；
- 统一 submission metadata；
- registry 条目可链接任意 GitHub release/repo/object storage；
- 能显示 harness、base model、development method、license、privacy status、evaluation、lineage。

---

# 3. 非目标（v0.1 明确不做）

以下项目非常重要，但 **不得阻塞 v0.1**：

### NG1. 不要求跨 harness 100% 无损恢复

不要求：

`Hermes → Image → OpenClaw`

后行为逐 token 等价，也不要求原生 state DB 在另一 harness 可执行。

---

### NG2. 不做新的模型格式

Agent Image 不重新定义模型权重格式。

模型可以通过：

- URI
- registry reference
- local model identifier
- provider/model name
- optional digest

被引用。

---

### NG3. 不做云端 Agent Hub

v0.1 registry 是 GitHub-first 的聚合索引，不建设：

- 用户系统
- 付费市场
- 托管运行
- 中心化 image store
- recommendation engine

---

### NG4. 不做 Habitat 平台

协议允许记录：

```yaml
development:
  method: habitat
  habitat: negotiation-ground
```

但 v0.1 不要求实现通用 Habitat runtime。

---

### NG5. 不定义“什么训练方法是正确的”

Agent Image Protocol 只记录 development provenance，不规定：

- RL
- SFT
- context training
- Habitat training
- human coaching
- self-play

哪一种更优。

---

### NG6. 不把任何 harness 的私有格式强制标准化

无法通用解释的内容进入 typed opaque/native layer。

**宁可显式 opaque，不可错误归一化。**

---

# 4. 用户与核心使用场景

## Persona A：Agent 开发者

我有一个已经工作/训练数十小时的 Agent，希望：

1. freeze；
2. 查看它包含什么；
3. 去除私人状态；
4. 发布；
5. 让别人恢复或继续训练。

流程：

```text
source agent
  → agent-image build
  → inspect
  → redact/publish
  → verify
  → push to GitHub
```

---

## Persona B：Harness 作者

我希望自己的 harness 可以：

- export Agent Image；
- import Agent Image；
- 声明能够理解哪些 layer；
- 保留无法解释的 layer；
- 参加统一 registry。

---

## Persona C：Agent 使用者

我看到一个公开的 trained agent，希望：

```text
pull → inspect provenance → verify digest → restore → run
```

我需要知道：

- 它基于什么模型；
- 在什么环境训练；
- 是否包含用户私密记忆；
- 哪些 state 会在我的 harness 被丢弃；
- 评测是否可信；
- license 是什么。

---

## Persona D：研究者

我需要比较：

- untrained image
- trained image
- forked images
- different habitat outcomes

因此需要：

- lineage
- diff
- evaluation records
- reproducibility metadata

---

# 5. 核心对象模型

Agent Image v0.1 逻辑上定义为：

```text
AgentImage =
  Manifest
  + Runtime
  + Identity
  + Skills
  + Memory
  + Experience
  + Workspace
  + Development
  + Evaluation
  + Lineage
  + Native Layers
  + Privacy Metadata
```

不是所有 Image 都必须包含全部层。

---

# 6. Logical Layers

## L1. `runtime`

描述 Agent 依赖什么执行环境。

最少：

```yaml
runtime:
  harness:
    id: hermes
    version: "..."
  adapter:
    id: org.agentimage.hermes
    version: "0.1.0"
  model:
    provider: optional
    family: optional
    id: optional
    digest: optional
```

---

## L2. `identity`

Agent 的 role / soul / bootstrap / persona / behavioral configuration。

例：

- Hermes `SOUL.md`
- OpenClaw `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`
- DSH profile-level behavioral config
- vHarness activation / generation policy 等

要求：

- preserve original file where possible；
- semantic tags are metadata, not destructive conversion。

---

## L3. `skills`

可执行或解释性的技能资源：

- `SKILL.md`
- scripts
- tool skill metadata
- skill configs
- plugin-assisted skills

必须记录：

- source path
- media type
- digest
- portability (`portable | adapter-specific | opaque`)

---

## L4. `memory`

Agent 已形成的可持久知识与用户/环境记忆。

建议子类：

```text
semantic
episodic
user
procedural
imported
other
```

v0.1 不强求自动分类准确；adapter 可以标记 `unknown`。

---

## L5. `experience`

**与 memory 分离。**

用于保存“Agent 经历过什么”：

- sessions
- transcripts
- trajectories
- training episodes
- replay traces
- interaction logs

原则：

> Memory 是 Agent 对经验的持久表征；Experience 是经验本身或其可审计轨迹。

默认 privacy classification 必须高于普通 config。

---

## L6. `workspace`

Agent 在成长过程中依赖/产生的工作资产：

- notes
- plans
- code
- artifacts
- todo state
- knowledge base

默认不得无脑导出整个 home directory。

adapter 必须 allow-list 或要求用户显式 opt-in。

---

## L7. `development`

这是 Agent Image 相对 profile/export 的核心差异层。

最少 schema：

```yaml
development:
  method: habitat | self_play | human_coaching | rl | sft | mixed | unknown
  started_at: optional
  ended_at: optional
  duration_seconds: optional
  episodes: optional
  habitat:
    id: optional
    version: optional
    uri: optional
  notes: optional
  evidence:
    - path: optional
      digest: optional
      kind: session | eval | log | other
```

---

## L8. `evaluation`

允许：

```yaml
evaluation:
  suites:
    - id: negotiation-v0
      before:
        score: 0.45
      after:
        score: 0.62
      evidence: ...
```

要求：

- 不能把声明当作验证；
- 必须区分 `self_reported`, `reproduced`, `third_party`；
- registry UI/README 不能把 self-reported score 渲染成官方认证。

---

## L9. `lineage`

最少：

```yaml
lineage:
  parent:
    uri: ...
    digest: sha256:...
  base:
    uri: ...
    digest: ...
  fork_reason: optional
```

支持：

```text
base → trained → specialized → forked → retrained
```

v0.1 不要求 merge semantics。

---

## L10. `native`

无法标准化但必须保存的 harness-specific state。

示例：

```yaml
native:
  - harness: dsh
    media_type: application/vnd.deepseek.dsh-profile+tar
    path: layers/native/dsh-profile.tar
    digest: sha256:...
```

原则：

> Native layer 是协议的 escape hatch，不是失败。

---

# 7. Portability Levels

协议必须明确声明 image / import / restore 的可移植等级。

## P0 — Archive

- 可保存、inspect、verify；
- 不承诺可执行恢复。

## P1 — Native Restore

```text
Harness A → Image → Harness A
```

核心状态恢复成功。

**v0.1 的四个首发 adapter 目标至少达到 P1，若某 harness 因公开接口限制无法 P1，必须明确标为 P0 且给出 blocker。**

## P2 — Semantic Migration

```text
Harness A → Image → Harness B
```

可迁移：

- identity
- portable skills
- selected memory
- selected workspace

允许丢弃：

- runtime DB
- internal caches
- harness-native plugin state

必须给 migration report。

## P3 — Behavioral Portability

跨 harness 后，通过指定 benchmark 验证行为能力接近源 Agent。

**P3 明确不是 v0.1 发布阻塞项。**

---

# 8. Adapter Requirements

每个 adapter 必须实现统一 contract：

```text
detect()
inspect_source()
export()
validate_export()
restore_native()
migrate_semantic()
report_capabilities()
```

允许 `migrate_semantic()` 返回 unsupported，但不得 silent no-op。

每个 adapter 必须输出 capability matrix：

```yaml
capabilities:
  archive: true
  native_restore: true
  semantic_migration:
    identity: true
    skills: true
    memory: partial
    experience: false
```

---

# 9. 首发 Adapter 特定需求

## 9.1 Hermes

当前 Hermes 的 profile export 能包含 config、SOUL、MEMORY、USER、skills、plugins、cron、scripts、sessions、memories、knowledge、preferences 等；named profile 甚至可能包含 `state.db`、logs、caches。credentials 文件名会被过滤，但内容不会自动做隐私审查。

v0.1 Hermes adapter：

### MUST
- 识别默认 profile 与 named profile；
- 尽可能复用 Hermes 官方 export，而非复制私有实现；
- 将：
  - SOUL/config → identity/runtime
  - skills → skills
  - MEMORY/USER/memories/knowledge/preferences → memory
  - sessions → experience
  - state DB/unknown profile state → native
- 默认剔除 `auth.json`, `.env`；
- 对 `USER.md`, sessions, memories 标记 private/high-risk；
- native restore 能重建一个新的 Hermes profile；
- 不覆盖现有 profile，除非显式 `--force`。

### SHOULD
- 支持 profile distribution metadata 作为 provenance；
- 保留 distribution version/source URI。

---

## 9.2 OpenClaw

OpenClaw 的 Agent 状态以 workspace、bootstrap files、memory、skills 和运行时配置为核心；其现有工具已能导入 Hermes/Codex/Claude Code 的部分 Markdown memory。

v0.1 OpenClaw adapter：

### MUST
- 探测 agent workspace；
- 识别常见 bootstrap/identity 文件；
- 识别 workspace memory 与 imported memory；
- 识别 skills；
- identity / memory / skills 分层导出；
- native restore 到新的 agent/workspace；
- 对 secrets/credentials/config 中敏感字段使用 deny-list + allow-list；
- 不把整个 OpenClaw home 无条件打包。

### SHOULD
- 支持从 Agent Image semantic import 到 OpenClaw；
- 至少完成一条 Hermes → Agent Image → OpenClaw 的 P2 demo：
  - identity 部分迁移
  - SKILL.md-compatible skills 迁移
  - selected memory 迁移
- 生成 migration report。

---

## 9.3 DSH

DSH 是 developer preview，架构快速变化。其 profile 是 `$DSH_HOME/profiles/<name>` 下的可运行 composition，`dsh.profile` 指定 ordered bundles；bundle 是带 `dsh.bundle` manifest 的配置 patch layer。整个运行时由 Cordis 插件树组合。

v0.1 DSH adapter：

### MUST
- 不把 DSH 当前内部结构硬编码进协议核心；
- source detect 支持 profile；
- 导出：
  - profile manifest
  - ordered bundle list
  - profile `cordis.patch.yml`
  - out-of-tree plugin dependency metadata
- 将完整 profile composition 作为 typed native layer 保留；
- 记录 DSH version；
- restore 到新 profile name；
- 如果 bundle 不可解析/不可下载，restore 必须 fail loud；
- DSH breaking-change 风险写入 adapter metadata。

### SHOULD
- 运行 `--dump-config`（如环境允许）保存 resolved composition snapshot，用于审计但不作为唯一恢复源。

---

## 9.4 vHarness

vHarness adapter 是首发一等公民，但协议不得为其定制。

### MUST
- 本地 Codex 先检查当前 vHarness 仓库实际状态模型；
- 编写 `docs/vharness-mapping.md`；
- 显式映射：
  - harness/runtime config
  - model routing
  - skills
  - session/context state
  - memory
  - tool/plugin state
  - secrets
- 未确认的数据结构不得凭空发明；
- 需要的 opaque state 使用 native layer。

### SHOULD
- 成为协议功能最完整的 reference adapter；
- 至少 P1；
- 若已有 Harness Image / Pulse Image 概念，保留兼容迁移说明，而不是粗暴替换旧格式。

---

# 10. CLI 需求

binary 名称暂定：

```bash
agent-image
```

最低命令：

```bash
agent-image build
agent-image inspect
agent-image verify
agent-image restore
agent-image migrate
agent-image diff
agent-image redact
```

示例：

```bash
agent-image build --from hermes:research-bot -o research-bot.aimg
agent-image inspect research-bot.aimg
agent-image verify research-bot.aimg
agent-image restore research-bot.aimg --to hermes:new-research-bot
agent-image migrate research-bot.aimg --to openclaw:new-agent
agent-image diff base.aimg trained.aimg
agent-image redact private.aimg --policy public -o public.aimg
```

v0.1 不要求 `push/pull` registry client。

---

# 11. Image Container 需求

v0.1 可以采用简单、可审计的 tar/zip 结构，不必一开始依赖 OCI。

建议扩展名：

```text
.aimg
```

内部：

```text
manifest.yaml
index.json
layers/
  identity/
  skills/
  memory/
  experience/
  workspace/
  development/
  evaluation/
  native/
meta/
  checksums.txt
  migration-report.json
  redaction-report.json
```

要求：

- deterministic packing（在相同输入与 metadata policy 下尽可能稳定）；
- 每个 layer 有 digest；
- manifest 有整体 digest 或可生成 content digest；
- 禁止 path traversal；
- restore 时必须解包到 staging dir，验证后再移动。

---

# 12. Security / Privacy Requirements

## S1. Secret deny rules

默认必须拒绝打包至少：

```text
.env
auth.json
credentials*
*token*
*.pem
*.key
id_rsa
id_ed25519
```

注意：文件名过滤不够；已知 config 中的 token/key 字段也要支持 scrub。

---

## S2. Privacy classes

每个 layer/item：

```text
public
private
secret
unknown
```

默认：

- sessions → private
- USER/profile memory → private
- auth → secret
- unknown → private

发布模式不允许包含 `secret`，`unknown/private` 需明确 override。

---

## S3. Public build

必须支持：

```bash
agent-image redact IMAGE --policy public
```

并输出 report：

- removed items
- transformed items
- unresolved risks

---

## S4. No silent loss

导出/迁移/恢复任何无法处理的 state：

- `preserved`
- `redacted`
- `unsupported`
- `dropped_by_user`

四选一并写 report。

禁止“没报错但文件没了”。

---

# 13. Registry 需求

首发为 GitHub 仓库/页面即可。

每条至少：

```yaml
name:
description:
image_uri:
image_digest:
source_harness:
target_harnesses:
base_model:
development_method:
development_duration:
evaluation:
privacy:
license:
author:
lineage:
```

Submission 必须声明：

- 是否包含用户数据；
- 是否含原始 sessions；
- 是否已 redacted；
- 是否可以商业使用；
- image 是否可被复现或只是 snapshot。

---

# 14. 版本与兼容

协议使用：

```text
agent-image/v0.1
```

v0.x：

- 允许破坏性修改；
- 必须提供 migration notes；
- adapter 与 spec 分开 version；
- image manifest 必须声明 spec version；
- loader 遇到未知 major/minor 必须 fail or warn according to compatibility table，不可猜测。

---

# 15. 成功指标

v0.1 首发成功不是“功能最多”，而是同时满足：

1. 协议 repo 可读、概念边界清楚；
2. 四个 harness 都有真实 adapter；
3. 至少三个 adapter 达 P1；
4. 至少一条 P2 semantic migration demo；
5. image 可 inspect / verify / diff / redact；
6. privacy 默认安全；
7. 有一个 before → train/practice → freeze → restore → after demo；
8. registry 接受第三方 trained Agent；
9. 文档让第三方在不修改 core 的情况下实现第五个 adapter。

---

# 16. 首发演示建议

## Demo A — Same Harness Native Restore

```text
Hermes Agent
→ build Agent Image
→ delete/isolated environment
→ restore to new Hermes profile
→ verify identity/skills/memory/native state
```

## Demo B — Cross Harness Semantic Migration

```text
Hermes
→ Agent Image
→ OpenClaw
```

迁移：

- identity
- portable skills
- selected memory

明确展示哪些东西没迁。

## Demo C — Trained Agent

```text
base agent
→ training ground / repeated practice
→ measured improvement
→ freeze as Agent Image
→ restore on fresh runtime
→ measured capability retained
```

**Demo C 是协议叙事最重要的证明。**

---

# 17. 发布边界

## v0.1 必须发布

- Spec
- JSON Schema / YAML example
- CLI
- Hermes adapter
- OpenClaw adapter
- DSH adapter
- vHarness adapter
- Native restore tests
- one semantic migration
- privacy/redaction
- registry template
- examples

## v0.1 可以延期

- hosted registry
- OCI backend
- remote push/pull
- signature infrastructure beyond checksum
- P3 behavioral portability framework
- team images
- vHabitat packaging
- incremental/delta images
- merge semantics
- encrypted private layers
- cloud secrets injection
- GUI

---

# 18. 最终产品边界声明

Agent Image Protocol 不是：

- “把整个 home 目录压缩”
- “把 system prompt 换一个后缀”
- “另一个 Agent framework”
- “vHarness 私有镜像”
- “替代 Hermes/OpenClaw/DSH”

它是：

> **位于 Agent harness 之上的开放制品协议，用来保存、分发、审计和继续一个 Agent 已经形成的发展状态。**

首发的战略判断是：

> **让 Hermes、OpenClaw、DSH、vHarness 成为同一个协议的 producer/consumer，而不是为每个生态再造一个互不兼容的 image 概念。**
