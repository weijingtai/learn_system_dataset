# T05a：M8 concept→span 的 mentions 映射

## 0. 目标

`openspec/acceptance/m8-span-identity.sh` 目前 7 PASS + `mentions_mapping` BLOCKED（exit 2）。
本任务把 `mentions_mapping` 从 BLOCKED 推进——**若下面「二、待用户决定」两项已获批准**，
推进到真正的 PASS；**若未获批准**，执行者读到本文档即止步于「二」，不写任何代码
（AGENTS.md 会话铁律：拿不准就停手）。

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
见「二、待用户决定 #1」。

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
是规格确实没写。见「二、待用户决定 #2」。

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
或 (b)「二、待用户决定 #1」（概念发号）解决之后，某些断言恰好通过其他显式引用路径
获得主体——但这仍然是"轨道一/轨道二是否命中"的问题，跟 mentions 映射是否产出
无必然因果。

**如果验收时发现「无主体断言数」没有变化，这是符合裁决的正确结果，不是本任务
失败**。见 ACT 完成判据里对此的明确措辞与 act/01.yaml 的「不做」清单。

## 2. 待用户决定（执行者读到这里，两项都未获批准前止步，不写代码）

### #1（关键，挡住"真书上出现非零 mentions"）：新概念如何发号材化

M4 抽取出的、M4 时刻还不存在对应 `co_` 号的新术语（真书 7 个 surface 全部如此），
被 M6 批准 `admit_new` 之后，谁在哪一步给它发一个正式 `co_<tech>_NNNNNN` 号，
写回到什么产物里，供 M7 `_build_concepts` 读到？

- **候选 (a)**：仿照 Pattern 的号段机制。给 `id_range` 加一个 `co_<technique_id>` 键
  （`model.py:414-429,445-461` 对应扩一份），`apply.py` 新增
  `_build_concepts` 的姊妹发号逻辑（仿 `apply.py:744-756`
  的 `_build_patterns` 水位线循环），对已批准的 `new_concept_candidates`
  按 `(source_id, surface)` 升序发号，写入 `id_allocation`/`allocated_pattern_ids`
  的姊妹字段。
- **候选 (b)**：不在 M7 自动发号；改为要求 M6 审核台在批准 `admit_new` 时
  必须由人工指定 `concept_ref`（类似 `pattern_id` 显式携号入账的既有路径，
  `apply.py:758-780` 那条分支），Agent 侧只负责把人工指定的号写进
  `candidate.concept_ref` 再走现有 `_build_concepts`。
- **候选 (c)**：维持现状不实现，`new_concept_candidates` 永远停在候选层，
  `mentions_mapping` 只对"已有 `concept_ref`"的 concept_mentions 生效
  （即本任务范围收窄为「二、待用户决定 #1 未解决前」的子集）。

**主 Agent 建议**：(c) 作为**本任务（T05a）当下的范围**——本任务只做「1.3 断点 B」
与「1.4 M8 空白」两处机械修复，让 `mentions_mapping` 在**已有 concept_ref 的
concept_mentions**（跨 Release 复用、或未来经人工指定的场景）上产出真实非空的
`mentions` 并通过验收；`new_concept_candidates` 的发号机制（候选 (a)/(b) 二选一）
**另立任务**（建议编号 T05a2），因为它涉及 Snapshot `id_range`/`id_allocation`
schema 变更、跨 M6/M7 多处校验器改动，量级与风险都不适合夹在"补一个 span 字段"
里一起做。理由：断点 A 的修复范围（是否允许 Agent 自动发号 vs 必须人工指定）
本身是一个需要用户拍板的产品/流程问题（自动发号意味着"新概念的诞生不经人工
确认"，这与 CHARTER 对 Pattern/Concept 新增走人工审核的既有精神是否一致，
需要用户判断），不是本任务可以单方面决定的实现细节。

**若用户选 (c)**：本任务完成后，真书上 `mentions` 很可能仍是空字典
`{}`（因为真书这 7 个 surface 全部缺 `concept_ref`）——`mentions_mapping`
判据届时会从"BLOCKED"变成"结构已具备但真书暂无非空样本"，执行者需要在
mini_ed01 或新建的最小夹具上构造一个**已带 `concept_ref` 的 concept_mention**
用例来验证映射逻辑本身是对的（TDD.md 的 R15 用例）；不得为了让真书 mentions
非空而编造 concept_ref。

**若用户选 (a) 或 (b)**：本任务需要先等 T05a2（或本任务本身临时扩大范围，
由用户明示）落地，再验证真书非空样本。

### #2：`evidence_map_pack.mentions` 的具体形状

现状 `evidence_map_pack` 没有任何登记形状可循（见 1.4）。需要用户确认：

- **候选 (a)**（主 Agent 建议）：Concept 对象新增 `source_span_ids: [span_id,...]`
  （排序去重，字段名与 assertion 已有的 `source_span_ids` 同名同形，
  `apply.py:928` 那种写法），`build_evidence_map_pack` 从
  `snapshot_knowledge["concepts"]` 派生出
  `mentions: {concept_id: [span_id,...]}`（只保留同时出现在本
  `evidence_map_pack.entries` 里的 span_id，即与本 edition_part 相关的部分——
  概念可能跨版次累积了别的版次的 span，不该混进本包）。
  理由：改动面最小，与既有 assertion 的字段命名/形状一致，`_check_sorted`
  一类既有校验模式可直接复用。
- **候选 (b)**：Concept 保留完整逐条 mention（`[{source_id, source_span_id,
  surface, support_type}]`），信息更全，未来给 GraphProjectionPack 或
  SearchIndexPack（T05b）用起来更方便，但改动面更大、`provenance` 与新字段
  语义上有重叠，需要一并理清。
- **候选 (c)**：不改 Concept schema，`mentions` 直接从 M4 `candidate_set`
  现读——**否决**：违反 M8 纯函数层"只吃 M7 Snapshot"的既有分层（`packs.py`
  文档开头明文"纯函数：不读文件、不访问 Ledger"，且 M8 与 M4 之间隔着 M6/M7，
  多次提交/多版次时 M4 候选集不是唯一权威）。

**主 Agent 建议**：(a)。字段名、`mentions` 的键值形状、是否登记进
`INTERFACES.md §3.10`（连带修正 1.4 提到的名实不符——是否在本任务里顺手登记，
还是留给专门理清 §3.10 的任务，也请用户一并定），都需要用户点头后才写代码。

---

**执行者须知**：上面两项只要有一项未获用户书面批准（回报/TODO.md/裁决记录里
能看到明确采纳意见），**不得**开始 act/01.yaml 的任何写操作，只需在回报里写清楚
"待 #1/#2 裁决"并停手。若用户已经批准，回报里注明批准出处（哪条消息/哪次裁决），
再按 act/01.yaml 执行。

## 3. 范围

**做**（用户已批准 #2、且 #1 选 (c) 时）：
- `pipeline/assembly/model.py`：`validate_snapshot_knowledge` 对 concept 新增
  `source_span_ids` 字段的校验（列表、排序、元素经 `ids.validate("source_span_id", ...)`）。
- `pipeline/assembly/apply.py`：`_build_concepts`/`_concept_provenance` 把
  `mention["evidence"]` 的 `source_span_id` 收集进 concept 的 `source_span_ids`
  （新概念与已有概念合并时都要正确并集）。
- `pipeline/dataset_compiler/packs.py`：`build_evidence_map_pack` 与
  `_build_offset_evidence_map_pack` 新增 `mentions` 键的派生与写入。
- 对应测试：`pipeline/assembly/tests/test_apply.py`、
  `pipeline/dataset_compiler/tests/test_packs.py`。
- （视用户对 §3.10 的意见）`docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`
  登记新字段。

**不做**：
- 不实现「待用户决定 #1」候选 (a)/(b)（新概念发号）——那是 T05a2 或用户另行指示。
- 不touch `assertion.concept_refs` 的产出/推断——第 107 条裁决 P7 明确禁止 Agent 代补。
- 不改 `pipeline/corpus/_fixture/mini_ed01/`（金标）。
- 不改 `pipeline/dataset_compiler/gate.py` 的判定逻辑（`mentions_mapping` 这项
  验收本身在 `acceptance.py`，不在 `gate.py`；若发现 `gate.py` 需要跟着改，
  停手上报，不擅自扩大范围）。
- 不放宽 `openspec/acceptance/m8-span-identity.sh` 或 `acceptance.py` 里任何
  既有判据（`§3.8` 无主体披露、fail-closed 等）。

## 4. 非目标

- T05b（SearchIndexPack / D14-C）、T05c（KnowledgeEntry 补全）、T05d
  （GraphProjectionPack）、T05e（IdentityMigrationMap）——各自独立任务，
  本任务不得抢做。
- 不解决"真书最终 entry 数低"这一内容问题（见 1.5）。

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
  Given Snapshot 里所有 concept 的 source_span_ids 都是空列表（真书当前状态，
        待「待用户决定 #1」解决前的常态）
  When 编译 EvidenceMapPack
  Then evidence_map_pack["mentions"] == {}（键必须存在，参考 packs.py 里
       page_index/excluded_pages 恒存在的既有写法）
  And  m8-span-identity.sh 的 mentions_mapping 判据据此给出诚实结论
       （不得把 {} 报成"已产出"而蒙混过关，也不得因为 {} 就继续 BLOCKED——
       结构已具备、真书暂无非零样本，是 FAIL 还是新的 BLOCKED 文案，
       由 acceptance.py 的实现如实反映，不得含糊成"看起来像 PASS"）

场景四（R15，真实形状全链路）：qianyuan_ed01_text 宿主上跑一次 run_m8，
        构造一条"临时补一个已带 concept_ref 的 concept_mention"的最小验证
        （不是伪造真书数据，是在测试夹具/临时 Ledger 副本上验证映射逻辑，
        真书正本只读，见 act/01.yaml）
  Given qianyuan_ed01_text 宿主跑到 M7，Snapshot 里人为（在测试内，不落盘到
        正本）加入一个带 source_span_ids 的 concept
  When run_m8 编译
  Then mentions_mapping 判据 PASS，且回指的 span_id 在 evidence_map_pack.entries
       里能查到对应原文
```

## 6. 完成判据（与 act/01.yaml 一致，此处摘要）

1. `openspec/acceptance/m8-span-identity.sh` 的 `mentions_mapping` 行不再是
   `BLOCKED`；若「待用户决定 #1」选 (c)，真书上允许仍是 `mentions: {}` 的
   诚实结果（不是 PASS 造假），但**逻辑本身**必须有非空场景验证通过
   （场景一/四）。
2. 真书或宿主上，若某条 assertion 因为本任务而**新**获得可回指 span 的
   concept 挂接，必须真实可回指（场景一/二）；**不要求**「无主体断言」计数
   下降（1.5 已说明原因，下降与否都不是本任务的判据）。
3. `§3.8` 无主体断言披露口径（`known_defects` 里 `assertion_without_subject`）
   逐字不放宽。
4. 不改 `mini_ed01` 金标；不新增违反 M8 纯函数约束的文件/网络/时间依赖。
