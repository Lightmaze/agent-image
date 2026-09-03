# 文档交付与指代清单

- 建立日期：2026-08-25
- 适用范围：Agent Image 仓库中的计划、阶段判断、设计说明、验收说明和重要 README 改写
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
| “我们” | Agent Image 项目的当前维护者与执行者 |
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

### 2026-08-27 — Agent Image 公开身份与 README 首屏修正

- 状态：`DECLARED`
- 文档性质：项目公开名称、包身份、仓库入口与首发叙事的统一改写
- 直接读者：第一次从 GitHub、release 或生态引用进入项目的 developer / operator；其次是 package consumer、adapter author 与 release maintainer
- 希望促成的行动：让读者在数秒内理解 Agent Image 保存的是发展后的 Agent 状态，并沿最短路径恢复首个可用 Agent；需要建立信任时再进入协议、边界与证据材料
- 时间范围：`v0.1.0-rc.1` 首次公开发布及其发布后初期
- 公开性：公开仓库、Python package metadata、release 说明与中英文 README；尚未存在的仓库和 release URL 不写成既成事实

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| Agent Image | 项目公开主名，也是保存 developed-agent state 的制品类别 | first-time developer / operator、生态传播者 | 一个简短、可复述、可搜索的对象名称 |
| Open Agent Image Protocol v0.1 | `.aimg`、manifest、privacy、provenance、loss 与 adapter contract 的正式协议名 | protocol implementer、adapter author、reviewer | 精确的互操作契约，而不是需要背诵的品牌全称 |
| `agent-image` | Python distribution、CLI 与计划中的 GitHub repository slug | package consumer / contributor | 名称一致的安装、调用和贡献入口 |
| hero comparison | 同模型 fresh Agent 为 `48%`、fresh-restored public image 为 `100%` 的 24 个新合成决策对照 | first-time developer / operator | 在第一屏看见“恢复了什么”的直接结果；精确分数和限制链接到 evidence |
| “体验” | 从理解对象，到取得 artifact、验证、恢复并让 Agent 完成首个任务 | first-time operator | 不必先学习完整协议或审计体系即可看见开发状态被保留 |
| “质量” | 首屏认知压缩、命名一致性、命令可执行性和恢复后能力共同成立 | project lead / release maintainer | 不是更少严谨性，而是严谨性服务于可理解、可使用的结果 |
| “完成” | 两种语言的首屏与命令对齐；包和制品名一致；新发布包通过 clean install、测试、语言与隐私检查 | project lead / release maintainer | 可以继续进入公开仓库创建和 rc.1 发布动作的统一候选 |

- 首要质量判断：陌生读者能否先看懂并试用“下载一个成长后的 Agent”，而不是先面对协议治理清单。
- 证据的角色：行为数字后的可追溯支持材料，以及 release gate；不占据首次使用路径的主叙事。
- 与当前默认声明的差异：公开主名从完整协议名称收敛为 `Agent Image`；正式标准仍称 `Open Agent Image Protocol v0.1`。Python distribution 从 `open-agent-image` 统一为 `agent-image`，import namespace 保持 `agent_image`。

### 2026-08-26 — `README.md` 与 `README.zh-CN.md` 独立语言入口

- 状态：`DECLARED`
- 文档性质：项目公开入口的英文规范版本与简体中文本地化版本
- 直接读者：第一次发现、安装、恢复或集成 Agent Image 的英文或简体中文 developer / operator；其次是 adapter author 与 release maintainer
- 希望促成的行动：让读者选择一种语言后，在单一语言表面中理解项目边界、完成 hero image 恢复，并找到开发与集成入口
- 时间范围：当前 `v0.1.0-rc.1` 本地候选到首次公开 release
- 公开性：进入公开仓库；两份 README 顶部互链，尚未存在的公开 URL 不得写成已经上线

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| English / `README.md` | 协议的英文规范公开入口 | 英文 developer / operator、国际 contributor | 不混入平行中文段落的完整安装、恢复、开发与边界说明 |
| 简体中文 / `README.zh-CN.md` | 与英文事实和声明边界对齐的中文本地化入口 | 简体中文 developer / operator、中文 contributor | 不必跨语言拼接即可完成同一主路径并理解相同能力边界 |
| “用户” | 获取 image、恢复 Agent 或集成 adapter 的 developer / operator | 对应语言的首次读者 | 可选择语言并直接开始使用，而不是自行翻译协议入口 |
| “质量” | 两种语言都能独立、准确、顺畅地带读者完成同一核心任务 | first-time operator | 一致的能力预期、命令和限制，不出现一边过时或夸大 |
| “完成” | 两份 README 相互可发现、事实对齐、语言边界检查通过 | project lead / release maintainer | 可作为公开仓库的双语入口 |

- 首要质量判断：读者只阅读自己选择的语言版本，也能正确理解项目并完成 hero Agent 的恢复与首次任务。
- 证据的角色：语言边界、链接和 claim-alignment 检查是发布支持材料；不增加普通读者的操作步骤。
- 与当前默认声明的差异：`README.md` 明确作为英文规范版本；`README.zh-CN.md` 是完整本地化版本，不是摘要或逐段夹译。

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

### 2026-09-03 — v0.1.0-alpha.2 public preview release

- 状态：`DECLARED`
- 文档性质：当前可移植 developed-state artifact 的首次公开预览与发布说明
- 直接读者：第一次发现 Agent Image 的开发者、准备恢复示例 Agent 的 operator、后续贡献者
- 希望促成的行动：从公开 release 安装 CLI，验证并恢复 hero image，理解当前能力边界后决定试用或贡献
- 时间范围：固定 `v0.1.0-alpha.2`；后续完整 vHarness / Agent Image 生命周期通过新版本向前演进
- 公开性：进入公开仓库与 GitHub prerelease；只包含合成数据、公开制品、项目 noreply 身份和经过复核的证据

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| Agent Image alpha | 可检查、可验证并能在已声明 harness 中原生恢复的 developed-state artifact | first-time operator | 一个真实可运行的公开预览，不是未来完整生命周期的代称 |
| image digest | 当前 v0.1 alpha 的 layer payload root；与物理 release 文件 SHA-256 分离 | protocol implementer / artifact consumer | 可核对当前 payload 身份，同时知道完整 computational identity 仍会继续演进 |
| hero image | 只含合成采购训练状态的 Hermes image | developer / evaluator | 一条短而完整的恢复与使用路径 |
| “发布” | 新公开 GitHub 仓库、不可变 alpha tag、prerelease 与六个可下载制品 | open-source user | 可以 clone、安装、下载和复核；不等于正式 v0.1 或完整 vHarness 隔离已经完成 |

- 首要质量判断：陌生用户能否从公开 release 直接获得一个可安装、可验证、可恢复、可使用的 Agent Image。
- 证据的角色：支撑公开声明与故障定位，不增加普通用户主路径的步骤。
- 与当前默认声明的差异：原本地 `rc.1` 改为公开 `alpha.2`，因为新的身份与隔离语义尚未进入当前实现；已完成能力不撤回，未完成能力不提前宣称。

## 写作后回看

正式文档完成后，用三句话复核：

1. 文档实际把什么交给了谁？
2. 接收者得到的是结果，还是一组需要自己解释的机制与证据？
3. 文档是否悄悄把次要接收者的需求变成了首要目标？

若答案偏离写作前声明，先修正文档；交付对象确实发生变化时，先更新登记，再重写相关部分。
