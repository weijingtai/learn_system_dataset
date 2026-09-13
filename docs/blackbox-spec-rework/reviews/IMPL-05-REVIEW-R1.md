# IMPL-05 四查审查 R1（独立审查者 W4-R5）

- 审查对象：提交 `8cedae2` 的 `docs/blackbox-spec-rework/work-items/impl-05-knowledge/` 全部 15 文件。已验证 HEAD（`6cd4379`）与该提交在该目录下无差异（`git diff 8cedae2 HEAD --stat -- <目录>` 为空），以当前文件为准只读。
- 依据：`G7-RULINGS.md` §1 P1–P9、§3、§6、§9 第 2/10/13/17/21 条、§9.1 第 25–26 条、§9.2 第 27 条、§9.3 第 34–43 条（第 43 条为用户决定）、§9.5 第 46 条、§9.6 第 47–50 条；`reviews/G7-DRAFTS-REVIEW-R2.md` G7-Q01–Q16；规格 `openspec/learn-system-blackbox-architecture.md` §5/§6/§7/§7.1/§8/§12/§13.1/§17/§17.1/§19/§19.0/§20/§22；已验收代码 `pipeline/ledger/`（service/store/states/ids/errors/fixture_ingest）、`pipeline/corpus_compiler/step.py`、`pipeline/validation/inputs.py`；`pipeline/dataset_compiler/`（只读）；`INTERFACES.md` §2.4/§3.1/§3.2/§3.10/§4/§6 I-11 与 `check_interfaces.py`；`openspec/acceptance/run_all.sh`；任务管线（HANDBOOK/SCHEMA.md/run_task.py/task-templates）；fixture `mini_ed01/`。
- 只审不改；本报告为唯一写入文件。

## 一、忠实性

- Q01–Q16 ↔ README §4 D-01–D-16 逐条对应，且与 G7 §3 的加裁一致（Q01 按 P6、Q02 加「金标独占 ACT（P4）」、Q10 按 P2+P3、Q13 采纳 A）。
- P1/第 43 条：M4 最薄接入、首纵切外；20.1/20.4/20.8/20.9 只写「转判前置之一」（README §6.6），本包不改 `run_all.sh` 且完成判据要求其输出与基线逐字相同，不伪造 PASS。
- P6：渠道闭集只收 `fixture_gold`/`task_pipeline_manual`，`model_adapter` 在 begin 前拒收（act/00 S3、act/03 步骤 3），并有禁模型 import 的 grep 门禁。
- P7：签发 StepRun 归 M6（D-07）；本包只冻结 `review_decision` 形态与 `derive_content_status` 纯函数；测试替身显式声明（BDD §7 前言、act/06 tests_first）；金标全路径后字节不含 `expert_verified` 有验收检查（act/07 status_ceiling）。
- P2/P3：新 artifact_type 只提名（§6.1.1），登记归 act/12；复用已登记 `validation_report`（与第 35、50 条一致）；`0.1.0-draft`；不新增 `openspec/schemas/` 文件。
- P4/第 48 条：fixture m4 金标与 `verify.sh` V5/V6 扩展为主 Agent 独占 ACT，执行者禁改 fixture，K4 以其落地为强制前置（README §3/§9/§10 N2、ACT.yaml preconditions、act/07 preconditions）。
- P5/D-15：只认 `succeeded` + `compile_corpus`；输出经 `result_json["output_artifact_ids"]` + `artifacts.artifact_type` 只读 SELECT（与已验收 `pipeline/validation/inputs.py:130-137` 同法）；不依赖 `list_transformations` 返回输出（`service.py:129-131`、`store.py:552-558` 实证只返回表行）。
- P9：不改 `pipeline/ledger`；错误码复用九码。
- 忠实性发现：F1、F2、F3、F4。

## 二、覆盖性

- BDD §1–§9 逐场景核对：均有具名 tests 用例或 verify 命令落点（1.x→act/00，2.x→act/01，3.x→act/02，4.x→act/03，5.x→act/04，6.x→act/05，7.x→act/06，8.x→act/07，9.x→act/08）。缺口仅 F6（BDD 4.4 的「M4 已封存」提交分支）。
- 用例数阈值 16/41/65/80/94/106/118/129/134 与各 ACT `tests` 段具名用例累计逐一相符（计数：00=9+7、01=25、02=24、03=4+11、04=14、05=12、06=12、07=11、08=5），TDD §1「数值以 ACT tests 段逐条计数」口径自洽。
- `m4-stage-gate.sh` 16 项判定（13 PASS + 3 BLOCKED，exit 2）由 ACT 07 完整产出，BLOCKED 说明行名逐字取 §19 第一列（M4 Knowledge Extraction / M3 Corpus Compilation / Contract Registry）；`run_all.sh`、`m3-coverage.sh` 均为只读回归基线。
- TDD §1 每 ACT Red→Green 成对；K1–K5 分组与 `depends_on` 一致；ACT 时长 75/90/75/85/90/75/60/80/45 分钟，全部 ≤110。

## 三、可执行性（逐项给出代码 文件:行号）

- Ledger 方法与签名全部实测吻合：`put_run_artifact` 仅收 configuration/technique_profile、写即 sealed、返回二元组（`service.py:66,528-597`）；`begin_step_run` stage 由配置内容推导（`service.py:295-310,369,405-410`）；`put_artifact` 返回 `(artifact_id, revision_id)`（`service.py:442-526`）；`seal_revision:599`、`register_stage_package:718-774`、`record_transformation` 含 `model_ref`/`human_event_revision_ids` 且校验输入/输出/事件归属（`service.py:777-843`）；`await_human:885-920`、`record_human_event` decision_type 八类或 None、不消费 token（`service.py:922-963`；`states.py:57-66`）、`resume:965-989`；`finish_step_run` 只校验 StepResult、无 StagePackage 亦可（`service.py:1132-1185`）；`fail_step_run:1187`；`write_checkpoint` 签名 keyword-only（`service.py:1364-1377`）；`LedgerReader.read_object:1606`。
- act/03「configuration_artifact_id 取 config（修订号）」与 StepRequest Schema（`configuration_artifact_id` 为 `$ref: artifactRevisionId`）及已验收先例（`corpus_compiler/step.py:89,113`）一致。
- 脚手架签名吻合：`ingest(fixture_dir, service, asset_root=None, *, stages=…)`（`fixture_ingest.py:255`，stages 须为前缀）；`run_m3(service, edition_part_id, *, batch_size=10)`（`corpus_compiler/step.py:35`）；m3 StepResult `output_artifact_ids` 恰含 1 corpus_package + 1 corpus_spans + 1 coverage_report + 1 stage_package（`corpus_compiler/step.py:372`）；`payload.spans_revision_id`/`gate_profile=="structural_only"`/`manifest.content_sha256==spans sha`（`corpus_compiler/step.py:317-331`）；fixture-only m3 带 `operation=="compile_corpus"`（`fixture_ingest.py:354-356`、`expected/m3.stage_package.yaml:39`）且无 `spans_revision_id`（README §6.1 判断属实）。
- 附录 A 实测全部吻合：`spans.yaml` sha256=`ec6d77b9…44ef`、43 条（page_001 4、page_003 39）；s02 [5,12]、s04 [20,37]、s12 [67,72]、s19 [118,122]；s04 [0,7]→[20,27]、[7,12]→[27,32]，s02 quote→[8,12]，s12 [1,3]→[68,70]，s19 [1,4]→[119,122]；page_001 内 s02 先于 s04（000001 归「宋錢如璧撰」成立）；s13「宮」×2（歧义用例）；「辰」×5、「胎」×1（D-06 证据复现）。
- canon：6 个 yaml，closed_set_size 合计 49（8+12+12+10+5+2），`co_shared_branch_05` 在册；`pipeline/registry/schools/` 仅 `_TEMPLATE.yaml`（D-05 `schools: []` 属实）。
- fixture `verify.sh` V5/V6 现仅覆盖 m1–m3，`for stage in ("m1", "m2", "m3")` 出现 2 次——与 TDD §0「K4 前须为 0」及 F5 修正点自洽。
- legacy：`ge_ju_rules` 实测 496 条、original_text 非空 0；库 sha256=`1f25a930…c764` 与 `legacy-storage-transition.md` 登记及 act/08 `LEGACY_DB_SHA256` 一致；`run_all.sh 20.7` 分支（`run_all.sh:264` 起）与 act/08 verify「仍以 FAIL 20.7 开头」相容。
- 任务管线依据属实：`run_task.py --model manual` 存在；SCHEMA.md `relation` 五值；HANDBOOK 工位 4/5 形态与 `layer: main/commentary` 为 M3 语料层字段（F3 修正点成立）；`stage5_assertions` 模板在。
- `check_interfaces.py` 当前实测 `I00-IF SUMMARY pass=18 fail=0`、exit 0，`REQUIRED_TYPES` 无任何 M4 类型——与 N1 背景一致，但与包内门禁组合矛盾（F2）。
- 可执行性发现：F1、F2、F5、F7。

## 四、独立性

- ACT 依赖无环：00→01→02→03→04→05→07 主链；06 仅依赖 00（编入 K3 串行）；08 依赖 01；`ACT.yaml` executor_groups 与各 ACT `depends_on` 一致，无环。
- 写范围互不重叠：仅 `pipeline/knowledge_extraction/**` 与 `openspec/acceptance/m4-stage-gate.sh`；与 `pipeline/dataset_compiler/`、`pipeline/validation/`、`pipeline/corpus_compiler/`、`pipeline/ledger/` 及 impl-08 的 `pipeline/orchestrator/`、`pipeline/contract_registry/` 零写交集；不写 `run_all.sh`。act/04→act/05 串行复写 `step.py`/`__main__.py` 属同包顺序 ACT，非共享面并发。
- 防同错同过：`gate.py` 禁 import `assemble`/`submission`、页块自算（act/02 contract + verify grep + `test_gate_does_not_import_assemble_or_submission`）；`acceptance.py` 禁 import 三模块、自维护 ITEM_KEYS、自算正则与页块、不读 `run_m4` 返回 gate、永不执行副本 `verify.sh`（act/07 contract + 2 个源码扫描用例 + `test_shell_never_trusts_copy_verify`）；`resume_m4` 以冻结输入重算 lane/dispute 字节比对（BDD 6.6）；金标路径后字节扫描 `expert_verified`。
- 测试宿主 tempfile；`tests/data/appendix_a` 与 fixture 金标逐字字节比对（act/07 `test_tests_data_equals_fixture_gold`）。

## 发现（编号｜严重度｜文件:行号｜问题｜依据 文件:行号｜修改建议）

- F1｜阻断｜act/00.yaml:32｜`canonical_json` 定义缺 `separators=(",", ":")` 与 `allow_nan=False`，与 README 固化默认不同（json.dumps 缺省分隔符含空格，两者字节不同）｜README.md:115；ACT.yaml:52（公开返回键/字节须与 contract 逐字一致）；act/07.yaml:37-38（golden_match 以 expected `manifest.content_sha256` 比对 sha256(candidate_set 字节)，金标由主 Agent act/05 生成器另产）｜act/00 contract 补齐为与 README §5.3 逐字相同的 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")`，全包唯一口径，否则 ACT 00 即触发「contract 两种理解→停手上报」（ACT.yaml:64），且 K4 金标哈希存在系统性错位风险。
- F2｜阻断｜ACT.yaml:13,57（另见 TDD.md:13、PROMPT-G1.md:39,48,68、ACCEPTANCE.md:9,22）｜开工前提/门禁/停手规则硬编码 `I00-IF SUMMARY pass=18 fail=0`，同句又要求「§4 已含上述 M4 类型」「§4 仍只有旧命名→停手上报」：act/12 执行前 §4 无 M4 类型（实测 pass=18 且 REQUIRED_TYPES 无 M4），act/12 执行后按其 Green 期望为 pass=24，两种状态都无法同时满足，执行者必在 K2 开工前提或任一回归处停手｜G7-RULINGS.md:137（第 47 条：act/12 须在 impl-05 K2 前执行并验收）；impl-00 act/12.yaml:45,62（Green 期望 `pass=24 fail=0`）；check_interfaces.py:16-24（当前 REQUIRED_TYPES）；README.md:393（N1 选项 A 自认会把 M4 类型加入必查清单）｜全部 6 处改为「末行 `I00-IF SUMMARY pass=24 fail=0`（以 act/12 验收值为准）且 §4 含本包五个 M4 类型、旧名清零」；ACCEPTANCE §0 派发前核对同步。
- F3｜重要｜README.md:148｜公开读方法清单列出 `list_step_runs`，`pipeline/ledger` 无此方法（只有 `list_step_run_events`）；执行者按 contract 调用将 AttributeError，或按 on_fail「Ledger 公开方法行为与 contract 假设不符→停手上报」空停｜service.py:111-163（LedgerReadMixin 方法面：get_revision/get_step_run/list_step_run_events/list_transformations/latest_checkpoint/list_checkpoints/run_status/stage_progress）、service.py:1606（read_object）｜改为 `list_step_run_events`（并注明其事件流语义）或删除该名；各 ACT contract 实际未引用 `list_step_runs`，删除即可。
- F4｜重要｜README.md:148｜允许只读 SELECT `human_events`、`processing_runs`（act/03.yaml:33 technique_id 取 processing_runs 表 SELECT；act/05.yaml:19 R4 human_events 表 SELECT），同句却称「缺口清单以 impl-00 README §5.2 为唯一清单」，而该清单只登记 frozen_inputs、artifacts.artifact_type、stage_packages 三类，未含这两表；违反第 25 条「唯一清单」裁定，impl-08 补读接口时将遗漏｜impl-00-interfaces/README.md:119；G7-RULINGS.md:90（第 25 条）、:73（第 13 条）｜在 §6.1 明示这两类为新增只读缺口，并列入向主 Agent 提请补登 impl-00 §5.2 的待办（或在可行处改用公开方法：人工事件可见性可部分经 `list_step_run_events` 事件流替代）。
- F5｜重要｜act/03.yaml:71｜`test_resolve_refuses_fixture_only_m3` 断言消息含「M3 未通过」，但 contract 只把该消息绑定于「候选 0 个」分支；fixture-only m3（ingest 写入 operation=compile_corpus 且 succeeded）会通过候选过滤、落入「恰 1 个 corpus_spans/coverage_report」输出形状分支，该分支的 code/message 未定义，测试期望不可由 contract 推出｜act/03.yaml:30（消息仅定义于候选 0/多分支）、:28（输出恰 1 个规则无错误定义）；fixture_ingest.py:354-356、expected/m3.stage_package.yaml:39｜在 act/03 contract 为输出形状不符分支显式指定 `ExtractionRefused(code="REF_001", message 含「M3 未通过」)`（或另定消息并同步改测试注释），消除两种理解。
- F6｜建议｜BDD.md:38（4.4）｜「M4 已封存」的 submit 拒收分支无具名用例（现有 4 例覆盖重复/渠道/c 路/形状错误）｜act/03.yaml:48（步骤 4 含 M4 已封存拒收）、act/03.yaml:68-80（tests 列表无对应）｜补一具名用例（如 `test_submit_refused_after_m4_sealed`，可并入 act/03 或 act/04 后），或从 BDD 4.4 删除该分支。
- F7｜建议｜act/05.yaml:25（W4）｜`write_checkpoint` 调用缺 `edition_part_id` 实参；Ledger 签名要求该 keyword-only 参数（无默认值）｜service.py:1364-1377；对照 act/03.yaml:55（步骤 8 已写 `edition_part_id=ep`）｜W4 补「edition_part_id=ep」。

## 判定

**REWORK**（阻断 2：F1、F2；重要 3：F3、F4、F5；建议 2：F6、F7。阻断修复并复审前不得派发 K1；F2 涉及与 act/12 的顺序契约，建议由主 Agent 一并核对 impl-00 act/12 的 pass 期望。）

本判定只覆盖 `8cedae2` 的工作包文本与已验收代码的一致性；未发现任何伪造 PASS/BLOCKED、越权写范围或同错同过问题，修复上述文本级缺陷后包体质量可达 READY。

（审查者：W4-R5；依据 HEAD `6cd4379` 只读核查；`git diff --check` 无输出。）
