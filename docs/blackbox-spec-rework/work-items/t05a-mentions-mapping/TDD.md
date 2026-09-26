# TDD：T05a concept→span 的 mentions 映射

`export LC_ALL=en_US.UTF-8`（macOS）/ `export LC_ALL=C.UTF-8`（云端容器，见
AGENTS.md）；`PY=.venv/bin/python`；
`TA="$PY -m unittest discover -s pipeline/assembly/tests -t ."`；
`TD="$PY -m unittest discover -s pipeline/dataset_compiler/tests -t ."`；
在仓库根运行。

**前提**：本文档的用例只在「README.md 二、待用户决定 #1/#2」都已获批准
（#1 采纳候选 (c)：`new_concept_candidates` 发号机制不在本任务做）之后才动手写。
若尚未批准，执行者到此止步，不建这些测试文件的实现部分（测试本身可以先写，
但不许改 `apply.py`/`packs.py`/`model.py` 让它们变绿）。

## 0. 开工基线

```bash
git status --short pipeline/assembly pipeline/dataset_compiler docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md   # 空
$TA 2>&1 | tail -1     # 基线：OK 305 (skipped=2)（合并 claude/wizardly-maxwell-pqrzh9 后的数字，执行者开工时实测核对，若不同就地记录基线，不当成异常）
$TD 2>&1 | tail -1     # 基线：OK 279（同上，`docs/handoff/T04-CLOUD.report.md:211` 已记 279；执行者开工时以自己实跑为准）
bash openspec/acceptance/m8-span-identity.sh 2>&1 | tail -1   # 基线：SUMMARY pass=7 fail=0 blocked=1，exit 2
```

## 1. `pipeline/assembly/tests/test_apply.py`：Concept 装配时保留 span 归属

新增测试方法，加进既有 `class TestApplyResolutions(unittest.TestCase)`
（第 521 行起），复用文件里已有的 `concept_mention()`（第 129-136 行）、
`candidate_set()`（第 171-201 行左右）、`view_ed01()`/`view_ed02()`
（第 274-357 行左右）等既有 helper 的写法风格，不要另起一套 fixture 体系。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_concept_evidence_source_span_ids_are_carried_into_snapshot` | 单版次视图，`concept_mentions=[concept_mention("三辰", CO1)]`（`concept_mention()` 助手固定带 `evidence=[ev(SPAN_A)]`，见 `test_apply.py:129-136`），`approved` 里含 `(CO1, "concept")` | 调 `apply_resolutions(...)`（同 `view_ed01()` 已有的调用方式） | `result["knowledge"]["concepts"]` 里 `concept_id == CO1` 的那条含 `source_span_ids == ["ss_..."]`（`SPAN_A` 常量对应的 span_id，读 `test_apply.py` 顶部常量定义取实际值） | `_concept_provenance`（`apply.py:703-710`）当前不产出 `source_span_ids` 键，`KeyError` 或断言失败 |
| `test_concept_source_span_ids_union_across_multiple_mentions_same_source` | 同一 `source_id` 下，两条 `concept_mention` 指向同一个 `CO1`、各带不同 span（比照 `concept_mention()` 助手手写两条，`evidence` 分别指向 `SPAN_A`、`SPAN_C`） | 调 `apply_resolutions` | `source_span_ids` 是两个 span 的并集、排序、去重 | 同上，字段不存在 |
| `test_concept_source_span_ids_merge_across_editions` | 复用 `view_ed01()`（`CO1` 带 `SPAN_A`）与 `view_ed02()`（`CO1` 带另一个 span，`test_apply.py:328` 已有 `concept_mentions=[concept_mention("通載", CO1)]`），两版次一起 apply | `existing["source_span_ids"]` 覆盖两版次的并集，不丢失版次一已有的 span | `_build_concepts` 现有分支（`apply.py:669-698`）在"已存在的 concept"分支完全没碰 `source_span_ids`，字段不存在或只含后一版次 |
| `test_new_concept_candidates_without_pre_existing_concept_ref_are_not_silently_materialized` | 沿用 `view_ed01()` 里已有的 `new_concept_candidates=[new_concept_candidate("通載")]`（`test_apply.py:287`），**不**在 `approved` 里加任何对应批准项（与现状一致，即待用户决定 #1 采纳 (c) 之后的预期行为） | 调 `apply_resolutions` | `result["knowledge"]["concepts"]` 里没有一条因为这个 `new_concept_candidate` 而出现（即"通載"仍不是任何 `concept_id` 的 `name`/`aliases`，除非它同时也被写进某条 `concept_mention` 且带 `concept_ref`） | 这是一条**回归护栏**，Red 期即应为绿（现状本来就不材化）；若本任务的改动让它意外材化了，说明动了「待用户决定 #1」范围外的东西，必须转红逼停 |

## 2. `pipeline/assembly/tests/test_model.py`：Snapshot 校验器接受/拒绝新字段

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_validate_snapshot_knowledge_accepts_concept_source_span_ids` | 构造一份含 `concepts: [{"concept_id": CO1, "name": "三辰", "aliases": [], "provenance": [...], "source_span_ids": ["ss_x"]}]` 的最小 `knowledge` 字典（比照 `model.py:414-429` 的 `empty_snapshot_knowledge` 输出手工补字段） | `validate_snapshot_knowledge(knowledge)` | 不抛异常 | 若新校验规则写成"未知键即拒收"这种严格模式，需要显式放行；若压根没加校验，此用例本身先绿也可以，但要另有一条校验"非法值必须拒收"的用例（见下一行），二者合起来才算把这个字段纳入了校验 |
| `test_validate_snapshot_knowledge_rejects_concept_source_span_ids_not_sorted_or_invalid` | 同上，但 `source_span_ids` 故意乱序或塞一个非法 span_id（如 `"not-a-span"`） | `validate_snapshot_knowledge(knowledge)` | 抛 `SchemaViolation`（乱序/重复）或 `InvalidIdentifier`（格式非法，经 `ids.validate("source_span_id", ...)`，仿 `model.py` 里 `_check_sorted`/其它字段现成的校验写法） | 新校验代码写之前，字典里多一个键不会被校验，用例转红 |

## 3. `pipeline/dataset_compiler/tests/test_packs.py`：EvidenceMapPack 派生 mentions

加进既有 `class EvidenceMapPackTests(unittest.TestCase)`（第 206 行起）与
`class OffsetEvidenceAndReferenceOnlyTests(unittest.TestCase)`（第 759 行起，
offset 档），不要新开 class（除非发现既有 class 的 `setUp` 与本组用例强烈冲突，
那样要在回报里说明为什么另开）。

| 测试名 | 准备 | 动作 | 断言 | 预期先红原因 |
|---|---|---|---|---|
| `test_evidence_map_pack_mentions_maps_concept_to_span_within_this_edition` | `snapshot_knowledge={"concepts": [{"concept_id": "co_qizheng_000001", "source_span_ids": ["ss_qianyuan_ed01_o0008663"]}]}`（span_id 取自本 fixture 已有的某个真实 span，或测试自建的最小 spans_doc 里的 span_id，确保它也出现在 `spans_doc["spans"]` 里，即会进 `entries`） | `build_evidence_map_pack(..., snapshot_knowledge=snapshot_knowledge)` | 返回的 `pack["mentions"] == {"co_qizheng_000001": ["ss_qianyuan_ed01_o0008663"]}`，且这个 span_id 同时出现在 `pack["entries"]` 的键里（可回指，场景一） | `build_evidence_map_pack` 当前不产 `mentions` 键，`KeyError` |
| `test_evidence_map_pack_mentions_excludes_spans_outside_this_edition_entries` | `snapshot_knowledge` 里某个 concept 的 `source_span_ids` 含一个**不属于**本次 `spans_doc["spans"]` 的 span_id（模拟跨版次遗留） | 同上调用 | `pack["mentions"]` 里该 concept 对应的列表**不含**这个外部 span_id（若该 concept 因此变成空列表，`mentions` 里这个 concept_id 键本身是否保留——按候选 (a) 保留但值为 `[]`，还是整键剔除，本条断言按 README「场景二」定，执行者动手前把这条的具体断言写死在测试里再看 Red，不要含糊） | 同上，字段不存在；即使加了字段，若实现偷懒直接搬运整段 `source_span_ids` 不做交集过滤，本用例专门抓这个疏漏 |
| `test_evidence_map_pack_mentions_is_empty_dict_when_no_concept_has_spans` | `snapshot_knowledge={"concepts": []}` 或所有 concept 的 `source_span_ids` 为空 | 同上调用 | `pack["mentions"] == {}`（键必须存在，不是 `None`，仿 `page_index`/`excluded_pages` 的既有写法） | 同上 |
| `test_offset_evidence_map_pack_mentions_same_derivation_as_glyphbox` | offset 档最小夹具（复用 `OffsetEvidenceAndReferenceOnlyTests` 已有的 `setUp` 数据） + 一个带 `source_span_ids` 的 concept | `_build_offset_evidence_map_pack(...)` | 同样产出正确的 `mentions`（offset 档函数目前完全不接 `snapshot_knowledge` 形参——见 `packs.py:452-453` 签名，本用例会先因为"函数不接受这个新形参"而 ERROR，逼着执行者把形参也补上，并确认 `build_evidence_map_pack` 第 329-336 行的 offset 分派把新形参转过去） | `TypeError: unexpected keyword argument` |

## 4. R15：真实形状全链路（qianyuan_ed01_text 宿主，写在 `test_packs.py` 或新建
`pipeline/dataset_compiler/tests/test_t05a_mentions_real_shape.py`——**新建哪个由执行者
按现有测试目录惯例决定，写清楚放哪个文件、为什么**）

| 测试名 | 准备 | 动作 | 断言 |
|---|---|---|---|
| `test_real_shape_mentions_round_trip_from_qianyuan_snapshot` | 用 `pipeline/corpus/_fixture/qianyuan_ed01_text` 宿主跑到 M3（`run_m1`→`run_m2`→`run_m3_text`，比照 `pipeline/dataset_compiler/acceptance.py` 里 `_prepare_ledger` 的既有调用序列），**在临时目录的 Ledger 副本上**手工构造一份最小 `CanonicalKnowledgeSnapshot`（不落盘进真书正本，不改 fixture）：技法 `qizheng`、一个带 `source_span_ids=["ss_qianyuan_ed01_o0008663"]` 的 concept（span_id 取自真实 `corpus_spans`，用 `pipeline/tools/rebuild_m4_span_list.py` 的既有查询方式核实这个 span_id 真实存在于该 edition_part），一个引用该 span 的 assertion | 调 `run_m8`（走 `resolve_m8_inputs` 正常输入，不绕 LedgerPort） | `evidence_map_pack.mentions` 非空且回指的 span_id 能在 `evidence_map_pack.entries` 里查到对应 `text`；`mentions_mapping` 判据（复用 `acceptance.py:642-653` 的函数直接调用，或整跑 `--check span_identity`）落在 `PASS` |

这条是 README「BDD 场景四」与 AGENTS.md 隐含的 R15 规则（真实形状输入走完全栈）的
落地。**不得**用编造的、书里没有的原文内容；span_id 与其原文文本都必须来自真实
`corpus_spans` 修订。

## 5. 篡改探针（写进 act/01.yaml 的 verify 部分，此处列清单）

1. 把 `_concept_provenance` 改回不带 `source_span_ids`（还原第 1 节改动）
   → `test_concept_evidence_source_span_ids_are_carried_into_snapshot` 等第 1 节用例转红。
2. 把 `build_evidence_map_pack` 里 mentions 的交集过滤去掉（直接搬运整段
   `source_span_ids`，不管是否属于本 edition_part 的 entries）
   → `test_evidence_map_pack_mentions_excludes_spans_outside_this_edition_entries` 转红。
3. 让 `mentions` 在没有任何 span 时返回 `None` 而不是 `{}`
   → `test_evidence_map_pack_mentions_is_empty_dict_when_no_concept_has_spans` 转红。
4. 删掉 R15 用例里 Snapshot 手工构造的 `source_span_ids`
   → `test_real_shape_mentions_round_trip_from_qianyuan_snapshot` 转红，
   `mentions_mapping` 判据回落到 BLOCKED/FAIL。

每条篡改前先 `cp` 备份改动文件（不是整仓），验证转红后立刻 `cp` 恢复，
把"改前 OK / 改后转红 / 恢复后 OK"三行贴进回报，不许只写结论。

## 6. 回归（每步改动后）

```bash
$TA 2>&1 | tail -1                 # 不得比开工基线多任何 skipped，OK 数只增不减
$TD 2>&1 | tail -1
bash openspec/acceptance/m8-span-identity.sh 2>&1 | tail -1
bash openspec/acceptance/run_all.sh | tail -1     # 不得让已 PASS 的行退步
git diff --check
```
