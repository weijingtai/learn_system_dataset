# TDD：T05a concept→span 的 mentions 映射

`export LC_ALL=en_US.UTF-8`（macOS）/ `export LC_ALL=C.UTF-8`（云端容器，见
AGENTS.md）；`PY=.venv/bin/python`；
`TA="$PY -m unittest discover -s pipeline/assembly/tests -t ."`；
`TR="$PY -m unittest discover -s pipeline/review/tests -t ."`；
`TD="$PY -m unittest discover -s pipeline/dataset_compiler/tests -t ."`；
在仓库根运行。

**裁决状态**：用户 2026-09-26 已裁决 README.md「二、已裁决」两项均为 (a)，
本任务范围包含 M6 队列纳入 concept 类候选（前置步骤，第 1 节）与 M7 概念发号
（第 2 节），不再是收窄版本。以下用例可以直接动手写，不再有「待批准才能动手」
的前置门槛。

## 0. 开工基线

```bash
git status --short pipeline/assembly pipeline/review pipeline/dataset_compiler docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md   # 空
$TA 2>&1 | tail -1     # 基线：OK 305 (skipped=2)（合并 claude/wizardly-maxwell-pqrzh9 后的数字，执行者开工时实测核对，若不同就地记录基线，不当成异常）
$TR 2>&1 | tail -1     # 基线：OK 179（`docs/handoff/T04-CLOUD.report.md:199` 已记 179；执行者开工时以自己实跑为准）
$TD 2>&1 | tail -1     # 基线：OK 279（`docs/handoff/T04-CLOUD.report.md:211` 已记 279；执行者开工时以自己实跑为准）
bash openspec/acceptance/m8-span-identity.sh 2>&1 | tail -1   # 基线：SUMMARY pass=7 fail=0 blocked=1，exit 2
```

## 1. 前置步骤：M6 队列纳入 concept 类候选（`pipeline/review/`）

仿 `pipeline/review/tests/test_pattern_review.py`（`PatternReviewTests`）
新建 `pipeline/review/tests/test_concept_review.py`（`ConceptReviewTests`），
复用同样的 `_seed()`/`_queue_item_ids()` helper 写法（用
`mock.patch.object(upstream_stub, "load_data", side_effect=...)` 往
`m4_candidates` 里注入 `concept_mentions`/`new_concept_candidates`）。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_new_concept_candidate_enters_review_queue` | 注入一条 `new_concept_candidate`（`surface="天官"`, `evidence=[{"source_span_id": ..., "support_type": "direct"}]`） | `open_review(...)` | `review_queue` 里有一条 `queue_item_id == "天官#review_source_fidelity"` | `inputs.py:161-174` 当前不读 `new_concept_candidates`，队列里没有这一条 |
| `test_concept_mention_enters_review_queue` | 注入一条已带 `concept_ref` 的 `concept_mention`（`concept_ref="co_qizheng_000001"`） | `open_review(...)` | 队列里有 `"co_qizheng_000001#review_source_fidelity"` | 同上，`concept_mentions` 未被读取 |
| `test_approved_new_concept_candidate_enters_reviewed_edition` | 沿用上面的候选，`record_decision(..., verdict="accept", ...)`、`close_review(...)` | 检查 `reviewed_edition.approved` | 含 `{"entity_id": "天官", "kind": "new_concept_candidate", ...}` 且 `content_status == "expert_verified"` | 同上，队列没有这一条，`record_decision` 会先因为找不到队列项而拒绝 |
| `test_rejected_new_concept_candidate_enters_rejected` | 同上但 `verdict="reject"` | `close_review` | `reviewed_edition.rejected` 含 `"天官"` | 同上 |
| `test_queue_from_upstream_independent_derivation_covers_concept_kinds` | 同上注入 | 调 `pipeline/review/acceptance.py` 的独立推导校验（`_check_queue_from_upstream` 或其公开入口，执行者核实调用方式） | 推导出的 expected queue 与实际队列一致 | `acceptance.py:242-248` 当前只算 assertions/school_views（T19 已加 patterns），不算 concept 类，两个集合不符 |
| `test_evidence_closure_covers_concept_kinds` | 同上，`evidence[].source_span_id` 指向真实存在于 `corpus_spans_doc` 的 span | `evaluate_review(...)`（`pipeline/review/gate.py`） | `checks["evidence_closure"]["passed"] is True` | `gate.py` 的 evidence_closure 循环只认 `kind=="assertion"`（与 T19 新增的 `kind=="pattern"` 分支），没有 concept 分支（执行者需按 README 2.1.7 写清楚具体断言） |

**篡改探针**（仿 T19 裁决指定的写法）：
- P1：只把队列构造里 concept 类那两段删掉（还原到"不读 concept_mentions/
  new_concept_candidates"）→ 上面 5 条用例全部转红。
- P2：`evaluate_review` 的 concept 分支删掉 → `test_evidence_closure_covers_concept_kinds`
  转红；`close_review` 整体因 `evidence_closure` 不过而拒审（若这是既有行为，
  贴出改前/改后的拒审 reason 对比）。

## 2. M7 概念发号（`pipeline/assembly/apply.py`/`incremental.py`）

新增测试方法，加进既有 `pipeline/assembly/tests/test_apply.py` 的
`class TestApplyResolutions(unittest.TestCase)`，以及 `pipeline/assembly/
tests/test_incremental_proposals.py`（或执行者核实后确定的现有存放
`allocate_ids` 测试的文件——先 `grep -rn "def test.*allocate_ids"
pipeline/assembly/tests/` 核实放哪个文件）。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_approved_new_concept_candidate_allocates_fresh_co_id` | 单版次视图，`new_concept_candidates=[new_concept_candidate("天官")]`（`test_apply.py:139-146` 既有助手），`approved_index` 里含该候选对应的 `entity_id="天官"`（按 `_is_concept_candidate_approved` 实际读取的形状构造，与队列 §1 的身份规则一致），`base_knowledge["id_range"]["co_qizheng"] = [1, 999999]` | `apply_resolutions(...)` | `result["knowledge"]["concepts"]` 里出现一条 `concept_id` 匹配 `^co_qizheng_[0-9]{6}$`、`name == "天官"` 的新 Concept，`source_span_ids` 含该候选 `evidence` 的 span | `_build_concepts` 目前不读 `new_concept_candidates`，也没有发号函数，`co_` 号不会出现 |
| `test_two_approved_new_concept_candidates_get_distinct_ascending_ids_by_source_and_surface` | 两条不同 surface 的候选同批批准 | 同上 | 两个新号按 `(source_id, surface)` 升序分配、互不相同、不落在已用号上 | 同上 |
| `test_unapproved_new_concept_candidate_is_not_materialized` | `new_concept_candidates=[new_concept_candidate("通載")]`，**不**批准 | `apply_resolutions(...)` | `result["knowledge"]["concepts"]` 里没有"通載" | 回归护栏，取代原来的 `test_new_concept_candidates_without_pre_existing_concept_ref_are_not_silently_materialized`（README 2.4 已改名/改断言方向），Red 期即应为绿（本条不依赖本任务改动） |
| `test_new_concept_candidate_without_m6_approval_is_not_materialized_even_with_auto_proposal` | 候选走完 R04 auto 提案生成（走 `apply_resolutions` 正常 `proposals` 参数），但决定环节 reject 或缺失 | 同上 | 不材化；`report["admit_new_without_object"]` 如实含这一条（`reason: candidate_not_materialized`），因为它是"有提案、没批准"的情形 | 这是本节唯一真正的新护栏（对应 README 2.4），本任务改动 `_build_concepts` 后必须仍然守住这一条，若不小心把"只要有 auto 提案就材化"写错了，本用例转红 |
| `test_used_concept_numbers_include_retired_and_base_concepts` | `base_state["concepts"]` 与 `base_state["retired"]` 各含若干 `co_qizheng_NNNNNN` 号 | 调 `_used_concept_numbers(base_state, "qizheng")` | 返回集合含两边全部号，格式非 `co_qizheng_` 前缀的（如 `co_shared_qizheng_01`）不计入 | `_used_concept_numbers` 函数不存在，`AttributeError`/`ImportError` |
| `test_allocate_ids_reports_concept_watermark` | `base_knowledge` 含若干 `concepts[]`，加一条本轮已获批带正式 `co_` 号的 concept_mention 视图 | 调 `incremental.allocate_ids(base_knowledge, views)` | 返回值 `id_allocation` 含 `"co_qizheng"` 键，值为已用号最大值 | `allocate_ids`（`incremental.py:158-205`）现在只算 `"pat_%s"` 键，没有 concept 键 |
| `test_id_range_missing_co_key_defaults_to_zero_and_is_backfilled` | `base_knowledge["id_range"]` **没有** `"co_qizheng"` 键（模拟真书现有 Snapshot 的状态），且 `base_knowledge["concepts"]` 为空（这条只测缺键本身，不测撞号，撞号场景见下一条） | `apply_resolutions(...)` | 不抛异常（与 Pattern 缺 `pat_<tech>` 时的硬性 `AssemblyRefused` 刻意不同）；返回的 `knowledge["id_range"]["co_qizheng"]` 被回填为一个合理缺省（执行者按 README 2.2「向后兼容」选定的具体缺省值，写清楚选了什么并在这条用例里断言这个具体值） | 这是 README 2.2「向后兼容」一节要求的行为，实现前会直接 `AssemblyRefused`（如果照抄 Pattern 的硬性检查）或 `KeyError`（如果没处理这个键） |
| `test_id_range_missing_co_key_with_existing_concept_allocates_strictly_above_existing_max` | `base_knowledge["id_range"]` **没有** `"co_qizheng"` 键，但 `base_knowledge["concepts"]` 里**已经存在**一条带 `concept_ref` 的 `co_qizheng_000003`（例如仿 `mini_ed01` 那种"已有 concept_ref、不经本任务发号机制进 Snapshot"的既有概念），同批再批准一条 `new_concept_candidate` | `apply_resolutions(...)` | 新分配的号**严格大于** `3`（不是从 `1` 开始，不撞已存在的 `co_qizheng_000003`）；再补一种情形：`co_qizheng_000003` 不在活对象里而在 `base_knowledge["retired_entity_ids"]`（已退役），新号仍必须严格大于 `3`（与 Pattern 的 `_used_pattern_numbers` 同时扫活对象与退役号同一口径） | 若实现按「协调者更正前」的写法把缺键场景的 `range_start`/`watermark` 一律定死为 `0` 而不扫描 `base_state["concepts"]`/`base_state["retired"]`，新号会从 `1` 开始，撞上已存在的 `co_qizheng_000003`，本用例的"严格大于"断言失败 |

## 3. `pipeline/assembly/tests/test_apply.py`：Concept 装配时保留 span 归属

新增测试方法，加进既有 `class TestApplyResolutions(unittest.TestCase)`
（第 521 行起），复用文件里已有的 `concept_mention()`（第 129-136 行）、
`candidate_set()`（第 171-201 行左右）、`view_ed01()`/`view_ed02()`
（第 274-357 行左右）等既有 helper 的写法风格，不要另起一套 fixture 体系。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_concept_evidence_source_span_ids_are_carried_into_snapshot` | 单版次视图，`concept_mentions=[concept_mention("三辰", CO1)]`（`concept_mention()` 助手固定带 `evidence=[ev(SPAN_A)]`，见 `test_apply.py:129-136`），`approved` 里含 `(CO1, "concept")` | 调 `apply_resolutions(...)`（同 `view_ed01()` 已有的调用方式） | `result["knowledge"]["concepts"]` 里 `concept_id == CO1` 的那条含 `source_span_ids == ["ss_..."]`（`SPAN_A` 常量对应的 span_id，读 `test_apply.py` 顶部常量定义取实际值） | `_concept_provenance`（`apply.py:703-710`）当前不产出 `source_span_ids` 键，`KeyError` 或断言失败 |
| `test_concept_source_span_ids_union_across_multiple_mentions_same_source` | 同一 `source_id` 下，两条 `concept_mention` 指向同一个 `CO1`、各带不同 span（比照 `concept_mention()` 助手手写两条，`evidence` 分别指向 `SPAN_A`、`SPAN_C`） | 调 `apply_resolutions` | `source_span_ids` 是两个 span 的并集、排序、去重 | 同上，字段不存在 |
| `test_concept_source_span_ids_merge_across_editions` | 复用 `view_ed01()`（`CO1` 带 `SPAN_A`）与 `view_ed02()`（`CO1` 带另一个 span，`test_apply.py:328` 已有 `concept_mentions=[concept_mention("通載", CO1)]`），两版次一起 apply | `existing["source_span_ids"]` 覆盖两版次的并集，不丢失版次一已有的 span | `_build_concepts` 现有分支（`apply.py:669-698`）在"已存在的 concept"分支完全没碰 `source_span_ids`，字段不存在或只含后一版次 |

## 4. `pipeline/assembly/tests/test_model.py`：Snapshot 校验器接受/拒绝新字段

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_validate_snapshot_knowledge_accepts_concept_source_span_ids` | 构造一份含 `concepts: [{"concept_id": CO1, "name": "三辰", "aliases": [], "provenance": [...], "source_span_ids": ["ss_x"]}]` 的最小 `knowledge` 字典（比照 `model.py:414-429` 的 `empty_snapshot_knowledge` 输出手工补字段） | `validate_snapshot_knowledge(knowledge)` | 不抛异常 | 若新校验规则写成"未知键即拒收"这种严格模式，需要显式放行；若压根没加校验，此用例本身先绿也可以，但要另有一条校验"非法值必须拒收"的用例（见下一行），二者合起来才算把这个字段纳入了校验 |
| `test_validate_snapshot_knowledge_rejects_concept_source_span_ids_not_sorted_or_invalid` | 同上，但 `source_span_ids` 故意乱序或塞一个非法 span_id（如 `"not-a-span"`） | `validate_snapshot_knowledge(knowledge)` | 抛 `SchemaViolation`（乱序/重复）或 `InvalidIdentifier`（格式非法，经 `ids.validate("source_span_id", ...)`，仿 `model.py` 里 `_check_sorted`/其它字段现成的校验写法） | 新校验代码写之前，字典里多一个键不会被校验，用例转红 |
| `test_validate_snapshot_knowledge_accepts_allocated_concept_ids_and_co_id_range` | `knowledge["id_range"]["co_qizheng"] = [1, 999999]`，`knowledge["allocated_concept_ids"] = ["co_qizheng_000001"]` | `validate_snapshot_knowledge(knowledge)` | 不抛异常 | 新键未被 `empty_snapshot_knowledge`/校验器认识前会因未知键或格式检查缺失而行为不确定，需要这条钉住 |

## 5. `pipeline/dataset_compiler/tests/test_packs.py`：EvidenceMapPack 派生 mentions

加进既有 `class EvidenceMapPackTests(unittest.TestCase)`（第 206 行起）与
`class OffsetEvidenceAndReferenceOnlyTests(unittest.TestCase)`（第 759 行起，
offset 档），不要新开 class（除非发现既有 class 的 `setUp` 与本组用例强烈冲突，
那样要在回报里说明为什么另开）。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_evidence_map_pack_mentions_maps_concept_to_span_within_this_edition` | `snapshot_knowledge={"concepts": [{"concept_id": "co_qizheng_000001", "source_span_ids": ["ss_qianyuan_ed01_o0008663"]}]}`（span_id 取自本 fixture 已有的某个真实 span，或测试自建的最小 spans_doc 里的 span_id，确保它也出现在 `spans_doc["spans"]` 里，即会进 `entries`） | `build_evidence_map_pack(..., snapshot_knowledge=snapshot_knowledge)` | 返回的 `pack["mentions"] == {"co_qizheng_000001": ["ss_qianyuan_ed01_o0008663"]}`，且这个 span_id 同时出现在 `pack["entries"]` 的键里（可回指，场景一） | `build_evidence_map_pack` 当前不产 `mentions` 键，`KeyError` |
| `test_evidence_map_pack_mentions_excludes_spans_outside_this_edition_entries` | `snapshot_knowledge` 里某个 concept 的 `source_span_ids` 含一个**不属于**本次 `spans_doc["spans"]` 的 span_id（模拟跨版次遗留） | 同上调用 | `pack["mentions"]` 里该 concept 对应的列表**不含**这个外部 span_id（若该 concept 因此变成空列表，`mentions` 里这个 concept_id 键本身是否保留——保留但值为 `[]`，本条断言按 README「场景二」定，执行者动手前把这条的具体断言写死在测试里再看 Red，不要含糊） | 同上，字段不存在；即使加了字段，若实现偷懒直接搬运整段 `source_span_ids` 不做交集过滤，本用例专门抓这个疏漏 |
| `test_evidence_map_pack_mentions_is_empty_dict_when_no_concept_has_spans` | `snapshot_knowledge={"concepts": []}` 或所有 concept 的 `source_span_ids` 为空 | 同上调用 | `pack["mentions"] == {}`（键必须存在，不是 `None`，仿 `page_index`/`excluded_pages` 的既有写法） | 同上 |
| `test_offset_evidence_map_pack_mentions_same_derivation_as_glyphbox` | offset 档最小夹具（复用 `OffsetEvidenceAndReferenceOnlyTests` 已有的 `setUp` 数据） + 一个带 `source_span_ids` 的 concept | `_build_offset_evidence_map_pack(...)` | 同样产出正确的 `mentions`（offset 档函数目前完全不接 `snapshot_knowledge` 形参——见 `packs.py:452-453` 签名，本用例会先因为"函数不接受这个新形参"而 ERROR，逼着执行者把形参也补上，并确认 `build_evidence_map_pack` 第 329-336 行的 offset 分派把新形参转过去） | `TypeError: unexpected keyword argument` |

## 6. R15：真实形状全链路（qianyuan_ed01_text 宿主，走完整 M4→M6→M7→M8）

写在 `test_packs.py` 或新建
`pipeline/dataset_compiler/tests/test_t05a_mentions_real_shape.py`（**新建
哪个由执行者按现有测试目录惯例决定，写清楚放哪个文件、为什么**）。

| 测试名 | 准备 | 动作 | 断言 |
|---|---|---|---|
| `test_real_shape_mentions_round_trip_from_qianyuan_snapshot` | 用 `pipeline/corpus/_fixture/qianyuan_ed01_text` 宿主跑到 M3（`run_m1`→`run_m2`→`run_m3_text`，比照 `pipeline/dataset_compiler/acceptance.py` 里 `_prepare_ledger` 的既有调用序列），继续走 M4（复用该宿主已有的抽取件，或补一个最小 `new_concept_candidate` 提交件——span_id 与原文文本必须来自真实 `corpus_spans` 修订，用 `pipeline/tools/rebuild_m4_span_list.py` 的既有查询方式核实存在），M6 走公开入口批准这条候选，M7 `apply_resolutions` 装配 Snapshot（**在临时目录的 Ledger 副本上**，不落盘进真书正本，不改 fixture） | 调 `run_m8`（走 `resolve_m8_inputs` 正常输入，不绕 LedgerPort） | Snapshot.concepts 里出现对应新 Concept、`evidence_map_pack.mentions` 非空且回指的 span_id 能在 `evidence_map_pack.entries` 里查到对应 `text`；`mentions_mapping` 判据（复用 `acceptance.py:642-653` 的函数直接调用，或整跑 `--check span_identity`）落在 `PASS` |

这条是 README「BDD 场景四」与 AGENTS.md 隐含的 R15 规则（真实形状输入走完全栈）的
落地。**不得**用编造的、书里没有的原文内容；span_id 与其原文文本都必须来自真实
`corpus_spans` 修订。

## 7. 篡改探针（写进 act/01.yaml 的 verify 部分，此处列清单）

1. 把 `_concept_provenance` 改回不带 `source_span_ids`（还原第 3 节改动）
   → 第 3 节用例转红。
2. 把 `build_evidence_map_pack` 里 mentions 的交集过滤去掉（直接搬运整段
   `source_span_ids`，不管是否属于本 edition_part 的 entries）
   → `test_evidence_map_pack_mentions_excludes_spans_outside_this_edition_entries` 转红。
3. 让 `mentions` 在没有任何 span 时返回 `None` 而不是 `{}`
   → `test_evidence_map_pack_mentions_is_empty_dict_when_no_concept_has_spans` 转红。
4. 删掉 R15 用例里 M6 对候选的批准决定（改成 reject）
   → `test_real_shape_mentions_round_trip_from_qianyuan_snapshot` 转红，
   `mentions_mapping` 判据回落到 BLOCKED/FAIL。
5.（第 1 节）把 M6 队列构造里 concept 类那两段删掉 → 第 1 节 5 条用例全部转红。
6.（第 2 节）把 `_build_concepts` 里"消费已批准 new_concept_candidates"那段
   删掉 → 第 2 节 `test_approved_new_concept_candidate_allocates_fresh_co_id`
   等转红。
7.（第 2 节，撞号护栏，2026-09-26 协调者更正新增）把缺
   `id_range["co_qizheng"]` 时的 `watermark` 计算改回"缺键就是 `0`"
   （即改回不扫描 `base_state["concepts"]`/`base_state["retired"]` 的旧写法）
   → `test_id_range_missing_co_key_with_existing_concept_allocates_strictly_above_existing_max`
   转红（新号会撞上已存在的 `co_qizheng_000003`）。

每条篡改前先 `cp` 备份改动文件（不是整仓），验证转红后立刻 `cp` 恢复，
把"改前 OK / 改后转红 / 恢复后 OK"三行贴进回报，不许只写结论。

## 8. 回归（每步改动后）

```bash
$TA 2>&1 | tail -1                 # 不得比开工基线多任何 skipped，OK 数只增不减
$TR 2>&1 | tail -1
$TD 2>&1 | tail -1
bash openspec/acceptance/m8-span-identity.sh 2>&1 | tail -1
bash openspec/acceptance/run_all.sh | tail -1     # 不得让已 PASS 的行退步
git diff --check
```
