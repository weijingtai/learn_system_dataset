# T-02 完整标识格式转录：执行工作包

状态：`ACCEPTED`（执行、返工、双轴审查及用户确认均完成）

## Goal

把既有冻结 ID 格式原样接入黑箱架构 §8.1，完成六类新对象 ID 的提议、返工、用户确认和冻结，为 D-02 机器 Schema 消除歧义。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 的 T-02
- `pipeline/schemas/core/SCHEMA.md` v0.2
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md`
- `openspec/learn-system-blackbox-architecture.md` §8
- D-01 已确认的逻辑身份／不可变 Revision 分离规则

## Dependencies

- D-01：`ACCEPTED`
- D-03：可并行验收，但 D-02 仍需等 D-03 与 T-02 均 `ACCEPTED`

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 在 §8 下新增或补全 `§8.1 标识与版本规范`
- 原样转录八类已冻结格式
- 添加并冻结六类新对象格式
- 明确 Schema version 与 content Revision 分离

## Confirmed ID formats

为减少代码与第三方依赖，统一使用 Python 标准库 `uuid.uuid4().hex` 产生 32 位小写十六进制稳定段：

| 对象 | 冻结格式 | 含义 |
|---|---|---|
| Artifact | `art_<32hex>` | 制品的稳定逻辑身份；内容修订时不换号 |
| Artifact Revision | `rev_<32hex>` | 不可变内容修订；每次封存或修正都换号 |
| ProcessingRun | `prun_<32hex>` | 一次完整处理运行；每次重新发起都换号 |
| StepRun | `srun_<32hex>` | 一个阶段任务的一次运行；每次重跑都换号 |
| StagePackage | `pkg_<stage>_<32hex>` | 阶段包逻辑身份，`stage` 仅限 `m1`–`m8`；物理版本另用 `rev_` |
| Release | `rel_<32hex>` | 一次正式发布的数据集身份；每次新发布都换号 |

使用 `prun_` 而非 `pr_`，避免与已冻结 Proposition ID 冲突。用户已于 2026-09-09 确认本表；权威语义见架构规格 §8.1。

## Forbidden

- 不修改任何已冻结格式、前缀或数字位数。
- 不创建 Schema、验证器、代码或迁移脚本。
- 不修改 PLAN、HANDOFF、TODO、BDD、TDD、ACT 或验收脚本。
- 不得擅自修改已确认的新前缀。
- 不增加身份、用户或鉴权 ID。

## Stop conditions

本工作包已经验收结束。后续若发现照抄源冲突或需要修改已冻结前缀，必须新建变更工作包，不得直接改写 §8.1。

## ACT review（wjt-react 四查）

- 忠实性：通过；八个冻结格式、六个新对象、版本轴分离均直接对应 T-02。
- 可执行性：通过；唯一写路径、真实读路径、顺序、停止条件与提交格式明确。
- 可验收性：通过；Red baseline、逐字符串 Green checks、语义复核与全局回归均已给出。
- 防越界性：通过；禁止代码、Schema、依赖、计划和门禁修改，新前缀不得擅自冻结。

结论：执行提交 `6e317cc`、返工提交 `376e78c` 均已验收，用户已确认六类前缀，T-02 为 `ACCEPTED`。
