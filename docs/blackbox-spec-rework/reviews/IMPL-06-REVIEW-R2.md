# IMPL-06 复审 R2（独立审查者 W4-R5）

- 复审对象：返工提交 `479d44e`（docs(impl-06): address four-check R1 and rulings 67-68）后的 `work-items/impl-06-review/`，对照 R1（`9c1d971`）F1–F4/S1/S2 与 G7-RULINGS §9.14 第 67/68 条；以 HEAD（`e2c8d79`）文本为准。
- 核对手段：`review_events.required_decision_types` 实跑推导、awk 具名用例计数、全量 diff 逐条比对。

## R1 发现闭合核对

- F1｜闭合（第 67 条）｜act/01 `build_review_queue(*, candidates, seen_revision_id)` 改为逐对象调用 `review_events.required_decision_types`（P9 唯一来源，M6 不另立映射）。**实跑推导**（`pipeline/knowledge_extraction/review_events.py:144-149`）：assertion（`school_ids=[]`）→ `('review_source_fidelity',)`；school_view → `('review_source_fidelity', 'review_school_attribution')`；合成 4 对象 → 队列 **5 项**（3×1 + 1×2）。失效计数按 5 决定重算并全链自洽：invalidated = 可达候选 3 + 校验条目 0 = **3**；carried_forward = 不可达候选 as_…003（1）+ 内容等价的 as_…002 决定（1）+ 不可达的 as_…003 决定（1）= **3**；needs_review = as_…001 与 sv_…1 的三条决定（content_changed）= **3**；valid 4、ratio 0.75、warnings 告警——与 BDD 3.1（含推导过程）、act/03 `test_s1_counts_exact`/`test_s1_school_view_two_decisions_need_review`、act/04 `expected_review`（decisions 5/checkpoints 6/rework 3-3-3-4-0.75/rereview 3 项 active 3 carried 2）、act/08、act/09、act/11:33 逐处一致。
- F2｜闭合（第 68 条）｜act/01 新增 `decision_entry`（键序 11 项）：事件锚恒 seen（`event.target.artifact_revision_id == queue_item.seen` 校验）、`modify ⇔ modified_revision_id` 非空且合法、carried ⇒ carried_from 非空；act/02 `decision_anchoring` 据此校验（`test_wrong_seen_anchor`/`test_modify_without_modified_revision`/`test_accept_with_modified_revision` 三用例）；act/05 `record_decision` 构造 entry；act/06 `reviewed_edition.decisions` 增 `modified_revision_id`；BDD 1.3/5.5 改写一致（5.5 明确「事件锚恒 seen，`decision_entry.modified_revision_id` 指向 reviewed_candidate」）；R1 的两个不可实现用例已删除替换。
- F3｜闭合｜act/01 签名补 `seen_revision_id`（keyword-only，经 `validate("artifact_revision_id")`），act/05 步骤 5 调用一致。
- F4｜闭合｜阈值改为「具名用例实际累计」：awk 实测 20/21/15/8/15/12/9/12/8/9 → 累计 **20/41/56/64/79/91/100/112/120/129** == TDD §1 == ACCEPTANCE；TDD 明确「阈值 = 各 ACT 具名用例（`- test_` 行）实际累计」，README §1 同步 ≥129。
- S1/S2（R1 建议）｜闭合｜act/11 commit message 改「11 checks PASS, snapshot / workbench seed / real upstream BLOCKED」；snapshot_projection 说明去前缀重复 + TDD §2 增第 61 条豁免注记。
- 附加一致性：act/04 种子改「合成 M4 输入经真实 Ledger 写路径注入 4 对象（含 school_view）」（fixture 金标 candidate_set 无 school_view，理由成立，D-11 A 口径）；act/06 Gate 调用改为逐对象携带 `required_decision_types`；`normalize_content` 修正为取 `source_object`（顺带修复 R1 未标注的潜在键位错误）。

## 返工引入的新问题

- N1｜阻断｜act/02.yaml（fold_decisions/decision_anchoring）与 act/09.yaml:32｜carried 条目锚点语义冲突：act/02 现要求**每条** decision_entry `seen_artifact_revision_id == seen_revision_id`（Gate 参数 = 复审新 candidate_set 修订）且 `fold_decisions` 对 `entry.seen != 队列项 seen` 一律 REF_001；而 act/09 复审金标的 2 条 carried 条目源自首审决定（其事件锚 = **旧** candidate_set 修订），act/09:32 只写「carried_from_revision_id = 其 seen_artifact_revision_id」，未定义 carried entry 自身的 `seen_artifact_revision_id` 取值——按旧 seen 则 fold REF_001 且 anchoring 失败（复审金标 `test_close_rereview_standings_three_active_two_carried` 必败），按新 seen 则与「carried_from = 其 seen」的行文冲突；且 `model.decision_entry` 的事件锚等值校验使「旧事件 + 新队列项」根本无法通过构造｜act/02.yaml（fold_decisions/decision_anchoring 契约行）、act/09.yaml:32；BDD 9.2（队列 seen = M4' 新修订）｜统一语义：act/02 `decision_anchoring` 改条件式（standing == "active" ⇒ seen == seen_revision_id；standing == "carried_forward" ⇒ seen == 复审队列项 seen（新）且 carried_from_revision_id == 旧候选集修订），`fold_decisions` 同口径；act/09:32 写明「carried entry 的 seen_artifact_revision_id 取复审队列项 seen（新），其旧 seen 入 carried_from_revision_id；carried 条目不经 `decision_entry` 的事件锚等值校验（或为其增 carried 模式）」。
- S3｜建议｜act/11.yaml:36｜upstream_real 的 BLOCKED 说明仍写「本次为 fixture_gold + 非生产合成决定」，但返工后 M4 输入为纯合成注入（act/04 步骤 3），不再消费 fixture 金标｜act/04.yaml（步骤 3）｜改为「本次为非生产合成 M4 输入与合成决定」。

## 判定

**REWORK**（R1 的 F1–F4 与 S1/S2 全部闭合，第 67/68 条落位准确；但返工引入新阻断 N1——carried 条目锚点语义未定义使复审金标路径在字面契约下必败。N1 为一处语义补写，修复后可达 READY。）

（审查者：W4-R5；以 HEAD `e2c8d79` 只读核查，`required_decision_types` 实跑取证；`git diff --check` 无输出。）
