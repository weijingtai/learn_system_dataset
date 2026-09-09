# T-02 完整标识格式转录：执行工作包

状态：`READY`（ACT 四查通过；等待用户派发）

## Goal

把既有冻结 ID 格式原样接入黑箱架构 §8.1，并把新对象 ID 写成明确的“提案、待用户确认”，为 D-02 机器 Schema 消除歧义。

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
- 添加六类新对象的待确认提案
- 明确 Schema version 与 content Revision 分离

## New ID proposal

为减少代码与第三方依赖，统一使用 Python 标准库 `uuid.uuid4().hex` 产生 32 位小写十六进制稳定段：

| 对象 | 提案格式 |
|---|---|
| Artifact | `art_<32hex>` |
| Artifact Revision | `rev_<32hex>` |
| ProcessingRun | `prun_<32hex>` |
| StepRun | `srun_<32hex>` |
| StagePackage | `pkg_<stage>_<32hex>` |
| Release | `rel_<32hex>` |

使用 `prun_` 而非 `pr_`，避免与已冻结 Proposition ID 冲突。此表必须在架构规格中标记“提案、待用户确认”，执行者无权冻结。

## Forbidden

- 不修改任何已冻结格式、前缀或数字位数。
- 不创建 Schema、验证器、代码或迁移脚本。
- 不修改 PLAN、HANDOFF、TODO、BDD、TDD、ACT 或验收脚本。
- 不把新前缀写成最终规范。
- 不增加身份、用户或鉴权 ID。

## Stop conditions

若照抄源不存在或互相冲突、新前缀与现有 ID 冲突、§8.1 已有不同定稿内容，停止并报告，不自行裁决。

## ACT review（wjt-react 四查）

- 忠实性：通过；八个冻结格式、六个新对象、版本轴分离均直接对应 T-02。
- 可执行性：通过；唯一写路径、真实读路径、顺序、停止条件与提交格式明确。
- 可验收性：通过；Red baseline、逐字符串 Green checks、语义复核与全局回归均已给出。
- 防越界性：通过；禁止代码、Schema、依赖、计划和门禁修改，新前缀不得擅自冻结。

结论：`READY`。该结论只准许派发 T-02，不解除 D-02 的阻塞。
