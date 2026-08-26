# 阶段判断：从协议成立到开源制品成立

- 日期：2026-08-25
- 项目：Open Agent Image Protocol
- 当前状态：`LOCAL RC / PUBLIC EXPERIENCE INCOMPLETE`
- 文档性质：阶段性工作判断；v0.1 的规范优先级保持不变

## 一句话判断

Open Agent Image Protocol 已经拥有可信的本地协议与实现证据，但还没有形成一个陌生开发者能够下载、理解、恢复并亲自验证的公开 Agent Image。

下一阶段把现有能力收束成一个足够清楚、足够有力的开源制品闭环。

## 原始目标

本项目要定义并发布一种新的开放制品：

> A portable checkpoint of a developed agent.

它位于具体 harness 之上，使一个已经形成技能、记忆、实践史和运行状态的 Agent 可以被：

```text
train
→ freeze
→ inspect / verify
→ share
→ restore / migrate
→ fork and continue training
```

首发对象始终是开放协议、参考实现、四个 harness adapter、最小 Registry，以及一个能够证明“这不是 profile backup”的 trained-agent artifact。

## 本阶段的设计原则

“先把东西做成它自己，再把它做成一套严谨的软件系统”在当前阶段意味着：

- 以首个公开 hero artifact 为中心组织现有能力；
- 将 79 项测试、四个 adapter 和 Gate E 报告作为可信的支持证据；
- 从外部开发者的完整使用路径重新呈现协议与参考实现；
- 让开发者直接感受到 image 恢复了一个已经发展过的 Agent，再从真实使用暴露的缺口决定是否扩展协议。

本阶段所说的体验，是外部开发者从获得 artifact 到验证其能力状态的完整开源使用体验。

## 当前已经成立的部分

| 对象 | 当前结论 |
|---|---|
| Core 与 CLI | 本地 RC 候选；archive、manifest、digest、privacy、reports 与版本规则已实现 |
| Adapter SDK | typed contract 与 Python entry point 已实现；第五方 adapter 可在不修改 Core 的情况下注册 |
| Hermes | pinned real P1；named-profile round-trip 已验证 |
| OpenClaw | pinned real P1；同时是首条 Hermes → OpenClaw P2 consumer |
| DSH | pinned real P1；ordered bundles 与 native composition 得到保留 |
| vHarness | scoped real P1；Host authority、provenance 与 typed loss 保持在 host 层 |
| Privacy / security | 本地矩阵通过；unknown/private 默认保护，secret fail closed，无 silent loss |
| Packaging | wheel/sdist 与干净环境安装 smoke 已通过，不依赖手工 `PYTHONPATH` |
| Trained-agent Gate E | 在一个合成采购谈判任务中，通过同 harness fresh restore 保留了测得的发展状态 |
| Registry | schema 与 validator 已成立；当前记录仍以本地、private/withheld evidence 为主 |

这些结果说明协议底座不是一个 renamed tarball，也不是 fixture-only proposal。

## 当前尚未成立的部分

项目还缺少一个外部开发者可以完整走通的公开路径：

```text
获得真实 .aimg
→ verify
→ inspect 它的发展来路与隐私边界
→ restore 到干净 target
→ 运行一个短小的 held-out task
→ 看见 fresh 与 restored 的能力差异
```

具体缺口包括：

- 没有随公开 release 下载的 developed-agent `.aimg`；
- 没有面向首次使用者的短路径，将安装、检查、恢复和行为验证连成一次体验；
- 当前 Gate E 需要约 428 万 tokens 和 1687 次模型调用，适合作为深证据，不适合作为首次体验；
- Registry 尚未以公开 artifact URI、digest、license、privacy 和 evidence status 登记首个可下载 image；
- Windows/Linux/macOS 的托管 CI 尚未形成观察证据；
- 尚未获得创建 public remote、push 或发布 tag 的明确授权。

因此，当前最诚实的状态不是“产品已经完成”，也不是“协议需要推倒重来”，而是：

> 协议与参考实现接近本地 RC；公开制品和采用体验尚未闭环。

## Gate E 的正确位置

现有 Gate E 应保留为严谨、可追溯的支持证据。它证明了在受限条件下，某种实践形成的有效状态可以穿过 freeze / fresh restore。

它没有自动证明：

- 任意能力都能被保存；
- 跨 harness 后行为等价；
- 外部用户能够轻松复现实验；
- 当前 image 已经是一个值得下载的社区制品。

下一阶段不是再造一套更复杂的实验框架，而是从现有正面结果中提炼一个小型公开验证。完整实验保留科学深度；首次体验只承担理解与复现。

## 下一阶段的中心制品

首个 hero artifact 应是一个完全由合成数据训练、可以公开分发的采购谈判 Agent Image。暂用工作名：

```text
procurement-negotiator-v1.aimg
```

它至少应携带或引用：

- base model、provider version、采样参数与工具集；
- parent/base image 与 lineage；
- practice episode、reflection 和 evaluation 的 digest-bound evidence；
- source harness 与 portability declaration；
- privacy classification 与 public-redaction report；
- 当前验证等级：same-harness P1 developed-state retention。

这个名字和包装可以在实际 artifact 生成时调整，但必须与实际训练量和 portability evidence 对齐。

## 首次使用体验

外部开发者应能在约十五分钟内完成：

1. 在干净环境安装发布包，不设置 `PYTHONPATH`。
2. 从 release asset 或 Registry 记录获得 `.aimg` 与 checksum。
3. 运行 `verify`，确认 archive、manifest 与 layer digests。
4. 运行 `inspect`，看见 lineage、development、evaluation、privacy 和 native state，而不泄露 payload。
5. 恢复到一个全新的 Hermes named profile，不覆盖现有 target。
6. 使用相同模型与参数，运行一个规模很小的 held-out 对比。
7. 亲眼看见 fresh profile 与 restored profile 的策略差异，并能继续检查完整 Gate E evidence。

这个体验的价值不来自动画或营销文案，而来自主张与操作之间几乎没有距离：

> 下载的是 image；恢复出来的是已经形成能力的 Agent。

行为验证可以需要用户自己的模型凭证，但下载、checksum、verify 和 inspect 不应需要模型访问。完整 428 万 token 复现实验也不应成为首次使用的前置条件。

## 阶段推进

### Stage A — 收束发布主线

- 统一 README、PROJECT_STATUS、Final Review 与阶段判断；
- 保持 v0.1 schema beta freeze；
- 将现有 Gate E 定位为 supporting evidence，而不是完整采用体验。

退出条件：README、PROJECT_STATUS、Final Review 与本文件对项目目标和证据边界没有冲突。

### Stage B — 生成公开 hero artifact

- 从已通过 Gate E 的合成 developed state 构建可公开 image；
- 完成 public redaction、secret scan、digest、license、lineage 与 evidence binding；
- 为首次使用者提供短小 held-out comparison，同时保留完整实验入口。

退出条件：本地全新环境可以只依赖发布候选包和公开材料完成 download-equivalent、verify、inspect、restore 与短评测。

### Stage C — 形成外部可复现证据

- 在 Windows 与 Linux 至少各完成一次真实 hero path；
- 让未参与实现的人仅依赖公开文档重跑；
- 记录失败点，只有真实使用暴露协议缺口时才讨论兼容扩展。

退出条件：capability claim、命令、artifact digest 和 evidence 可以由第三方对账。

### Stage D — 经授权公开发布

- 创建 public remote 并执行发布前隐私审计；
- 发布包、`.aimg`、checksums、Registry record 与 release notes；
- 按 `beta.1 → rc.1 → v0.1.0` 推进，不把本地证据冒充托管 CI 证据。

退出条件：外部开发者能够从公开入口完成首次使用体验；正式标签仍受 Final Review 与明确发布授权约束。

## 范围纪律

当前资源集中于 hero artifact、外部复现和公开发布闭环。v0.1 schema 维持 beta freeze；只有真实使用证据暴露状态边界缺失时，才讨论兼容扩展。完整 Gate E 仅在 hero artifact 出现状态缺失或不可复现时重跑。所有能力描述以已验证的 portability level 为准。

## 本阶段的最终判断

项目现在不缺少另一轮全面架构设计。它缺少的是第一个真正进入别人手中的 Agent Image。

下一块砖不是新接口，而是：

> 一个可下载、可验证、可恢复、可亲自比较，并且所有能力声明都不超过证据的 developed-agent artifact。

当这个闭环成立，Open Agent Image Protocol 才从“严谨的协议实现”迈入“真实存在的开源制品”。
