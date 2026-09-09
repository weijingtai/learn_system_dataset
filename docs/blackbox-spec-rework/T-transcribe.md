# T 类返工指令 — 转录型（答案已在既有已定稿文档，只需搬运与接线）

> 对应 PLAN.md「黑箱架构规格 R1 审查返工项」中可机械完成的部分。
> **执行者要求**：中等模型即可。**不需要做设计决策**——每条都给出了照抄源的精确坐标。
> **唯一目标文件**：`openspec/learn-system-blackbox-architecture.md`（除 T-14 另涉 §19 表）。
> **通用禁令**：
> 1. 不得发明本文件未给出的字段名、枚举值或对象名。缺什么就停下上报，不要自造。
> 2. 不得改动 `§20 黑箱完成标准` 的条目编号与顺序（T-17 除外，且只改表述不改条数）。
> 3. 照抄源与规格冲突时，**以照抄源为准**，并在规格中标注「取代/沿用」关系，不要静默二选一。
> 4. 每条改完立即跑该条的验收命令，绿了再做下一条。不要攒一批再验。

---

## T-01 ｜ 术语三层模型写入 M4

- **对应返工项**：RB 组第 8 条
- **规格落点**：`§12 M4 Knowledge Extraction`，在「M4 将 SemanticSpan 分别提取为候选」列表**之前**插入一个「术语判层前置步骤」小节；另在 `§5` 基础设施段的 Contract Registry 描述里补两个冻结输入。
- **照抄源**：`knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md`
  - 三层定义：`§二`（L1 共享源数据层 / L2 同形异义层 / L3 技法独有层），含各自 ID 规则 `co_shared_<domain>_NN`、`hg_NNNN`、`co_<technique>_NNNNNN`
  - 三步判层：`§三`（1 L1 闭集匹配确定性免模型 → 2 L2 同形表比对必须按当前技法选义项 → 3 L3 技法新词进候选）
  - 存放路径：`schemas/shared/canon/`、`schemas/shared/homographs/`
- **要写的内容**：
  1. 三层的名称、ID 规则、存放路径，逐字沿用照抄源，不要改写措辞。
  2. 明确「L1 匹配为确定性路径，不调用模型」——这是效率与准确率的关键，必须写进规格正文而不是脚注。
  3. 明确「L2 命中时必须绑定带技法的 concept_id（义项），禁止裸绑字面」。
  4. 在 `§5` 的 Contract Registry 条目后追加：`schemas/shared/canon` 与 `schemas/shared/homographs` 为 M4 的冻结输入 Artifact。
- **禁止**：不要重新设计 ID 格式；不要把三层压缩成两层；不要把 L1 描述成「模型辅助」。
- **验收命令**：
  ```bash
  grep -c "co_shared_\|homograph_id\|schemas/shared/canon" openspec/learn-system-blackbox-architecture.md   # 期望 >= 3
  grep -q "确定性" <(sed -n '/## 12/,/## 13/p' openspec/learn-system-blackbox-architecture.md) && echo OK
  ```

---

## T-02 ｜ 新增「§8.1 标识与版本规范」

- **对应返工项**：RA 组第 3 条（ID 部分）
- **规格落点**：`§8 Package 公共结构`之后，新增 `§8.1`。
- **照抄源**：`pipeline/schemas/core/SCHEMA.md` 已冻结的 ID 格式（原样沿用，不要改）：
  | 对象 | 格式 | 出处 |
  |---|---|---|
  | 来源 | `src_<work>_ed<NN>` | SCHEMA.md §1 |
  | 原文片段 | `ss_<work>_ed<NN>_p<NNNN>_s<NN>` | SCHEMA.md §2 |
  | 知识单元 | `ku_<technique>_<6位数字>` | SCHEMA.md §3 |
  | 主张 | `as_<technique>_<6位数字>` | SCHEMA.md §4 |
  | 命题 | `pr_<technique>_<6位数字>` | SCHEMA.md §4 |
  | 共享概念 | `co_shared_<domain>_NN` | CROSS_TECHNIQUE_ONTOLOGY §二 |
  | 技法概念 | `co_<technique>_<6位数字>` | 同上 |
  | 同形字面锚 | `hg_<4位数字>` | 同上 |
- **要写的内容**：
  1. 上表原样搬入规格，并逐行标注「沿用 `pipeline/schemas/core/SCHEMA.md` v0.2」。
  2. 为规格新引入的对象补格式，命名风格与上表一致（前缀 + 下划线 + 稳定段）：
     `Artifact`、`ProcessingRun`、`StepRun`、`StagePackage`、`Revision`、`Release`。
     **前缀由执行者按上表风格提议，但必须在本条改完后单独列出待用户确认**，不得视为已定。
  3. 版本号规则：写明 Schema 版本与内容 Revision 是否同号（本条只需把「二者分离」写成明确陈述句，
     具体递增语义属 D 类，见 `D-design.md` D-02）。
- **禁止**：不要修改上表中任何已冻结格式；不要把 6 位数字改成其他位数。
- **验收命令**：
  ```bash
  grep -c "src_<work>_ed<NN>\|ss_<work>_ed<NN>\|ku_<technique>\|as_<technique>" openspec/learn-system-blackbox-architecture.md  # 期望 >= 4
  grep -n "§8.1\|## 8.1" openspec/learn-system-blackbox-architecture.md   # 必须命中
  ```

---

## T-03 ｜ 状态枚举四表

- **对应返工项**：RA 组第 3 条（枚举部分）、RD 组第 2 条
- **规格落点**：`§8.1` 之后新增 `§8.2 状态枚举全集`。
- **照抄源（三处，全部原样搬运）**：
  1. **内容状态 7 值** — `pipeline/schemas/core/SCHEMA.md §5`：
     `source_verified / machine_extracted / cross_model_reviewed / disputed / needs_expert / expert_verified / deprecated`
  2. **错误码 9 个** — `pipeline/schemas/core/SCHEMA.md §6`：
     `SRC_001 SRC_003 TXT_001 ID_001 ID_002 REF_001 SCH_001 SCH_002 SEM_001`（含各自中文释义，原样抄）
  3. **专家审核八类** — `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md §3.2`：
     来源忠实度 / 版本和校勘 / 流派归属 / 解释质量 / 案例真实性 / 现实效度 / 安全 / 权利
- **要写的内容**：四张表，中文只作释义列，取值一律英文小写下划线。
  1. **内容状态**：抄 7 值，标注「沿用 SCHEMA.md v0.2 §5」。
  2. **ReviewDecision 类型**：把八类审核落为八个枚举值（英文名由执行者按 `review_source_fidelity` 这类风格铸造），
     并在表头写明「取代 §14 原有的单一『专家签发』动作；依据 v1.2 §3.2 禁止用一个 expert_verified 覆盖所有含义」。
  3. **failure 分类**：抄 9 个错误码，标注「沿用 SCHEMA.md v0.2 §6」。
  4. **Artifact status / StepRun status**：本条**只建空表并标注 `TODO(D-03)`**，取值属设计型，见 `D-design.md` D-03。
- **禁止**：不要给 7 值增删；不要把八类合并；不要在本条自行发明 StepRun 状态值。
- **验收命令**：
  ```bash
  for v in source_verified machine_extracted cross_model_reviewed disputed needs_expert expert_verified deprecated; do
    grep -q "$v" openspec/learn-system-blackbox-architecture.md || echo "缺失: $v"; done
  grep -c "SRC_001\|TXT_001\|SEM_001" openspec/learn-system-blackbox-architecture.md   # 期望 >= 3
  grep -c "来源忠实度\|流派归属\|案例真实性" openspec/learn-system-blackbox-architecture.md  # 期望 >= 3
  ```

---

## T-04 ｜ 三级消费级别与 G1–G7 门禁接线

- **对应返工项**：RD 组第 1 条
- **规格落点**：`§13 M5` 与 `§16 M8` 各改一处。
- **照抄源**：`pipeline/DATASET_ACCEPTANCE_STANDARD.md §3`（三级表）与 `§4`（G1–G7 全文）
- **要写的内容**：
  1. `§16` M8 冻结项清单中，把「消费级别」加为**显式输入参数**，取值 `INTERNAL_DEMO / DEV_SEARCH / PUBLIC_RELEASE`，
     并抄入原文那句约束：「编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据」。
  2. `§16` 增一张小表：各级别的准入状态门槛，直接引用 `G7` 的三条
     （INTERNAL_DEMO 可展示 machine_* 但须隔离水印；DEV_SEARCH 至少 cross_model_reviewed；
     PUBLIC_RELEASE 全部 expert_verified）。
  3. `§13` M5 的 Validator 清单逐条对应 G1–G6，并**明确标注每条在 M5 执行还是延到 M8**：
     建议 G1/G2/G3/G4/G5 在 M5，G6 在 M5（规则可执行性）+ M8（索引产出后复验），G7 在 M8。
     执行者按此填表，如认为分配不合理则停下上报，不要自行改。
- **禁止**：**不得新造门禁名**。全规格只允许出现 G1–G7 这七个名字。
- **验收命令**：
  ```bash
  grep -c "INTERNAL_DEMO\|DEV_SEARCH\|PUBLIC_RELEASE" openspec/learn-system-blackbox-architecture.md  # 期望 >= 3
  grep -c "fail-closed" openspec/learn-system-blackbox-architecture.md                                # 期望 >= 1
  for g in G1 G2 G3 G4 G5 G6 G7; do grep -q "$g" openspec/learn-system-blackbox-architecture.md || echo "缺失: $g"; done
  ```

---

## T-05 ｜ `evidence_level` 枚举（首纵切档位已裁定）

- **对应返工项**：RD 组第 3 条
- **规格落点**：`§11 M3` 末尾 + `§13 M5` Validator 条件。
- **照抄源**：`pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G3` 已给出两档的实质定义：
  - 通用档：「每个 span 必须有 source offset 或等价的确定性 anchor，以及 quote hash」
  - 扫描档：「OCR 书源还必须能追到扫描页、图像哈希和 OCR 字框范围」
  另见 `LEARN_SYSTEM_TARGET.md:140`：「纯文本引用只能算开发级证据，不能算最终无损证据链」。
- **要写的内容**：
  1. 枚举两档：`offset_level`（offset + quote hash）与 `glyphbox_level`（追加扫描页 + 图像哈希 + 字框范围）。
  2. 可发布性结论：`offset_level` 只可用于 `INTERNAL_DEMO` / `DEV_SEARCH`；`PUBLIC_RELEASE` 要求 `glyphbox_level`
     （依据 TARGET:140）。
  3. **首纵切档位写死为 `glyphbox_level`** —— 这是 2026-09-08 用户裁定（首纵切改用七政《三辰通载》影宋鈔本），
     不需再问。
  4. 写入 `§13` M5 Validator 判定条件：级别不足时 FAIL，不得降级放行。
- **禁止**：不要增加第三档；不要把首纵切档位写成「待定」。
- **验收命令**：
  ```bash
  grep -c "offset_level\|glyphbox_level" openspec/learn-system-blackbox-architecture.md  # 期望 >= 2
  grep -q "glyphbox_level" <(sed -n '/## 13/,/## 14/p' openspec/learn-system-blackbox-architecture.md) && echo "M5已接线"
  ```

---

## T-06 ｜ EvidenceMapPack 内容定义

- **对应返工项**：RB 组第 6 条
- **规格落点**：`§16` 的 PublicationPackage 子包清单下，为 `EvidenceMapPack` 补内容说明。
- **照抄源**：`LEARN_SYSTEM_TARGET.md §6`（行 130-138 的完整证据链）与 `DATASET_ACCEPTANCE_STANDARD §4-G3`。
- **要写的内容**：
  1. 逐段写出链路：`EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage/字框坐标 → SourceAsset 页标识`。
  2. 一句硬约束：坐标系必须与 `SourceAssetPack` 中页图的像素尺寸同源可换算（否则客户端无法高亮）。
  3. 一句门禁：该链路完整性是 `ValidationReport` 的 fail-closed 检查项。
- **禁止**：不要把 SourceAnchor 留在 M3 内部而不进发布包。
- **验收命令**：
  ```bash
  grep -q "字框" <(sed -n '/## 16/,/## 17/p' openspec/learn-system-blackbox-architecture.md) && echo OK
  grep -c "EvidenceMapPack" openspec/learn-system-blackbox-architecture.md   # 期望 >= 2(清单 + 说明)
  ```

---

## T-07 ｜ KnowledgePack ↔ PublicationPackage 双向映射表

- **对应返工项**：RB 组第 2 条
- **规格落点**：`§16` 末尾新增一张表。
- **照抄源**：`LEARN_SYSTEM_TARGET.md §9`（行 185-202，KnowledgePack 十四个目录）与规格 `§16` 现有八个子包。
- **要写的内容**：一张两列表，左列是 TARGET 的十四个目录，右列是它落在哪个子包（或标注「本期不产出」）。
  十四项一个都不能漏：`release-manifest / schema / concepts / entries / assertions / applicability-rules /
  school-views / evidence-links / source-spans / source-anchors / scan-assets-or-references /
  exact-search-index / fulltext-index / optional-vector-index / query-contract`。
  若 `KnowledgeDataPack` 就是 `KnowledgePack` 的新名，必须写出一句取代声明。
- **禁止**：不要留空行；无归宿的项必须显式写「本期不产出（依据 §21）」而不是省略。
- **验收命令**：
  ```bash
  for d in concepts entries assertions applicability-rules school-views evidence-links source-spans source-anchors query-contract; do
    grep -q "$d" openspec/learn-system-blackbox-architecture.md || echo "映射表缺: $d"; done
  ```

---

## T-08 ｜ Tag 区三个耦合接口的承接点

- **对应返工项**：RB 组第 7 条
- **规格落点**：`§16`（承载点）+ `§1`（边界声明处补一句指向）。
- **照抄源**：
  - `README.md:20` — 三个接口的名字：最小盘面概念字典、MarkContentBinding 内容供给、EvidenceBundle 服务
  - `tag_system/README.md:30-32` — 三条的具体描述
  - `tag_system/TAG_SYSTEM_DESIGN.md:222/224/225` — 字段名 `omen_carrying`、`condition_affordance`、`school_variance_display`
  - `tag_system/TAG_SYSTEM_DESIGN.md:307` — 「是否改变当前判断」属 MarkContentBinding 内容状态字段，由知识层供给，UI 不得猜测
  - `tag_system/TAG_SYSTEM_DESIGN.md:438` — 最小盘面概念字典规模约 100–200 个概念，仅稳定 ID + 名称 + 基础类象，**不含规则 DSL**
- **要写的内容**：逐项写出每个字段来自哪个 Module、哪个 Package。若本期不产出，必须在 `§21 非目标`中显式列出
  并说明 Tag 侧的临时替代方案，不能只是不提。
- **禁止**：不要改字段名；不要把「不含规则 DSL」这条限制丢掉。
- **验收命令**：
  ```bash
  grep -c "MarkContentBinding\|EvidenceBundle\|盘面概念字典" openspec/learn-system-blackbox-architecture.md  # 期望 >= 3
  grep -c "omen_carrying\|condition_affordance\|school_variance_display" openspec/learn-system-blackbox-architecture.md  # 期望 >= 3
  ```

---

## T-09 ｜ Local Orchestrator 只读查询契约（六项）

- **对应返工项**：RC 组第 6 条
- **规格落点**：`§5` 的 Local Orchestrator 条目下展开；`§7` 末尾补一句进度事件上报要求。
- **照抄源**：返工项原文已列全六项，直接搬：
  `RunStatus` / `StageProgress` / `PendingQueue` / `BlockingReasons` / `ReworkImpact` / `ThroughputEstimate`
- **要写的内容**：六项各一行说明其返回什么。其中 `PendingQueue` 必须显式列出五个队列：
  M2 异常页与低置信字、M3 边界分歧、M4 类别分歧、M6 待签发、M7 待裁决。
  `§7` 补一句：Module 必须在运行中上报进度事件，否则上述查询无数据来源。
- **禁止**：不要少于六项；不要把它写成「未来可扩展」。
- **验收命令**：
  ```bash
  for q in RunStatus StageProgress PendingQueue BlockingReasons ReworkImpact ThroughputEstimate; do
    grep -q "$q" openspec/learn-system-blackbox-architecture.md || echo "缺: $q"; done
  ```

---

## T-10 ｜ 异常页终态枚举

- **对应返工项**：RC 组第 7 条
- **规格落点**：`§10 M2` 末尾。
- **照抄源**：返工项已给三值；现状证据见 `ocr/data_work/logs/anomalies.jsonl`（已登记 page_002 无文本、page_010 盘面页）
  与 `ocr/experiments/curve_segment.py`（弧线字切分仍为原型）。
- **要写的内容**：
  1. 枚举 `manually_transcribed / known_unrecognizable / deferred`。
  2. 明确哪些终态可让 M2 Gate 通过：`manually_transcribed` 与 `known_unrecognizable` 可放行，
     `deferred` 阻断。理由写一句：这与 `§6.1「失败为零」`不冲突，因为「客观不可识别」不是失败。
  3. `known_unrecognizable` 必须附理由与证据 Artifact，不得裸标。
- **禁止**：不要允许 `deferred` 放行；不要把异常页静默跳过。
- **验收命令**：
  ```bash
  grep -c "manually_transcribed\|known_unrecognizable\|deferred" openspec/learn-system-blackbox-architecture.md  # 期望 >= 3
  ```

---

## T-11 ｜ §19 差距表修正三行低估 + 补十二项遗漏

- **对应返工项**：RE 组全部 5 条
- **规格落点**：`§19` 表格。
- **实测数字（已由审查复核，直接用，不要重新统计）**：

  | 行 | 要补的内容 | 复核命令 |
  |---|---|---|
  | M1 | 「当前实现」补 `pipeline/registry/works/`、`tools/ingest_epub.py`；差距补「转录不可由记录的 raw+tool 重放」 | `grep -n "PUA\|勘误" pipeline/tools/ingest_epub.py`（期望无输出＝工具无勘误逻辑） |
  | M6 | 补数据体全空：496 rules，`original_text` 非空 0，`is_verified=1` 为 0，`ge_ju_versions` 0 行，`conditions` 404，`chapter` 486 | `sqlite3 pattern_knowledge_workbench/assets/ge_ju_database.sqlite "select count(*) from ge_ju_rules where trim(coalesce(original_text,''))<>''"` |
  | M8 | 把「零命中假绿」改为「span→mentions 映射键碰撞：148 span 塌缩为 18 键、6 组碰撞，修好解析后将链到错误页」 | `sed -n '135,152p' pipeline/rag/build_index.py` |

- **新增行（每行都要附一条当前必 FAIL 的判据命令）**：
  1. 工作台唯一键 `{patternId, schoolId}` 禁止多书多主张 — `grep -n "uniqueKeys" -A3 pattern_knowledge_workbench/lib/database/tables.dart`
  2. `ge_ju_schools` 把 book(1) 与 school(2) 混存同表 — `sqlite3 <db> "select type,count(*) from ge_ju_schools group by type"`
  3. 干净环境不可构建 — `grep -c "192.168" pattern_knowledge_workbench/pubspec.yaml`（期望终态 0）
  4. 启动覆盖本地库 + 保存即 verified — 见 `act/01.yaml`、`act/02.yaml` 的 VERIFICATION
  5. 测试宿主匮乏：全仓非 OCR 部分仅 1 个 748B 脚手架 — `find . -name "test_*.py" -o -name "*_test.dart" | grep -v ocr/ | wc -l`
  6. goldens 只有 bazi/qtbj，无非八字 fixture — `find pipeline/validators/goldens -type f`
  7. OCR R7 横排分支取轴错误 — 引用 `ocr/HANDOFF_OCR_FIXES.md:181-185`
  8. `pipeline/TODO.md:12-14` 三项 P0 语义阻断（忠实性门禁、命例/注文/通则分层、条件例外结构化）
- **反向说明（务必不要写错）**：`pipeline/requirements.txt` **已存在**且含环境自检，
  PLAN.md 里「pipeline 无依赖声明」的旧表述**已不成立**，不得计入遗漏。
- **验收命令**：
  ```bash
  grep -c "^|" <(sed -n '/## 19/,/## 20/p' openspec/learn-system-blackbox-architecture.md)   # 表行数应从 13 增至 21 以上
  grep -c "496\|148\|18 键" openspec/learn-system-blackbox-architecture.md                    # 实测数字已写入
  ```

---

## T-12 ｜ §19 增「层级」列并按拓扑标注

- **对应返工项**：RF 组第 6 条
- **规格落点**：`§19` 表格加一列。
- **依据（审查已验证的依赖拓扑）**：
  ```
  L0 内核契约(ArtifactRef + §7 接口 + §8 信封)
    └─ L1 Artifact Ledger(Object Store + Metadata + §17 StepRun 事务) ─ L1' LineageGraph
         ├─ L2  Local Orchestrator(状态机/Gate/Checkpoint/失效传播)
         ├─ L2' Contract Registry 完整体(Package Schema/TechniqueProfile/迁移器)
         └─ M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8
  ```
- **要写的内容**：为 12 行各加 `L0 / L1 / L2 / Module` 标注，并在表下写一句：
  「本表行序为盘点顺序，非施工顺序；施工顺序见上方拓扑，三个基础设施是前置层。」
- **禁止**：不要重排表行（会打乱既有引用），只加列 + 加说明。
- **验收命令**：
  ```bash
  grep -q "非施工顺序\|前置层" openspec/learn-system-blackbox-architecture.md && echo OK
  ```

---

## T-13 ｜ §3–§18 逐节加状态标签

- **对应返工项**：RF 组第 7 条
- **规格落点**：`§3` 到 `§18` 每节标题下一行。
- **照抄源**：`AGENTS.md:39` 要求区分「已确认设计 / 讨论候选 / 待验证假设 / 最终规范」四态。
- **要写的内容**：每节加一行 `状态：<四态之一>`。判定规则（照此填，不要自由发挥）：
  - 已在 `§2 已确认原则` 中有对应条目的 → `已确认设计`
  - 本轮 R1 返工正在改的（§4 §7 §8 §10 §11 §12 §13 §14 §16 §17）→ `待验证假设`
  - `§16` 那句「建议一个 Technique 一个 Release」→ 单独标 `讨论候选`
  - 其余 → `讨论候选`
- **禁止**：不要给任何一节标 `最终规范`（整份规格尚未获批）。
- **验收命令**：
  ```bash
  grep -c "^状态：" openspec/learn-system-blackbox-architecture.md   # 期望 >= 16
  grep -c "^状态：最终规范" openspec/learn-system-blackbox-architecture.md   # 期望 0
  ```

---

## 完成后统一自检

```bash
cd /Users/jingtaiwei/Git/Public/learn_system
bash docs/blackbox-spec-rework/verify-T.sh    # 见同目录，逐条打印 PASS/FAIL
git diff --stat                                # 应仅含 openspec/ 下文件
```
