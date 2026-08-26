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
- 文档性质：首个公开 trained-agent image 的有限行为验证预注册与结果报告
- 直接读者：实验执行者、release maintainer，以及需要判断该 artifact 是否可作为首发示例的 reviewer
- 希望促成的行动：在模型调用前冻结对照条件和成功阈值，随后决定该公开镜像能否进入 operator-first 发布路径
- 时间范围：当前 `v0.1.0` release candidate；只评估已生成并固定 digest 的公开 hero image
- 公开性：预注册与汇总结果进入仓库；模型原始响应、凭证和逐调用 usage 留在忽略的本地工作目录

| 文中对象或指代 | 实际指向 | 交付给谁 | 接收者获得什么 |
|---|---|---|---|
| public-restored Agent | 从固定 digest 的公开 `.aimg` 在隔离 Hermes home 中恢复出的 Agent | image consumer / operator | 下载并恢复后即可使用的采购谈判能力 |
| quick comparison | fresh、private-trained、public-restored 三臂、72 次模型调用的有限对照 | release maintainer / reviewer | 判断公开化与恢复是否保留训练所得能力的支持证据 |
| fresh / private-trained controls | 同模型、参数、工具集与场景下的因果参照 | experiment reviewer | 区分基础模型能力、训练后状态与公开恢复状态 |
| “用户” | 首次取得并运行该 hero image 的 developer / operator | developer / operator | 不必先理解实验体系，即可完成恢复和实际任务 |
| “质量” | 公开恢复后的 Agent 能否立即、稳定地完成目标任务 | developer / operator | 实际可用的能力，而不是额外的审计工作量 |
| “完成” | 预注册冻结、对照执行、结果诚实发布并据此作出 release 判断 | 项目负责人 / release maintainer | 可继续进入首发体验，或明确知道需要修正什么 |

- 首要质量判断：公开 artifact 恢复后，operator 能否直接获得已形成的任务能力。
- 证据的角色：支持材料与 release gate，不是使用该 image 的必经流程。
- 与当前默认声明的差异：本次“用户”明确仅指 hero image 的 developer / operator；原始模型响应不作为公开交付物。

## 写作后回看

正式文档完成后，用三句话复核：

1. 文档实际把什么交给了谁？
2. 接收者得到的是结果，还是一组需要自己解释的机制与证据？
3. 文档是否悄悄把次要接收者的需求变成了首要目标？

若答案偏离写作前声明，先修正文档；交付对象确实发生变化时，先更新登记，再重写相关部分。
