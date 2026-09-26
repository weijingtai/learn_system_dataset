# T05a：M8 concept→span 的 mentions 映射

## 0. 目标

`openspec/acceptance/m8-span-identity.sh` 目前 7 PASS + `mentions_mapping` BLOCKED（exit 2）。
本任务把 `mentions_mapping` 从 BLOCKED 推进到真正的 PASS，并让真书/`qianyuan_ed01_text`
宿主上 M6 通过的新概念真正进入 Snapshot、在 M8 产出词条。

> **裁决状态（用户 2026-09-26）**：原「二、待用户决定」两项均已裁决为 (a)，
> 见「二、已裁决」。**本任务范围已扩大**，不再是"只处理已有 concept_ref 的
> concept_mention"这个收窄版本——新概念发号（M7 概念创世）与 M6 队列纳入
> concept 类候选（前置步骤）都在本任务范围内，逐条机械步骤见下方「二」。

> **基线更正（本文档定稿时已核实）**：本任务书基于分支 `worktree-agent-a05fa5819d06e2a48`
> 与 `claude/wizardly-maxwell-pqrzh9`（`d3c01d3`）合并后的树核实，**不是** main。
> 合并带来的关键变化：**T04 已完成**——真书《乾元秘旨》已在账本副本
> `var/ledgers/qianyuan_t04` 上跑通 M1→M8；**T05f 已完成**（`packs.build_knowledge_data_pack`
> /`build_graph_projection_pack`/`build_evidence_chain` 已在 `pipeline/dataset_compiler/step.py`
> 里真实接入 `run_m8`，不再是"只有测试在调"）。下面 1.1–1.4 的行号均已按合并后的树重新核对。
> 真书实测结果（`docs/handoff/T04-CLOUD.report.md:186,225`，`--check publication
> --ledger var/ledgers/qianyuan_t04`）：`knowledge_chain 知识链闭合：2 个词条、26 条断言；
> 2 条七段证据链逐条回指 span；无主体断言 24 条已按 §3.8 披露`——与用户交代的现状完全一致。

`mentions_mapping` 判据的判定代码：`pipeline/dataset_compiler/acceptance.py:642-653`
（`_check_mentions_mapping`）——它只看 `evidence_map_pack` 里有没有一个非空的
`mentions` 键（`facts["mentions"] = evidence.get("mentions")`，取自
`pipeline/dataset_compiler/acceptance.py:617-633` 的 `_m8_output_facts`，
`mentions` 赋值在第 633 行）。**这个键目前在任何路径下都不存在**：
`pipeline/dataset_compiler/packs.py` 的 `build_evidence_map_pack`
（第 293-449 行）与 `_build_offset_evidence_map_pack`（第 452-528 行）
产出的 pack 字典里都没有 `mentions` 这个键（已用 `Read` 重新核对合并后的
`packs.py` 全文，`compute_known_defects` 因 T04B 多了一个
`assertion_without_subject` 形参致使行号从合并前的 531 行起后移，但
`build_evidence_map_pack` 起始行仍是 293，内容逐字未变）。

> **附带发现（出了本任务范围，不改，只记录）**：合并后的 `step.py` 里，
> `_compile_knowledge_and_chain`（`step.py:424`）把七段证据链文档也
> `_put_sealed(service, step_run_id, "evidence_map_pack", chain_bytes)`——
> 与 `step.py:604` 那条真正的 `packs.build_evidence_map_pack` 输出用了
> **同一个 artifact_type 字符串** `"evidence_map_pack"`，在同一个 `step_run_id`
> 下产生两条 artifact_type 相同但内容结构完全不同的修订。发布包层面靠
> `publication_packs` 的键名区分（`step.py:760` 用 `evidence_map_pack`
> 键存前者的 revision id，`step.py:768` 用 `evidence_chain` 键存后者），
> 不会互相覆盖，`mentions_mapping` 判据实际读到的仍是前者（span 身份那份）
> ——所以不影响本任务的判定，但这是 Ledger 内 artifact_type 命名的一个真实
> 缺陷，建议另开一条 TODO（如 T05a3）由主 Agent核实后请用户裁决要不要改名，
> 本任务不得顺手改。

## 1. 根因：数据在哪一步断的（逐段实测追踪）

链路：M4 `concept_mention` 候选 →（M6 审核，本任务不改）→ M7 `apply.py` 装配进
`CanonicalKnowledgeSnapshot.knowledge.concepts` → M8 `packs.build_evidence_map_pack`
读 `snapshot_knowledge` 产出发布包。**断点有三处，都在 M7 装配这一步**，M8 侧还有一处
「从未写过这个功能」的空白。

### 1.1 M4 侧：候选本身携带 span 证据（未断，验证用）

`pipeline/knowledge_extraction/assemble.py:582-611` 把两路 lane 的抽取结果规约为
`candidate_set.concept_mentions[]`（`{surface, concept_ref, evidence, content_status, origin}`）
与 `candidate_set.new_concept_candidates[]`（`{surface, technique_id, evidence, content_status, origin}`）。
`evidence` 都是 `[{source_span_id, support_type}]`（`pipeline/knowledge_extraction/submission.py:204-220`
的 `_concept_mention_item` 规范化）。**真书实测**（`pipeline/corpus/_fixture/qianyuan_ed01_text/m4/submission_concept_mention_a.yaml`，
已用 `cat` 读出）：a 路 7 个 surface（天官/七煞/化禄/通根/天官经/伤官/食神），
每个都有 `evidence: [{source_span_id: ss_qianyuan_ed01_..., support_type: direct}]`，
**但 7 个 item 都没有 `concept_ref` 字段**（b 路同样没有）。

`assemble.py:592`：`if item["concept_ref"] is not None:` 进 `concept_mentions`，
否则进 `new_concept_candidates`。真书这 7 项 `concept_ref` 缺省即 `None`
（`pipeline/knowledge_extraction/submission.py:153`：`"concept_refs"` 是断言字段，
`_concept_mention_item` 里 `concept_ref` 单数字段若原文没给就是 `None`——见
`pipeline/knowledge_extraction/__init__.py:53-56` 该类目字段定义），**所以真书这
7 项全部落进 `new_concept_candidates`，没有一项进入 `concept_mentions`**。

### 1.2 M6/M7 侧断点 A：`new_concept_candidates` 批准后从不材化为 Concept

`pipeline/assembly/incremental.py:360-373`（R04 提案生成）会把 `new_concept_candidates`
与 `concept_mentions` 一起按 surface/concept_ref 分组出 `merge`/`alias` 提案，`admit_new`
分支（`incremental.py:404-409`）走**自动**批准——即真书这 7 个 surface 理论上会各自
生成一条 `admit_new` 提案并被批准。

但批准之后，**没有任何代码给它们发一个新的 `co_qizheng_NNNNNN` 号**：

- `pipeline/assembly/model.py:414-429`（`empty_snapshot_knowledge`）的 `id_range` 只要求
  `pat_<technique_id>` 这一个键（`model.py:445-446`：`expected_range_key = "pat_%s" % tech`），
  **没有 `co_<technique_id>` 的号段**。
- `pipeline/assembly/apply.py:835`（`_new_pattern`）是 Pattern 唯一的发号函数，
  `apply.py:744-756`（`_build_patterns` 里 `number = max(watermark + 1, range_start)` 的循环）
  是 Pattern 唯一的号池游标逻辑。**Concept 没有对应函数**——全仓库对
  `technique_concept_id` 唯一的处理是 `apply.py:86-112`（`_validate_node_id`，M8 侧）与
  `apply.py:656`（`_build_concepts` 里的 `ids.kind_of(ref) != "technique_concept_id"` 校验），
  两处都只**校验**已有的号，不**发**新号。
- `pipeline/assembly/apply.py:639-700`（`_build_concepts`）只读
  `view["candidate_set"].get("concept_mentions", [])`（第 650 行），**从不读
  `new_concept_candidates`**。`view["candidate_set"]` 是原始 M4 候选集
  （`apply.py:507`：`"candidate_set": cset_doc`，未被 M6 决定改写——决定只在
  `reviewed_edition`/`approved_index` 里，`candidate_set` 字节本身不变）。

  实测（读测试夹具核实此路径确实空转）：`pipeline/assembly/tests/test_apply.py:171-187`
  的 `candidate_set()` 助手、`test_apply.py:139-146` 的 `new_concept_candidate()` 助手、
  `test_apply.py:287`（`view_ed01()` 里 `new_concept_candidates=[new_concept_candidate("通載")]`）——
  但同一视图的 `approved=[...]`（`test_apply.py:296-299`）里**没有给"通載"的批准项**
  （只批准了 `concept_mentions` 里那条 `三辰`/`CO1`），全仓库找不到一个测试断言
  "一个 `new_concept_candidate` 被批准后出现在 `result["knowledge"]["concepts"]` 里"。
  这不是我漏看，是这条路径确实没人写过。

**结论 A**：M4 阶段"没有预先声明 `concept_ref` 的新术语"（真书的正常情形——
天官/七煞等都是这份书第一次出现的术语，不可能预先有号）目前**完全没有材化为
Concept 的路径**。这不是一个可以在本任务里"顺手补上"的小 bug——它需要一套发号
机制（号段、水位线、确定性、跨 Release 保号），量级接近 `_build_patterns` 那一整块
逻辑，而 Snapshot 的 `id_range`/`id_allocation` schema 也要跟着扩一个 `co_<tech>` 键。
**用户 2026-09-26 已裁决要做这套发号机制**，机械步骤见「二、已裁决」2.2。

真书实测数字与这个结论**不矛盾**（本环境没有 `var/ledgers/qianyuan_t04`
与 `.venv`，无法在本任务书定稿前重新跑一遍 `--check publication` 亲眼核实
`concepts[]` 是否恰为空列表，**这一步推断标注为待执行者在拿到真书账本的机器上
用下面命令复核，不作为已核实事实陈述**）：

```
.venv/bin/python -m pipeline.dataset_compiler.acceptance \
  --fixture pipeline/corpus/_fixture/qianyuan_ed01_text \
  --check publication --ledger var/ledgers/qianyuan_t04
```

推断依据：`docs/handoff/T04-CLOUD.report.md:187,226`（`graph_projection`
判据）报告 `28 节点、2 条关系`；`packs.py:704-710`（`build_graph_projection_pack`）
把 `kind=concept` 的节点接在 `knowledge_data.concepts`，而
`build_knowledge_data_pack` 的 `pack["concepts"]`（`packs.py:1053-1063`）
直接取自 `snapshot_knowledge.get("concepts", [])` 排序后原样搬入——
若 Snapshot 里真有 Concept 材化，`concepts[]` 就会非空、`graph_projection_pack`
里就会出现 `kind=concept` 的节点。执行者按上面命令复核后，把「真书 Snapshot
`concepts` 是否为空列表」的结论写进回报，不确定就如实写"未能复核"，不要
替我把这条断言当成已证实的事实。

### 1.3 M6/M7 侧断点 B：即使 concept_ref 已存在，evidence（span）在装配时被丢弃

即使某条 `concept_mention` **已经**带着合法 `concept_ref`（比如跨 Release 复用旧概念，
或未来断点 A 解决后），`pipeline/assembly/apply.py:639-700`（`_build_concepts`）装配出的
Concept 对象也**不含任何 span 信息**：

```
apply.py:649   mentions: Dict[str, List[dict]] = {}
apply.py:650-653  for mention in view["candidate_set"].get("concept_mentions", []):
                       ref = mention.get("concept_ref")
                       if ref:
                           mentions.setdefault(ref, []).append(mention)
apply.py:666   surfaces = sorted({nfc_key(item["surface"]) for item in items})
apply.py:671-676  by_id[ref] = {"concept_id": ref, "name": surfaces[0],
                                 "aliases": surfaces[1:],
                                 "provenance": [_concept_provenance(...)]}
```

`_concept_provenance`（`apply.py:703-710`）只取 `name`/`aliases`/`content_status`，
`mention["evidence"]`（即 `source_span_id`）**从未被读取**。对比同一文件里断言的
装配（`apply.py:918,928`：`evidence = _evidence_of(candidate, links_by_entity)` 与
`"source_span_ids": sorted({item["source_span_id"] for item in evidence})`）——断言
有这一步，概念没有。

`pipeline/assembly/model.py:432-674`（`validate_snapshot_knowledge`）逐项校验
`concepts`/`patterns`/`assertions`/`school_views`，**从未提到 concept 上的
`source_span_ids` 或类似字段**（第 521 行只 `_check_sorted` 按 `concept_id` 排序），
印证 Concept 目前的 schema 里根本没有留 span 字段的位置。

**结论 B**：即使概念已经存在（断点 A 之外的路径），span 归属信息在
`_build_concepts`/`_concept_provenance` 这一步就被丢了。这是本任务范围内、
风险可控的机械修复（加一个字段、把已经在手的 `evidence` 里的 `source_span_id`
接上去），不涉及发号，不改变任何既有 ID。

### 1.4 M8 侧空白：`mentions` 字段从未被设计，`§3.10` 登记的形状对不上实现

`docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md:330-349`
（`§3.10 evidence_map_pack.schema.json`）登记的形状是
`{release_id, chains[] minItems 1}`，每条 chain 恰 7 键——**这其实是
`build_evidence_chain`（`pipeline/dataset_compiler/packs.py:1105-1210`）产出的
证据链条目形状，不是 `build_evidence_map_pack` 实际产出的形状**
（`packs.py:426-439`：`pack_type/schema_version/source_id/.../entries/page_index/excluded_pages`，
`offset` 档在 `packs.py:503-517` 另一套键）。`§3.10` 与代码实现的这处名实不一致
是既有缺陷，本任务**不修**（超出范围，已如实记录，供另立任务处理）；但它说明：
`evidence_map_pack.mentions` **在任何登记文档里都不存在**——这不是"漏读了规格"，
是规格确实没写。机械步骤见「二、已裁决」2.5。

`pipeline/dataset_compiler/step.py:595-601`（`run_m8` 里调用 `build_evidence_map_pack`）
已经把 `inputs["snapshot_knowledge"]` 传进去（`snapshot_knowledge=inputs["snapshot_knowledge"]`）
——**这条线本身是通的**，只是 `build_evidence_map_pack` 目前只用它算
`knowledge_chain`（`packs.py:313`），没有用它算任何 concept→span 的东西。
即：**只需要改 `packs.py`（M8 纯函数层）与 `apply.py`/`model.py`（M7），
不需要新的 M8 输入接线**。（T05f 合并进来后，`snapshot_knowledge` 同一份对象
在 `step.py:378-379`、`step.py:687` 也被 `build_knowledge_data_pack`/
`build_graph_projection_pack` 复用；本任务给 concept 加字段不影响这两处，
因为它们各自只读自己关心的键。）

### 1.5 与「无主体断言」的关系（重要边界，防止误判完成）

`pipeline/dataset_compiler/packs.py:865-902`（`build_knowledge_data_pack` 文档注释）与
`docs/blackbox-spec-rework/G7-RULINGS.md` 第 107 条裁决 Q-M8-01 原文明确：
**assertion 的主体只来自 Snapshot 中已审定的显式引用**——Pattern 的
`assertion_ids`（轨道一）与 **assertion 自己的 `concept_refs`**（轨道二，
`packs.py:919-937`）。这是**另一个字段**（assertion 级，`assertion.concept_refs`，
复数），跟本任务要修的「concept 对象上挂 span」完全不是一回事，也**不经过**
`concept_mention`/`_build_concepts`。

实测：`pipeline/corpus/_fixture/qianyuan_ed01_text/m4/submission_assertion_a.yaml`
（已用 `cat` 读出前 60 行）与 b 路提交件里，**没有一条 assertion item 带
`concept_refs` 字段**（`assemble.py:192,200` 会把缺省值规约为 `[]`）。
`pipeline/assembly/apply.py:890-973`（`_build_assertions`）装配 Snapshot 断言时，
产出的字典（`apply.py:921-932`）里也**没有 `concept_refs` 这个键**——
即使 M4 侧填了，M7 这一步也接不住。

`pipeline/tools/supplement_m4_concept_mentions.py:22,145-146`（脚本头部注释）
与第 107 条裁决原文都明确写着：`concept_refs` **一律不推断**，
"若真书最终 entry 数为 0，M8 知识链 Gate 如实失败并报告，由主 Agent 请用户在
M6 以 `modify` 补显式引用——**不由 Agent 代补**（P7）"。

**结论**：本任务**不得**、也**不能**通过工程手段让 assertion 的 `concept_refs`
凭空出现——那违反已经落笔的裁决，是明确禁止的"推断"。真书「26 条断言 24 条无主体」
这个数字（**已用当前真书账本副本实测复核**：`.venv/bin/python -m
pipeline.dataset_compiler.acceptance --fixture pipeline/corpus/_fixture/qianyuan_ed01_text
--check publication --ledger var/ledgers/qianyuan_t04`，输出见
`docs/handoff/T04-CLOUD.report.md:217-228`：`knowledge_chain` 一行逐字为
"2 个词条、26 条断言...无主体断言 24 条已按 §3.8 披露"），**不会**因为本任务而下降，
除非：(a) 用户在 M6 走 `modify` 显式补 `concept_refs`（人工，P7 已裁定不由 Agent 代做），
或 (b) 本任务「二、已裁决」2.2 的概念发号落地之后，某些断言恰好通过其他显式引用
路径获得主体——但这仍然是"轨道一/轨道二是否命中"的问题，跟 mentions 映射是否
产出无必然因果。

**如果验收时发现「无主体断言数」没有变化，这是符合裁决的正确结果，不是本任务
失败**。见 ACT 完成判据里对此的明确措辞与 act/01.yaml 的「不做」清单。

## 2. 已裁决（用户 2026-09-26，两项均选 (a)）

> 原「待用户决定 #1/#2」已裁决，**不另立 T05a2**，纳入本任务：
> 1) 新概念发号：仿 Pattern 建 concept 号池游标（`id_range` 增 `co_<tech>` 键、
>    `id_allocation` 同口径），M6 已审通过的 `new_concept_candidates` 在 M7 发
>    `co_` 号成为 Concept；
> 2) `mentions` 形状：Concept 加 `source_span_ids`，M8 派生 `mentions`（与之前
>    版本的建议 (a) 相同，未变）。
>
> 本节把裁决 1) 写成可严格照做的机械步骤：改哪些文件/函数、Snapshot schema
> 变更点与版本号、`INTERFACES.md` 需登记的章节、与现有 Pattern 发号逐条对照、
> 退役号/最大号既有边界如何处理。裁决 2) 的机械步骤仍是原「候选 (a)」段落
> （见下 2.5），未变。

### 2.0 前置实查结论：`new_concept_candidates` 目前**不在** M6 审核队列里

T19（`8d81337`）只把 **pattern** 纳入了 M6 `candidate_objects`/审核队列；
`concept_mention`/`new_concept_candidate` **没有**被纳入。实查证据：

- `pipeline/review/model.py:11`：`ENTITY_ID_KINDS = {"assertion": "assertion_id",
  "pattern": "pattern_id", "school_view": "school_view_id"}` —— 无 `concept`/
  `concept_mention`/`new_concept_candidate` 键。
- `pipeline/review/inputs.py:161-174`（`resolve_m6_inputs` 的 `candidate_objects`
  组装）：只收 `assertions`/`patterns`/`school_views` 三类，`candidate_set_doc.
  get("concept_mentions")`、`.get("new_concept_candidates")` 两个键**从未被读取**。
- `pipeline/review/step.py:940-950`（`close_review` 里另一处独立组装的
  `cand_objects`，与 `inputs.py` 那份并列存在、需要同步改，T19 已证明这一点：
  T19 commit 同时改了这两处）：同样只有 assertion/pattern/school_view 三类。
- `pipeline/review/rework.py:122-135,588-596`（两处候选清单，T19 同样都改了）：
  同样缺 concept 类。
- `pipeline/review/__init__.py:3`：`CANDIDATE_KINDS = ("assertion", "pattern",
  "school_view")` —— 无 concept 类。

**结论**：M6 队列纳入 `concept_mention`（已带 `concept_ref`）与
`new_concept_candidate`（未带 `concept_ref`，真书 7 个 surface 全部如此）是
本任务的**前置步骤**，逐条照 T19 的改法做（下面 2.1），不是可选项——没有这一步，
M7 永远拿不到"已审批准"的新概念候选，2.2 的发号机制无从触发。

### 2.1 前置步骤：M6 队列纳入 `concept_mention` 与 `new_concept_candidate`

严格照 T19（`git show 8d81337`）逐文件对照改，**不改 `genesis.py`**（T19 原则
延续：genesis 的候选/提案生成早已按 R04 统一处理 concept 类，见下方 2.1.7）。

**身份规则**（与 assertion/pattern/school_view 的区别，必须先弄清楚才能改代码）：

- `kind="concept_mention"`：`entity_id` = 该 mention 的 `concept_ref`
  （已经是合法 `co_<tech>_NNNNNN` 或 `co_shared_<tech>_NN`，见
  `pipeline/assembly/model.py:378` 的双模式校验写法）。
- `kind="new_concept_candidate"`：**没有**预先存在的 ID（这正是问题所在，
  真书 7 个 surface 全部如此）。**本任务定的身份规则（机械决定，非待裁决）**：
  用该候选的 `surface` 字符串本身作为审核队列的 `entity_id`（不经
  `pipeline.ledger.ids.validate`，因为 `surface` 是原文术语文本，不是 Ledger
  身份前缀家族的一员；`pipeline/ledger/ids.py` 文件头声明"本模块不新增任何
  前缀"，用 `surface` 直接做队列内部 key 不新增任何前缀，符合这条约束）。
  一个 `source_id` 内 `new_concept_candidates` 的 `surface` 已经是去重后的
  （`pipeline/knowledge_extraction/assemble.py:582-611` 的 `ranked`/解决逻辑
  已按 surface 归并），不会在同一份候选集里重复。

**2.1.1 `pipeline/review/__init__.py:3`**：
```python
CANDIDATE_KINDS = ("assertion", "pattern", "school_view", "concept_mention", "new_concept_candidate")
```

**2.1.2 `pipeline/review/model.py:11`**（`ENTITY_ID_KINDS`）与
**`build_review_queue`（`model.py:123-155` 附近）的校验分支**：
`concept_mention`/`new_concept_candidate` 不适合塞进 `ENTITY_ID_KINDS`
单值映射（`concept_ref` 可能是两种正则之一，`surface` 根本不是 ids.py 家族），
改成显式分支，不勉强复用 `validate(ENTITY_ID_KINDS[kind], entity_id)`：

```python
from pipeline.ledger import ids  # 新增 import（原文件已 import validate，这里另引 ids 模块本身）

# ENTITY_ID_KINDS 保持原样不加新键（concept 类走下面的显式分支，不进这个表）

def _validate_entity_id(kind: str, entity_id) -> None:
    if kind == "concept_mention":
        if not (
            isinstance(entity_id, str)
            and (
                re.match(ids.PATTERNS["technique_concept_id"], entity_id)
                or re.match(ids.PATTERNS["shared_concept_id"], entity_id)
            )
        ):
            raise InvalidIdentifier(f"Invalid concept_ref {entity_id}", code="ID_001")
    elif kind == "new_concept_candidate":
        if not isinstance(entity_id, str) or not entity_id:
            raise SchemaViolation("new_concept_candidate 的 surface 必须为非空字符串", code="SCH_002")
    else:
        try:
            validate(ENTITY_ID_KINDS[kind], entity_id)
        except InvalidIdentifier:
            raise InvalidIdentifier(f"Invalid id {entity_id}", code="ID_001")
```
（顶部需要 `import re`，若文件尚未 import；`ids.PATTERNS` 见
`pipeline/ledger/ids.py:22-42`。）`build_review_queue` 里原来直接调
`validate(ENTITY_ID_KINDS[kind], entity_id)` 那一行（`model.py:136`）
改为调 `_validate_entity_id(kind, entity_id)`。

**2.1.3 `pipeline/review/inputs.py:161-174`**（`resolve_m6_inputs`）：
```python
assertions = candidate_set_doc.get("assertions") or []
patterns = candidate_set_doc.get("patterns") or []
school_views = candidate_set_doc.get("school_views") or []
concept_mentions = candidate_set_doc.get("concept_mentions") or []
new_concept_candidates = candidate_set_doc.get("new_concept_candidates") or []
candidate_objects = [
    {"entity_id": a["assertion_id"], "kind": "assertion", "source_object": a}
    for a in assertions
] + [
    {"entity_id": p["pattern_id"], "kind": "pattern", "source_object": p}
    for p in patterns
] + [
    {"entity_id": cm["concept_ref"], "kind": "concept_mention", "source_object": cm}
    for cm in concept_mentions
] + [
    {"entity_id": ncc["surface"], "kind": "new_concept_candidate", "source_object": ncc}
    for ncc in new_concept_candidates
] + [
    {"entity_id": v["school_view_id"], "kind": "school_view", "source_object": v}
    for v in school_views
]
```

**2.1.4 `pipeline/review/step.py`**：四处按 T19 的改法逐条对照（该文件行号
以本任务开工时的实际内容为准，用 `grep -n` 重新定位，不要死抠下面写的旧行号）：
  - `_modified_by_entity_id`（T19 改的那处，`doc.get("assertion_id") or
    doc.get("pattern_id") or doc.get("school_view_id")`）：追加
    `or doc.get("concept_ref") or doc.get("surface")`。
  - `_carried_decision_entries` 的 `objects = {...}` / `objects.update({...})`：
    追加 `objects.update({cm["concept_ref"]: cm for cm in cand_set.get("concept_mentions", []) or []})`
    与 `objects.update({ncc["surface"]: ncc for ncc in cand_set.get("new_concept_candidates", []) or []})`。
  - `record_decision` 里查 `orig_obj` 的那几段 `for a in cand_set.get(...)`
    循环：追加对 `concept_mentions`（按 `concept_ref`）与
    `new_concept_candidates`（按 `surface`）的同形循环。
  - `close_review` 里的 `cand_objects = [...]`（第二处独立组装，见 2.0 已指出）：
    与 2.1.3 同样的四段拼接手法追加 concept_mention/new_concept_candidate 两段。

**2.1.5 `pipeline/review/rework.py`**：两处（`_candidate_objects` 与
`_resolve_rerun_inputs` 里的 `candidate_objects`）都按 2.1.3 的手法追加两段。

**2.1.6 `pipeline/review/console.py:165` 附近**（`cmd_show` 查目标对象）：
在 `assertion`/`pattern`/`school_view` 三级 `if not target:` 链式查找之后
追加 concept_mention（按 `concept_ref`）与 new_concept_candidate（按
`surface`）两级查找，`kind` 分别赋 `"concept_mention"`/`"new_concept_candidate"`。

**2.1.7 `pipeline/review/gate.py` 的 `evidence_closure`**（`evaluate_review`
函数内，`# evidence_closure` 注释之后那段）：`concept_mention`/
`new_concept_candidate` **自带** `evidence`（形如
`[{source_span_id, support_type}]`，与 assertion 一样，不像 pattern 要经
`assertion_ids` 转引），所以**复用 assertion 分支的校验方式**，不是复用
T19 给 pattern 新写的转引分支。在现有 `for x in reviewed_edition.get(
"approved", []): ... if c and c.get("kind") == "assertion":` 那段之后
（T19 的 pattern 分支之前或之后均可，注意 `closure_ok`/`break` 的控制流不要
把后续分支跳过——用 `continue` 风格重写这一段循环体，不要用会中断整个 for
的裸 `break`，除非确认每次 `break` 之后不会漏判其它候选，必要时把整段循环
体的判断结构从"逐条 break"改成"逐条收集失败原因、循环结束后统一判定"，
执行者动手前把改动前后的控制流画一遍确认不会漏判），新增：
```python
elif c and c.get("kind") in ("concept_mention", "new_concept_candidate"):
    links = (c.get("source_object") or {}).get("evidence") or []
    if len(links) < 1:
        closure_ok = False
        break
    for link in links:
        span_id = link.get("source_span_id")
        if span_id not in spans_dict:
            closure_ok = False
            break
        text = spans_dict[span_id].get("text", "")
        # 注意：assertion 分支用的是已被 normalize_evidence_offsets 转成局部坐标
        # 的 link["start"]/link["end"]；concept 候选的 evidence 未经这一步规范化
        # （只有 support_type，没有 start/end/quote_sha256），本分支只能校验
        # span_id 存在，不能校验引文哈希——如实做到"能核多少核多少"，
        # 不得为了凑校验而编造 start/end。
```
  （**如果执行者发现 concept 候选的 `evidence` 确实缺 `start_offset`/
  `end_offset`/`quote_sha256`，导致这条闭合检查比 assertion 分支弱，这是
  如实反映数据形状，不是缺陷——`normalize_candidate_object`/
  `normalize_evidence_offsets`【`pipeline/review/model.py:21-115`】目前
  只对 assertion 类调用；是否也对 concept 候选调用是本任务**新增的一致性
  问题**，若执行者判断需要也调用一遍，才能保持"进了队列的候选都有
  局部坐标"这一既有不变量，就照做并在回报里说明；若判断不需要，也要
  在回报里说明理由，不要不声不响地留下一个只有 concept 类没有局部坐标的
  不一致状态）。

**2.1.8 `pipeline/review/acceptance.py:242-248`**（`_check_queue_from_upstream`
的 `expected` 集合）：追加对 `concept_mentions`/`new_concept_candidates` 的
同形两段，key 分别用 `concept_ref`/`surface`。

**2.1.9 `pipeline/review/testing/upstream_stub.py`**（测试桩数据装配，T19 已
证明这是必需的同步点）：`seed_upstream` 里追加读取
`cands_data.get("concept_mentions", [])`/`.get("new_concept_candidates", [])`，
写入 `candidate_set["concept_mentions"]`/`["new_concept_candidates"]` 与
`counts` 对应两键（缺省仍是 `[]`/`0`，不改变现有测试桩的默认行为）。

**2.1.10 `INTERFACES.md` §3.5**（M6 候选类别卡片，T19 已改过一次加入
pattern，本次照样加 `concept_mention`/`new_concept_candidate` 两类，附
决定类型闭集 `review_source_fidelity`）与 `impl-06-review/README.md` §5.1–§5.3
（T19 同步过的位置）。

**先红后绿**：仿 `pipeline/review/tests/test_pattern_review.py`
（`PatternReviewTests`，`_pattern()`/`_seed()`/`_queue_item_ids()` 等 helper）
新写一个 `ConceptReviewTests`，至少覆盖：入队（`concept_mention` 与
`new_concept_candidate` 各一条）、已审进 `reviewed_edition.approved`、拒审进
`rejected`、验收独立推导（`acceptance.py` 的 `_check_queue_from_upstream`）、
证据闭合（2.1.7 的新分支）。篡改探针仿 T19：只从队列删掉 concept 类候选 →
`close_review` 失败 `reason` 含 `queue_coverage`/`outcome_consistency`/
`package_counts`；验收推导去掉 concept 类 → 队列项集合不符。

### 2.2 M7 概念发号（`pipeline/assembly/apply.py`/`incremental.py`/`model.py`）

**与现有 Pattern 发号逐条对照**（左列 Pattern 现状，右列 Concept 本任务要加的）：

| 环节 | Pattern（现状，参照） | Concept（本任务新增，逐字仿照） |
|---|---|---|
| Snapshot 号段声明 | `id_range["pat_<tech>"] = [start, end]`，`model.py:414-429`（`empty_snapshot_knowledge`）初始化，`model.py:445-450`（`validate_snapshot_knowledge`）**硬性要求存在**，缺即 `SchemaViolation` | `id_range["co_<tech>"] = [start, end]`，`empty_snapshot_knowledge` 同步初始化；**但 `validate_snapshot_knowledge` 对这一键不硬性要求存在**——理由见下方"退役号/边界处理"一节，这是与 Pattern 唯一的刻意不同点，其余逐字照抄 |
| 已用号收集（M6 增量轮，跨版次） | `incremental.py:158-205`（`allocate_ids`）的 `used` 列表：基底 `patterns[]` 已有号 + `retired_entity_ids` 里的号 + `allocated_pattern_ids` 里的号 + 本轮各视图里**已获批、带正式号**的候选号 | 新增 `_concept_number_of(concept_id, technique_id)`（仿 `incremental.py:150-154` 的 `_number_of`，前缀 `"co_%s_" % technique_id`，**注意与 `co_shared_` 前缀天然不冲突**，不需要额外排除逻辑，因为 `"co_%s_" % technique_id` 这个具体前缀字符串不会等于 `"co_shared_"`）；`allocate_ids` 里追加对应的 `used_concepts` 收集循环（基底 `concepts[]`、`retired_entity_ids`、新增 `allocated_concept_ids`、本轮各视图里已获批带正式 `co_` 号的 `concept_mentions`），返回值 `id_allocation` 字典追加一键 `"co_%s" % technique_id: max(used_concepts) if used_concepts else 0` |
| 号池游标 / 发号循环 | `apply.py:744-756`（`_build_patterns` 里 `pending`/`number = max(watermark+1, range_start)` 循环，按 `(source_id, candidate_key)` 升序） | 新增函数 `_allocate_new_concepts(base_state, view_docs, concept_watermark, concept_range_start, technique_id)`（放在 `_build_concepts` 附近），逐条对照 `_build_patterns` 的 `pending` 收集与发号循环，但候选来源是 `view["candidate_set"].get("new_concept_candidates", [])`，"已批准"判断见下方 `_is_concept_candidate_approved`，排序键用 `(source_id, surface)`（候选没有 `candidate_key` 字段，直接用 `surface`），新号格式 `"co_%s_%06d" % (technique_id, number)` |
| 已用号集合（同一轮内，供发号循环避让） | `apply.py:855-861`（`_used_pattern_numbers`，遍历 `base_state["patterns"]` 与 `base_state["retired"]`） | 新增 `_used_concept_numbers(base_state, technique_id)`，遍历 `base_state["concepts"]` 与 `base_state["retired"]`，同形逐字照抄 |
| "已批准"判断 | `apply.py:882-886`（`_is_approved`，检查 `pattern_id`/`candidate_key` 是否在 `approved_index` 里） | 新增 `_is_concept_candidate_approved(approved_index, candidate)`：检查 `candidate.get("concept_ref")`（对已有 `concept_mention`）或 `candidate.get("surface")`（对 `new_concept_candidate`，对应 2.1 定的队列 `entity_id` 规则）是否在 `approved_index` 里 |
| 材化后回填 `id_allocation` | `apply.py:1774-1794`（`_id_allocation`，取"活对象 ∪ 补发"的最大号） | 新增 `_concept_id_allocation(base, knowledge, technique_id, concept_range_key)`，逐字照抄 `_id_allocation` 的写法，只是遍历 `knowledge.get("concepts", [])` 与新的 `allocated_concept_ids` 而非 `patterns`/`allocated_pattern_ids`；`apply.py:434` 那行 `knowledge["id_allocation"] = _id_allocation(...)` 改成**先算两个再合并**：`knowledge["id_allocation"] = {**_id_allocation(...), **_concept_id_allocation(...)}` |
| Snapshot 里记"补发但未必是活对象"的号 | `knowledge["allocated_pattern_ids"]`（`apply.py:298-300`，与基底并集） | 新增 `knowledge["allocated_concept_ids"]`，同样在 `apply_resolutions` 里与基底并集；`model.py` 的 `validate_snapshot_knowledge` 与 `empty_snapshot_knowledge` 都要同步加这一键（**Snapshot 结构变更，见下方版本号一节**） |
| `_build_concepts` 消费"已批准 admit_new" | **无**（Pattern 走的是 `_build_patterns`，两者本来就是分开的函数） | 修改 `apply.py:639-700`（`_build_concepts`）：在现有"只读 `concept_mentions`"逻辑之后，追加读取 `view["candidate_set"].get("new_concept_candidates", [])`，对每个满足 `_is_concept_candidate_approved` 的候选，用 `_allocate_new_concepts` 分配到的号新建 Concept 对象（`concept_id`/`name`=surface/`aliases`=[]/`provenance`=[新条目]/`source_span_ids`=该候选 `evidence` 的 span 并集，`source_span_ids` 字段本身是 2.5 的改动，两者在同一个函数里一起做，不要分两次改同一段代码），并把这个 `surface`（连同新分配的 `co_` 号）计入返回的 `materialized["concept"]` 集合——**这一步直接让 `_admit_new_without_object`（`apply.py:1797-1828`）不再把这些候选报成 `candidate_not_materialized`**，不需要额外改 `_admit_new_without_object` 本身 |
| `_link_subjects`/下游关系 | Pattern 材化后会被 `_link_subjects(patterns, assertions)`（`apply.py:287`）处理 | Concept 目前**没有**类似的下游 link 步骤，本任务**不新增**（M8 侧靠 assertion 自己的 `concept_refs` 字段挂接，见 README 1.5；本任务只负责让 Concept 对象材化并带上 `source_span_ids`，不负责给它挂断言） |

**Snapshot schema 变更点与版本号**：
- 新增字段：`concepts[].source_span_ids`（2.5，本节之外已裁决）、
  `id_range["co_<tech>"]`、`id_allocation["co_<tech>"]`、`allocated_concept_ids[]`。
- `pipeline/assembly/model.py` 里目前**没有找到一个显式的 Snapshot schema
  版本号常量**（执行者动手前用 `grep -rn "schema_version" pipeline/assembly/`
  确认一次；若确实没有版本号机制，本任务**不新增**一个只为了这次变更服务的
  版本号——那是另一个需要用户单独决定"要不要给 Snapshot 加版本号机制"的问题，
  本任务只在 `INTERFACES.md`、`docs/blackbox-spec-rework/work-items/
  impl-07-assembly/`（若有该目录，执行者核实路径）里用文字登记这几个新字段，
  不发明版本号）。
- `INTERFACES.md` 需登记的章节：搜索 `CanonicalKnowledgeSnapshot`/
  `knowledge.concepts`/`id_range` 现在登记在哪一节（执行者用
  `grep -n "id_range\|allocated_pattern_ids\|CanonicalKnowledgeSnapshot"
  docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`
  核实，把结果贴进回报），在那一节旁边登记新字段，不新开一节，除非现有文档
  确实没有对应章节（那种情况下新开一节并说明原因）。

**退役号/最大号的既有边界如何处理**：
- Pattern 侧已知约束（`apply.py:1780-1784` 注释明写）：`id_allocation` 校验
  要求 `== max(活对象∪补发)` 且 `>= max(活对象∪已退役∪补发)`，"命名空间最大号
  被退役"时两者不可兼得，Pattern 现状靠"调用方不退役最大号"这个人工约束
  规避，不是代码强制的。**Concept 侧本任务照抄这个既有边界，不新增更强的
  约束，也不去"顺手修好"Pattern 那个已知缺陷**（超出范围）。
- Concept 退役（`retired_entity_ids` 含 `co_` 号）目前完全没有测试或代码路径
  触发过（真书至今 0 个 Concept），**本任务不新增 Concept 退役的专门处理**，
  只要 `_used_concept_numbers`/`_concept_id_allocation` 遍历
  `base_state["retired"]` 时能正确识别 `co_` 前缀的号（复用 `_number_of`
  风格的前缀匹配即可，退役号本身怎么产生不是本任务的事）。
- **向后兼容（新增边界，Pattern 没有这个问题，Concept 有；2026-09-26 协调者
  更正）**：真书账本 `var/ledgers/qianyuan_t04` 上已经存在一个**没有**
  `id_range["co_qizheng"]` 键的 Snapshot（T04B/T05f 产出时就没有这个键，
  因为这个键是本任务才引入的）。若照抄 Pattern 在 `apply_resolutions`
  开头的硬性检查（`apply.py:236-241`：缺 `id_range[range_key]` 就
  `AssemblyRefused`），**下一次任何人对着真书账本跑 `apply_resolutions`
  （包括本任务自己验证时）都会先炸在这一步**，不是因为新代码有 bug，是因为
  老 Snapshot 缺新键。

  **本文档最初版本定的处理方式（缺键时 `range_start` 一律取 `0`）有撞号
  风险，已更正**：老 Snapshot 虽然没有 `id_range["co_qizheng"]` 这个**号段
  声明**键，但**可能已经含有带 `concept_ref` 的 `co_qizheng_NNNNNN` 概念
  对象**——例如 `pipeline/corpus/_fixture/mini_ed01` 一类夹具，若其
  `concept_mentions` 早就显式声明过某个 `co_qizheng_000003` 之类的号（走
  1.1 提到的"已有 `concept_ref`"路径，不需要本任务的发号机制就能进
  Snapshot），那么"缺键就把 `range_start` 定死为 0"会让 `_allocate_new_concepts`
  从 1 号开始发号，**撞上** Snapshot 里已经存在的 `co_qizheng_000001`
  这类号——这正是 Pattern 侧 `range_start`/`watermark` 两者取
  `max()`（`apply.py:748`：`number = max(watermark + 1, range_start)`）
  要防的那类问题，缺键时只处理 `range_start` 却不管 `watermark`/已用号集合
  就会把这层保护绕过去。

  **更正后的处理方式（机械决定，仍不是待裁决项）**：`apply.py` 在算
  concept 的 `range_key`/`range_start` 那几行旁边，对 concept **单独处理成
  不 raise 的缺省**——若 `id_range` 没有这个键：
    1. `range_start` 缺省取 `0`（不变）；
    2. 但**紧接着**，`watermark`（决定发号从哪开始，见对照表第 2 行的
       `allocate_ids`/`_concept_number_of`）仍必须按 `_used_concept_numbers`
       同一套逻辑，扫过 Snapshot 里**现存**的 `co_<tech>_NNNNNN` 概念对象
       （`base_state["concepts"]`）与**已退役号**（`base_state["retired"]`，
       与 Pattern 侧 `_used_pattern_numbers` 同口径，两者都要扫，不能只扫
       活对象），取其中的最大号；若一个都没有，`watermark` 才是 `0`。
    3. 新发号仍走 `number = max(watermark + 1, range_start)`（与 Pattern
       逐字同一行代码逻辑，`range_start` 缺省 0 时这一步自然退化成
       "从现存最大号+1 开始"，不需要为 concept 另写一条不同的取最大值公式）。
    4. 在组装 `knowledge["id_range"]` 时把这个缺省值（`0`，不是算出来的
       watermark）**写回**（下一轮起 Snapshot 就有这个键了，不需要一次性
       迁移脚本、不需要额外操作 `var/ledgers/qianyuan_t04`）。

  换句话说：**缺键只影响 `id_range` 这个"声明的号段下限"，不影响"已用号
  集合"的扫描**——已用号集合本来就该无条件扫描（Pattern 侧从来不会因为
  `id_range` 有没有声明就跳过扫描 `base_state["patterns"]`），本次更正只是
  把 concept 版本里被漏掉的这一步补上，逐字对齐 Pattern 现有逻辑，不是
  发明新规则。这仍是与 Pattern 刻意不同的**唯一**一点（`id_range` 键的
  存在性要求从 raise 改成缺省 0），已用号扫描本身与 Pattern 完全同形，
  不是执行者可以自由选的"待裁决"，是本文档定的机械规则，照做即可。

### 2.3 M7 侧先红后绿

新增/扩充 `pipeline/assembly/tests/test_apply.py`（`_allocate_new_concepts`/
`_is_concept_candidate_approved`/`_used_concept_numbers` 的单元行为）与
`pipeline/assembly/tests/test_incremental_proposals.py` 或等价文件
（`allocate_ids` 新增 `co_<tech>` 键的行为；执行者先 `grep -rn "def test.*allocate_ids"
pipeline/assembly/tests/` 核实这类用例现在放在哪个文件，就近增补，不新开文件
除非确认没有合适的既有文件）。见 TDD.md 第 2 节的具名用例清单。

### 2.4 与旧的护栏用例的关系

TDD.md 原有的
`test_new_concept_candidates_without_pre_existing_concept_ref_are_not_silently_materialized`
护栏**含义已经反过来**：本任务裁决后，M6 批准的 `new_concept_candidate` **应该**
被材化，不再是"不得材化"。该用例改名为
`test_new_concept_candidates_without_m6_approval_are_not_materialized`，
断言反过来：**没有**经 M6 批准（即 `approved_index` 里没有这条候选的
`surface`）的 `new_concept_candidate`，即使它出现在 `candidate_set` 里，也
**不得**被 `_build_concepts` 材化成 Concept——这才是真正需要守住的不变量
（"M7 创世只收 M6 已审的对象"，与 Pattern/assertion 同一原则），而不是"新概念
永远不材化"。TDD.md 第 1 节已按此改写。

### 2.5 `evidence_map_pack.mentions` 的具体形状（原候选 (a)，已裁决未变）

Concept 对象新增 `source_span_ids: [span_id,...]`（排序去重，字段名与
assertion 已有的 `source_span_ids` 同名同形，`apply.py:928` 那种写法），
`build_evidence_map_pack` 从 `snapshot_knowledge["concepts"]` 派生出
`mentions: {concept_id: [span_id,...]}`（只保留同时出现在本
`evidence_map_pack.entries` 里的 span_id）。理由：改动面最小，与既有
assertion 的字段命名/形状一致。**这一节与本文档最初版本的「候选 (a)」
完全相同**，之前已经详细写在 1.4/BDD 场景/TDD.md/act/01.yaml 里，不重复。

## 3. 范围

**做**：
- `pipeline/review/__init__.py`、`model.py`、`inputs.py`、`step.py`、`rework.py`、
  `console.py`、`gate.py`、`acceptance.py`、`testing/upstream_stub.py`：M6 队列
  纳入 `concept_mention`/`new_concept_candidate`（2.1 逐条机械步骤）。
- `pipeline/assembly/model.py`：`validate_snapshot_knowledge`/
  `empty_snapshot_knowledge` 新增 `concepts[].source_span_ids`、
  `id_range["co_<tech>"]`（宽松，见 2.2 向后兼容）、
  `id_allocation["co_<tech>"]`、`allocated_concept_ids[]` 四处 schema 变更的校验。
- `pipeline/assembly/incremental.py`：`allocate_ids` 新增 concept 号位计算
  （`_concept_number_of` 与 `used_concepts` 收集，2.2 对照表第 2 行）。
- `pipeline/assembly/apply.py`：新增 `_allocate_new_concepts`、
  `_used_concept_numbers`、`_is_concept_candidate_approved`、
  `_concept_id_allocation` 四个函数（2.2 对照表逐条仿 Pattern），改
  `_build_concepts`/`_concept_provenance` 消费已批准的
  `new_concept_candidates` 并材化 Concept、收集 `source_span_ids`，改
  `apply_resolutions` 里 `id_allocation`/`allocated_pattern_ids` 附近的组装
  逻辑加上 concept 的姊妹字段。
- `pipeline/dataset_compiler/packs.py`：`build_evidence_map_pack` 与
  `_build_offset_evidence_map_pack` 新增 `mentions` 键的派生与写入（2.5）。
- 对应测试：`pipeline/review/tests/`（新建 `test_concept_review.py` 或按执行者
  判断并入既有文件）、`pipeline/assembly/tests/test_apply.py`、
  `pipeline/assembly/tests/test_incremental_proposals.py`（或等价文件）、
  `pipeline/dataset_compiler/tests/test_packs.py`。
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`
  与 `impl-06-review/README.md`：登记新字段/新候选类别（2.1.10、2.2「Snapshot
  schema 变更点」）。

**不做**：
- 不touch `assertion.concept_refs` 的产出/推断——第 107 条裁决 P7 明确禁止 Agent 代补。
  「无主体断言」计数是否下降不是本任务判据（见 1.5、6.2）。
- 不改 `pipeline/assembly/genesis.py`（2.1 已注明，genesis 的候选/提案生成
  早就统一处理 concept 类，不需要改）。
- 不改 `pipeline/corpus/_fixture/mini_ed01/`（金标）。
- 不改 `pipeline/dataset_compiler/gate.py` 的判定逻辑（`mentions_mapping` 这项
  验收本身在 `acceptance.py`，不在 `gate.py`；若发现 `gate.py` 需要跟着改，
  停手上报，不擅自扩大范围）。
- 不新增 Snapshot 版本号机制、不修 Pattern 已知的"最大号退役"边界缺陷、
  不实现 Concept 退役的专门流程（2.2「退役号/最大号既有边界如何处理」已说明）。
- 不放宽 `openspec/acceptance/m8-span-identity.sh` 或 `acceptance.py` 里任何
  既有判据（`§3.8` 无主体披露、fail-closed 等）。

## 4. 非目标

- T05b（SearchIndexPack / D14-C）、T05c（KnowledgeEntry 补全）、T05d
  （GraphProjectionPack）、T05e（IdentityMigrationMap）——各自独立任务，
  本任务不得抢做。
- 不解决"真书最终 entry 数低"这一内容问题本身（assertion 没有 `concept_refs`
  仍需 M6 人工 `modify` 补，见 1.5）——本任务解决的是"就算将来有了
  `concept_refs`，Concept 这一端现在连材化都做不到"这个更底层的缺口。

## 5. BDD 场景

```gherkin
场景一：已有 concept_ref 的 concept_mention，span 归属应能在 EvidenceMapPack 里查到
  Given 一份 M7 Snapshot，其中 concept co_qizheng_000001 的
        source_span_ids 包含 ss_x（经 M4 concept_mention 显式声明并被 M6 批准）
  When 运行 M8 run_m8 编译 EvidenceMapPack
  Then evidence_map_pack.mentions["co_qizheng_000001"] 包含 "ss_x"
  And  "ss_x" 也出现在 evidence_map_pack.entries 里（可回指真实 span）

场景二：mentions 与 entries 的 span 集合不相交时不得凭空捏造条目
  Given concept 的 source_span_ids 里有一个 span 不属于本 edition_part 的
        evidence_map_pack.entries（例如来自另一版次）
  When 编译 EvidenceMapPack
  Then mentions 里不出现这个 span_id（防止「回指不到 span」的假映射）

场景三：没有任何 concept 带 span 时，mentions 如实为空字典，不是 None、不是缺键
  Given Snapshot 里所有 concept 的 source_span_ids 都是空列表（尚无任何
        concept_mention/new_concept_candidate 被 M6 批准的情形，例如一份
        技法还没做过一轮 M4/M6）
  When 编译 EvidenceMapPack
  Then evidence_map_pack["mentions"] == {}（键必须存在，参考 packs.py 里
       page_index/excluded_pages 恒存在的既有写法）

场景四（R15，真实形状全链路）：qianyuan_ed01_text 宿主上跑一次 run_m8，
        走完整的 M4→M6→M7→M8（不是伪造真书数据，是在测试夹具/临时 Ledger
        副本上走真流程，真书正本只读，见 act/01.yaml）
  Given qianyuan_ed01_text 宿主跑到 M4，candidate_set 里有至少一个
        new_concept_candidate（真实 surface + 真实 evidence，取自该宿主已有
        的抽取件或最小新增夹具）
  When  M6 走公开入口（open_review/record_decision/close_review）批准这条
        候选（accept 决定），M7 apply_resolutions 据此发一个新 co_ 号
  Then  Snapshot.concepts 里出现这个新 Concept，带正确的 source_span_ids
  When  run_m8 编译
  Then  mentions_mapping 判据 PASS，且回指的 span_id 在 evidence_map_pack.entries
        里能查到对应原文

场景五（M6 前置步骤的护栏）：未经 M6 批准的候选不得被 M7 材化
  Given 一个 new_concept_candidate 出现在 candidate_set 里，但 M6 审核台
        对它的决定是 reject（或队列里根本没有它，模拟"忘了纳入队列"这种回归）
  When  apply_resolutions 装配 Snapshot
  Then  这个 candidate 的 surface 不出现在任何 Concept 的 name/aliases 里，
        也不消耗任何 co_ 号

场景六（拒审/reject 不占号）：
  Given 一个 new_concept_candidate 被 M6 明确拒审（reject）
  When  M7 apply_resolutions
  Then  号池游标不为这条候选前进（下一条被批准的候选拿到的还是同一个号，
        不会因为拒审的候选而跳号——除非该候选恰好携带了自己声明的号，
        本场景假定它没有，因为 new_concept_candidate 结构里没有 concept_ref）
```

## 6. 完成判据（与 act/01.yaml 一致，此处摘要）

1. `openspec/acceptance/m8-span-identity.sh` 的 `mentions_mapping` 行 PASS
   （不再是 `BLOCKED`）。
2. **新增（用户 2026-09-26 裁决要求）**：真书或 `qianyuan_ed01_text` 宿主上，
   经 M6 通过（`accept`）的新概念（`new_concept_candidate`）真实进入 M7
   Snapshot（`concepts[]` 出现对应条目、带正确 `source_span_ids`、消耗一个
   新分配的 `co_` 号），并在 M8 产出的 `evidence_map_pack.mentions` 里可回指
   到真实 span（场景四）。这一步允许在**真书账本的临时副本**或最小测试夹具
   上验证（真书正本只读，见 act/01.yaml），回报里必须给出实测命令与输出。
3. 未经 M6 批准的候选不得被材化（场景五/六），号池游标不因拒审候选跳号。
4. `mentions` 里不出现"回指不到本 edition_part 的 entries"的假映射（场景二）。
5. **不要求**「无主体断言」计数下降（1.5 已说明原因：那需要 assertion 自己的
   `concept_refs` 字段，P7 禁止 Agent 代补，与本任务解决的 Concept 材化是
   两件事）——若验收时发现这个数字没变，是符合预期的结果，不是失败。
6. `§3.8` 无主体断言披露口径（`known_defects` 里 `assertion_without_subject`）
   逐字不放宽。
7. 不改 `mini_ed01` 金标；不新增违反 M8 纯函数约束的文件/网络/时间依赖；
   `genesis.py` 一字不改。
