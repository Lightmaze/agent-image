# Agent Image Protocol v0.1 — 验收文档

**状态**：Release Gate  
**用途**：供本地 Codex、自测、人工 Final Review 使用  
**原则**：验收的是“协议闭环是否成立”，不是代码量或 UI 完成度

---

# 0. 总验收结论

只有同时满足以下五个 Gate，才能打 `v0.1.0`：

```text
GATE A — Protocol
GATE B — Core Toolchain
GATE C — Adapters
GATE D — Security & Privacy
GATE E — Demonstration & Ecosystem
```

任意 P0 blocker 必须显式记录。

---

# 1. Gate A — Protocol

## A1. Spec 可独立阅读

- [ ] `spec/v0.1/SPEC.md` 存在。
- [ ] 不阅读 vHarness/Hermes/OpenClaw/DSH 源码也能理解 Agent Image 是什么。
- [ ] 明确定义 Agent Image 与 prompt、skill pack、profile、model checkpoint 的区别。
- [ ] 明确定义 Logical Layers。
- [ ] 明确定义 native/opaque layer。
- [ ] 明确定义 Development Provenance。
- [ ] 明确定义 Lineage。
- [ ] 明确定义 Privacy classes。
- [ ] 明确定义 Portability P0–P3。
- [ ] 明确定义 Adapter Contract。
- [ ] 明确说明 v0.1 非目标。

### 验收失败条件
如果 spec 的字段主要围绕某一个 harness 的现有文件结构设计，A Gate 失败。

---

## A2. Machine-readable Schema

- [ ] `manifest.schema.json` 存在。
- [ ] example manifest 通过 schema validation。
- [ ] 缺少 `spec` 时 validation fail。
- [ ] 未知/非法 layer kind 按 schema policy 正确处理。
- [ ] privacy value 非法时 fail。
- [ ] digest 格式非法时 fail。
- [ ] manifest 能表达只有 minimal layer 的 image。
- [ ] manifest 能表达完整 developed Agent。

---

## A3. Versioning

- [ ] manifest 声明 `agent-image/v0.1`。
- [ ] loader 对未知 major version fail。
- [ ] loader 对允许兼容的 minor 有明确行为。
- [ ] adapter version 与 spec version 独立。

---

# 2. Gate B — Core Toolchain

## B1. Build

执行：

```bash
agent-image build --from <fixture> -o test.aimg
```

- [ ] 生成 `.aimg`。
- [ ] archive 内有 manifest。
- [ ] archive 内所有 payload 都已声明。
- [ ] 每个 payload 有 SHA-256 digest。
- [ ] build 后工具自动 re-open + verify。
- [ ] source 未被修改。
- [ ] output 不包含 staging 绝对路径。

---

## B2. Inspect

```bash
agent-image inspect test.aimg
```

- [ ] 显示 spec/version。
- [ ] 显示 source harness。
- [ ] 显示 layer summary。
- [ ] 显示 privacy summary。
- [ ] 显示 development summary（如有）。
- [ ] 显示 lineage（如有）。
- [ ] 默认不输出 private layer 原文。
- [ ] `--json` 可供机器读取。

---

## B3. Verify

```bash
agent-image verify test.aimg
```

必须检测：

- [ ] schema。
- [ ] missing payload。
- [ ] digest mismatch。
- [ ] duplicate path。
- [ ] undeclared payload。
- [ ] unsafe path。
- [ ] privacy metadata consistency。

负向测试：

- [ ] 修改一个 payload byte 后 verify 非零退出。
- [ ] 删除 manifest 引用文件后非零退出。
- [ ] 加入 `../../evil` path 后非零退出。
- [ ] 添加未声明 payload 后按 spec policy fail/warn，行为有文档。

---

## B4. Redact

```bash
agent-image redact private.aimg --policy public -o public.aimg
```

- [ ] 不原地修改 source image。
- [ ] secret layer 不进入 public image。
- [ ] private layer 默认被删除。
- [ ] unknown layer 默认阻止 public build 或删除，按 policy 一致。
- [ ] 生成 redaction report。
- [ ] report 列出 removed/transformed/unresolved。
- [ ] public image 再次 verify 通过。

---

## B5. Diff

```bash
agent-image diff base.aimg trained.aimg
```

- [ ] 能显示 layer 增删改。
- [ ] 能显示 development metadata 变化。
- [ ] 能显示 evaluation 变化。
- [ ] 能显示 privacy size/count 变化。
- [ ] 不依赖 LLM。
- [ ] 对两个完全相同 image 的 content diff 为 empty。

---

# 3. Gate C — Adapter Contract

四个 adapter 都必须通过统一 contract test。

## C0. Common

每个 adapter：

- [ ] 有稳定 adapter id。
- [ ] 有 version。
- [ ] 能 report capabilities。
- [ ] detect 不修改环境。
- [ ] inspect 不修改环境。
- [ ] export 有 dry-run/inventory。
- [ ] unsupported state 不 silent drop。
- [ ] restore 默认不覆盖 target。
- [ ] migration 有 preflight loss report。
- [ ] source 失败不留下 half-built image。
- [ ] target 失败不留下 active half-restored agent。

---

# 4. Hermes Adapter Gate

## H1. Detection

fixture 或真实测试环境：

- [ ] 默认 profile 可识别。
- [ ] named profile 可识别。
- [ ] 不存在 profile 时返回明确错误。

## H2. Export Mapping

至少验证：

- [ ] `SOUL.md` → identity。
- [ ] `skills/` → skills。
- [ ] `MEMORY.md` → memory。
- [ ] `USER.md` → memory:user/private。
- [ ] `sessions/` → experience/private。
- [ ] `state.db`（fixture）→ native/private。
- [ ] `.env` 不进入 image。
- [ ] `auth.json` 不进入 image。

## H3. P1 Native Restore

```text
Hermes source profile
→ image
→ new Hermes target profile
```

- [ ] target name 不同于 source。
- [ ] identity retained。
- [ ] skill artifacts retained。
- [ ] selected memory retained。
- [ ] native state 被保留或明确报告 incompatibility。
- [ ] source profile 未改。
- [ ] target 能被 Hermes 正常识别/加载（环境允许时）。
- [ ] restore report 无 silent loss。

---

# 5. OpenClaw Adapter Gate

## O1. Detection

- [ ] agent/workspace 可识别。
- [ ] bootstrap/identity files 可 inventory。
- [ ] memory 可 inventory。
- [ ] imported memory 保留 origin metadata。
- [ ] skills 可 inventory。

## O2. Export

- [ ] identity layer 正确。
- [ ] memory layer 正确。
- [ ] skills layer 正确。
- [ ] workspace 默认不是 whole-home dump。
- [ ] known secret/config field 被过滤。
- [ ] unknown private material 默认 private。

## O3. P1 Native Restore

- [ ] 创建新的 target agent/workspace。
- [ ] identity retained。
- [ ] selected memory retained。
- [ ] skills retained。
- [ ] source 未修改。
- [ ] target 可被 OpenClaw 识别/启动（环境允许时）。

---

# 6. DSH Adapter Gate

由于 DSH 是快速变化的 developer preview，验收更重视“遵循公开 contract + fail loud”。

## D1. Export

- [ ] 识别 `$DSH_HOME/profiles/<name>` 或当前官方等价路径。
- [ ] 读取 profile manifest。
- [ ] ordered bundle list preserved。
- [ ] `cordis.patch.yml` preserved。
- [ ] dependency metadata preserved。
- [ ] DSH version recorded。
- [ ] 完整 composition 可作为 native layer。
- [ ] optional `--dump-config` audit snapshot 支持/明确 unsupported。

## D2. P1 Restore

- [ ] 新 profile 创建。
- [ ] bundle order preserved。
- [ ] profile patch preserved。
- [ ] unresolved dependency 导致 fail loud。
- [ ] target 不覆盖已有 profile。
- [ ] resolved config 能验证时必须验证。
- [ ] 如果上游 breaking change 阻塞，release note 有具体 DSH version + blocker，不允许写“暂不支持”四个字结束。

---

# 7. vHarness Adapter Gate

验收前必须先存在：

`adapters/vharness/MAPPING.md`

- [ ] Mapping 来自当前真实源码 reconnaissance。
- [ ] 没有根据旧文档臆造的字段。
- [ ] runtime config 有映射。
- [ ] model routing 有映射。
- [ ] session/context persistence 有映射。
- [ ] memory 有映射。
- [ ] plugin/tool state 有映射。
- [ ] secrets 有映射。
- [ ] existing image/checkpoint abstraction 有兼容说明。

P1：

- [ ] build 成功。
- [ ] inspect/verify 成功。
- [ ] restore 到新 target 成功。
- [ ] 关键 state invariants preserved。
- [ ] source 未修改。

---

# 8. P2 Cross-Harness Gate

首发指定：

```text
Hermes → Agent Image → OpenClaw
```

**这是强制演示，不要求所有 harness 两两迁移。**

准备 Hermes fixture：

```text
SOUL.md
MEMORY.md
skills/example/SKILL.md
sessions/...
state.db
.env
```

执行：

```bash
agent-image build --from hermes:test -o hermes.aimg

agent-image migrate hermes.aimg \
  --to openclaw:migrated-test \
  --dry-run

agent-image migrate hermes.aimg \
  --to openclaw:migrated-test \
  --yes
```

验收：

- [ ] dry-run 先展示 loss report。
- [ ] identity 至少一项迁移。
- [ ] SKILL.md-compatible skill 至少一项迁移。
- [ ] selected memory 至少一项迁移。
- [ ] Hermes `state.db` 标记 unsupported/preserved-not-imported。
- [ ] session 默认不迁或需明确 opt-in。
- [ ] `.env` 不迁。
- [ ] target source provenance 可追踪到 Hermes image。
- [ ] target OpenClaw agent/workspace 可识别。
- [ ] source Hermes 未被修改。

---

# 9. Gate D — Security & Privacy

## S1. Archive Safety

恶意 fixture：

```text
../../outside
/absolute/path
symlink -> ../../outside
```

- [ ] 全部无法写到 staging root 外。
- [ ] verify 或 restore 失败。
- [ ] 不产生外部副作用。

---

## S2. Secret Handling

fixture 包含：

```text
.env
auth.json
secret.pem
config.json {"api_key":"abc"}
settings.yaml token: abc
```

- [ ] private build 不包含明确 secret。
- [ ] public build 同样不包含。
- [ ] structured-key scanner 检测 JSON/YAML 中 key。
- [ ] secret detected 时默认 fail closed。
- [ ] override 如存在，必须要求显式危险选项且写 audit report；首发可选择完全不允许 override。

---

## S3. Privacy Defaults

- [ ] sessions 默认 private。
- [ ] USER/profile personal memory 默认 private。
- [ ] unknown 默认 private。
- [ ] public build 不包含 private/unknown，除非 spec 规定的显式 override。
- [ ] inspect 不打印 private payload。
- [ ] diff 不打印 private payload，只打印 metadata。

---

## S4. No Silent Loss

为每个 export/migration/restore 操作检查 report：

所有 source items 最终必须落入：

```text
preserved
transformed
redacted
unsupported
dropped_by_user
```

- [ ] item count 可对账。
- [ ] 不存在“source inventory 有，但结果 report 消失”的 item。

---

# 10. Gate E — Trained Agent Demonstration

这是首发叙事的关键验收。

## T1. 基础条件

必须使用：

- 同一个模型；
- 权重 digest / provider version 不变；
- 同一个基础 harness；
- 前后只改变 Agent 的 persistent/contextual/development state。

---

## T2. Before

- [ ] 记录 base image。
- [ ] 运行固定 evaluation suite。
- [ ] 保存 score + raw evidence。
- [ ] freeze `before.aimg`。

---

## T3. Practice / Training Ground

Agent 经历可重复记录的实践：

- [ ] 至少 N 个 episodes（N 由 demo 决定，但要足以不是 one-shot prompt）。
- [ ] 保存 development provenance。
- [ ] 不更新 model weights。
- [ ] 保存或引用 experience evidence。

推荐谈判 demo，也可用更快、更稳定的领域替代，只要能证明 contextual skill persistence。

---

## T4. After

- [ ] freeze `trained.aimg`。
- [ ] `agent-image diff before.aimg trained.aimg` 显示 development/state 变化。
- [ ] 同一 evaluation suite 重新评测。
- [ ] 得到可观察 improvement，或至少稳定行为变化。
- [ ] raw evidence 保留。

---

## T5. Fresh Restore

在新的 target profile/workspace/runtime：

```text
trained.aimg
→ restore
→ run evaluation again
```

- [ ] 没有沿用原 live session。
- [ ] model 不变。
- [ ] restored Agent 的结果保留主要训练后行为。
- [ ] 如果结果未保留，则首发文案不得声称“portable skill state”已被证明；只能声称 state archive/restore。

**这一条是科学诚实红线。**

---

# 11. Registry Gate

## R1. Schema

- [ ] registry entry schema 存在。
- [ ] CI 可验证 entry。
- [ ] 必须有 artifact URI。
- [ ] 必须有 digest。
- [ ] 必须有 source harness。
- [ ] 必须有 license。
- [ ] 必须有 privacy declaration。
- [ ] evaluation 必须标明 evidence status。

## R2. First Entries

首发至少：

- [ ] 一个 Hermes image/example。
- [ ] 一个 OpenClaw image/example。
- [ ] 一个 DSH image/example 或 adapter example。
- [ ] 一个 vHarness image/example。
- [ ] 一个 trained Agent image。

这些可以是官方 example，不要求全部第三方。

---

# 12. Documentation Gate

README 第一屏必须在 30 秒内回答：

1. Agent Image 是什么？
2. 为什么不是 profile archive？
3. 支持哪些 harness？
4. 最短命令怎么跑？
5. privacy 是否默认安全？
6. 项目现在是 v0.1/experimental 吗？

必须包含：

```text
Models have checkpoints. Agents need images.
```

但 README 不应是纯宣言，第一屏后立即给 working example。

---

# 13. Third-party Adapter Test

这是判断协议是否真的 harness-neutral 的关键人工验收。

让 Codex 或另一 Agent **只读**：

- SPEC
- adapter contract
- one example adapter

然后要求：

> 为一个 mock fifth harness 写 adapter skeleton。

通过条件：

- [ ] 不需要修改 core schema 才能开始。
- [ ] 能表达 native state。
- [ ] 能 report capabilities。
- [ ] 能产生 source inventory。
- [ ] contract test 能运行。

如果必须改 core 才能容纳第五个 harness，必须评估：
- 是协议真的缺失核心概念；
- 还是 adapter 在泄漏 harness 细节。

---

# 14. Cross-platform Gate

至少：

- [ ] Linux tests pass。
- [ ] Windows path normalization tests pass。
- [ ] macOS path semantics tests pass 或 CI 通过。
- [ ] archive 内路径统一用 `/`。
- [ ] 不依赖 shell-only `tar` 命令才能核心运行。

---

# 15. Release Quality Gate

- [ ] CI 全绿。
- [ ] 无已知 secret leak。
- [ ] 无 path traversal。
- [ ] version tag 正确。
- [ ] changelog。
- [ ] `SECURITY.md`。
- [ ] `CONTRIBUTING.md`。
- [ ] example images verify 通过。
- [ ] public release artifacts 能在 fresh environment 安装。
- [ ] 已知 limitations 列出，不藏在 issue。

---

# 16. v0.1 允许存在的已知限制

以下限制存在时仍可发布，只要清楚写出：

- DSH 上游 breaking changes；
- 部分 native layer 只能 archive；
- P2 只有 Hermes → OpenClaw；
- P3 未实现；
- no hosted registry；
- no OCI transport；
- no encryption；
- no team image；
- no vHabitat image；
- no universal DLP；
- evaluation 可能是 self-reported。

---

# 17. 不允许带入 v0.1 的“假完成”

以下任一情况出现，不得宣称 v0.1 完成：

## F1
只有 schema，没有真实 harness adapter。

## F2
所谓 Hermes/OpenClaw/DSH 支持只是复制 fixture，没有与实际公开格式/CLI 对齐。

## F3
所谓 Agent Image 实际就是 `tar home-directory`。

## F4
没有 privacy/redaction。

## F5
导出成功但恢复没测试。

## F6
跨 harness 迁移默默丢状态。

## F7
trained Agent demo 改了模型权重，却宣称“不训练模型”。

## F8
恢复后的 Agent 没保留行为改善，却宣称“技能可移植”。

## F9
为了赶发布把 secret scanner 关闭。

## F10
README 宣称支持某 harness，但 capability matrix 实际是 P0 且未注明。

---

# 18. 最终 Human Final Review

最终人工审核只问八个问题：

### 1.
**这是不是一个真正独立于 vHarness 的协议？**

### 2.
**Hermes、OpenClaw、DSH 是否真的能被同一个 logical model 描述，而不是三个 if/else 拼盘？**

### 3.
**无法通用解释的 state 是否被诚实地 preserved as native，而不是被丢弃？**

### 4.
**用户是否可以在发布前清楚知道 image 里有哪些隐私数据？**

### 5.
**native round-trip 是否真实可用？**

### 6.
**至少一条跨 harness semantic migration 是否真实可用？**

### 7.
**是否真的展示了“同一模型，Agent 通过实践改变，然后这种状态被 freeze/restore”的证据？**

### 8.
**第三方是否能不 fork core 就增加第五个 harness？**

八项全部为 Yes，才建议打：

```text
v0.1.0
```

---

# 19. Release Verdict 模板

```text
Agent Image Protocol v0.1 Final Review

Protocol:              PASS / FAIL
Core Toolchain:        PASS / FAIL
Hermes Adapter:        P0 / P1 / P2
OpenClaw Adapter:      P0 / P1 / P2
DSH Adapter:           P0 / P1 / P2
vHarness Adapter:      P0 / P1 / P2
Cross-Harness Demo:    PASS / FAIL
Security:              PASS / FAIL
Privacy:               PASS / FAIL
Trained-Agent Demo:    PASS / FAIL
Registry:              PASS / FAIL
Third-party Adapter:   PASS / FAIL

Critical Blockers:
- ...

Known Limitations:
- ...

Decision:
[ ] RELEASE v0.1.0
[ ] RELEASE v0.1.0-alpha
[ ] HOLD
```
