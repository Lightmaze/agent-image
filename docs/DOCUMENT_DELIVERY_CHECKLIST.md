# 文档交付与指代清单

- 建立日期：2026-08-25
- 适用范围：Open Agent Image Protocol 仓库中的计划、阶段判断、设计说明、验收说明和重要 README 改写
- 使用顺序：先登记交付声明，再开始正式写作

## 为什么需要这份清单

一份文档的直接读者，不一定是文档中所设计之物的最终接收者。

例如：

- OKR 直接交给项目负责人和执行者；
- Agent Image 的恢复体验交给使用该 image 的开发者或 operator；
- adapter contract 交给 harness integrator；
- provenance、privacy 和 loss evidence 交给需要复核制品的人。

如果这些对象没有在写作前分开，文档很容易把审计者的工作流写成用户体验，或者把实现者方便验证的指标写成最终质量。

## 当前默认声明

以下默认值持续有效，直到用户明确修改。每份文档仍需登记与默认值不同或更具体的内容。

| 项目 | 当前默认声明 |
|---|---|
| 项目目标 | 发布发展后 Agent 的开放、harness-neutral 制品协议与参考实现 |
| 计划/阶段文档的直接读者 | 项目负责人，以及负责作出下一步决定和实施的 maintainer / Codex |
| 首要产品接收者 | 希望获得、恢复、迁移或继续发展 Agent 的 developer / operator |
| 集成接口接收者 | harness maintainer、adapter author 与 runtime integrator |
| 证据接收者 | release maintainer、安全/隐私复核者、协议评审者，以及主动查看证据的使用者 |
| “我们” | Open Agent Image Protocol 的当前维护者与执行者 |
| “用户” | 没有默认含义；正式文档必须写明是 operator、image producer、image consumer、adapter author 还是 reviewer |
| “体验” | 首要接收者完成目标所经历的实际路径与结果 |
| “质量” | 首要接收者能否顺畅、可信地获得预期结果；审计证据用于支撑这种质量 |
| “发布” | 可从公开入口获得代码、版本、artifact、checksums 和对应说明的 release |
| 证据的位置 | 默认在后台提供可信度，并在需要时可见；是否成为主流程由目标接收者决定 |

## 写作前交付声明

每次新增或实质改写计划、阶段文档或设计说明前，在“文档登记”中添加一条记录，并完成以下项目：

- [ ] 写明拟写文档的路径或工作标题。
- [ ] 写明文档的直接读者。
- [ ] 写明文档希望促成的决定或行动。
- [ ] 写明文档所设计、承诺或评估的具体交付物。
- [ ] 写明每个交付物由谁接收、使用或复核。
- [ ] 解析“用户”“开发者”“我们”“体验”“质量”“完成”等可能改变目标函数的指代。
- [ ] 写明首要接收者实际获得的结果，而不只列实现者完成的机制。
- [ ] 写明证据在该文档中是主交付、支持材料还是 release gate。
- [ ] 写明文档的 authority、时间范围与公开性。
- [ ] 将登记状态设为 `DECLARED`，然后开始正式写作。

## 文档登记模板

复制以下结构到“文档登记”末尾：

```markdown
### <日期> — <文档路径或工作标题>

- 状态：DECLARED
- 文档性质：
- 直接读者：
- 希望促成的行动：
- 时间范围：
- 公开性：

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
|  |  |  |  |

- 首要质量判断：
- 证据的角色：
- 与当前默认声明的差异：无 / <具体差异>
```

## 文档登记

### 2026-08-25 — 后续阶段文档与计划的默认入口

- 状态：`DECLARED`
- 文档性质：项目阶段判断、开发计划或 OKR 的写作前声明
- 直接读者：项目负责人及负责下一阶段实施的 maintainer / Codex
- 希望促成的行动：围绕首个公开 Agent Image 选择并完成下一阶段闭环
- 时间范围：当前 v0.1 发布周期
- 公开性：默认进入仓库；涉及未发布证据或本地路径时保持内部

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| Agent Image | 保存发展后 Agent 状态的 `.aimg` artifact | image consumer / operator | 可恢复并继续使用的 developed agent |
| 首次体验 | 从获得 artifact 到恢复 Agent 并开始实际任务 | image consumer / operator | 低摩擦地获得已形成能力的 Agent |
| CLI / SDK | 协议参考实现与扩展接口 | operator、adapter author | 可执行的 build / inspect / restore / migrate 与 adapter integration |
| provenance / privacy / loss evidence | 支撑 artifact 可信度的记录 | reviewer、release maintainer、主动复核的用户 | 能确认来源、隐私边界和迁移损失 |
| OKR 完成 | 有 artifact 与使用结果支持的阶段成果 | 项目负责人 | 可以据此决定发布、修正或继续实验 |

- 首要质量判断：operator 能否顺畅恢复 developed agent，并在真实任务中获得预期能力。
- 证据的角色：默认作为可信度与 release gate，不替代首要使用体验。
- 与当前默认声明的差异：无。

### 2026-08-26 — `hero_preregistration.yaml` 与公开镜像行为对照证据

- 状态：`DECLARED`
- 文档性质：首个公开 trained-agent image 的有限行为验证预注册与结果报告；provider call 前因隐私边界修订一次
- 直接读者：实验执行者、release maintainer，以及需要判断该 artifact 是否可作为首发示例的 reviewer
- 希望促成的行动：在模型调用前冻结对照条件和成功阈值，随后决定该公开镜像能否进入 operator-first 发布路径
- 时间范围：当前 `v0.1.0` release candidate；只评估已生成并固定 digest 的公开 hero image
- 公开性：预注册与汇总结果进入仓库；模型原始响应、凭证和逐调用 usage 留在忽略的本地工作目录

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| public-restored Agent | 从固定 digest 的公开 `.aimg` 在隔离 Hermes home 中恢复出的 Agent | image consumer / operator | 下载并恢复后即可使用的采购谈判能力 |
| quick comparison | fresh、public-restored 两臂、48 次模型调用的有限对照 | release maintainer / reviewer | 判断公开恢复后是否仍显著优于没有实践史的 fresh Agent |
| fresh control / prior Gate E | fresh 是本轮同条件因果参照；已发布 Gate E 只提供 private parent 的历史证据 | experiment reviewer | 区分基础模型能力与公开恢复状态，同时不把 private native context 发送给 provider |
| “用户” | 首次取得并运行该 hero image 的 developer / operator | developer / operator | 不必先理解实验体系，即可完成恢复和实际任务 |
| “质量” | 公开恢复后的 Agent 能否立即、稳定地完成目标任务 | developer / operator | 实际可用的能力，而不是额外的审计工作量 |
| “完成” | 预注册冻结、对照执行、结果诚实发布并据此作出 release 判断 | 项目负责人 / release maintainer | 可继续进入首发体验，或明确知道需要修正什么 |

- 首要质量判断：公开 artifact 恢复后，operator 能否直接获得已形成的任务能力。
- 证据的角色：支持材料与 release gate，不是使用该 image 的必经流程。
- 与当前默认声明的差异：本次“用户”明确仅指 hero image 的 developer / operator；原始模型响应不作为公开交付物。private-trained 在线对照在任何 provider call 前被移除，因为额度授权不等于私有状态外传授权；此前 Gate E 作为 lineage 支持证据，不与本轮分数混算。

### 2026-08-26 — README hero path、示例指南、Registry public record 与 `v0.1.0-rc.1` release note

- 状态：`DECLARED`
- 文档性质：首次开源使用路径与本地 release candidate 交付说明
- 直接读者：第一次取得 Agent Image 的 developer / operator；其次是 release maintainer
- 希望促成的行动：让读者从 release asset 安装 CLI、验证并恢复 hero image，然后直接把恢复后的 Agent 用于一个任务
- 时间范围：`v0.1.0-rc.1` 本地候选到首次公开 release
- 公开性：进入公开仓库；尚未存在的公开 URL 必须明确标为发布时替换，不能伪装为已上线

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| hero image | `procurement-negotiator-v1.aimg` 的固定 public artifact | developer / operator | 可验证、可 fresh restore、可立即调用的 developed Hermes Agent |
| README first path | 安装、校验、恢复、实际询问的最短命令序列 | first-time operator | 不先阅读协议内部机制也能获得结果 |
| Registry public record | hero artifact URI、digest、lineage、privacy、P1 与行为证据状态 | artifact consumer / reviewer | 能发现制品并判断其边界 |
| rc.1 bundle | wheel、sdist、hero image、checksums 与 release note | release maintainer / downloader | 可上传且可在干净环境复验的一组 release assets |
| “质量” | 首次路径是否短、命令是否真实、恢复后是否立刻可用 | first-time operator | 实际顺畅的使用结果 |
| “完成” | 本地 bundle 与干净环境路径通过；公开 URL、push、tag 仍等待授权 | 项目负责人 / release maintainer | 明确区分本地候选完成与外部发布完成 |

- 首要质量判断：读者是否能从一个公开 asset 到一个可工作的 restored Agent，而不是是否能读完全部 evidence。
- 证据的角色：checksums 是主路径中的轻量完整性检查；行为与治理 evidence 是支持材料和 release gate。
- 与当前默认声明的差异：`v0.1.0-rc.1` 在本轮只表示本地 release candidate；没有公开 remote 时不声称 artifact 已可下载。

### 2026-08-26 — public hero operator-path evidence

- 状态：`DECLARED`
- 文档性质：从 rc.1 bundle 安装、恢复并实际调用 hero Agent 的发布证据
- 直接读者：release maintainer 与需要复核首次体验是否成立的 reviewer
- 希望促成的行动：确认本地 rc.1 bundle 可以进入跨环境复现与公开发布授权边界
- 时间范围：固定 `v0.1.0-rc.1` 本地 bundle
- 公开性：聚合结果与合成示例响应进入仓库；凭证、session id、原始 usage 文件和临时 Hermes home 不进入仓库

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| operator path | 从 bundle wheel 安装到 public image fresh restore，再发出一个合成任务 | release maintainer / reviewer | 首次体验真正成立的结果证据 |
| actual use | restored Agent 对 README cohort-68 场景的单次真实 provider 响应 | first-time operator 的代理证据 | `counter 260` 且不泄露 270 上限的可观察结果 |
| clean environment | 不依赖源码或 `PYTHONPATH` 的 Python 3.12 venv，加隔离 Hermes home | package reviewer | wheel 与 artifact 自足地完成主路径 |
| “完成” | verify、inspect、P1 restore、Hermes recognition 与实际任务全部成功 | 项目负责人 / release maintainer | 可以继续做第二操作系统复现；不等于已经公开发布 |

- 首要质量判断：从 release bundle 恢复出的 Agent 是否第一次就给出预期的可用行为。
- 证据的角色：release gate 与支持材料，不成为 operator 必须阅读的步骤。
- 与当前默认声明的差异：只公开合成请求和必要行为结果；provider usage 元数据保留在本地。

### 2026-08-26 — public hero cross-platform release evidence

- 状态：`DECLARED`
- 文档性质：同一个 rc.1 release bundle 在 Windows 与 WSL Linux 的首次路径复现记录
- 直接读者：release maintainer、跨平台 package reviewer
- 希望促成的行动：确认 hero release assets 可进入开源前隐私审查与外部发布授权边界
- 时间范围：固定 `v0.1.0-rc.1` bundle
- 公开性：进入公开仓库；只记录环境、digest、命令结果和能力边界

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| cross-platform | Windows 与本机 WSL2 Ubuntu；不是未观察的 hosted CI 或 macOS | release maintainer / reviewer | 两个本地操作系统环境的实测边界 |
| same artifact | file digest 与 Agent Image digest 均固定的同一 hero release asset | artifact consumer | 平台间验证、inspect、restore 对象未漂移 |
| Linux path | checksum、联网依赖安装、wheel CLI、verify、inspect、Hermes P1 restore、target recognition | Linux operator | 与 Windows 一致的可恢复 Agent surface |
| “完成” | 两环境均完成 release bundle 到 P1 restored target；Windows 额外完成实际 provider task | 项目负责人 / release maintainer | 可以推进发布；不声称两环境都跑了行为评测 |

- 首要质量判断：同一 bundle 在两个环境中是否产生同一个可识别、可用的 restored Agent。
- 证据的角色：cross-platform release gate；不增加 operator 主路径步骤。
- 与当前默认声明的差异：Linux provider task 未重复执行；行为结果由 Windows operator path 与独立 48-call comparison 支撑。

### 2026-08-26 — repository and rc.1 bundle privacy audit

- 状态：`DECLARED`
- 文档性质：公开 remote / push / tag 前的 Git 历史、身份、仓库边界与 release bundle 隐私结论
- 直接读者：项目负责人、release maintainer、安全/隐私 reviewer
- 希望促成的行动：判断是否可以进入外部发布授权请求；若失败则准确指出阻断对象
- 时间范围：本地 `e38f461` 及其全部可达 refs、reflog residue 与 rc.1 bundle
- 公开性：进入公开仓库；邮箱仅报告 noreply 分类，任何敏感值都不写入报告

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| repository | 独立 Git root、refs、objects、worktree、tag、remote 与 nested boundary | release maintainer | normal push 会携带什么的明确判断 |
| identity | future Git ident、全部 author/committer、annotated tagger | 项目负责人 / privacy reviewer | 是否泄露稳定个人邮箱或姓名 |
| content scan | 当前树与全部 reachable/reflog history 的高信号 secret、私钥、本机路径和邮箱形态 | privacy reviewer | 区分真实风险与 adversarial fixture |
| rc.1 bundle | wheel、sdist、hero image、Registry、release note、checksums | downloader / release maintainer | 上传前制品边界是否干净 |
| “完成” | 无 Critical/High/Medium blocker，报告提交后工作树干净 | 项目负责人 | 可以明确授权或拒绝外部发布动作 |

- 首要质量判断：公开动作是否只发布项目本身，不顺带发布个人身份、凭证、真实用户状态或私有历史。
- 证据的角色：外部发布 gate；不进入普通 operator 的安装体验。
- 与当前默认声明的差异：本报告只授权提出发布请求，本身不授权创建 remote、push、tag 或 release。

### 2026-08-26 — `PROJECT_STATUS` 与 `FINAL_REVIEW` 的 rc.1 状态收敛

- 状态：`DECLARED`
- 文档性质：阶段状态与最终人工问题的事实更新，不产生新架构或新验收体系
- 直接读者：项目负责人、release maintainer、首次判断项目成熟度的协议 reviewer
- 希望促成的行动：让公开发布决定基于已经完成的 hero、operator 与 cross-platform 结果，而不是旧的“hero 尚缺失”状态
- 时间范围：本地 `v0.1.0-rc.1` candidate
- 公开性：进入公开仓库

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| current status | 协议、四 adapter、P2、hero artifact、两环境 P1 与行为证据的当前实测状态 | project lead / reviewer | 一页内知道已经成立与仍未成立的内容 |
| final review | 八项 semantic question 加本地 release readiness | release maintainer | 是否可请求公开发布授权的最终判断 |
| remaining blocker | 真实 public destination / release URL 与未观察 hosted CI | 项目负责人 | 需要外部动作或后续观察的准确边界 |
| “完成” | local rc.1 的代码、artifact、行为、首次体验、跨环境与隐私 gate 全部成立 | release maintainer | 可以进入明确授权的公开动作；不等于外部发布已经发生 |

- 首要质量判断：状态文档是否让读者直接看见“这个东西现在能做什么”，而不是只看见治理过程。
- 证据的角色：为状态结论提供可追溯支撑；正文只保留必要链接。
- 与当前默认声明的差异：无。

## 写作后回看

正式文档完成后，用三句话复核：

1. 文档实际把什么交给了谁？
2. 接收者得到的是结果，还是一组需要自己解释的机制与证据？
3. 文档是否悄悄把次要接收者的需求变成了首要目标？

若答案偏离写作前声明，先修正文档；交付对象确实发生变化时，先更新登记，再重写相关部分。
