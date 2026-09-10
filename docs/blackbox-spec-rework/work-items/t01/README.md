# T-01 术语三层模型写入 M4：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据已定稿文档 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md`，将跨技法术语三层模型（L1 共享源数据 / L2 同形异义 / L3 技法独有）接入黑箱架构规格：
1. 在 `§12 M4 Knowledge Extraction` 之前建立「术语判层前置步骤（三层模型）」，明确 L1 确定性闭集免模型、L2 带技法义项绑定（禁裸绑字面）、L3 技法候选三步判层规则；
2. 在 `§5 总体组织` 的 Contract Registry 中追加 `schemas/shared/canon` 与 `schemas/shared/homographs` 为 M4 的冻结输入 Artifact；
3. 原样保持术语 ID 命名规范与存放路径。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-01
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二（三层定义）与 §三（三步判层）
- `openspec/learn-system-blackbox-architecture.md` §5 与 §12
- `docs/blackbox-spec-rework/verify-T.sh`（T-01 判据）

## Dependencies

- T-02：已 `ACCEPTED`，§8.1 已收录相关 ID 前缀；
- T-03：已 `ACCEPTED`，状态枚举全集已冻结；
- 本任务与 T-04 均修改 `openspec/learn-system-blackbox-architecture.md`，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：
  1. `§5` 基础设施段：在 Contract Registry 描述追加 `schemas/shared/canon` 与 `schemas/shared/homographs` 为 M4 的冻结输入 Artifact；
  2. `§12` M4 段：在提取候选前插入「术语判层前置步骤（三层模型）」，详细列出 L1、L2、L3 的定义、ID、存放路径、判定机制与禁令。

## Forbidden

- 严禁重新设计或篡改三层术语 ID 规则（`co_shared_<domain>_NN`、`hg_NNNN`、`co_<technique>_<6位数字>`）。
- 严禁将三层模型压缩或删减。
- 严禁将 L1 描述成“模型辅助”或“调用大模型”；必须在正文中明确写明「L1 匹配为确定性字典匹配，不调用模型」。
- 严禁允许 L2 裸绑字面；必须写明「必须按当前技法选择对应义项绑定带技法的 concept_id，绝对禁止裸绑字面」。
- 严禁修改代码、Schema、测试、工作包或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与架构已有章节存在语义冲突；
2. Green checks 未通过或全局回归发现非预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完全照搬 `CROSS_TECHNIQUE_ONTOLOGY.md` §二与 §三，无自行发明概念。
- **可执行性**：通过；两个明确落点（§5 与 §12），命令与判据确定。
- **可验收性**：通过；T-01 自动化判据明确（`co_shared_`、`homograph_id`、`schemas/shared/canon` 出现且 `§12` 包含“确定性”），全局 FAIL 数由 14 严格减少为 13。
- **防越界性**：通过；单文件只改规格，无代码及依赖越界。

结论：工作包六件套完备，符合 G0 准出规范，状态置为 `READY`。
