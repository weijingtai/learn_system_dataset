# impl-08 四查审查 R1（独立审查者，W4-R8）

- 被审对象：提交 `cd6c7a6` 中 `docs/blackbox-spec-rework/work-items/impl-08-orchestrator/` 全部文件（README/ACT.yaml/BDD/TDD/ACCEPTANCE/PROMPT-I1/act/00–10）。
- 依据：`G7-RULINGS.md` §1 P1–P9、§6、§9.1 第 25–26 条、§9.2 第 27/32 条、§9.3 第 34–43 条（第 43 条为用户决定：维持关键路径）；规格 §5/§6/§7/§7.1/§17/§19.0/§20/§22；已验收代码与 `openspec/acceptance/run_all.sh` 以当前工作树只读核对。
- 方法：工作包全文通读；对每个 ACT 引用的入口签名、返回键、Ledger 方法、事件 payload、Schema 必填键逐条与实际代码比对；对 D-9「实测命中」行号用同口径 grep 复测；对 run_all.sh 20.1/20.9/20.10 分支逐行比对；用例数阈值按具名用例累计算。

## 一、忠实性

**结论：总体忠实。** 逐项核对结果：

- 裁决 34–43 与 README §4.1 各条推荐一一对应（34=D-4 B、35=N-4 A、36=D-6 A、37=D-7 A、38=D-8 C、39=D-9 B、40=N-2 A、41=N-3 A、42=D-16 A、43=N-1 维持 BLOCKED），ACT.yaml global_rules 与 act/00/03/04/05/08 均按已裁方向写（entry_kwargs/owns_processing_run、N-2 A、D-8 C、D-16 A、act/10 DEFERRED）。
- §20.1：README §1 期望 `BLOCKED registered_modules_m1_m6 … exit=2`，act/07 `on_fail` 明令「不得把 registered_modules_m1_m6 写成 PASS」，符合第 43 条「如实 BLOCKED 不伪造」。
- §20.9：run_all.sh:314–315 现状 `BLOCKED … "GraphProjectionPack 未实现"`，ACT 09 不触碰，与第 43 条一致。
- 不改 `pipeline/ledger/**`：act/10 标 `DEFERRED` 且不入 `executor_groups`（ACT.yaml:8,42-44、README §8/§9、PROMPT-I1 禁写清单）。
- 新 artifact_type：D-11/N-4 A 复用已登记 `validation_report`（act/04:63-65、ACT.yaml:51）；例外见 F2。
- run_all.sh：写范围仅 ACT 09，且 `preconditions` 注明「impl-04 ACT 08 已验收（P4）…本 ACT 为其后唯一写者」（act/09:6-9）；两处替换目标行在现状中逐字存在（run_all.sh:197、:322）。
- 规格引文抽查全部属实：§5:116–128 六项查询与五队列名逐字、§6.1:149 合取、§17:828/836、§17.1:843–845、§7.1:222 无超时、§14.1:641–642 阈值、§19 首列行名逐字、§20:935–947、§22.3:991、§7:203/§8:244 schema_version "1.0.0" 与 artifact_ref.schema.json `$defs.schemaVersion` const 一致。

## 二、覆盖性

**结论：9 章 BDD 场景→具名用例映射完整，唯 F3 一处缺用例；ACT 07/08/09 可产出 §20.1/§20.10/orchestrator-gate/contract-registry 判定。**

- BDD 1–9 逐条映射具名用例：1.1→test_repository_registry_is_consistent；1.2→sha256/path/version/stage_rows/human_queues/duplicate/imported_entry/consumes_order/stub/port/entry_kwargs 十一例（缺「stage 超出 m1–m8」，见 F3）；1.3–1.6、2.1–2.3、3.1–3.4、4.1–4.5、5.1–5.9、6.1–6.6、7.1–7.6、8.1–8.5、9.1–9.4 均各有具名用例（act/00–09 tests 清单逐一比对，无缺号）。
- orchestrator-gate.sh 六项、contract-registry.sh 五项、run_all.sh 20.1/20.10 判定均可由 ACT 07/08/09 的 acceptance 模块 + accept_check 产出；accept_check 的 BLOCKED 行解析与 block_line 的 `前置缺失: %s；%s` 格式（run_all.sh:76）吻合，并有无法解析时的宿主 BLOCKED 兜底（act/09:25-29）。
- 反同错同过：real_chain 不调用 evaluate_stage_gate（act/07:22,30）、test_gate_bypass_defect_detected 注入 Gate 放行缺陷、orchestrator 越界判 FAIL 而非 BLOCKED（act/08:35, BDD 9.3）。
- 阈值可达性：具名用例累计 ACT00=15、+ACT01=29、ACT02 后 45、ACT03 后 61、ACT04 后 87、ACT05 后 99、ACT06 后 114、ACT07 后 124；TR 侧 +ACT08=134、+ACT09=139。TDD §1 各阈值（15/25/15/30/46/55/65/74/34/72/38）全部低于累计具名数，无需凑数（注：act/01 verify 写 ≥24 与 TDD ≥25 口径不一，见 F6）。

## 三、可执行性

**结论：签名/返回键/Ledger 语义逐条核对全部与代码一致；唯 F1、F2 两处使 ACT 03/07 按字面不可达，构成阻断。**

入口与返回键（已逐个实读代码）：

- `run_m3(service, edition_part_id, *, batch_size=10)` corpus_compiler/step.py:35；返回 `step_run_id/stage_package_id/package_revision_id/spans_revision_id/…/gate`（:381–403）；StagePackage `manifest.output_artifacts=[corpus_package]`（:329）。
- `run_m5(service, edition_part_id, *, target_consumption_level="INTERNAL_DEMO")` validation/step.py:59；`validation.passed = gate["passed"]`（:275）；返回 `validation_package_revision_id/gate/counts`（:332–357）。
- `run_m8(service, edition_part_id, *, consumption_level, min_app_version=None, release_id=None)` dataset_compiler/step.py:194；自建 `release_run`（:211–212）；StagePackage `payload.consumption_level`（:525，act/07 断言可算）、`manifest.output_artifacts=[publication_package]`（:535）；返回含 `processing_run_id`。
- `ingest(fixture_dir, service, asset_root=None, *, stages=STAGES)` fixture_ingest.py:255，`STAGES=("m1","m2","m3")`（:39–40）、`STAGE_OUTPUT_TYPES`（:43–47，m1=source_manifest/m2=ocr_page_set/m3=corpus_package，与 expected/m1、m3.stage_package.yaml 一致）；返回 summary 含 processing_run_id/edition_part_id/technique_id（act/07 准备 A 可用）。
- `register_source_assets(service, edition_part_id, asset_root)` shim/m1_shim_source_assets.py:250；经 `supersede_step_run` 接替最近 succeeded m1 运行（:286、:313）；:180–234 无 stage_package 写入（grep 证实）。

Ledger（service.py，除注明外）：`_live_step_run:253`（running/awaiting_human 可写，act/05 在 awaiting_human 上 put human_event 可行）、`_configuration_stage:295–310`（D-1 成立，step_request.schema.json 无 stage 字段）、`create_processing_run:319`、`begin_step_run:405`、`supersede_step_run:412`、`put_artifact:442`（artifact_type 仅限 `^[a-z][a-z0-9_]*$`:455，桩的 stub_output 等可写）、`put_run_artifact:528`（闭集 configuration/technique_profile:548，返回 `(artifact_id, revision_id)`，act/04 `[1]` 取修订号成立）、`seal_revision:599`、`register_stage_package:718`（`pkg_<stage>_` 前缀校验与 act/02 wrong_stage「换匹配前缀」写法吻合）、`record_transformation:777`（键名与 act/02 逐字一致）、`await_human:885`（返回 token:917；事件 payload 含 `pending_queue`，act/06 读法成立）、`record_human_event:922`（事件 artifact_type 必须 human_event，act/05 脚手架吻合；不消费 token）、`resume:965`、`suspend:991(reason, source)`、`recover:1033`（回 awaiting_human 重锚 token，BDD 6.4 可行）、`finish_step_run:1132`（校验 output/validation/log 三列表 sealed 且属本 StepRun:1155–1162，同事务封存 StepManifest:1183）、`fail_step_run:1187`（事件 `failure` payload `failure_revision_ids`:1209，act/04 run_legacy failed 重建读法逐字成立）、Checkpoint 阶段封存守卫:1280–1285、`write_checkpoint:1364`（键 completed_tasks/human_decisions/pending_queue/next_pointer）、`recover_from_checkpoint:1430`（返回 `(new_step_run_id, plan)`，plan 含 `completed_task_ids`，act/05/act/02 读法成立）、读方法 `:117–164`。client.py:108–451 公开方法与 act/01 `LEDGER_PORT_METHODS` 26 个一一对应；`read_object` client.py:451、service.py:1606。`run_status` 返回 `status/started_at/finished_at/step_runs`（:1538–1555）；`stage_progress`（:1558）字段与 act/06 契约吻合；step_runs 列含 status_version/request_json/result_json/supersedes_step_run_id/created_at/updated_at（store.py:88–102）；artifact_revisions 含 artifact_id/schema_id/step_run_id/status/sha256（store.py:36–59）；utcnow 为 ISO-8601 Z 结尾（store.py:198），act/06 吞吐解析可行。错误类 LedgerError/InvalidResumeToken/WriterLocked（errors.py:26,95,88）支撑 RegistryInvalid/OrchestratorRefused 与 CLI exit 3。

验证命令与期望：verify-T.sh、g3-r3/mutations.sh、g4-r3/check_d16.py、openspec/schemas/verify.sh、fixture manifest.yaml、test_daemon.py、ledger cli `--root` 约定均存在；m3-coverage.sh 行格式与 act/07 声明一致；fixture expected m3 `content_sha256: ec6d77…`（expected/m3.stage_package.yaml:32）可计算比对。

时长：60/80/75/75/90/90/75/90/85/45 分钟，全部 ≤110（act/10 90 分钟为 DEFERRED 不计）。

## 四、独立性

**结论：通过。** depends_on 链 00→01→…→09 线性无环（act/10 依赖 08 且 DEFERRED）；11 个 ACT 的 `writes` 两两不相交（逐对核对 ACT.yaml:10-43）；与 impl-04 写范围（`pipeline/dataset_compiler/**`、`m8-span-identity.sh`、run_all.sh）交集仅 run_all.sh 且被 ACT 09 前置互斥（P4）；与 `pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/ledger/**` 零写交集。Gate 判据独立：act/03 gate.py 禁 import runner/module/stubs/edition_run（含 AST 级用例 test_gate_module_imports_are_independent）；real_chain 自 Ledger 重算；test_gate_bypass_defect_detected 注入缺陷验证判定不与被验实现同源。Orchestrator 源码不得 import 加工 Module 包、不得出现 .store/.objects（ACT.yaml:49-50、TDD §2 多条 grep、act/08 对 orchestrator 越界判 FAIL）。

## 五、发现清单

格式：编号｜严重度｜文件:行号｜问题｜依据｜修改建议。

- F1｜阻断｜act/03.yaml:28-30（对照 :16-18）、BDD.md:32、act/07.yaml:28、act/03.yaml:59｜`stage_package_valid` 要求「每个 effective StepRun 恰 1 个 StagePackage」，与同包 N-2 A 矛盾：m1_shim 接替运行不承载 StagePackage（shim:180–234）且按 :16-18 的规则留在有效集内（接替者无包→被接替的 fixture m1 运行不移除），于是 eff(m1)={fixture 运行(1 包), shim 运行(0 包)}，按字面 m1 Gate 必 blocked；而 BDD 4.4、test_superseded_run_without_stage_package_stays_effective（act/03:59）与 act/07 real_chain「m1/m2 Gate passed（imported）」均要求 passed，act/07 的 5 PASS 期望不可达｜G7-RULINGS §9.3 第 40 条；m1_shim_source_assets.py:180–234,286,313｜二选一并同步 BDD 4.2/4.4 与 act/07： (a) `stage_package_valid` 改为「每个 effective StepRun 的 stage_package 数 ≤ 1，且存在至少一个 effective StepRun 恰承载 1 个本 stage 的 StagePackage」（负例 test_blocked_when_stage_package_missing 仍失败）；或 (b) effective_step_runs 增加规则「supersede 他人但自身不承载本 stage StagePackage 的接替运行不入有效集」。
- F2｜阻断｜act/07.yaml:21（对照 act/04.yaml:63-65、BDD.md:37、TDD.md:64、act/08.yaml:35）｜gate_chain_stub_m1_m6 要求「m2–m6 各 StepRun 的首个 artifact 为 stage_gate_report」：(1) `stage_gate_report` 是 N-4 被否决的 B 案类型名，与裁决 35（复用 `validation_report`）冲突；(2) 该证据修订由 act/04 put+seal 后不进入 result_json 任何列表，而公开读方法闭集（LedgerReadMixin :111–164）无「按 step_run_id 枚举修订」能力（正是 D-6 三缺口之一），验收又不得出现 .store/.objects（TDD.md:64 与 act/08 orchestrator 扫描双杀）→ 该子判据按声明读取面不可实现，执行者只能停手或违规绕过｜G7-RULINGS §9.3 第 35 条、§9.1 第 25/36 条；put_artifact 不落 StepRun 事件（service.py:442–527）；finish_step_run 允许 validation_report_ids 收 sealed 且属本 StepRun 的修订（service.py:1155–1162）｜act/04 增一句：Gate 证据写入并 seal 后把该修订号并入最终 StepResult 的 `validation_report_ids` 首位（Ledger 校验可通过：sealed 且 step_run_id 归属成立）；act/07 与 BDD 5.1 改为「result_json.validation_report_ids 首位的修订经 read_object 内容 `kind=="stage_gate"`、`gate=="passed"`、`stage==上游`」。备选：授权验收用只读 sqlite 连接枚举修订（§9 第 13 条先例），但须同步修订 TDD.md:64 与 act/08 扫描豁免，不推荐。
- F3｜重要｜BDD.md:8（对照 act/00.yaml:73-89）｜BDD 1.2 列举的 12 种篡改中「stage 超出 m1–m8」无任何具名 tests 用例（15 例中无对应；`stage_invalid` 规则只在 contract act/00:60 出现）｜覆盖性规则「每场景 ≥1 具名用例」；check_registry R3 `stage_invalid`（act/00.yaml:60）、pipeline.ledger.ids.STAGES（ids.py:36）｜test_catalog.py 增一例（如 test_module_stage_out_of_closed_set_detected），TDD §1 阈值相应上调。
- F4｜重要｜TDD.md:26-30,83-89 与各 act verify 行（如 act/00.yaml:91）｜unittest 回归取行用 `2>&1 | tail -1` / `tail -3`，未按 G7-RULINGS §9.2 第 27 条统一为 `2>&1 | grep -E "^(Ran|OK|FAILED)"`（impl-03 TDD.md:67–69 已按此惯例），而 README §2:54 自引第 27 条为依据｜G7-RULINGS §9.2 第 27 条｜TDD §0/§3 与各 ACT verify 的 unittest 命令统一改为 grep 取行（verify-T.sh/mutations.sh/run_all.sh 的 tail -1 取 SUMMARY 属另一语境，可保留）。
- F5｜重要｜act/08.yaml:40（对照 README.md:143 D-9、act/08.yaml:36-38）｜「实测命中」清单少计 3 处：validation/inputs.py:6、validation/context.py:4、dataset_compiler/inputs.py:6 的 docstring 行含 `reader.store.conn`/`reader.objects.get`，同口径 `grep -nE '\.store\b|\.objects\b'`（排除 tests/）实测 m5 共 10 处、m8 共 11 处；BLOCKED 行「最多列 5 处，超出写等共 <n> 处」的实际文本将与此清单不符（m3 亦由 6 处触发截断）｜scan_ledger_internals 定义（act/08.yaml:26）不排除注释行；实测 grep 复测｜更新 act/08:40 实测清单（或在 scan 契约中显式声明排除纯注释/docstring 行并说明实现方式），使 BLOCKED 期望文本可预算。
- F6｜建议｜act/01.yaml:66 对照 TDD.md:45｜ACT 01 verify 写「用例数 ≥ 24」，TDD §1 写「≥ 25」，两处阈值口径不一（具名累计 29，均可达，不影响执行）｜同一 ACT 的两处阈值应一致，建议统一为 25。
- F7｜建议｜act/02.yaml:51-58 对照 P2、INTERFACES.md §4｜桩专用 artifact_type（`stub_output`、`review_queue_item`）由生产文件 stubs.py 写入而未入 INTERFACES §4 闭集；P2 字面「实现不得使用」存在被误读为阻断的风险（put_artifact 仅校验命名正则 service.py:455，可写）｜P2 闭集意图约束生产数据模型；建议在 README §5.8 或 act/02 契约注明「桩产物类型仅测试与验收场景使用，不入闭集、不得出现在生产登记表产物中」。
- F8｜建议｜act/07.yaml:36-39 对照裁决 37｜registered_modules_m1_m6 未来转 PASS 时「PASS 行逐项披露 imported/legacy 绑定来源」（第 37 条）未给文本模板；当前 BLOCKED 行仅披露串联范围｜G7-RULINGS §9.3 第 37 条；README.md:135 D-7 A｜补 PASS 行格式（如按 stage 列 `m1:imported、m3:legacy_self_driving…`），避免届时现场发明措辞。
- F9｜建议｜act/05.yaml:17-19,30｜契约用属性式伪码（`latest.content`、`latest.step_run_id`、`t.task_id`），而 latest_checkpoint 实际返回 dict（service.py:137–149），与 act/03/act/06 的键式记法混用｜服务返回 dict（`_checkpoint_with_content`）｜统一为键访问记法（`latest["content"]`），纯文档一致性。

## 六、判定

**REWORK**（阻断 2 项：F1、F2；重要 3 项：F3、F4、F5；建议 4 项：F6–F9）。

F1 使 act/07 的 5 项 PASS 期望（real_chain m1 Gate）按字面不可达；F2 使 gate_chain_stub_m1_m6 的证据子判据不可实现且与裁决 35 冲突。两项均在 ACT 07/03 契约文本层面，修订后应复审（R2 重点：F1 语义选定后 BDD 4.2/4.4 与 act/07 负例矩阵的一致性；F2 修订后 TDD §2 的 grep 豁免面）。

（本审查未修改被审工作包与任何代码/规格/Schema/fixture/台账；仅新增本文件。）
