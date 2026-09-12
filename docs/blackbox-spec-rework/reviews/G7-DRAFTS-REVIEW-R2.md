# G7 DRAFTS REVIEW R2

生成时间：2026-09-12 11:41:14

## 1. 完整度表
所有 7 个包（impl-04 至 impl-10）的文件与 ACT YAML 均未出现截断情况。

## 2. 接口对账表（附证据）
| 生产者 | 消费者 | 不一致说明与证据对照 |
|---|---|---|
| impl-09 (M1/M2) | Ledger | **拟新增闭集外类型**（提议级别，不写 `schemas`）<br>草稿原文 `impl-09-intake/README.md:122`: `- \`source_asset\`：页图原字节...`<br>契约原文 `INTERFACES.md:317`: `## 4. artifact_type 总表（在 Contract Registry 落地前充当临时闭集，D-10）` |
| impl-10 (M3) | Ledger/M4 | **拟新增闭集外类型**（提议级别，不写 `schemas`）<br>草稿原文 `impl-10-corpus-semantic/README.md:187`: `本包新增 artifact_type：semantic_windows、model_request...`<br>契约原文 `INTERFACES.md:317`: `## 4. artifact_type 总表...` |
| impl-05 (M4) | Ledger | **拟新增闭集外类型**（提议级别，不写 `schemas`）<br>草稿原文 `impl-05-knowledge/README.md:173`: `本包拟新增 artifact_type：candidate_submission...`<br>契约原文 `INTERFACES.md:317`: `## 4. artifact_type 总表...` |

## 3. 冲突提议（附证据）
### 3.1 新增 artifact_type 与 Schema 归属
**性质说明**：上述 `impl-05/09/10` 均在 README 内**建议通过 ACT 契约冻结或由 Registry 接管，未直接修改共享 `openspec/schemas/*.schema.json`**。仅在命名上意图越出 `INTERFACES.md` 定义的临时闭集边界。

### 3.2 验收脚本修改冲突
各包均提议修改 `openspec/acceptance/run_all.sh` 或 `m3-coverage.sh`，且各有不同意图：
- **impl-07 (M7)** <br>草稿原文 `impl-07-assembly/README.md:162`: `- A：... ACT 10 把 run_all.sh 的 20.5) 分支改为调用它：0 → PASS，2 → BLOCKED...`<br>意图：接管 run_all 20.5 判定。
- **impl-08 (Orchestrator)** <br>草稿原文 `impl-08-orchestrator/README.md:74`: `openspec/acceptance/run_all.sh（ACT 09，只新增 accept_check 函数并改 20.1 与 20.10 两个 case 体）`<br>意图：接管 run_all 20.1 和 20.10 判定。
- **impl-10 (M3)** <br>草稿原文 `impl-10-corpus-semantic/README.md:153`: `3. m3-coverage.sh：增 SEMANTIC_FIXTURE_DIR（默认规范路径...`<br>意图：对 `m3-coverage.sh` 追加语义层宿主目录入参和透传。

### 3.3 Snapshot 归属冲突
M8 的前置输入 Snapshot 究竟归属于 M7 生成还是 M8 自主接收？
- **impl-06 (M6)** <br>草稿原文 `impl-06-review/README.md:149`: `- A：保留 §6.2 的运行与阶段归属，M8 输入契约从第一天就是 Snapshot；若主 Agent 把它派给 M7 草案，删除 ACT 10...`

## 4. 统一待裁决表 (全量 62 条)
| 编号 | 来源包与草稿条目号 | 问题一句话 | 各选项完整含义（每项一句） | 草稿推荐 | 建议与理由 | 规格文件:行号 | 优先级 |
|---|---|---|---|---|---|---|---|
| G7-Q01 | impl-05-knowledge / D-01 | 模型调用是否在首切片内 | A: 首切片不调用模型。候选只经提交件 Adapter 登记，渠道闭集中只收 `...<br>B: 接入 Model Adapter，调 `config.yaml` 端点（结...<br>C: 以 `run_task.py --model mock` 形态登记「moc... | A | 同推荐项 | §12.2 | P1 |
| G7-Q02 | impl-05-knowledge / D-02 | fixture 候选金标的来源与内容 | A: 主 Agent 在 fixture 增 `m4/` 目录（assertio...<br>B: 金标只放 `pipeline/knowledge_extraction/t...<br>C: 新建含 page_008 的第二 fixture，产出真实七政主张（改动大... | A | 同推荐项 | §22.1 | P2 |
| G7-Q03 | impl-05-knowledge / D-03 | M4 输入的 Span 层 | A: 薄接入消费 StructuralSpan；candidate_set 与 ...<br>B: M4 整体等 M3 语义层落地后再做。<br>C: M4 自行做语义合段（侵占 M3 职责，§11:519）。 | A | 同推荐项 | §12.2 | P2 |
| G7-Q04 | impl-05-knowledge / D-04 | 候选提交件如何登记为 Ledger 冻结修订（Adapter 形态） | A: 每路（category × lane）一个 m4 submit StepR...<br>B: 单个 assemble StepRun 以字节参数接收提交件并在内部封存（...<br>C: Ledger 新增运行级类型 `candidate_submission`... | A | 同推荐项 | §7:207 | P1 |
| G7-Q05 | impl-05-knowledge / D-05 | Contract Registry 冻结输入（canon / homographs / 流派闭集）如何进入 Ledger | A: Registry Adapter 读 canon 目录，生成运行级 `te...<br>B: 同 A，但本批冻结 `sch_qizheng_001` 琴堂派、`sch_...<br>C: 主 Agent 在 Ledger 新增运行级类型 `contract_re... | A | 同推荐项 | §5:128 | P1 |
| G7-Q06 | impl-05-knowledge / D-06 | 「L1 确定性字典匹配 100% 准确」与七政文本实测冲突 | A: 首切片「只校验不扫描」：提交件自带的 `co_shared_*` 引用必须...<br>B: 自动扫描，但命中只记 `needs_context`、不直接绑定（与 §1...<br>C: 自动扫描 + 七政复合词停用表（需新登记冻结输入与维护流程）。 | A | 同推荐项 | §12.1 | P2 |
| G7-Q07 | impl-05-knowledge / D-07 | 「人工签发 expert_verified」归属 M4 还是 M6 | A: 签发 StepRun 归属 M6 薄接入工作包（在 M5 之后）；本包只冻...<br>B: 在 M4 assemble StepRun 内追加签发队列（签发早于 M5...<br>C: 在本包宿主内临时写一个 stage=m6 的签发 StepRun（宿主与阶... | A | 同推荐项 | §22.3 | P2 |
| G7-Q08 | impl-05-knowledge / D-08 | expert_verified 需要哪些审核决定齐备，verdict 闭集是什么 | A: 首切片最小集：`review_source_fidelity` 必需；候选...<br>B: 八类全部 `accept` 或显式 `not_applicable` 才可...<br>C: 按消费级别设不同必需集合（INTERNAL_DEMO / DEV_SEAR... | A | 同推荐项 | §8.2 | P2 |
| G7-Q09 | impl-05-knowledge / D-09 | 人工闭集 ID（as_ / pr_ / pat_）分配与重跑保号 | A: assemble 配置修订写 `id_range`（首切片 as / pr...<br>B: Pattern 候选不分配 pat_（`pattern_id: null`...<br>C: 新建号段登记冻结输入（新 artifact_type 与登记流程）。 | A | 同推荐项 | §8.1 | P2 |
| G7-Q10 | impl-05-knowledge / D-10 | 新 artifact_type 与 CandidatePackage 机器 Schema | A: 首切片用内部结构版本 `schema_version: "0.1.0-dr...<br>B: 本批先由主 Agent 新增 L0 Schema 并纳入 `openspe...<br>C: 不设独立制品，全部塞进 StagePackage payload（payl... | A | 同推荐项 | §8:232 | P0 |
| G7-Q11 | impl-05-knowledge / D-11 | 是否在本批新建 §19.0 判据脚本 | （详情见草稿原文） | A | 同推荐项 | §19.0 | P2 |
| G7-Q12 | impl-05-knowledge / D-12 | §20.7 legacy 候选与 M4 的关系 | A: 首切片不接 run_all，不在 `pipeline/tools/` 建该...<br>B: 本批在 `pipeline/tools/import_legacy_can...<br>C: 主 Agent 先把 20.7 判据改为「执行导入工具并核对准入/拒收计数... | A | 同推荐项 | §20:943 | P2 |
| G7-Q13 | impl-05-knowledge / D-13 | 被拒候选是否阻断 M4 Gate | （详情见草稿原文） | A | 同推荐项 | §6.1 | P0 |
| G7-Q14 | impl-05-knowledge / D-14 | M4 类别裁决人工事件的 decision_type | （详情见草稿原文） | A | 同推荐项 | §8.2 | P2 |
| G7-Q15 | impl-05-knowledge / D-15 | M4 如何定位 M3 产出（与 impl-02 的接口） | A: 只认「succeeded 且 Transformation `compil...<br>B: 扩展 fixture_ingest 让 m3 也写 corpus_span...<br>C: 允许读 fixture `spans.yaml`（违背只读冻结修订）。 | A | 同推荐项 | :40 | P2 |
| G7-Q16 | impl-05-knowledge / D-16 | 七政任务包模板与术语表 | （详情见草稿原文） | A | 同推荐项 | :147 | P2 |
| G7-Q17 | impl-07-assembly / D-01 | 首纵切里 M8 的 Snapshot 从哪来 | A: 把本包 ACT 02–04 的纯函数「创世汇编」（空基底 + 单个 Rev...<br>B: M8 草案自带薄适配器，把单个 ReviewedEditionPackag...<br>C: 纵切中 M8 直接消费 ReviewedEditionPackage，规格... | A | 同推荐项 | :662 | P2 |
| G7-Q18 | impl-07-assembly / D-02 | ReleaseRun 在 Ledger 里的 scope 键 | A: 每个 ReleaseRun 先 `new_id("artifact_id"...<br>B: 改 Ledger Schema，新增 `release_scope_id`...<br>C: 以 Snapshot 的 `art_` 作键——第二个 ReleaseRu... | A | 同推荐项 | :81 | P1 |
| G7-Q19 | impl-07-assembly / D-03 | Snapshot 的粒度与身份 | A: 每个 technique 一个 Snapshot Artifact（`ar...<br>B: 每个 Work 一个 Snapshot。<br>C: 每次 Release 新建一个 Snapshot Artifact。 | A | 同推荐项 | §8.1 | P0 |
| G7-Q20 | impl-07-assembly / D-04 | Pattern 身份谁发号 | A: M4/M6 只能携带已正式的 `pat_`（在基底 Snapshot 中存...<br>B: 每个 EditionRun 的 M4 自行发 `pat_`，M7 合并时换...<br>C: 等 Contract Registry 先落地再做 M7（本包整体顺延）。 | A | 同推荐项 | :60 | P0 |
| G7-Q21 | impl-07-assembly / D-05 | 「并入」与「合并」必须是两种语义 | A: `MergeProposal.relation` 闭集 `{attach,...<br>B: 所有跨 Edition 同一格局都视作合并换号（违反 §20.5）。<br>C: `attach` 不经提案、直接静默并入（违反「提案、差异和决定全部保留」... | A | 同推荐项 | §8.1 | P2 |
| G7-Q22 | impl-07-assembly / D-06 | 自动裁定与人工裁决的边界 | B: 名称相等即自动 attach（违反 §15 `:653` 保留同名异义）。<br>C: 全部人工（可行，但 §6.2 的自动通道无实现、无测试）。 | A | 同推荐项 | §6.2 | P2 |
| G7-Q23 | impl-07-assembly / D-07 | 「可比内容」如何判定 | A: 可比单元 = (work_key, `collation_key`)，两侧...<br>B: 允许按 NFC 文本相似度阈值自动对齐（引入可调阈值，结果随阈值漂移）。<br>C: 本批不做对勘，只做 Pattern 聚合（§15 `:655` 与 §20... | A | 同推荐项 | :655 | P2 |
| G7-Q24 | impl-07-assembly / D-08 | 对象级「所见修订」的粒度 | A: 对象不单独入 Ledger；所见修订 = 承载该对象的包级修订（`revi...<br>B: 每个 Pattern/Assertion/SchoolView 各是一个 ...<br>C: 交给 M6 草案决定，M7 两种都兼容（接口不收敛）。 | A | 同推荐项 | §8.1 | P2 |
| G7-Q25 | impl-07-assembly / D-09 | M7 人工决定的 `decision_type` | A: 对勘相关 → `review_edition_collation`；冲突组...<br>B: 规格 §8.2 新增第 9 类 `review_identity_asse...<br>C: 全部 None。 | A | 同推荐项 | §8.2 | P2 |
| G7-Q26 | impl-07-assembly / D-10 | 新规范 fixture 与期望产物 | A: 新建规范 fixture `pipeline/corpus/_fixtur...<br>B: 期望产物放 `pipeline/assembly/tests/data/`...<br>C: 等真实 M4–M6 产出与真实第二版次（无限期 BLOCKED）。 | A | 同推荐项 | :54 | P2 |
| G7-Q27 | impl-07-assembly / D-11 | 新 artifact_type | A: 新增 `reviewed_edition_knowledge`（M6 产出...<br>B: 全部塞进一个 `m7_output` 内容（丢失分项血缘，§18 `:85...<br>C: 等 Contract Registry 统一登记后再实现（L2' 未实现，... | A | 同推荐项 | :857 | P0 |
| G7-Q28 | impl-07-assembly / D-12 | 提案与对勘关系的标识 | A: 不发登记 ID。`proposal_key = "<kind>:" + s...<br>B: 每个提案一个 `art_`/`rev_`（Artifact 爆炸）。<br>C: 登记 `mp_`/`ap_`/`cfp_`/`erp_`/`aln_` 等... | A | 同推荐项 | :93 | P2 |
| G7-Q29 | impl-07-assembly / D-13 | §20.5 何时 PASS，谁改 `run_all.sh` | A: `m7-assembler.sh` 保留 `BLOCKED upstrea...<br>B: 金标输入即可判 PASS（20.5 的性质只取决于 M7），ACT 10 ...<br>C: 本包不改 `run_all.sh`，20.5 维持「M7 未实现」直到 M... | A | 同推荐项 | - | P2 |
| G7-Q30 | impl-07-assembly / D-14 | 同一 Edition 的新修订（M6 返工）进入 ReleaseRun | A: 本包支持「替换」。以 (source_id, edition_part_i...<br>B: 本包拒绝替换，另批实现。<br>C: 旧 Edition 的全部贡献失效后重算（违反 §14.1 `:643` ... | A | 同推荐项 | :745 | P2 |
| G7-Q31 | impl-07-assembly / D-15 | 基底 Snapshot 修订的状态与并发 | A: 新 Snapshot 修订封存后调用 `supersede_revisio...<br>B: 不 supersede，靠「查最新修订」判断基底（违反 §7 `:207`）。<br>C: 同一 technique 只允许一个 running release_ru... | A | 同推荐项 | :207 | P2 |
| G7-Q32 | impl-07-assembly / D-16 | M7 Checkpoint 落盘粒度 | A: 视同人工阶段：非人工 task（`propose_r<N>`、`seal_...<br>B: 只按非人工 task 落盘。 | A | 同推荐项 | §17.1 | P2 |
| G7-Q33 | impl-07-assembly / D-17 | Part 级 ReviewedEditionPackage 能否汇编 | A: 允许。Snapshot 逐 Edition 记已汇编 `edition_p...<br>B: 只接受完整 Edition（首纵切宿主只有「卷一·前三页」，永远无法汇编）。 | A | 同推荐项 | §6.1 | P2 |
| G7-Q34 | impl-07-assembly / D-18 | Work 标识 | A: 以 `src_<work>_ed<NN>` 的 `<work>` 段作 `...<br>B: 新登记 `wk_` 前缀。 | A | 同推荐项 | :45 | P2 |
| G7-Q35 | impl-09-intake / D-09-01 | 宿主目录与模块划分 | A: 两个包 `pipeline/source_intake/`（M1）与 `p...<br>B: 单包 `pipeline/intake/`，下设 m1、m2 子模块。<br>C: 挂进 `ocr/` 工具旁路。这违反 §2 第 2 条独立 Module，... | A | 同推荐项 | - | P2 |
| G7-Q36 | impl-09-intake / D-09-02 | EditionPart / Work / Edition 身份与申报件落点 | A: 申报件 YAML 进 Git（只含元数据，不含受版权限制的内容）。由主 A...<br>B: M1 每次新发号，并按 (source_id, label) 在 Ledg...<br>C: 首次发号后写回 `var/`（不进 Git，克隆后身份丢失）。 | A | 同推荐项 | §8.1 | P0 |
| G7-Q37 | impl-09-intake / D-09-03 | 人工终态决定表的作者与落点 | A: 用户亲笔写 YAML 决定表进 Git（`…/part_p001_p010...<br>B: 在 FastAPI + Vue 校对工具里加终态 UI。超出最薄形态，且 ...<br>C: 主 Agent 或执行者代填。这等于伪造人工决定。 | A | 同推荐项 | §10.1 | P2 |
| G7-Q38 | impl-09-intake / D-09-04 | page_010 盘面页的终态路径 | A: M2 先按原字节封存原始 `ocr_page` 修订；再以 `prev_r...<br>B: 改 M3 规则，允许有行的 known_unrecognizable 页被...<br>C: 用户在 OCR 工具里人工转录后标 `manually_transcrib... | A | 同推荐项 | :245 | P2 |
| G7-Q39 | impl-09-intake / D-09-05 | M2 Gate 画像（校对完成度） | A: `gate_profile: intake_only`。只判异常页终态、证...<br>B: 全部字框为 verified 或 corrected 才放行。需要用户校对...<br>C: 按 OCRProfile 抽样实际正确率 ≥95% 放行（ocr-prof... | A | 同推荐项 | §10:480 | P2 |
| G7-Q40 | impl-09-intake / D-09-06 | §7「只读冻结输入」与工作目录读取的边界 | A: 把二者视为本 Module 的外部摄入边界。begin 前一次读入全部字节...<br>B: 先由一个独立登记步骤把 OCR 文件写成 Artifact，M2 Step...<br>C: 不处理。 | A | 同推荐项 | §7:207 | P2 |
| G7-Q41 | impl-09-intake / D-09-07 | 新 artifact_type | A: 新增以上四类；质量报告嵌入 `validation_report`，不另设类型。<br>B: 合并为单一 `ocr_log`。Artifact 没有 role 字段，合...<br>C: 不登记日志。违反 §10:474「完整审计日志」与 legacy-stor... | A | 同推荐项 | §22.1 | P0 |
| G7-Q42 | impl-09-intake / D-09-08 | source_manifest、ocr_page_set 内容形状与 m1/m2 payload | A: source_manifest 的顶层键集合与顺序同 fixture `m...<br>B: payload 完全照抄 fixture。路径会指向不存在或无关的 fix...<br>C: 为 m1/m2 payload 另立 Schema。需要新 Schema，... | A | 同推荐项 | :76 | P2 |
| G7-Q43 | impl-09-intake / D-09-09 | 人工决定写回路径、decision_type 与 deferred | A: 单进程完整走 §7.1。每个有终态的页：put 并 seal human_...<br>B: 遇 deferred 直接 `fail_step_run`（记为 Gate...<br>C: 照抄 fixture_ingest，不走 §7.1。 | A | 同推荐项 | :226 | P2 |
| G7-Q44 | impl-09-intake / D-09-10 | OCRProfile 缺失与「原始 OCR / 校订修订」分离 | A: 配置修订记 `ocr_profile_revision_id: null`...<br>B: 本包实现最薄 OCRProfile YAML 与 Schema。要新增 S...<br>C: 忽略。 | A | 同推荐项 | §10:476 | P2 |
| G7-Q45 | impl-09-intake / D-09-11 | 验收脚本命名与 CLI 退出码 | A: 本包新建这两份 §19.0 脚本，均返回 2（照 m3-coverage ...<br>B: 另建 `intake-real10.sh`，§19.0 两脚本留待纵切后。<br>C: 两者都建。 | A | 同推荐项 | §19.0 | P2 |
| G7-Q46 | impl-09-intake / D-09-12 | 与 M3 输入解析的接口风险（需 impl-02 负责方确认） | A: 本包在 begin 前拒绝「同一 Part 已有任何 m1 或 m2 运行...<br>B: 本包立即改 impl-02 的 inputs.py。越界，而且 impl-...<br>C: 不处理。 | A | 同推荐项 | :83 | P2 |
| G7-Q47 | impl-09-intake / D-09-13 | 字框与行文本不一致 | A: M2 Gate 只把它记为警告写进 `validation_report....<br>B: 阻断 Gate，由用户在 OCR 工具修正。<br>C: M2 自动以字框重算 line.text。这是静默改文，违反 §11:50... | A | 同推荐项 | :35 | P2 |
| G7-Q48 | impl-09-intake / D-09-14 | 权利、准入决定与源 PDF 派生关系 | A: 权利状态与发布策略取自申报件（沿用 fixture 已登记的文本「文字公版...<br>B: M1 额外登记一条准入 human_event，M1 进入 awaitin...<br>C: 不记。 | A | 同推荐项 | §9:452 | P2 |
| G7-Q49 | impl-10-corpus-semantic / D1 | SemanticSpan 标识前缀（阻断 ACT 00/02/03） | B: SemanticSpan 改用 `ss_`，StructuralSpan ...<br>C: 不设领域 ID，用 `ss_…#<start>-<end>` 复合键。违反... | C | 同推荐项 | :27 | P0 |
| G7-Q50 | impl-10-corpus-semantic / D2 | 真实模型调用开关与 Adapter 归属 | B: 本包直接实现某厂商 Adapter，由显式开关 + 密钥环境变量启用，测试...<br>C: M3 不自带 Proposer 接口，等 M4 Model Adapter... | A | 同推荐项 | §11:516 | P1 |
| G7-Q51 | impl-10-corpus-semantic / D3 | `gate_profile` 新取值与 M4 消费约束 | B: 取值 `full`。更短但语义不自明。<br>C: 删除 `structural_only` 路径，只保留完整 M3。要改 i... | C | 同推荐项 | :34 | P2 |
| G7-Q52 | impl-10-corpus-semantic / D4 | StepRun 拓扑：语义层放在哪个 StepRun（阻断 ACT 04/05） | B: 先 `run_m3`（结构包封存）再开语义 StepRun，以 `supe...<br>C: 改 Ledger，允许同阶段多个任务 StepRun 各自 succeed... | A | 同推荐项 | §7.1 | P0 |
| G7-Q53 | impl-10-corpus-semantic / D5 | 回放录制的身份：Adapter 后端还是冻结输入 | B: 把录制内容嵌进 `configuration` 修订（`put_run_a...<br>C: 新增 artifact_type 并扩展 `fixture_ingest`... | A | 同推荐项 | §12.2 | P0 |
| G7-Q54 | impl-10-corpus-semantic / D6 | M3 边界裁决的 `decision_type` | B: 传 `None`，类型只写在事件内容里。可行但 Ledger 侧无法按类型查询。<br>C: 规格 §8.2 增第 9 类 `review_segmentation`。... | A | 同推荐项 | §8.2 | P2 |
| G7-Q55 | impl-10-corpus-semantic / D7 | 语义层金标放在哪（阻断 ACT 00） | B: 扩展 `mini_ed01/tools/build_fixture.py`...<br>C: 放进 `pipeline/corpus_compiler/semantic... | A | 同推荐项 | - | P0 |
| G7-Q56 | impl-10-corpus-semantic / D8 | 复用结构层私有 Ledger 读写助手（影响 ACT 04） | B: 先由主 Agent 批一个纯重构 ACT，把它们抽到公开模块 `pipel...<br>C: 在语义子包里重写一份。重复实现，输入契约可能漂移。 | A | 同推荐项 | - | P1 |
| G7-Q57 | impl-10-corpus-semantic / D9 | 为达 exit 0 必须修改的三个结构层已有文件（阻断 ACT 06） | B: 另建 `openspec/acceptance/m3-semantic.s... | A | 同推荐项 | :86 | P0 |
| G7-Q58 | impl-10-corpus-semantic / D10 | §11 第 5 条「条件/结论、正文/注文、通则/命例完整性检查」的范围 | B: 最小实现片段类型（`heading/catalog/paratext/pr...<br>C: 第 5 条单列一行 BLOCKED，`m3-coverage.sh` 维持... | A | 同推荐项 | :521 | P2 |
| G7-Q59 | impl-10-corpus-semantic / D11 | 字框不对齐行的 `evidence_level`（影响 ACT 02/03 金标计数） | B: 一律 `glyphbox_level`、只给行 bbox。会在证据链上假绿。<br>C: 字框不对齐的行拒绝编译（fail-closed）。fixture 无法通过... | A | 同推荐项 | §22.1 | P2 |
| G7-Q60 | impl-10-corpus-semantic / D12 | 窗口选择规则（规则层占位） | B: 规则由 TechniqueProfile 声明（标题/条目/表格识别器）。...<br>C: 多行窗口（连续需模型的行合并成窗口，允许跨行片段）。散文、注疏必需，但 o... | C | 同推荐项 | §11:515 | P2 |
| G7-Q61 | impl-10-corpus-semantic / D13 | 是否引入复核模型 C（§11:518「由独立复核或人工决定」） | B: 引入 C 重读原文，只有 C 不能与 A 或 B 完全一致时才进人工。多一... | A | 同推荐项 | §12.2 | P1 |
| G7-Q62 | impl-10-corpus-semantic / D14 | 新 artifact_type 与内容格式登记 | B: 本包同时新增 `openspec/schemas/semantic_spa... | A | 同推荐项 | - | P0 |

## 5. 依赖与下游约束补充建议
- **impl-07-assembly 缺下游约束说明**：
  应在 `docs/blackbox-spec-rework/work-items/impl-07-assembly/README.md` 第 295 行（即 `### 5.1 上游输入（M7 消费）` 的 M6 行 `约束` 列）补充文字：
  `所属 StepRun 必须 succeeded`
