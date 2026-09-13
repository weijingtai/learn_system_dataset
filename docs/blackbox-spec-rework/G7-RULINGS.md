# G7 草稿统一裁决（主 Agent）

更新时间：2026-09-12
依据：`reviews/G7-DRAFTS-REVIEW-R2.md`（impl-05/07/09/10 共 62 条）、impl-04/06/08 各 README「§4 待主 Agent 裁决」、`G7-PLAN.md`。
效力：下列裁决覆盖草稿中的推荐；未单列的条目**默认采纳草稿推荐**，但与本文件 §1 原则冲突者以原则为准。执行者定稿时发现冲突，写待裁决停手，不自行取舍。

## 1. 通用原则

- **P1 首纵切只走关键路径**。首纵切 = Ledger → M3 结构层 → M5 → M8，在 mini_ed01 上以 `INTERNAL_DEMO` 编译；M4/M6/M7 与知识链前三段在首纵切内不接，判定为 BLOCKED 而非伪造。M8 的首切片不依赖 CanonicalKnowledgeSnapshot，Snapshot 归属（impl-06 D-01、impl-07 Q17/Q19/Q20）推迟到 W4/W5 再裁。
- **P2 artifact_type 单一闭集**。唯一登记处为 `impl-00-interfaces/INTERFACES.md` §4 临时闭集，直至 impl-08 Contract Registry 落地接管。任何包新增类型只提名，由「该波的登记 ACT」一次性写入闭集；同一时刻只有一路写 INTERFACES §4。未入闭集的类型名，实现不得使用。
- **P3 子包内容 Schema 先放代码草案**。新产物的内容结构以代码内草案契约表达，`schema_version: "0.1.0-draft"`；准入层对 `PUBLIC_RELEASE` 以 `draft_schema` 拒绝。首纵切内不向 `openspec/schemas/` 新增文件（L0 四份不动），Schema 正式化随 impl-08 Contract Registry。
- **P4 共享面独占**。`openspec/acceptance/run_all.sh`、`pipeline/corpus/_fixture/`、`pipeline/ledger/`、`INTERFACES.md` §4：每波至多一个 ACT 写同一文件；各包判据先落在自己的 §19.0 脚本（如 `m5-evidence-gate.sh`），`run_all.sh` 只在使某条 §20 由 BLOCKED 转判的那一波由指定包改。W3 内只有 impl-04 的 run_all ACT（20.4/20.8）可写 `run_all.sh`。
- **P5 上游只认 succeeded**。所有下游解析上游 StagePackage 时只接受所属 StepRun `succeeded` 的包（impl-02 ACCEPTANCE §5.3）。impl-07 README §5.1 M6 行须补此约束（R2 §5）。
- **P6 首纵切零模型调用**。M3 语义层、M4 候选均不在首纵切内调用真实模型；需要模型输出处以录制回放或金标注入表达，真实调用开关与 Adapter 归属（Q01、Q50、Q53、Q61）推迟到对应波次，届时仍默认关闭。
- **P7 人工决定不可伪造**。执行者与主 Agent 不得代填人工决定；测试只用 fixture 已登记的人工事件。真实前十页的终态决定表由用户本人撰写（Q37 采纳 A），列为 W4-J 前的**用户待办**。
- **P8 新 ID 前缀须用户确认**。任何新前缀（如 SemanticSpan，Q49）按 T-02 惯例先登记册提议、用户确认后才能用；W5 前向用户提出。
- **P9 不改已验收模块行为**。impl-01/impl-02 已验收文件只允许经独立 ACT、带回归门禁修改；impl-10 Q57「改结构层三个文件」、impl-08 D-9「M3 入口越过端口」均留到对应波次单独裁。

## 2. impl-04 M8（W2-D 定稿，W3-F 实现）

| 条目 | 裁决 | 说明 |
|---|---|---|
| D1 上游缺席的输入策略 | **A 尾链首切片** | 只冻结 M3 StagePackage 及其血缘输入与页图；EvidenceMapPack 前三段标 BLOCKED，不注入合成知识（P1）。附带冲突：采纳「仅在临时 Ledger 内编译、INTERNAL_DEMO」口径。 |
| D2 页图登记的薄 M1 | **A**，但文件与 CLI 名显式标 `m1_shim`，README 登记「impl-09 M1 落地后替换」 | 不改 impl-01 已验收的 `fixture_ingest.py`（P9）。 |
| D3 缺页图退出码 | **A 退出 3** | 与宿主缺失同类。 |
| D4 新 artifact_type | **A 提名通过**，由 W2-C 登记 ACT 写入 INTERFACES §4（P2） | 复用类型不变。 |
| D5 子包 Schema | **A 代码草案 0.1.0-draft**（P3） | |
| D6 run_all.sh 20.4/20.8 | **A 单独 ACT**，为 W3 唯一 run_all 写入者（P4） | |
| 其余条目 | 采纳推荐 | 水印文案采用草案「INTERNAL_DEMO｜机器转录，未经人工校对｜不得作为知识来源或权威依据」；`source_verified` 不算 release 级。 |

## 3. impl-05 M4（W4 之前不定稿）

采纳 R2 推荐，另：Q10 按 P2+P3（提名入闭集、内容 Schema 代码草案）；Q13 被拒候选不阻断 Gate、只计数（采纳 A）；Q01 按 P6；Q02 金标进 fixture 须作为独占 ACT（P4）。M4 首纵切外，定稿排入 W4 前。

## 4. impl-06 M6（W4-H）

D-01 推迟（P1）；D-02 采纳 A（CLI，零新依赖）；D-11 采纳 A（fixture 金标注入推进）；D-08 `invalidate_revision` 是否违反 §2:32 留 W4 定稿时单独裁；其余采纳推荐。

## 5. impl-07 M7（W5-L，首纵切外）

Q17/Q19/Q20 推迟（P1）；Q27 按 P2；Q29 采纳 C（本包不改 run_all，直至 W5 另裁）；补 P5 约束；其余采纳推荐。

## 6. impl-08 Orchestrator + Contract Registry（W4-I）

D-1 StepRequest 缺 stage 字段属 L0 Schema 变更，W4 定稿时单独裁（倾向补字段并走 D-02 变更流程）；D-11 按 P2；D-18 与 impl-02 时序已解除（impl-02 ACCEPTED）；其余留 W4 定稿。

## 7. impl-09 M1/M2（W4-J）

Q36 采纳 A（申报件元数据进 Git）；Q37 按 P7 由用户撰写；Q41 按 P2；Q46 采纳 A（begin 前拒绝同 Part 已有 m1/m2 运行）；其余采纳推荐。

## 8. impl-10 M3 语义层（W5-K）

Q49 按 P8 须用户确认前缀；Q52/Q53/Q55/Q57/Q62 推迟到 W5 定稿；Q50、Q61 按 P6。

## 9. impl-00 与 impl-03（W1-A `1f32177` 合并去重的 23 条）

**impl-00 的首纵切裁剪**：按 P1/P3/P9，impl-00 在首纵切内只保留两类 ACT——（a）INTERFACES §4 闭集登记（M5、M8 新类型）；（b）impl-03、impl-04 的 verify 实际引用到的 fixture 期望产物（若无引用则不做）。m4/m6/m7 金标、`stage_payload_m4..m8` Schema、`fixture_ingest.py` 灌入 m1–m8（原 act/09）一律移入 README「纵切后待办」，状态 `DEFERRED`，不删除文件内容。

| # | 条目 | 裁决 |
|---|---|---|
| 1 | impl-00 D-01 前十页无规则正文，FactSet 匹配无宿主 | 首纵切不做 FactSet 匹配，§22.2 该项判 BLOCKED；扩页宿主纵切后再议（P1） |
| 2 | impl-00 D-02 ↔ impl-03 D-01 M5 冻结输入边界 | 采纳 impl-03 `corpus_only`（M3 包及其血缘输入，17 修订）；impl-00 对齐 |
| 3 | impl-00 D-03 首纵切是否含 M7、M8 读什么 | **不采纳推荐**：M7 不进首纵切；M8 按 §2 D1-A 尾链只读 M3 包与页图 |
| 4 | impl-00 D-04 ReleaseRun 归属 | 采纳推荐（首纵切单 Part，`edition_part_id` 取该 Part），跨 Part Release 纵切后改 Ledger 再议 |
| 5 | impl-00 D-05 阶段 payload 入 Schema | **不采纳**：P3，首纵切不新增 `openspec/schemas/` 文件 |
| 6 | impl-00 D-06 ↔ impl-03 D-13 金标投影与对抗输入 | 采纳推荐（身份归一化投影；对抗用 mock compiler） |
| 7 | impl-00 D-07 UUID 金标确定性 | 采纳推荐（生产 uuid4；金标比对前身份归一化，不在生产代码写常量 ID） |
| 8 | impl-00 D-08 ↔ impl-03 D-11 无前缀对象与返工任务身份 | 采纳推荐（不新增前缀，P8） |
| 9 | impl-00 D-09 ↔ impl-03 D-04/05/08/12 blocked 放行等 | 采纳推荐：`INTERNAL_DEMO` 下 failed=0 放行、blocked 逐项披露 |
| 10 | impl-00 D-10 ↔ impl-03 D-09 M5 类型与 ValidationPackage 结构 | 采纳：`gate_results`、`validation_package` 提名入闭集（P2），结构为代码草案（P3） |
| 11 | impl-00 D-11 M4 模型调用 | 推迟（M4 不在首纵切，P6） |
| 12 | impl-00 D-12 ↔ impl-03 D-02 quote hash 归属 | 采纳：M5 按 `sha256(quote)` 复算，不改 M3 spans（P9） |
| 13 | impl-00 D-13 ↔ impl-03 D-13/14 热点文件写权与只读查询 | `fixture_ingest.py` 首纵切不改（P9）；Ledger 读优先用 LedgerReader 公开方法，缺口处允许只读 SELECT 并在 README 登记清单，供 impl-08 补读接口 |
| 14 | impl-00 D-14 ReviewDecision verdict | 推迟至 W4（M6） |
| 15 | impl-00 D-15 首纵切子包范围 | 以 impl-04 定稿（`2e4f9a7`）为准，impl-00 对齐 |
| 16 | impl-00 D-16 SourceAssetPack 字节 | **不采纳**：按 impl-04 D2 与规格 §16:723，页图字节登记进 Ledger |
| 17 | impl-00 D-17 ↔ impl-03 D-10 错误码闭集 | 采纳推荐（映射现有 9 码，缺项 null，并在 README 列缺口清单） |
| 18 | impl-03 D-03 四点坐标 vs box | 采纳推荐 |
| 19 | impl-03 D-06 G1 重放 | 采纳推荐：只有 `replay.py` 可 import M3 compiler，其余 Validator 独立实现 |
| 20 | impl-03 D-07 目标消费级别 | 采纳推荐：配置带 target（首纵切 `INTERNAL_DEMO`），报告三级都算 |
| 21 | impl-03 D-08 Gate 未通过时 M5 StepRun 终态 | 采纳推荐（跑完即 succeeded 并封存报告），**追加约束**：M5 StagePackage `validation.passed` 如实反映 Gate；下游消费 M5 包须同时满足 StepRun `succeeded` 与 `validation.passed == true`（P5 的 M5 特例） |
| 22 | impl-03 D-12 G4/G5/G6 | 采纳推荐：`not_evaluated`，验收判 BLOCKED |
| 23 | impl-03 D-15 上游终态过滤 | 采纳（P5） |

### 9.1 W2 定稿中新发现的三条（`ac21b30` 回报）

| # | 问题 | 裁决 |
|---|---|---|
| 24 | `validator_report` 是否入闭集 | 不入。impl-03 定稿（`1a189ae`）已改为复用通用 `validation_report`；首纵切 M5 新类型只有 `gate_results`、`validation_package`。INTERFACES §4 M5 行残留的 `gate_report` 由 impl-00/10 删除。 |
| 25 | Ledger 只读查询缺口（`frozen_inputs`、`artifacts.artifact_type`、`stage_packages` 按 StepRun 取包） | 按第 13 条：首纵切允许只读 SELECT，impl-00 README §5.2 为唯一缺口清单；impl-08 以公开读方法补齐后回改调用方。 |
| 26 | impl-03 `count_mismatch`/`unproofread_glyphs`/`replay_tool_mismatch` 无对应错误码 | 按第 17 条填 `code: null`，缺口清单并入 impl-00 README §5.2，错误码闭集扩充随 impl-08 Contract Registry。 |

### 9.2 W3 实现 K1 回报中的裁定（2026-09-12）

| # | 来源 | 裁决 |
|---|---|---|
| 27 | M8 w3f：回归命令 `| tail -1` 误取验收输出 | 各包回归命令取行统一为 `2>&1 \| grep -E "^(Ran\|OK\|FAILED)"` |
| 28 | M5 w3e：amend 未推送的 ACT 00 提交 | 接受并登记；已推送或已被他人引用的提交一律不得 amend |
| 29 | M5 w3e：`CHECK_CODES` 映射由实现推导 | 接受；`registry.py` 模块 docstring 必须列出完整「检查名 → 错误码/None」表，主 Agent 验收时核对 |
| 30 | M5 w3e：`build_context` 键集超出 act/04 字面 | 以 K1 `fixture_context()` 键集为准，K2 新增用例断言两者键集相等 |
| 31 | M5 w3e：`g1_frozen_bytes` 附加 `fail_closed`；`g3_references` 的 relation/subject 承载 | 接受；`gate_results.broken_relations` 汇总 `g3_references` 全部发现的 (from, to, relation) |
| 32 | M8 w3f K2：act/03 薄 M1 以 `begin_step_run` 新建 m1 运行写 Checkpoint，被 Ledger 阶段封存守卫拒绝（`service.py:1280-1285`，m1 已由 ingest 运行 succeeded 封存） | 采纳 A：改用 `supersede_step_run` 接替该 EditionPart 最近一个 succeeded 的 m1 运行（经读接口查出，不写死号），其余契约逐字不变；不改 Ledger（P9）。附加：act/03 新增用例断言登记页图前后 `resolve_m3_inputs` 的 `manifest_revision_id` 不变；act/04 以接替后的 m1 运行读取页图登记。impl-09 真实 M1 落地时同样经 supersede 或在首次 M1 运行内登记页图，再议。 |
| 33 | M5 w3e K2 六条 | ① `g3_evidence` 字框比对缺陷修正落在 `9aaccf5` 而非 `0a77975`，接受登记；② act/04–06 脚手架写 `ingest(m1,m2,m3)` 与 BDD §0「ingest(m1,m2)→run_m3→run_m5」不一致，以 BDD 真实链路为准，文档随 impl-03 收尾修订；③ `build_context` 19 键、`assemble_validation_package` 追加 `gate_results_revision_id`/`edition_part_id` 关键字参数接受；④ errored Validator 报告顶层 `detail` 接受（0.1.0-draft）；⑤ **返工**：begin 之后 `status=failed` 的 CLI 退出码与 M3 一致为 1（`FAILED` 1、`GATE_FAILED` 1、begin 前 `REFUSED` 2、`WriterLocked` 3）；⑥ 知悉。 |

### 9.3 impl-08 定稿（`cd6c7a6`）待裁决

| # | 条目 | 裁决 |
|---|---|---|
| 34 | D-4 Stage Gate 报告是否落盘 | 采纳 B：作为下游 StepRun 的首个 artifact 落盘 |
| 35 | N-4 Gate 报告 artifact_type | 采纳 A：复用已登记 `validation_report`（内容 `kind=stage_gate`），不新增类型（P2） |
| 36 | D-6 Ledger 读缺口补法 | 采纳 A：首纵切不改 `pipeline/ledger`（P9），act/10 公开读方法 `DEFERRED`，缺口仍以 impl-00 README §5.2 为唯一清单 |
| 37 | D-7 §20.1 是否计入 imported（fixture 灌入）与 legacy 绑定 | 采纳 A：计入，并在 PASS/BLOCKED 行逐项披露来源 |
| 38 | D-8 §20.10 判定口径 | 采纳 C：OCR/模型/索引/存储四类 Adapter 逐项判定，合成结论取最弱；首纵切只有存储端口可判，其余 BLOCKED |
| 39 | D-9 M3 入口越过端口访问 Ledger 内部 | 采纳 B：该项判 BLOCKED 并列出 文件:行号，不改 impl-02（P9），端口化随后续批次 |
| 40 | N-2 m1_shim supersede 与 Gate/lineage | 采纳 A：仅当接替者承载 StagePackage 时才从有效运行中移除被接替者；lineage 用 succeeded 集合 |
| 41 | N-3 M8 legacy 绑定 | 采纳 A：descriptor 增 `entry_kwargs` 与 `owns_processing_run` |
| 42 | D-16 ReworkImpact/ThroughputEstimate 口径 | 采纳 A：血缘可达计数 + 历时均值 |
| 43 | N-1 §22.3 要求 §20.1（及 20.9）成立 vs P1 | **用户决定（2026-09-12）：维持关键路径**。首纵切交付「Ledger→M3→M5→M8」可跑通证据链；§20.1、§20.9 在首纵切内如实判 BLOCKED 并写明原因（M4/M6 未接入、GraphProjectionPack 未编译），不伪造 PASS；M4/M6 最薄接入与 GraphProjectionPack 排入下一波，接入后由判据自动转判。首纵切「完成」以 §20.3/20.4/20.8 可判且 20.1/20.9 BLOCKED 披露为准，不改规格 §22.3 正文。 |

### 9.4 impl-04 K3 待裁决

| # | 条目 | 裁决 |
|---|---|---|
| 44 | ACT 08：fixture 副本删一条 span 时 20.4 的失败落点（act/08 正文「fx 先行」vs BDD §9.2「落点 span_key_unique」） | 采纳 A：保持 `fx` 先行，被改副本在仓库内规范 `verify.sh` 的 `manifest_sha256` 先失败，20.4/20.8 落点 `FAIL fixture_host`（D-18，且与已验收 ACT 07 `test_shell_never_trusts_copy_verify` 一致）。BDD §9.2 与 act/08 verify 注释的「span_key_unique」为文档错误，由主 Agent 修订；`span_key_unique` 落点以直接调用 `python -m pipeline.dataset_compiler.acceptance --check span_identity` 证明。 |

### 9.5 impl-08 四查 R1（`5ab873c`）阻断项裁定

| # | 条目 | 裁决 |
|---|---|---|
| 45 | F1 `stage_package_valid`「每个有效 StepRun 恰 1 包」与第 40 条（不承载包的接替运行不移除被接替者）矛盾，m1 Gate 必 blocked | 包判定改为：该阶段有效运行中**承载 StagePackage 的运行恰 1 个且包合法**；不承载包的接替运行（如 m1_shim）不计入包判定，但须 `succeeded` 且在 lineage 可达 |
| 46 | F2 Gate 报告「落为下游 StepRun 首个 artifact」不可由公开读接口取回，运行级类型又受 `service.py:66` 限制，改 Ledger 违反 P9 | **修订第 34 条**：首纵切 Stage Gate 报告不落盘，由 `evaluate_stage_gate` 返回、CLI 打印、EditionRun 结果 JSON 携带，验收独立重算；落盘随 D-6 读缺口关闭后另立 ACT（`DEFERRED`） |

### 9.6 impl-05 定稿（`8cedae2`）待裁决

| # | 条目 | 裁决 |
|---|---|---|
| 47 | N1 M4 artifact_type 登记与 INTERFACES §2.4/§3.2/§4 旧命名对账 | 采纳 A：新增 impl-00 登记 ACT（act/12，单写者，P2），改写 §4 M4 行与 §2.4/§3.1/§3.2，并把 M4 类型加入 `check_interfaces.py` 必查清单；须在 impl-05 K2 前执行并验收 |
| 48 | N2 K4 是否以 fixture m4 金标为强制前置 | 采纳 A：强制前置，缺失即停手；金标不得由实现方自产，恢复 impl-00 act/05 并裁剪为「仅 m4 金标 + verify.sh 对应扩展」的独占 ACT（P4），与 act/12 同批起草、四查后执行 |
| 49 | N3 候选证据坐标（页块绝对 `start_offset/end_offset` vs INTERFACES I-11 span 相对 `char_start/char_end`） | 采纳 A：以页块绝对坐标为准，与 M3 span 偏移、M5 严格 offset 校验同一坐标系；INTERFACES §3.1/I-11 随 act/12 同步改写 |
| 50 | N4 M4 候选 Gate 结果是否落盘 | 采纳 A：作为 M4 自身 StepRun 的 `validation_report` 落盘并列入 `validation_report_ids`（可公开读回）；与编排层 Stage Gate 报告（第 46 条不落盘）无关 |

### 9.7 impl-00 前置 ACT（`6cd4379`）待裁决

| # | 条目 | 裁决 |
|---|---|---|
| 51 | A1 act/12 是否一并把 §3.10 `evidence_map_pack.evidence_link` 改为页块绝对坐标 | 采纳：一并改。已验收 `pipeline/dataset_compiler`、`pipeline/validation` 代码与 impl-04 文档中 `char_start/char_end` 均为 0 处（M8 首切片知识链前三段 `not_compiled`，未冻结该字段），与第 49 条同一坐标系 |
| 52 | A2 m4 金标生成器位置；以及金标内人工裁决事件 `ruling_m4_d001` 的性质 | 采纳 A：生成器放 fixture `m4/build_expected_m4.py`，不改 `tools/build_fixture.py` 与 m1–m3 字节。**补充（P7）**：fixture 中新增的人工裁决/签发事件属测试合成，须在内容中显式标注 `synthetic_fixture: true`（actor 标为 fixture 作者），README 写明「仅供验收宿主，不计入真实 expert_verified、不得进入任何发布级别判定」；验收与实现不得把它当作真实人工决定 |

## 10. 用户待办

1. W4-J 前：撰写真实前十页人工终态决定表（P7，Q37）。
2. W5 前：确认 M3 语义层 SemanticSpan 的 ID 前缀（P8，Q49）。
