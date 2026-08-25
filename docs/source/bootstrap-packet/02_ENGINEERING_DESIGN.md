# Agent Image Protocol v0.1 — 工程设计文档

**状态**：Implementation Design  
**目标读者**：本地 Codex / Maintainers  
**原则**：先完成开放协议与可验证闭环，再扩展平台能力  
**首发目标**：Spec + CLI + Hermes/OpenClaw/DSH/vHarness adapters + 最小 Registry

---

# 1. 工程目标

实现一个 harness-neutral 的 Agent Image 工具链，使：

```text
Harness Native State
        │
        ▼
     Adapter
        │
        ▼
Canonical Agent Image
        │
 ┌──────┼──────────┐
 ▼      ▼          ▼
inspect verify    redact
 │
 ├───────────────┐
 ▼               ▼
Native Restore   Semantic Migration
```

必须确保：

1. 核心协议不知道 Hermes/OpenClaw/DSH 的内部路径；
2. harness-specific 逻辑完全留在 adapter；
3. 无法标准化的 state 进入 typed native layer；
4. 每一次 export / migrate / restore 都有 loss report；
5. privacy/redaction 是核心能力，不是发布前脚本。

---

# 2. 推荐仓库布局

优先 monorepo，避免首发阶段版本漂移。

```text
agent-image/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── pyproject.toml / package.json / go.mod
│
├── spec/
│   ├── v0.1/
│   │   ├── SPEC.md
│   │   ├── manifest.schema.json
│   │   ├── manifest.example.yaml
│   │   ├── layers.md
│   │   ├── portability.md
│   │   ├── privacy.md
│   │   └── adapter-contract.md
│
├── src/
│   ├── core/
│   ├── container/
│   ├── manifest/
│   ├── security/
│   ├── diff/
│   ├── migration/
│   └── cli/
│
├── adapters/
│   ├── hermes/
│   ├── openclaw/
│   ├── dsh/
│   └── vharness/
│
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── security/
│
├── examples/
│   ├── minimal/
│   ├── hermes-roundtrip/
│   ├── openclaw-roundtrip/
│   ├── dsh-roundtrip/
│   ├── vharness-roundtrip/
│   └── hermes-to-openclaw/
│
└── registry/
    ├── README.md
    ├── schema.json
    └── examples/
```

如果现有 vHarness repo 更适合把 adapter 放在其内部：

- core spec/CLI 仍保持独立；
- vHarness 只提供 adapter package；
- 不得让 core import vHarness module。

---

# 3. 技术栈建议

**优先选择本地 Codex 最容易维护、跨平台最稳定的栈。**

如果当前项目没有强约束，建议：

- Python 3.11+ 或 Go 1.22+ 均可；
- v0.1 更重视文件系统、安全打包、schema、CLI，Python 实现速度更快；
- JSON Schema 作为 machine-readable contract；
- YAML 作为 human-facing manifest；
- SHA-256 作为 v0.1 digest；
- tar + gzip 或 zip 作为 container；
- 不引入数据库。

**重要：不要为了“像 Docker”而在 v0.1 引入 OCI。**
后续可增加 OCI transport，而不改变 logical image model。

---

# 4. 核心数据模型

建议内部 canonical model 与 manifest schema 一一对应。

伪代码：

```python
@dataclass
class AgentImageManifest:
    spec_version: str
    image: ImageMetadata
    runtime: RuntimeMetadata | None
    layers: list[LayerDescriptor]
    development: DevelopmentMetadata | None
    evaluations: list[EvaluationRecord]
    lineage: LineageMetadata | None
    privacy: PrivacyMetadata
    provenance: ProvenanceMetadata
```

Layer：

```python
@dataclass
class LayerDescriptor:
    id: str
    kind: Literal[
        "identity",
        "skills",
        "memory",
        "experience",
        "workspace",
        "development",
        "evaluation",
        "native",
        "other",
    ]
    media_type: str
    path: str
    digest: str
    size: int
    privacy: Literal["public", "private", "secret", "unknown"]
    portability: Literal["portable", "adapter-specific", "opaque"]
    source: SourceDescriptor | None
```

---

# 5. Manifest v0.1 建议

```yaml
spec: agent-image/v0.1

image:
  name: research-agent
  version: 0.1.0
  created_at: 2026-08-24T00:00:00Z
  digest: sha256:...

runtime:
  harness:
    id: hermes
    version: "..."
  adapter:
    id: org.agentimage.hermes
    version: "0.1.0"
  model:
    provider: nous
    id: optional
    family: optional

layers:
  - id: identity-main
    kind: identity
    media_type: text/markdown
    path: layers/identity/SOUL.md
    digest: sha256:...
    privacy: public
    portability: portable

  - id: hermes-native
    kind: native
    media_type: application/vnd.hermes.profile+tar
    path: layers/native/hermes-profile.tar.gz
    digest: sha256:...
    privacy: private
    portability: opaque

development:
  method: habitat
  duration_seconds: 604800
  episodes: 142
  habitat:
    id: negotiation-ground
  evidence:
    - kind: evaluation
      path: layers/evaluation/negotiation.json

evaluations:
  - id: negotiation-v0
    status: self_reported
    before:
      score: 0.454
    after:
      score: 0.627

lineage:
  parent:
    uri: ghcr.io/example/agent:base
    digest: sha256:...

privacy:
  default: private
  public_build: false
  unresolved_items: 0

provenance:
  source_harness: hermes
  source_adapter: org.agentimage.hermes
  export_tool_version: 0.1.0
```

---

# 6. Image 容器格式

建议 `.aimg` = tar.gz。

内部禁止任意路径。

```text
/
├── manifest.yaml
├── index.json
├── layers/
│   ├── identity/
│   ├── skills/
│   ├── memory/
│   ├── experience/
│   ├── workspace/
│   ├── development/
│   ├── evaluation/
│   └── native/
└── meta/
    ├── checksums.txt
    ├── source-report.json
    ├── redaction-report.json
    └── migration-report.json
```

`index.json` 用于机器快速读取，不重复保存业务字段；可以只列：

- path
- digest
- size
- media type

---

# 7. Build Pipeline

```text
detect source
   ↓
adapter inspect
   ↓
build source inventory
   ↓
classify items
   ↓
apply secret policy
   ↓
map semantic layers
   ↓
preserve native state
   ↓
copy to staging
   ↓
hash every artifact
   ↓
emit manifest
   ↓
validate schema
   ↓
pack deterministic archive
   ↓
re-open archive
   ↓
verify
```

**最后一步 re-open + verify 是强制的。**

不能假设 pack 成功等于 image 正确。

---

# 8. Restore Pipeline

```text
open archive
   ↓
validate container paths
   ↓
verify all digests
   ↓
validate manifest version
   ↓
resolve adapter
   ↓
adapter preflight
   ↓
create staging target
   ↓
restore semantic/native layers
   ↓
adapter validate target
   ↓
atomic move / activation
   ↓
emit restore report
```

原则：

- 不直接写入正式 profile/workspace；
- 目标已存在默认拒绝；
- `--force` 前必须再验证 target；
- restore error 时不留下 half-restored live agent。

---

# 9. Semantic Migration Pipeline

跨 harness 不使用 native restore。

```text
Image
 ↓
select portable layers
 ↓
target adapter capability negotiation
 ↓
mapping
 ↓
preflight loss report
 ↓
user accepts / --yes
 ↓
materialize target
 ↓
validate
 ↓
migration report
```

preflight 必须展示：

```text
PRESERVE:
  identity: 4 files
  skills: 7
  memory: 3

TRANSFORM:
  Hermes USER.md → OpenClaw USER.md

UNSUPPORTED:
  Hermes state.db
  Hermes cron runtime state

REDACT:
  sessions/...
```

---

# 10. Adapter Contract

建议接口：

```python
class AgentImageAdapter(Protocol):
    id: str
    version: str

    def detect(self, locator: str | None) -> list[SourceCandidate]: ...
    def inspect_source(self, source: SourceCandidate) -> SourceInventory: ...
    def export_plan(self, source: SourceCandidate, policy: ExportPolicy) -> ExportPlan: ...
    def execute_export(self, plan: ExportPlan, staging_dir: Path) -> ExportResult: ...

    def native_restore_preflight(
        self, image: AgentImage, target: TargetLocator
    ) -> RestorePlan: ...

    def execute_native_restore(
        self, plan: RestorePlan
    ) -> RestoreResult: ...

    def semantic_import_preflight(
        self, image: AgentImage, target: TargetLocator
    ) -> MigrationPlan: ...

    def execute_semantic_import(
        self, plan: MigrationPlan
    ) -> MigrationResult: ...

    def capabilities(self) -> AdapterCapabilities: ...
```

不允许 adapter 自己直接 pack `.aimg`。

**core 负责容器、digest、manifest、security；adapter 只负责 source/target translation。**

---

# 11. Source Inventory

所有 adapter 先输出统一 inventory，再导出。

```json
{
  "items": [
    {
      "source_path": "...",
      "logical_kind": "memory",
      "media_type": "text/markdown",
      "privacy": "private",
      "portability": "portable",
      "action": "include",
      "reason": "recognized Hermes MEMORY.md"
    }
  ]
}
```

优点：

- inspect 与 build 共用；
- 支持 dry-run；
- 用户能看到会打包什么；
- 安全测试可直接验证 inventory。

---

# 12. Security Architecture

## 12.1 Path Safety

所有 archive path：

- 必须是 relative；
- 禁止 `..`；
- 禁止绝对路径；
- 禁止 symlink escape；
- restore 默认不创建外部 symlink。

测试恶意 archive。

---

## 12.2 Secret Scanner v0.1

分两层：

### Filename deny-list
- `.env`
- `auth.json`
- credential/key/token files
- SSH keys

### Structured-key scanner
对 YAML/JSON/TOML 识别：

```text
api_key
apikey
token
access_token
refresh_token
secret
password
credential
private_key
```

v0.1 不需要做“通用内容 DLP”。

但文本层必须支持用户显式 exclude。

---

## 12.3 Privacy Policy

```python
ExportPolicy(
    mode="private" | "public",
    include_experience=False,
    include_user_memory=False,
    include_workspace=False,
    allow_unknown=False,
)
```

### private build
允许 private，但禁止 secret。

### public build
默认：
- secret → reject
- private → exclude
- unknown → reject
- public → include

用户 override 必须留 audit record。

---

# 13. Diff Engine

`agent-image diff A B`

至少输出：

```text
Manifest:
  runtime.model: unchanged
  source_harness: unchanged

Layers:
  + 14 experience records
  + 3 procedural memory files
  ~ identity/SOUL.md
  + development/habitat.json

Evaluation:
  negotiation-v0: 0.45 → 0.62

Privacy:
  private bytes: +2.3MB
```

v0.1 不做 LLM semantic diff。

文件级 + metadata diff 即可。

---

# 14. Verify Engine

`agent-image verify`

检查：

1. schema；
2. path safety；
3. duplicate paths；
4. every layer digest；
5. manifest references exist；
6. no undeclared payload；
7. privacy consistency；
8. secret policy（按 verify profile）；
9. adapter availability（可选 warning）；
10. image digest。

返回非零 exit code 表示 hard failure。

---

# 15. Hermes Adapter 实现方案

**优先使用官方 profile export 作为输入 snapshot。**

流程：

```text
locate profile
→ invoke `hermes profile export` when available
→ extract to isolated temp dir
→ inventory allow-listed files
→ semantic map
→ preserve remaining safe files in native layer
```

映射建议：

```text
config.yaml                  → runtime/identity metadata
SOUL.md                      → identity
system_prompt.md             → identity
AGENTS.md / CLAUDE.md        → identity/instructions
skills/                      → skills
MEMORY.md                    → memory
USER.md                      → memory:user
memories/                    → memory
knowledge/                   → memory/knowledge
preferences/                 → memory/preferences
sessions/                    → experience
cron/ scripts/ plugins/      → runtime/native or skills, conservative mapping
state.db                     → native
todo.json                    → workspace
```

注意：

- Hermes 官方 export 过滤文件名 credential，但不审查内容；
- Agent Image 仍必须二次 secret/privacy pass；
- named profile 的 whole-directory snapshot 不能直接视为 public-safe。

Native restore：

1. create new profile target；
2. restore official/native profile snapshot when compatible；
3. then validate expected files；
4. do not mutate source profile。

---

# 16. OpenClaw Adapter 实现方案

首先通过 OpenClaw 官方可用 CLI/API/已知 workspace layout 做 source discovery。

**不要假设所有 installation 的 workspace 路径相同。**

映射逻辑优先语义：

```text
SOUL.md / IDENTITY.md / USER.md / AGENTS.md → identity
MEMORY.md / memory/**                         → memory
skills/**                                    → skills
workspace notes/artifacts                     → workspace (opt-in)
runtime-specific state                        → native
```

需要兼容“imported memory”目录；保留 source provenance：

```yaml
source:
  origin: hermes
  imported_by: openclaw
```

Hermes → OpenClaw P2 demo：

1. Hermes Image；
2. target adapter preflight；
3. map:
   - SOUL/identity
   - SKILL.md-compatible skills
   - selected public/private-approved memory
4. write into new OpenClaw workspace；
5. emit loss report；
6. run OpenClaw validation/smoke test。

---

# 17. DSH Adapter 实现方案

DSH 变化快，所以 adapter 应最大程度依赖可观察公开 contract：

- `$DSH_HOME/profiles/<name>`
- `package.json` 中 `dsh.profile`
- ordered bundles
- `cordis.patch.yml`
- plugin dependencies
- `--dump-config`

构建：

```text
profile package.json            → runtime native metadata
dsh.profile.bundles             → ordered runtime composition
cordis.patch.yml                → native/config
dependencies                    → runtime dependencies
resolved dump-config (optional) → audit snapshot
```

关键策略：

> DSH 的 plugin graph 是 native state；不要“翻译”成虚构的通用 plugin schema。

restore：

1. 检查目标 DSH version compatibility；
2. create new profile；
3. restore package/profile files；
4. install/resolve dependencies；
5. verify all declared bundles；
6. run `dsh --profile <name> --dump-config`；
7. compare composition invariants。

如果当前 DSH CLI 没有无交互稳定恢复 API，adapter 可以用 filesystem + package manager，但必须封装在 adapter，不泄漏到 core。

---

# 18. vHarness Adapter 实现任务

本地 Codex 必须先执行 **repository reconnaissance**：

1. 找到当前 runtime/harness image 相关实现；
2. 找到 model routing schema；
3. 找到 session/context persistence；
4. 找到 memory；
5. 找到 plugin/tool config；
6. 找到 secret storage；
7. 找到 existing image/checkpoint abstractions；
8. 建立真实 mapping 表。

输出：

`adapters/vharness/MAPPING.md`

格式：

| vHarness object | Agent Image layer | export | restore | privacy | notes |
|---|---|---:|---:|---|---|

不允许依据本需求文档中的历史概念名臆造不存在的代码结构。

---

# 19. CLI UX

所有命令支持：

```text
--json
--quiet
--verbose
```

### build

```bash
agent-image build \
  --from hermes:research-bot \
  --policy private \
  --output research-bot.aimg
```

必须先输出 plan，除非 `--yes`。

### inspect

默认不打印 private payload，只打印 metadata。

### redact

只生成新 image，绝不原地修改。

### restore

target 必须显式：

```bash
--to hermes:new-name
```

### migrate

默认 dry-run。

---

# 20. Error Model

统一错误类别：

```text
E_SPEC_INVALID
E_IMAGE_CORRUPT
E_DIGEST_MISMATCH
E_UNSAFE_PATH
E_SECRET_DETECTED
E_ADAPTER_NOT_FOUND
E_SOURCE_NOT_FOUND
E_SOURCE_UNSUPPORTED
E_TARGET_EXISTS
E_NATIVE_INCOMPATIBLE
E_MIGRATION_LOSS_REQUIRES_CONFIRMATION
E_DEPENDENCY_UNRESOLVED
```

CLI error 必须：

- human-readable；
- `--json` 下 machine-readable；
- 非零 exit code。

---

# 21. Test Strategy

## Unit
- manifest parse
- schema validate
- digest
- path normalization
- privacy classification
- secret scanner
- diff

## Contract
同一组 adapter contract tests 跑四个 adapter。

## Fixtures
**禁止测试依赖真实用户 home。**

构建 synthetic fixtures：

```text
fixtures/hermes/default-safe
fixtures/hermes/named-with-private
fixtures/openclaw/workspace
fixtures/dsh/profile
fixtures/vharness/...
```

## Integration
若 harness CLI 在 CI 可安装：
- export/import smoke test
否则：
- adapter fixture roundtrip + optional nightly harness test

## Security
- path traversal archive
- symlink escape
- secret file
- token embedded JSON
- unknown private file
- corrupted digest
- undeclared payload

---

# 22. Native Round-trip Invariants

P1 不要求 byte-identical，但要求语义不变量。

### Hermes
- identity files preserved
- skills count/digests preserved
- selected memory preserved
- source never modified
- target launches / profile validates

### OpenClaw
- workspace identity preserved
- selected memory preserved
- skills preserved
- target agent/workspace recognized

### DSH
- ordered bundles preserved
- profile patch preserved
- dependency metadata preserved
- resolved profile validates

### vHarness
由 reconnaissance 后定义真实 invariants。

---

# 23. P2 Semantic Migration Invariants

首发只要求一条：

**Hermes → OpenClaw**

必须：

- target 是新的 OpenClaw agent/workspace；
- 至少一个 identity artifact 成功迁移；
- 至少一个 skill 成功迁移；
- 至少一个 memory artifact 成功迁移；
- unsupported Hermes native state 出现在 report；
- no source secret copied；
- target 可被 OpenClaw 探测/启动；
- migration 不修改 source。

---

# 24. Registry 工程

v0.1 不需要 server。

`registry/README.md` + PR workflow。

每个 entry 结构：

```yaml
apiVersion: agent-image-registry/v0.1
kind: AgentImageEntry

metadata:
  name: ...
  author: ...
  license: ...

artifact:
  uri: ...
  digest: ...

agent:
  source_harness: ...
  base_model: ...

development:
  method: ...
  duration_seconds: ...

evaluation:
  status: self_reported

privacy:
  redacted: true
  contains_user_data: false
```

CI：

- schema validate；
- URI present；
- digest format；
- license present；
- privacy declaration present。

---

# 25. GitHub 发布结构

建议第一批至少三个 repo 可以对外清晰：

### A. `agent-image`
Spec + CLI + adapters + examples

### B. `awesome-agent-images`
Registry

### C. Habitat repo / manifesto
可后发，不阻塞协议时间戳。

如果 vHarness 已经有独立 repo，不要为了首发搬迁历史。

---

# 26. 实现顺序（Codex 直接按此执行）

## Phase 0 — Reconnaissance
- 检查现有代码与 repo 名称；
- 决定 language；
- 验证四个 harness 的本机/CI 可访问程度；
- 写 ADR-0001。

## Phase 1 — Spec Core
- manifest schema
- layer descriptors
- privacy
- portability
- adapter contract
- fixture minimal image

## Phase 2 — Core CLI
- build skeleton
- inspect
- verify
- pack/unpack
- digest
- redact
- diff

## Phase 3 — Hermes
优先，因为其 export contract 最成熟。

完成 P1。

## Phase 4 — OpenClaw
完成 P1。

随后 Hermes → OpenClaw P2。

## Phase 5 — DSH
完成 profile native preservation + P1。

## Phase 6 — vHarness
基于真实 repo mapping 完成 P1。

## Phase 7 — Trained Agent Demo
- base
- practice
- image
- restore
- evaluation

## Phase 8 — Registry
- schema
- PR template
- first example entries

## Phase 9 — Release Hardening
- security
- Windows/macOS/Linux path tests
- docs
- changelog
- v0.1 tag

---

# 27. Codex 工作约束

这是为了避免 Agent 常见“demo 补成正式版”的错误。

## Rule 1
**每个 phase 先写 acceptance tests，再实现。**

## Rule 2
验证 demo 后，不把 demo 路径继续膨胀成 production architecture；生产模块按本文结构重新实现。

## Rule 3
不得为了“通用”引入首发不需要的抽象。

## Rule 4
任何 harness-specific special case 先问：
> 应该在 adapter 还是 core？

默认答案：adapter。

## Rule 5
任何数据丢失必须显式 report。

## Rule 6
任何 secret/privacy 风险默认 fail closed。

## Rule 7
不要等四个 adapter 都完美才写 spec；spec 是第一交付。

---

# 28. Engineering Definition of Done

工程上 v0.1 完成时：

```text
agent-image build
agent-image inspect
agent-image verify
agent-image redact
agent-image diff
agent-image restore
agent-image migrate
```

全部存在、测试通过，并且：

- Hermes P1
- OpenClaw P1
- DSH P1（若上游 breaking change 阻塞则有明确 blocker + P0）
- vHarness P1
- Hermes → OpenClaw P2
- privacy/security tests
- registry schema
- trained-agent demo

任何缺项必须在 release notes 中明确标为 experimental/unsupported，不能用文案掩盖。
