# IMPL-06 复审 R3（独立审查者 W5-R6）

- 复审对象：返工提交 `c740603` 后的 `work-items/impl-06-review/`，以 HEAD 文本为准。
- 核对手段：`git show` 逐条审查，awk 脚本全量统计具名用例阈值，接口一致性实跑脚本校验。

## R2 发现闭合核对

- N1｜闭合（第 69 条）｜act/01 `model.decision_entry` 正确区分 active / carried_forward 立场，carried_forward 的 `seen_revision_id` 保持首审旧修订，新增 `carried_to_revision_id` 与 `carried_from_revision_id`；act/01 `fold_decisions` 针对 carried 条目校验 `carried_to_revision_id` 而非 seen，不再报 REF_001；act/02 `decision_anchoring` 亦更新条件式以匹配上述字段取值；act/09 恢复时正确赋予上述字段；语义彻底理顺。**推演复审金标 `test_close_rereview_standings_three_active_two_carried` 能否通过：**
  复审阶段候选集版本为新修订（new_rev）。队列含 3 个 needs_review、2 个 carried_forward 项。执行时，2 条 carried_forward 记录被构造，传入 event 的 target 修订为旧修订（old_rev），故 `seen_revision_id` 初始化为 old_rev，而 `carried_to_revision_id` 赋为 new_rev。
  在 `fold_decisions` 时，2 条 carried 记录以 `carried_to_revision_id == new_rev` 匹配队列项的 seen（new_rev），顺利放行。
  在 Gate `evaluate_review` 的 `decision_anchoring` 中，active 立场通过 `seen == new_rev` 检查；carried 立场凭借 `carried_to_revision_id == new_rev`、`carried_from_revision_id` 于 `prior_decision_events` 中查得且其 seen（old_rev）与本条目 seen 相等，同时 `carried_content_hash` 等于当前对象 content_hash。条件皆满足，在字面契约下完全通过。
- S3｜闭合｜act/11 `upstream_real` 说明已准确修改为「非生产合成 M4 输入与合成决定」。

## 阈值核对

- 通过｜awk 统计各 act（01-11，排除已 WITHDRAWN 的 10）的 `- test_` 用例实际累计数分别为 23、48、63、71、86、98、107、119、129、138，与 README §1、TDD §1、ACCEPTANCE 所列阈值完全一致，全环节可达。

## 接口一致性

- 通过｜impl-06 产出的 artifact_type 仅为 `review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`。不再使用 `correction_request`。执行 `check_interfaces.py` 末行输出为 `I00-IF SUMMARY pass=29 fail=0`，返回状态码 0。

## 下游影响

- 评估｜第 69 条在 `decisions[]` 对象内部新增的 carried 字段未移除任何 impl-07（§0.3）消费的键。impl-07 对 `reviewed_edition` 各键集的校验及使用（包含 `evidence_links[]` 与 `school_views[]` 等）均与 §5.3 最新契约逐字一致；impl-07 读取了 `decisions[]` 但未对其内部深层结构进行严格限制或排他校验。此更新属于安全的向后兼容扩展，不对下游 M7 产生实质影响或导致 SchemaViolation。

## 返工引入的新问题

- 无｜通读 c740603 的全部改动（14 个文件），新文字对 `carried_to_revision_id` 等逻辑描述精确自洽，与未改动段落无矛盾，键集一致，未引入异常写范围变化。

## 判定

**READY**（所有前置发现已妥善闭合，机制自洽无断点，验证阈值与接口校验全通过。）
