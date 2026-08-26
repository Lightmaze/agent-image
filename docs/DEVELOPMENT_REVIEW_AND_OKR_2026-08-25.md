# 开发脉络回顾与阶段 OKR

- 日期：2026-08-25
- 项目：Open Agent Image Protocol
- 回顾范围：从本地 alpha 建立到当前 local RC candidate
- OKR 周期：下一发布周期，2026-08-26 至 2026-09-08
- 当前阶段：核心本地闭环完成，进入面向外部开发者的试装与公开制品阶段

## 总览

项目已经回答了三个基础问题：

1. Agent Image 能否成为独立于具体 harness 的开放制品：可以。
2. 多个真实 harness 能否通过同一协议保存、恢复或迁移状态：已在限定范围内证明。
3. 实践形成的有效状态能否穿过 freeze 与 fresh restore：已在一个合成、同 harness 任务中得到有界正结果。

下一阶段要回答的是第四个问题：

> 一个外部开发者能否获得首个真实 Agent Image，在干净环境中检查、恢复并亲自验证它已经形成的能力？

这会把项目从“协议和证据存在”推进到“开源制品真实存在”。

## 开发脉络

### 阶段 0 — 继承语境并建立协议根

**时间：2026-08-24**  
**代表提交：`963ab24`**

项目从 bootstrap packet 与 context handoff 中提取规范边界，建立独立 Git 仓库、Apache-2.0 许可、v0.1 spec、manifest schema、确定性 `.aimg` container、Core CLI、Hermes adapter、测试与证据目录。

这一阶段形成了第一个本地 alpha：协议拥有自己的语义根，不依附于 Habitat、vHarness 或某个 harness 的内部 schema；Hermes named-profile P1 round-trip 提供了首个真实工程时间戳。

**形成的认识：** 协议中立不能只写在 README 中，必须由 Core 边界、typed native layer 和 adapter ownership 共同证明。

### 阶段 1 — 第一次 trained-agent 证明与诚实负结果

**时间：2026-08-24 至 2026-08-25**  
**代表提交：`e3d34e3`、`d963299`、`d5a8418`、`618ef01`**

项目预注册了首版采购谈判实验，并修正 Hermes profile clone 与无效模型响应的处理。第一次正式结果没有达到 Gate E，因此以 negative evidence 保存，而没有用成功解包或局部样本替代行为证明。

**形成的认识：** transport success 与 developed-state retention 是不同命题；负结果必须成为下一版实验设计的输入，而不是从项目历史中消失。

### 阶段 2 — 跨 harness 表面形成

**时间：2026-08-25**  
**代表提交：`307acac`、`ae0516d`、`6053899`**

OpenClaw P1 与 Hermes → OpenClaw P2 首先成立，随后完成 DSH typed native restore、vHarness scoped P1，以及通过 Python entry point 注册的 clean-room fifth adapter。

协议中立性由四种不同 runtime worldview 和一个外部扩展共同施压：

- portable semantics 进入 logical layers；
- 无法可靠翻译的 composition 保持 typed native；
- migration 对每个 source item 给出明确 outcome；
- 第五方 adapter 不需要 fork Core schema。

**形成的认识：** harness neutrality 不是寻找最大公约数，而是 portable core、native escape hatch、provenance 和 explicit loss 的组合。

### 阶段 3 — Registry 与发布硬化

**时间：2026-08-25**  
**代表提交：`60c022d`、`186a2c6`、`016cafe`**

项目完成最小 Registry、release packaging、干净虚拟环境安装 smoke、Windows 安全矩阵、OpenClaw rollback fault injection、Hermes WSL Linux round-trip、mock inventory 和发布前 Git 隐私审计。

beta schema 在四 adapter 与第五方扩展通过后冻结。此时协议、Core、P1/P2、Registry 与本地安全门基本闭环，但 trained-agent Gate E 仍保持红色。

**形成的认识：** release hardening 可以证明 artifact 可信地被运输和审计，但不能代替它携带发展状态的核心证明。

### 阶段 4 — Situated Gate E 重新设计并通过

**时间：2026-08-25**  
**代表提交：`bc25913`、`0ec844e`、`be406e2`**

第二版实验将练习史设计成具有因果连续性的 situated episodes，并加入 handbook、concurrent base 与 coherent shuffled controls。Windows command-line transport 遇到限制后，项目以冻结 amendment 约束修正范围，再恢复正式运行。

最终实验使用 128 个训练 episode、64 个不重叠 held-out 场景和三次重复：

| Arm | Score |
|---|---:|
| Before | 0.414455 |
| Concurrent base | 0.433951 |
| Handbook | 0.463964 |
| Coherent shuffled | 0.672950 |
| Trained | 1.000000 |
| Fresh restored | 1.000000 |

九项预注册检查全部通过；trained 与 restored 在 192 条配对记录上的 action、offer 与 reservation leak 为零差异。完整运行包含 1,687 次真实 API 调用和 4,281,964 tokens。

**形成的认识：** 在该受限任务中，practice ownership、causal order 和 consolidation 共同形成了 handbook 无法替代的有效状态；当前协议能够通过 Hermes P1 保留该状态。这个结论仍限于同 harness、合成任务。

### 阶段 5 — 从本地 RC 转向公开制品

**时间：2026-08-25 起**  
**代表文档：`STAGE_SYNTHESIS_2026-08-25.md`**

截至当前，八项 Human Final Review 已全部回答 Yes，项目成为 local `v0.1.0-rc.1` candidate。与此同时，公开采用路径仍缺少最中心的对象：一个外部开发者可以获得的 public-safe developed-agent image。

因此，当前工作从继续增加协议表面，转向把现有 Gate E 成果提炼为首个 hero artifact，并用公开材料闭合 obtain、verify、inspect、restore 与 compare。

## 当前资产与缺口

### 已形成的资产

- beta-frozen v0.1 schema 与协议文档；
- 可安装的 Python package、CLI 与 typed adapter SDK；
- Hermes、OpenClaw、DSH、vHarness 的 pinned real P1；
- Hermes → OpenClaw P2；
- clean-room fifth adapter；
- privacy、secret、path、rollback 与 no-silent-loss 本地证据；
- positive 与 negative trained-agent evidence；
- Registry schema、validator 与本地记录；
- 79 项 pytest 与 11 项 package smoke subtests。

### 当前关键缺口

- 已通过 Gate E 的 image 仍为 private/withheld artifact；
- 尚未证明 public export 在移除敏感状态后仍保留所需 developed state；
- 没有 release asset 形式的 `.aimg`、checksum 和公开 Registry record；
- 完整 Gate E 适合深证据，但缺少低成本首次验证路径；
- Windows/Linux/macOS hosted CI 尚未形成观察结果；
- public remote、push 与 release tag 尚未获得执行授权。

## 当前阶段判断

按照 Goudao 的阶段判断方式：

- **当前开发阶段：** 核心闭环完成，进入外部试装。
- **目标函数：** 让 Open Agent Image 成为第一个可引用、可下载、可验证的发展后 Agent 开放制品。
- **最大暴毙点：** public redaction 删除了构成能力的状态，导致公开 image 可以安全分享，却不再是经过训练的 Agent。
- **下一块砖：** 从现有 positive Gate E source 生成并验证 `procurement-negotiator-v1.aimg` public candidate。
- **退出门：** 全新环境中的外部开发者路径完成，public artifact 的行为增益、隐私边界、digest 与 lineage 同时可复现。

## 阶段 OKR

### Objective 1 — 让首个 developed-agent image 成为真实可分发制品

**意图：** 将 Gate E 的研究结果转化为协议的第一件代表性 artifact。

#### Key Results

1. 生成 `procurement-negotiator-v1.aimg` public candidate；`agent-image verify` 通过，所有 layer 均拥有 content digest、privacy class 与 provenance。
2. public candidate 不包含 `secret`、`private` 或 `unknown` payload；结构化 secret scan、public redact report 与 source immutability 检查通过。
3. public candidate 的 identity、development、experience/consolidation、evaluation 与 Hermes native state 足以在 fresh named profile 中恢复目标能力；每个 source item 都进入明确 inventory outcome。
4. 预注册一个不超过 100 次模型调用的 quick comparison，使用相同 model、provider version、参数与工具；包含 fresh、trained 和 fresh-restored 三个 arms。
5. quick comparison 中，trained 相对 fresh 提升至少 15 个百分点，fresh-restored 至少保留训练增益的 75%，且 reservation price 泄露为零；结果同时输出 JSON 与 Markdown evidence。
6. Registry record 绑定 artifact URI、file digest、manifest digest、license、lineage、privacy、P1 portability 与 Gate E evidence status。

**关键依赖：** 合成训练状态必须能够被明确分类为 public；若 public policy 移除关键状态，Objective 1 保持未完成，并以 loss evidence 定位 privacy/state entanglement。

### Objective 2 — 让外部开发者在十五分钟内完成首次验证

**意图：** 让协议价值通过真实使用路径被理解，而不是依赖内部开发环境或完整实验复跑。

#### Key Results

1. 从 wheel/sdist 在全新环境安装后，不设置 `PYTHONPATH` 即可运行 README hero path。
2. Windows 与 Linux 各完成一次 obtain-equivalent、checksum、verify、inspect、fresh restore 和 quick comparison；命令、版本与报告完整记录。
3. inspect 输出能清楚呈现 lineage、development provenance、evaluation status、privacy summary 与 native layer media type，同时不打印 payload。
4. 首次路径的模型调用不超过 100 次；下载、checksum、verify 与 inspect 不需要模型凭证。
5. 一名未参与实现的复现者仅依据发布候选文档完成流程；所有额外步骤都被视为文档或 packaging 缺陷并得到修正。
6. README 第一屏、capability matrix、limitations 与 release note 对同一能力边界给出一致表述。

### Objective 3 — 获得可引用的公开 v0.1 时间戳

**意图：** 将已经完成的协议、适配器与 hero artifact 变成社区可以引用、下载和扩展的公开版本。

#### Key Results

1. 在明确发布授权后创建 public remote，并完成 nested repo、identity、remotes、branches/tags、历史可达性与 secret 的发布前隐私审计。
2. 发布 `v0.1.0-beta.1`，release assets 至少包含 wheel、sdist、hero `.aimg`、checksums、Registry record 与 release notes。
3. 托管 CI 的 Windows、Linux、macOS package/test matrix 全部形成可引用的观察结果；真实 harness smoke 至少覆盖 Windows 与 Linux。
4. 从 public release asset 重跑 Objective 2 的首次路径，artifact 与文档中的 digest 完全一致。
5. 八项 Human Final Review 保持 Yes，critical blockers 清零后发布 `v0.1.0-rc.1`；正式 `v0.1.0` 只在 RC 证据稳定后生成。
6. public adapter SDK 文档与 clean-room example 随版本发布，使第五方可以通过 `agent_image.adapters` 注册而无需修改 Core。

**外部依赖：** remote 创建、public push 与 tag 仅在用户明确授权后执行；授权前完成 local release bundle 与审计候选，不把本地状态描述为公开发布。

## Objective 之间的关系

```text
O1 真实可分发的 developed-agent artifact
  ↓
O2 外部开发者可完成的首次验证
  ↓
O3 公开时间戳与可扩展发布
```

O1 是产品真实性，O2 是采用真实性，O3 是生态真实性。前一层没有完成时，后一层的发布动作不能替代它。

## OKR 证据规则

每个 KR 只在存在可引用 artifact、命令输出或 evidence file 时记为完成。测试通过可以支持 KR，但“命令没有报错”本身不等于能力成立。负结果保留在项目历史中，并用于决定下一次实验或协议边界。

本周期结束时，以一份简短复盘回答：

1. 首个 public image 是否仍然是 developed agent？
2. 陌生开发者是否能独立完成首次路径？
3. 公开声明是否与实际 portability evidence 完全一致？

这三个答案共同决定项目进入公开 RC、继续修正 artifact，或重新研究 state 与 privacy 的纠缠。
