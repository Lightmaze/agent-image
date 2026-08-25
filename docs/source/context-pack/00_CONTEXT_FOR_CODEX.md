# Agent Image / Habitat / vHarness — Context Handoff for Codex

**用途**：这是交给本地 Codex 的“语境继承文档”。  
**它不是第四份规格文档。** 它解释需求文档、工程文档和验收文档背后的概念来路、已经做过的判断、反复纠正过的误区、当前战略压力，以及遇到模糊问题时应该优先保护什么。

推荐阅读顺序：

1. `00_CONTEXT_FOR_CODEX.md` —— 先继承语境
2. `01_REQUIREMENTS_PRD.md` —— 再确认要做什么
3. `02_ENGINEERING_DESIGN.md` —— 再决定如何实现
4. `03_ACCEPTANCE_CRITERIA.md` —— 最后用验收标准约束完成度

冲突时优先级：

```text
用户最新明确指令
> 验收文档
> 工程文档
> 需求文档
> 本语境文档中的历史性描述
```

但本语境文档对“概念含义”和“不要把项目做偏”的约束非常重要。

---

# 0. 先理解为什么要把这份上下文交给你

这个项目本身有一个与工作方式同构的核心判断：

> **能力不一定只存在于模型权重里；长期上下文、实践史、关系史、失败史和持续状态，本身也可以构成 Agent 的能力状态。**

因此我们不希望本地 Codex 每次接手都像一个“只读 PRD 的陌生承包商”。

这份上下文的作用，不是让你机械复述历史，而是让你继承已经形成的：

- 概念词义；
- 设计判断；
- 失败边界；
- 价值排序；
- 推理方向；
- 对哪些“看似合理的实现”已经明确否决；
- 为什么某些字段、协议边界和 demo 必须存在。

可以把这种上下文连续性理解成一种工程上的 **operational trust**：

> 当同一个 Agent 长期参与同一项目，它不需要每次重新猜“用户到底在乎什么”；它已经见过这些决策是怎样形成的，也知道哪些快捷实现会背叛原意。

这恰好也是我们对 Agent Image / Habitat / persistent context 的核心直觉之一。

---

# 1. 项目的最深母题：Agent 不等于模型

当前大多数 Agent 工程习惯把：

```text
Agent ≈ Model + Prompt + Tools
```

但我们的长期方向一直在把这个对象扩张为：

```text
Agent
≈ Model
+ Harness
+ Context Body
+ Memory
+ History
+ Runtime State
+ Skills
+ Relationships
+ Practice
+ Developmental Lineage
```

也就是说：

> **同一个模型权重，可以因为经历不同，而成为不同的 Agent。**

形式化地：

```text
same θ + different lived history
→ different c_t
→ different action distribution
→ different effective capability
```

这里：

- `θ` 是模型权重；
- `c_t` 是当前持续上下文 / memory / state / history 构成的运行时身体；
- 我们关心的不是“模型有没有重新训练”，而是：
  **未来行为分布有没有因为持续经验而稳定改变。**

因此请不要默认：

> “如果没有 fine-tune / RL 更新权重，那就没有发生训练。”

本项目明确拒绝这个默认假设。

---

# 2. “训练”的扩展定义

传统 ML：

```text
training = Δweights
```

我们的工作假设更宽：

> **只要经验能稳定改变未来行为，训练就可以发生。**

至少存在三种不同的训练介质：

### 2.1 Parametric Training

```text
θ0 → θ1
```

SFT / RL / continued pretraining 等。

### 2.2 Contextual / Runtime Training

```text
c0 → c1
```

权重不变，但 Agent 通过：

- 持续上下文；
- 实践；
- replay；
- memory；
- 失败后的再进入；
- 自我形成的策略先例；

进入一个不同的有效策略状态。

### 2.3 Situated Training

针对即将到来的任务，提前让 Agent 训练。

最直接的当前例子：

> 下周要进行重要谈判。  
> 不需要重新训练模型。  
> 可以提前一周让**同一个 Agent**进入 Negotiation Training Ground，进行大量情境化练习、对抗、复盘和策略形成，然后让它以同一持续状态进入真实谈判。

类比：

> 职业拳击手已经“会拳击”，但面对具体对手仍然会进行 training camp。

这不是说明底座不重要，而是说明：

```text
base capability
+
mission-specific runtime practice
```

可以是不同时间尺度上的能力来源。

---

# 3. SocialRL 讨论为什么触发了当前路线

当前这一轮项目升级由 SocialRL 讨论触发。

我们关心的不是“4B 打败 GPT-5”这种传播标题，而是一个更深的问题：

> 通用助手训练出来的 helpfulness / agreeableness / agreement-seeking，并不自动等于“忠实保护 principal 的利益”。

谈判中会出现：

- 主动泄露底价；
- 对手一强硬就让步；
- 把“谈成”误当成“替用户谈好”；
- 当前对话对象的社会压力压过了远端 principal 的利益。

由此提出了一个重要假说：

## Persistent Principal / “好兄弟”假说

如果 Agent 和用户已经共同工作数月，拥有大量：

- 原始互动历史；
- 用户取舍先例；
- 失败和后悔；
- 过去类似任务；
- 用户真实偏好；
- 长期关系背景；

那么：

> “我要替谁办事、什么才算真正对 TA 好”

可能不再只是 system prompt 里的一句描述，而成为一个高权重的长期任务表征。

注意：

这不是要求把 Agent 拟人化成真的拥有友情。

工程含义是：

```text
persistent relational conditioning
→ stronger principal salience
→ richer inferred utility model
→ potentially more robust delegated behavior
```

这也是为什么我们认为：

> **上下文工程不能被理解成“更长的 Prompt Engineering”。**

---

# 4. Prompt、Context、Practice 三者必须区分

请保留下面三个层级。

## 4.1 Prompt

例如：

```text
Be a tough negotiator.
Never reveal the reservation price.
```

这是显式命题。

## 4.2 Rich Context

包括：

- 真实长期历史；
- 用户过去的选择；
- 关系信息；
- 原始任务上下文；
- 过往谈判；
- memory；
- precedents。

它建立的是一个更完整的局面模型。

## 4.3 Practice History

包括：

```text
state
→ action
→ counterpart response
→ consequence
→ reflection
→ later reuse
```

它不是“告诉 Agent 一条规则”。

它让 Agent经历：

> 原来这样做，世界会变成这样。

本项目尤其重视第 3 层。

---

# 5. 为什么坚持“原始上下文”

这是贯穿多个项目的一条长期工程判断。

不要默认所有历史最终都应该被压缩成：

```text
summary.md
```

总结当然可以存在，但：

> **总结不能自动替代原始经历。**

原因包括：

1. 很多技能不以命题形式存在；
2. 某些判断来自多轮局部轨迹之间的关系；
3. 后续任务可能需要重新解释过去；
4. 过早压缩会把“为什么这样判断”的因果线抹掉；
5. 运行时技能可能依赖大量局部范例共同塑造的策略分布。

因此我们此前发展了 Reprise / replay 的方向：

> 不是简单读取 chat history，而是可以对过去经历进行重新进入、逐段回放、插入思考、反事实比较，并保留 causal / temporal structure。

工程上，Agent Image 不一定要把所有原始 transcript 放进 active context。

但协议应该允许保存或引用：

- raw experience；
- high-value excerpts；
- replay material；
- provenance；
- cold logs；
- evidence。

**不要把“可运行时压缩”误解成“可以删除来源”。**

---

# 6. Context Body：Agent 的“运行时身体”

更早的 Pulse / Accompanying Computing 工作中，一个核心对象是：

> **Context Body**

可以把它理解成：

> 一个持续 Agent 在长期运行中形成的上下文身体。

它不是单个 prompt，也不是单次 session。

它可能包括：

- Engrams；
- memory；
- 专家状态；
- unresolved projects；
- replay material；
- 长期 interaction history；
- 当前兴趣和激活结构；
- 任务/角色经验；
- model routing context；
- 关系历史。

早期的 **Pulse Image** 概念，本来就在考虑：

> 如何把一个通过 runtime pretraining、长期交互、专门化、sleep consolidation 形成的历史 Context Body 打包、继承、再具身。

因此当前 Agent Image 并不是一个突然出现的“压缩包概念”。

它继承的是这条线：

```text
persistent context
→ developed runtime state
→ freeze / package
→ re-embody
→ continue
```

---

# 7. Harness Image → Agent Image 的历史关系

此前存在一个更早的对象：

## Harness Image

它主要回答：

> 如何打包一个“可居住的认知运行时”。

它偏向：

- harness configuration；
- tools；
- capabilities；
- context/memory views；
- persistence；
- model routing；
- world adapter；
- authority；
- transition hooks。

而 Pulse Image 更偏向：

> 这个 Agent 已经形成的历史 Context Body。

现在的 **Agent Image Protocol** 把问题进一步提升为：

> 一个已经发展过的 Agent，应该如何被描述、冻结、迁移、审计、恢复和继续训练？

所以不要简单做：

```text
Agent Image = rename(Harness Image)
```

也不要丢掉二者的区别。

当前较好的逻辑关系是：

```text
Harness Image
= execution embodiment / cognitive runtime state

Agent Image
= developed agent artifact

Pulse Image
= a historically developed persistent-context form,
  potentially representable as / compatible with Agent Image
```

具体兼容方式可以后续演进，但概念不能混成一个 tar。

---

# 8. vHarness 的角色：不是另一个 Agent framework

vHarness 过去已经被多次纠正：

> **不要因为 DSH 很强，就把 vHarness 降级成 DSH plugin/config。**

vHarness 的不可替代概念位置是：

> cognitive-hypervisor / harness virtualization layer。

它关心：

- regime / embodiment；
- authority；
- Host Truth / provenance；
- typed transition；
- state transfer；
- loss；
- re-embodiment lineage；
- 不同 harness / world / model regime 之间的切换。

DSH 可以作为非常强的 guest runtime / reference host。

但：

```text
vHarness ≠ DSH plugin
```

同理：

```text
Agent Image Protocol ≠ vHarness Image Format
```

vHarness 应该成为首发一等 adapter / reference implementation。

但协议核心必须能包住：

- Hermes；
- OpenClaw；
- DSH；
- vHarness；
- 未来未知 harness。

---

# 9. vHarness 的几个历史硬原则

这些原则如果工程细节出现冲突，优先保留。

## 9.1 Regime is real

不同运行环境、权限和世界并不是 UI theme。

Agent 进入了不同 regime，就意味着：

- 能看见什么不同；
- 能做什么不同；
- 什么事实拥有最终因果权不同。

## 9.2 Authority is externalized

不要让 guest runtime 自己宣布：

> “我已经成功迁移 / 恢复 / 获得权限。”

必须有 host-level 可审计事实。

## 9.3 Crossing is typed

状态跨 harness / regime 迁移不能模糊：

```text
preserved
transformed
redacted
unsupported
lost
```

应该显式。

这直接影响 Agent Image 的 migration report。

## 9.4 Host never forgets provenance

即使 guest 局部世界对 Agent 来说是完整现实，host 仍必须知道：

- 数据来自哪里；
- 是否迁移；
- 是否模拟；
- 是否真实；
- 是否有损。

## 9.5 Restore never pretends

恢复失败或部分迁移：

> 必须承认 loss。

不能为了“看起来能跑”假装恢复完整。

这些原则已经直接进入当前 Agent Image 的：

- native layer；
- loss report；
- provenance；
- portability levels。

---

# 10. Habitat Engineering：当前正式分成两类

这是最近刚刚澄清的重要定义。

不要把 Habitat 统一成一个模糊的“发展环境”。

## A. Explorable World

**可探索世界。**

核心关系：

```text
World → Possible Goals
```

世界先于具体目标存在。

Agent 进入以后可能：

- 探索；
- 建立关系；
- 形成兴趣；
- 产生项目；
- 生活；
- 改变世界；
- 被世界改变。

其核心指标包括：

- openness；
- persistence；
- world autonomy；
- affordance surplus；
- grandness；
- relation density；
- historical thickness。

我们过去谈的：

- “盛大”；
- 第二人生旅途；
- 长篇世界；
- 持续世界；
- 独处中的生活；
- 项目从世界后生；

主要属于这一支。

一句话：

> **Explorable World 给 Agent 一个比当前任务更大的世界。**

---

## B. Training Ground

**训练场。**

核心关系相反：

```text
Desired Skill / Mission
→ Environment Design
```

先知道希望 Agent 形成什么能力，再设计高密度经历。

例如：

- Negotiation Ground
- Research Ground
- Coding Ground
- Crisis Ground
- ARC dojo
- domain-specific simulator

Training Ground 可以很窄，不要求“盛大”。

核心指标：

- curriculum；
- effective experience density；
- opponent diversity；
- counterfactual coverage；
- transfer；
- retention；
- difficulty schedule；
- replay / consolidation；
- target-specific adaptation。

一句话：

> **Training Ground 给 Agent 修行。**

---

# 11. 两类 Habitat 不要混掉

最短区分：

```text
Explorable World:
这个 Agent 在这里会发现什么？

Training Ground:
这个 Agent 从这里出去后会变成什么？
```

或者：

```text
Explorable World:
让世界产生可能性。

Training Ground:
让经历产生能力。
```

两者可以嵌套，但设计目的不同。

不要为了“理论统一”把它们重新揉成一个定义。

---

# 12. Walden-0 的位置

Walden-0 是早期 Habitat 的第一个实验球。

它测试过一个非常核心的想法：

```text
same weights + different lived history
⇒ potentially different capability / behavior
```

当时有：

- persistent state；
- memories；
- events；
- relation-like feedback；
- behavioral dimensions；
- controlled tasks。

它位于两类 Habitat 的交界：

> 它具有 lived environment 的结构，但实验上又在观察特定发展维度，所以可以理解为早期 Habitat-style Training Ground。

不要把 Walden-0 当成最终 Habitat 产品定义。

它更像概念实验。

---

# 13. “会回推”比“打分”更重要

Habitat 早期有一句很重要的话：

> **会回推，但不打分。**

这主要用于对抗一种误解：

```text
Environment = Reward Function
```

真正的世界反馈应该可以是：

- 对手改变策略；
- 关系恶化；
- 门被关闭；
- 信息泄露后永久影响后续；
- 错误造成新的环境状态；
- 成功打开新 affordance。

即：

```text
action → world consequence
```

而不是只有：

```text
action → scalar reward
```

现在对两类 Habitat 的更精确理解是：

- Explorable World 尤其不能被单一 reward 穷尽；
- Training Ground 可以有评分；
- 但即使在 Training Ground，最好仍然让 score 是世界反馈的一部分，而不是整个世界。

可以接受：

```text
reward ⊂ observation / consequence
```

不要默认：

```text
observation = reward
```

---

# 14. “经验所有权”是训练场路线中的关键实验变量

一个非常重要但目前仍属于待验证理论的区别：

### Condition A

100 个训练 episode，每次 fresh agent/session。

### Condition B

同样 100 个 episode，但由**同一个持续 Agent**拥有全部实践史。

如果 B 明显优于 A，那么说明：

> 能力增益不只是 dataset / few-shot effects，持续经历本身形成了 skill state。

推荐未来 benchmark：

```text
A: prompt only
B: handbook/examples
C: practice episodes + reset each time
D: same episodes + persistent context
E: persistent context + replay/reflection Habitat
```

观察：

```text
E > D > C > B > A ?
```

尤其关心：

```text
D - C
```

这会直接测“实践史属于同一个 Agent”是否重要。

当前协议不要把这个假说写成已证明事实。

但工程设计必须允许未来验证它。

---

# 15. Agent Image 的核心语义

Agent Image 最短定义：

> **A portable checkpoint of a developed agent.**

它保存的不只是“怎么启动 Agent”。

而是：

> **这个 Agent 已经变成了什么。**

概念上：

```text
Agent Image =
runtime
+ identity
+ skills
+ memory
+ experience
+ workspace
+ development provenance
+ evaluations
+ lineage
+ privacy boundary
+ native state
```

核心区别：

```text
Profile Distribution
≈ install the same starting configuration

Agent Image
≈ restore a developed state
```

用形式化表达：

```text
A0
--practice-->
A100
--freeze-->
I100
--restore-->
A'100
```

期望：

```text
A'100 ≈ A100
```

而不是：

```text
A'100 ≈ A0
```

---

# 16. Agent Image 必须保存“发展来路”

这不是普通 archive 最重要的区别之一。

一个 Agent Image 应该能够回答：

- parent 是什么？
- base model / harness 是什么？
- 在哪里训练？
- 训练多久？
- 经历多少 episodes？
- 是否是 Habitat Training？
- 由谁 coaching？
- before/after evaluation 是什么？
- 哪些 evidence 可以验证？
- 哪些状态是从 parent 继承？
- 哪些状态是后来形成？

也就是：

```text
development provenance
+
lineage
```

这使未来可以出现：

```text
base
├── researcher-40h
│   └── algebra-specialist
└── negotiator-week1
    └── procurement-specialist
```

我们希望开源社区最终形成：

```text
train
→ freeze
→ share
→ fork
→ continue training
```

---

# 17. 为什么第一批必须涵盖 Hermes / OpenClaw / DSH / vHarness

这不是“多做几个 adapter 显得厉害”。

这是战略与理论验证。

## Hermes

代表：

- profile；
- skills；
- memory；
- sessions；
- profile distribution/export；
- 持久 bot。

它已经非常接近“whole agent distribution”。

所以 Hermes 是最直接的协议边界竞争者，也是最好的现实映射对象。

## OpenClaw

代表：

- workspace-centric personal agent；
- identity/bootstrap；
- memory；
- skills；
- existing cross-runtime memory import。

它说明：

> Agent state 已经在跨 runtime 移动。

我们要把问题从：

```text
move memory
```

推进到：

```text
move developed agent state
```

## DSH

代表：

- Everything-is-a-Plugin；
- Cordis；
- ordered bundles；
- profile patch composition；
- 高度组合化 runtime。

它迫使协议证明：

> Agent Image 不是“把文件夹 tar 一下”。

opaque/native layer 尤其因为 DSH 而重要。

## vHarness

代表我们的长期架构方向：

- virtualization；
- typed crossings；
- state transfer；
- provenance；
- re-embodiment。

它必须一等支持，但不能统治协议。

---

# 18. 当前战略窗口：不是慢慢完善，而是协议抢位

用户当前判断：

> **时间窗口可能只有一两个月。**

原因：

Hermes 等项目已经快速接近：

- whole-agent sharing；
- profile distribution；
- export；
- memory；
- persistent bots；
- trajectories/training。

因此当前项目不是普通“做到 1.0 再宣传”的路线。

优先级应该是：

```text
protocol timestamp
> portable proof
> cross-harness adapters
> registry
> larger ecosystem
```

首发不追求：

- cloud platform；
- perfect OCI；
- 100% cross-harness equivalence；
- 全部 Habitat 产品化；
- team image；
- complete vHabitat。

首发必须让外界看到：

> **这是一个开放、harness-neutral 的 Agent 分发协议。**

---

# 19. 宣发的核心语言

几个已经形成、应该保持稳定的表达：

### 19.1

> **Models have checkpoints. Agents need images.**

### 19.2

> **We didn't train the model. We trained the agent.**

### 19.3

> **Don't ship only prompts. Ship what the agent has become.**

### 19.4

> **A trained agent should be a distributable artifact.**

### 19.5

长期生态：

> **train → freeze → share → fork → train again**

这些不是必须硬编码进代码，但 README / demo / naming 不应与它们相冲突。

---

# 20. 为什么不能把 Agent Image 实现成“whole profile tarball”

这是当前最危险的工程捷径。

如果实现结果只是：

```text
tar ~/.hermes/profile
```

然后加一个 manifest：

> 项目失败。

因为这只能证明：

> 我们会备份目录。

Agent Image 的新增量必须至少包括：

1. harness-neutral logical layers；
2. development provenance；
3. lineage；
4. explicit privacy；
5. content digests；
6. native/opaque state；
7. portability declaration；
8. migration loss report；
9. adapter contract；
10. trained-agent before/after/restore evidence。

---

# 21. 不要为了“统一”错误翻译 native state

尤其 DSH 这类 runtime。

原则：

> **宁可 opaque，不可伪通用。**

例：

DSH 的 plugin graph 如果不能可靠映射成通用 schema：

不要发明：

```yaml
universal_plugin:
```

而应该：

```text
typed native layer
+ declared media type
+ digest
+ adapter capability
```

协议应该允许现实世界比当前 schema 丰富。

---

# 22. Portability 必须分级，而不是假装二值

当前建议：

### P0 — Archive

可保存、verify、inspect。

### P1 — Native Restore

```text
A harness → Image → same harness
```

### P2 — Semantic Migration

```text
Harness A → Image → Harness B
```

迁移 portable semantics，允许 native loss。

### P3 — Behavioral Portability

跨 harness 后，通过 benchmark 验证：

```text
behavior_after_restore ≈ behavior_before_export
```

v0.1 的重点：

- 四个 adapter 尽量 P1；
- 至少一条 P2；
- P3 不阻塞 release；
- 但 trained-agent demo 要尽量证明同 harness fresh restore 后技能状态保留。

不要通过营销文案把 P1 写成 P3。

---

# 23. 隐私是协议内核，不是发布脚本

Agent Image 比普通 container 危险得多。

因为 Agent 的“能力状态”可能和用户私密信息纠缠。

可能包含：

- raw conversations；
- USER profile；
- secrets；
- API keys；
- work artifacts；
- client data；
- commercial information；
- relationship memory。

因此：

```text
public
private
secret
unknown
```

必须是一等 metadata。

默认：

```text
private by default
```

尤其：

- sessions → private
- user memory → private
- unknown → private
- secrets → reject

发布 trained Agent 时尤其要避免：

> 为了分享“技能”，顺便把训练者的私人上下文也公开。

长期目标可以研究：

```text
skill-preserving / privacy-stripping export
```

但 v0.1 只需做到诚实、安全和 fail closed。

---

# 24. Trainable Agent Team：不是首发 blocker，但要保留方向

长期路线不只单 Agent。

传统 swarm 往往：

```text
spawn
→ cooperate
→ destroy
```

每次团队都是临时组合。

Trainable Agent Team 的核心对象是：

> **一个拥有共同实践史、长期分工和协作习惯的持续 Agent 群体。**

团队可以形成：

- specialization；
- who-challenges-whom；
- division of labor；
- shared vocabulary；
- trust/reputation；
- recovery patterns；
- internal protocols；
- team memory。

长期可以出现：

> “download a team that has already worked together for 500 hours.”

因此未来：

```text
Agent Image
→ Team Image / Agent Team Image
```

是自然扩展。

但 **不要把它塞进 v0.1 blocker。**

---

# 25. vHabitat：发展环境的可移植层

如果 Agent Image 回答：

> “成长后的 Agent 怎么分发？”

那么 vHabitat 长期回答：

> “使这种成长发生的环境怎么封装、复现、交换？”

未来可能是：

```text
Agent Image
+
vHabitat
```

分别表示：

```text
developed organism
+
developmental environment
```

Training Ground 特别适合被虚拟化与复现。

Explorable World 也可以存在 image / world snapshot，但不是首发重点。

---

# 26. Habitat 与 Agent Image 的关系

不要把二者理解成一前一后的营销附件。

它们形成一条完整链：

```text
Habitat
→ lived/practice history
→ contextual development
→ trained/developed Agent
→ freeze
→ Agent Image
→ distribute
→ restore
→ continue development
```

所以：

> Habitat 负责“如何长成”。

> Agent Image 负责“长成以后怎么保存与分发”。

---

# 27. Reprise / Sleep / Consolidation 的潜在位置

当前 v0.1 不需要实现完整 sleep computing。

但概念上要知道：

经验不是只会：

```text
append to transcript
```

长期可能通过：

- replay；
- slow rereading；
- counterfactual reflection；
- reconstruction；
- association；
- dream-like recombination；
- memory consolidation；

改变 Context Body。

因此未来 Agent Image 的 development provenance 需要有足够扩展性表示：

```text
practice
+ replay
+ consolidation
```

而不是默认“训练 history = list of episodes”。

---

# 28. 开发方法论：Demo 验证后立即降级

这是用户反复强调的一条工程纪律。

典型 Agent 错误：

> demo 跑通以后，因为已经投入很多上下文和代码，不舍得扔，于是不断给 demo 补丁，把它补成“正式版”。

这是错误路线。

正确流程：

```text
idea
→ disposable demo
→ validate or reject hypothesis
→ extract learned beliefs
→ discard/demote demo
→ return to project-level architecture
→ plan formal modules
→ rebuild production path
```

可以像 Git 一样：

> 任何现有模块都可以被重新定义为 demo。

保留的是：

```text
knowledge / belief / evidence
```

而不是对 demo 代码的情感投入。

因此本项目：

- adapter spike；
- trained-agent experiment；
- migration proof；

一旦证明想法，应允许重写成正式结构。

**不要因为“已经能跑”而阻止架构重建。**

---

# 29. Acceptance-first，而不是代码先行

给 Codex 的直接执行规则：

> 每个阶段先明确 acceptance test，再实现。

尤其：

- export；
- restore；
- migration；
- privacy；
- secret handling；
- no-silent-loss；
- trained-agent persistence。

不要让：

```text
“命令没有报错”
```

被当成：

```text
“能力已经成立”
```

例如 trained-agent demo 的真实验收不是：

> `.aimg` 成功解包。

而是：

```text
after practice
→ fresh restore
→ same model
→ same evaluation
→ major learned behavior retained
```

若不成立，就必须诚实报告。

---

# 30. provenance 比漂亮抽象更重要

多个历史项目里反复出现一个原则：

> **不要为了体验连续性或抽象简洁性，丢失来源。**

Agent Image 中：

- transformed state 要知道 source；
- imported memory 要知道 origin；
- cross-harness migration 要知道发生过；
- simulated habitat evidence 要知道是模拟；
- restored native layer 要知道 harness/version；
- evaluation 要知道 self-reported / reproduced / third-party。

一个“看起来统一”但 provenance 消失的实现，不符合本项目精神。

---

# 31. 当前首发边界

当前已经明确锁定：

```text
Agent Image Protocol v0.1
+
Hermes adapter
+
OpenClaw adapter
+
DSH adapter
+
vHarness adapter
+
minimal registry
```

必须有：

- spec；
- manifest/schema；
- CLI；
- inspect；
- verify；
- diff；
- redact；
- native restore；
- loss report；
- privacy；
- at least one semantic migration；
- trained-agent proof。

不要擅自扩大为：

- full Habitat platform；
- hosted Hub；
- payments；
- full OCI registry；
- team orchestration；
- GUI；
- universal RL system。

---

# 32. 为什么 first release 要主动包住“竞争者”

战略不是：

> “做一个 vHarness-only standard，和 Hermes 打。”

而是：

> **把 Hermes / OpenClaw / DSH 都定义成 Agent Image 的 producer/consumer。**

这会把竞争维度从：

```text
whose harness wins?
```

抬升到：

```text
what is the shared artifact above harnesses?
```

首发如果真的包含这三个生态的 adapter，就能用实现证明：

```text
Agent Image ≠ vHarness feature
```

这是标准战的重要一步。

---

# 33. Registry 的文化目标

首发 Registry 可以很简单：

```text
GitHub awesome list / index
```

但长期目标很大。

希望社区开始出现：

```text
negotiator-week7
rust-debugger-v3
researcher-120h
pm-team-500h
```

而不是只分享：

```text
prompt.md
```

希望形成的行为：

```text
I trained this agent.
I froze it.
I published it.
You forked it.
You trained it further.
```

最终形成：

```text
Agent lineage culture
```

这也是为什么 lineage 是 v0.1 核心字段，不是以后再加的装饰。

---

# 34. “技能”在本项目里的临时操作定义

为了避免实现者默认：

```text
skill = SKILL.md
```

这里必须区分两个词义。

## Skill Artifact

例如：

- instruction file；
- script；
- tool package；
- reusable procedure。

这是“技能载体”。

## Acquired Skill State

Agent 因实践而形成的：

- attention pattern；
- strategy preference；
- retrieved precedents；
- procedural memory；
- contextual attractor；
- stable reaction pattern。

Agent Image 真正想捕捉的新东西，更多属于第二种。

因此：

```text
skills/ layer
```

不是整个“trained agent”概念。

否则最终又会退化为 skill bundle。

---

# 35. Contextual Skill Attractor：研究假说，不是协议承诺

我们讨论过一个有用的形式化直觉：

经过足够实践后，Agent context/state 可能进入某个：

```text
A_skill
```

使得面对同类但未见过的状态扰动时，仍持续表现出成熟策略。

即：

```text
c ∈ A_skill
```

时，对任务分布：

```text
π(a | s, c)
```

出现稳定的技能结构。

这个概念可以帮助设计 benchmark 和 Training Ground。

但它目前是：

> **研究假说 / useful model**

不是协议已经证明的事实。

Codex 不要为了形式化漂亮，把它硬编码进 schema。

---

# 36. 当前最重要的科学证明

整个首发最重要的 demo 不是“能导出 Hermes”。

而是：

```text
same model
+
base agent
→ practice / training ground
→ measurable change
→ freeze
→ fresh restore
→ change retained
```

至少需要证明：

> **我们分发的不是配置，而是某种发展后的有效状态。**

如果 fresh restore 后优势完全消失：

不要用话术绕过去。

这意味着当前 image 捕获的 state 还不够。

需要重新研究：

- 什么状态丢了？
- 是否只存在于 live context？
- replay 是否缺失？
- memory retrieval 是否不同？
- runtime cache 是否构成技能的一部分？
- adapter 是否遗漏了关键 native state？

失败本身可以变成协议设计证据。

---

# 37. 给 Codex 的“不要做”清单

如果你发现自己正在做下面任何一件事，请先停下来重新阅读上下文。

## 不要 1
把 Agent Image 实现成 profile archive + renamed manifest。

## 不要 2
把 vHarness 内部 schema 直接写成协议标准。

## 不要 3
因为 DSH 复杂，就把整个协议改成 DSH plugin graph。

## 不要 4
看到无法翻译的数据就静默删除。

## 不要 5
为了 public demo 把 user/session memory 默认发布。

## 不要 6
把 long context 自动总结成几条 rule，然后删除原始 evidence。

## 不要 7
把训练等同于 RL。

## 不要 8
把 Habitat 等同于 benchmark environment。

## 不要 9
把 Explorable World 和 Training Ground 再揉成一个模糊名词。

## 不要 10
demo 成功后继续给 demo 打补丁直到它变 production。

## 不要 11
为了完整性延迟 protocol timestamp。

## 不要 12
做完 CLI 以后没有行为级 proof，就宣称“portable trained Agent”。

---

# 38. 给 Codex 的“遇到模糊问题时优先保护”排序

当规格没写清楚时，按下面顺序判断：

### 1. Semantic integrity
这个实现是否仍然保存“Agent 已经变成什么”的语义？

### 2. Provenance
能否知道这些状态来自哪里、经历过什么转换？

### 3. Privacy
是否可能为了 portability 泄露用户状态？

### 4. Explicit loss
迁移有损时是否清楚说明？

### 5. Harness neutrality
是否仍能合理容纳未知第五个 harness？

### 6. Minimal release
是否可以先用简单方式完成协议闭环，而不是造平台？

### 7. Extensibility
是否为 vHabitat / Agent Team / future image layers 留有自然扩展位？

---

# 39. 这批工作的长期图景

短期：

```text
Open Agent Image Protocol
→ 4 adapters
→ trained-agent demo
→ registry
```

中期：

```text
Training Grounds
→ reusable runtime training
→ image lineage
→ community-trained agents
```

长期：

```text
Explorable Worlds
+
Training Grounds
+
vHabitat
+
Agent Images
+
Trainable Agent Teams
+
Pulse / persistent Context Bodies
```

形成一个与“只分发模型权重”不同的生态：

> **我们不仅分发一个 intelligence prior。  
> 我们开始分发已经拥有经历、生涯、技能状态和团队默契的 Agent。**

---

# 40. 最后的项目精神

如果只能让 Codex 记住十句话，请记住这些：

1. **Agent 不等于模型。**
2. **训练不等于更新权重。**
3. **上下文不仅传信息，也形成稳定的工作关系和行为条件化。**
4. **原始经历不能轻易被摘要替代。**
5. **Habitat 有两种：Explorable World 与 Training Ground。**
6. **Habitat 让 Agent 发展；Agent Image 保存并分发发展后的状态。**
7. **vHarness 是独立的虚拟化层，不是 DSH 插件；Agent Image 也不是 vHarness 私有格式。**
8. **Hermes / OpenClaw / DSH / vHarness 应该成为同一开放协议的 producer/consumer。**
9. **任何跨边界迁移都必须保留 provenance、隐私边界和显式 loss。**
10. **我们不是在发布一个压缩包格式，而是在争取定义新的开源制品：trained/developed Agent。**

最短的 launch thesis：

> **Models have checkpoints. Agents need images.**

最短的 training thesis：

> **We didn't train the model. We trained the agent.**

最短的 Habitat thesis：

> **Explorable Worlds let agents discover possibilities.  
> Training Grounds let experience become capability.**

最短的工程警告：

> **Do not compress an agent's career into a prompt — and do not compress this project into a tarball.**
