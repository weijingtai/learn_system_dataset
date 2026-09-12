# impl-04 四查审查 R1（独立审查者，W2-G）

- 审查对象：提交 `2e4f9a7` 的 `docs/blackbox-spec-rework/work-items/impl-04-dataset/`（全部文件；经 `git diff 2e4f9a7 HEAD --stat` 核对与工作树一致）。
- 依据：`G7-RULINGS.md` §1 P1–P9、§2 D1–D14；规格 §4/§6.2/§7/§8/§8.1/§8.2/§11.1/§13.1/§16/§17/§17.1/§18/§19/§19.0/§20/§22（grep 定位分段读取）；`id-prefix-registry.md`；`pipeline/ledger/service.py`、`store.py`、`ids.py`、`fixture_ingest.py`；`pipeline/corpus_compiler/step.py`；`openspec/acceptance/run_all.sh`、`m3-coverage.sh`；模板 `impl-02-corpus/`。
- 实测手段：fixture 数字用 `.venv/bin/python` 独立复算；`run_all.sh`、`m3-coverage.sh`、`verify-T.sh`、`check_d16.py` 实跑取输出；`m8-span-identity.sh` 实测 exit 127（尚不存在）。

## 判定：READY

无阻断发现；重要 2 条、建议 5 条（见下）。判定不替写包者修改任何文件。

## 一、忠实性 —— 通过

- P1/D1：EvidenceMapPack 只闭合尾链四段（`CHAIN_SEGMENTS` = SourceSpan→SourceAnchor→OcrPage→SourceAsset），`knowledge_chain: "not_compiled"`，前三段以 `mentions_mapping`/`knowledge_chain` BLOCKED 表达，不注入合成知识；M4/M6/M7 判 BLOCKED；D1 附带口径（临时 Ledger、INTERNAL_DEMO、验收后删除）已登记（README §4）。
- P2/D4：六个新 artifact_type 只提名，`ACT.yaml` preconditions 与 `PROMPT-F1.md` 均要求 W2-C 写入 INTERFACES §4 闭集后才可实现（探针缺陷见 R4-01）。
- P3/D5：`SUB_PACK_SCHEMA_VERSION = "0.1.0-draft"`；`PUBLIC_RELEASE` 以 `draft_schema` 拒绝（act/00 R2）；范围禁止新增 `openspec/schemas/**`。
- P4/D6：`run_all.sh` 仅 ACT 08 可写、仅 20.4/20.8 两段加一个辅助函数；两段不得出现 `pass_line`（act/08 contract 硬性 + verify 的 sed/grep 判据）；`SUMMARY pass=2 fail=1 blocked=8` 实测成立且改后不变。
- P5：resolve 与 README §6/§8.1、`ACT.yaml` preconditions 三处一致要求只接受所属 StepRun `succeeded` 的 m3 包（act/04 R2/R3）。
- P6：全包禁模型调用，act verify 有第三方依赖 grep 判据；P7：shim `human_decisions=[]`，未伪造人工决定；P8：只用已登记前缀 `rel_/pkg_/art_/rev_/prun_/srun_`（与 `ids.py` 模式逐一吻合），首切片不发 `ent_`；P9：禁改 `pipeline/ledger/**`、`corpus_compiler/**`、fixture，shim 不产生第二个 m1 包。
- D2：文件、CLI、`SHIM_TOOL` 三处显式标 `m1_shim`，README §10 登记「impl-09 M1 落地后替换」。D3：缺图 `BLOCKED_SOURCE_ASSET_MISSING` 退出 3（shell 与 CLI 两路；实测 fixture `verify.sh` 确实支持 `FIXTURE_ASSET_ROOT` 并打印该串 exit 3）。D9：`source_verified` 不算 release 级（act/00 R1 + act/02 检查 12 + 专项测试）。D10：水印文案与裁决逐字一致（act/01 `INTERNAL_DEMO_WATERMARK`）。D11：两条 mismatch span 降级 `line_bbox` 并披露。D13：R1 拒绝第二次 m8。D14：无 QueryContractPack/SearchIndexPack，deferred 清单齐备。
- 无超出裁决的新决定；README §2 引用行号抽核全部命中（§16:661-751、§17:836、§17.1:843、§19:878-890、§19.0:912、§20:940/944/945/947、§22.1:968、§22.3:991、§22.4:997-1000 等）；`build_index.py:133-138`、`legacy-storage-transition.md:27/65-67`、`DATASET_ACCEPTANCE_STANDARD.md:42/46/67/70/95-99` 均核对属实。

## 二、覆盖性 —— 通过（1 条建议）

- BDD §1–§8 每条场景均落到 act/00–07 的具名用例：如 1.4→`test_public_release_fixture_like_inputs_unmet_exact`+`test_public_release_all_expert_still_not_admitted`；2.4→`test_entries_keyed_by_full_span_id_not_seq`（39 键/4 组碰撞数字入断言）；3.2 的 24 类篡改逐一有对应 `test_gate_*`；6.1→五个结构用例+counts 断言；8.4→`test_shell_never_trusts_copy_verify`。
- §19.0 `m8-span-identity.sh` 由 ACT 07 产出：7 项判定 + `mentions_mapping` BLOCKED、exit 2，与 §19 第一列「M4 行差距未关闭」口径一致，未把 BLOCKED 写成修复（README §9 明示变 0 需 M4/D14-C/D1-B）。
- §20.4/20.8 判定由 ACT 08 产出（`m8_verdict` 三态 + 永不 PASS），20.6/20.9/20.11 保持 BLOCKED 不动，与 §9 影响分析表一致。
- 建议 R4-05：BDD 9.2（注入副本 → 20.4 FAIL）仅有 TDD Red/Green 行落点，无用例名、无 verify 命令，注入机制未写明。

## 三、可执行性 —— 通过（2 条重要、3 条建议）

- 逐 ACT 核对 `scope.write`、函数签名、检查名、退出码、verify 命令与期望值；ACT 时长 60–110 分钟，全部 ≤110。
- act/05–08 重点核对结果：
  - Ledger 方法调用全部真实存在且形参吻合：`create_processing_run("release_run", ep, technique_id)`（service.py:319-345）、`put_run_artifact(..., producer_module=, producer_version=)` 只收 configuration/technique_profile（:66,528-553）、`begin_step_run(request)`（:405，StepRequest 六键与 §7:187-193 一致）、`put_artifact(step, type, data, producer_module=, producer_version=, rights_scope=)`（:442-457）、`write_checkpoint(step, *, edition_part_id, stage, completed_tasks, human_decisions, pending_queue, next_pointer)`（:1364）、`record_transformation(step, *, operation, tool, tool_version, configuration_revision_id, input_revision_ids, output_revision_ids, validation_report_revision_id, human_event_revision_ids)`（:777）、`register_stage_package`（:718，登记 artifact_type `stage_package`）、`finish_step_run`（:1132）、`fail_step_run`（:1187）、`list_checkpoints(ep, stage)`（:150）、`service.store.conn`（store.py:220-228）、`service.objects.get`（service.py:140 先例）。
  - `ids.validate/new_id` 支持 `release_id/step_run_id/stage_package_id(stage="m8")/artifact_revision_id/source_span_id`（ids.py:17-26,90-121）；act/04 R3 的 SQL 所用 `artifact_revisions.step_run_id` 列存在（store.py:47）。
  - M3 产物对账：`stage_package` payload 逐键（`spans_revision_id/coverage/excluded_pages/gate_profile`）、`validation.passed`、`manifest.content_sha256`、`manifest.input_artifacts` 组成与 `corpus_compiler/step.py:303-352` 实际写入一致；`corpus_spans` 顶层键与 `source_anchor{page,image_sha256,line_id,bbox,chars}` 与 compiler.py:178-210 一致；fixture_ingest 灌入的 m3 包（`expected/m3.stage_package.yaml`）payload 确无 `spans_revision_id`，act/04 拒绝用例可成立；m1 Checkpoint `task_id "ingest_source"` 与 `fixture_ingest.py:54` 一致。
  - verify 命令可在仓库执行：门禁脚本全部存在且实测（`verify-T.sh` → `FAIL 合计: 0`；`check_d16.py` → `D16 OK`；`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`；`m3-coverage.sh` → exit 2；`m8-span-identity.sh` → exit 127）；act/08 的 `sed -n '/^    20\.4)/,/^    20\.5)/p'` 与 run_all.sh 实际缩进吻合；TDD §0 的目录计数（K2=7、K3=11）与目录规划一致；SUBAGENT_TODO.md:581 impl-02 状态 `ACCEPTED` 属实。
  - fixture 数字全部独立复算成立：43 spans（page_001=4、page_003=39）、glyph 41/line_bbox 2、字框 230、legacy 39 键 4 组碰撞、越界 0、`spans.yaml` sha256 = `ec6d77b9…44ef`；manifest 第 5-6 行 `rights_status/release_policy` 与引用一致。
- 重要 R4-01、R4-02 与建议 R4-03/04/05 见下节。

## 四、独立性 —— 通过

- 依赖无环：00→01→02；03→04→05→06（05 另依赖 02，跨组前置成立）；07←06；08←07。K1/K2/K3 分组与 `depends_on` 一致。
- 包内写集重叠仅出现在依赖边上且已注明约束：act/03 与 act/04 共写 `tests/_ledger_helpers.py`（act/04 限「只允许追加函数」）；act/05 与 act/06 共写 `step.py`（act/06 为「补」失败路径）。串行派发下无并行写冲突。
- 与同波并行包无冲突：G7-PLAN W3 行明确 `pipeline/validation/`（impl-03）、`pipeline/dataset_compiler/`（impl-04）、`pipeline/knowledge_extraction/`（impl-05）各自独占；`m8-span-identity.sh` 与 impl-03 的 `m5-evidence-gate.sh` 互不相交；`run_all.sh` W3 内唯一写入者为本包 ACT 08（P4），且 `ACT.yaml` preconditions 要求派发 ACT 08 前确认无并发改动。
- 防同错同过成立：gate.py 禁 import `packs/canonical/levels/step`（contract + verify grep + 专项测试三重约束）；acceptance.py 禁 import `packs/gate` 且不读 `run_m8` 返回 gate——run_m8 的 summary 键本就不含 gate（与 run_m3 不同），约束自洽可执行；acceptance 只信 fixture 金标与 Ledger 字节重算，永调仓库内规范 `verify.sh`。

## 发现清单

| 编号 | 严重度 | 位置 | 问题 | 依据 | 修改建议 |
|---|---|---|---|---|---|
| R4-01 | 重要 | PROMPT-F1.md:45 | 新类型入闭集探针失效：`grep -n 'source_asset_pack' INTERFACES.md` 在当前 HEAD 已有输出（§3.11 标题、§4:333 草案行），无论 W2-C 是否登记都通过，无法执行「未入闭集 → 停手」前置；且 §4 现行 M8 行仍是草案类型集（`release_validation_report`、`knowledge_data_pack` 等，无 `source_asset_page/source_asset_register`），与 D4 提名存在待对账差异 | G7-RULINGS.md:10（P2）、:26（D4）；INTERFACES.md:318-335 | 探针改为匹配 D4 独有新名（如 `grep -n 'source_asset_page' …/INTERFACES.md`，当前必无输出）；在 README §7 注明 §4 草案行与 D4 提名的差异（`release_validation_report` → 复用 `validation_report`），供 W2-C 登记 ACT 一次性对账 |
| R4-02 | 重要 | TDD.md:38-39；README.md:22；ACCEPTANCE.md:29 | 用例数阈值与 ACT tests 枚举算术不符：逐 act 累计 18+27+28+11+6+12=102（act/05 阈值 102 吻合），act/06 枚举 10 例→累计 112<阈值 115；act/07 再 12 例→累计 124<阈值 126。README §1 完成判据「用例 ≥ 126」与 ACCEPTANCE §2「用例数达 TDD §1 阈值」同样不可达；除非执行者自加未列名用例，否则与「用例名与 ACT tests 逐字」纪律冲突并触发停手 | act/06.yaml:25-35（10 例）；act/07.yaml:54-65（12 例）；act/00–05 各 tests 清点 | 将 act/06 Green 阈值改 ≥112、act/07 改 ≥124（README/ACCEPTANCE 同步为 124），或在 act/06/07 补列具名用例补足差额 |
| R4-03 | 建议 | act/05.yaml:61-65 | m8 StagePackage 契约只列 payload/manifest/lineage，未列 `stage_package.schema.json` 必填键 `validation/logs/failures`（另 `stage/status/schema_version` 未显式写出）；执行者须自行比照模板补齐，属隐含决定 | openspec/schemas/stage_package.schema.json:161-173（required）；impl-02 act/03.yaml:49-58 | contract 补一句：信封其余键（validation/logs/failures 等）比照 impl-02 act/03 模板，`validation.report_artifacts` 指向本包 validation_report |
| R4-04 | 建议 | act/03.yaml:29 | `rev = put_artifact(...)` 与真实返回不符：`put_artifact` 返回二元组 `(artifact_id, revision_id)`，直接赋值会使 rev 为元组 | service.py:442-458（docstring「返回 (artifact_id, revision_id)」）；corpus_compiler/step.py:195/218 均解包 | 伪代码改为 `_, rev = put_artifact(...)` |
| R4-05 | 建议 | act/07.yaml:18-21,59；act/08.yaml:24 | `test_tampered_span_golden_fails` 与 BDD 9.2「副本树注入→20.4 FAIL」的判定落点未写明：span_identity 7 项检查均以 Ledger 内 spans_doc 为基准，对 fixture `spans.yaml` 金标的比对未列为检查项或说明注入方式（篡改金标是副本树场景下唯一稳定的 FAIL 途径） | act/07 contract 检查清单；BDD.md:70-72 | 在 `span_key_unique` 补「且 == fixture spans.yaml 金标 span_id 集合」，或在 act/08 写明注入方式为「fixture 副本 spans.yaml 删一条 span」并为其补一条 verify 命令 |
| R4-06 | 建议 | README.md:73-75 | 「文本比字框多 1 字：6 字/5 框、17 字/16 框」的「框」口径未注明：实测两 span 字框数为 8、18（其中空字符框 3、2 个），5/16 是拼接后非空字符数；D11 判定用 join 语义不受影响，但「框」字易被误读为 `len(chars)` 断言 | 实测（s03 text 6/框 8/空 3；s04 text 17/框 18/空 2） | 注明「按拼接后非空字符计；实际字框数 8、18，其中空字符框 3、2 个」 |
| R4-07 | 建议 | ACCEPTANCE.md:29 | 「两套 `unittest` 全过」与实际三套不符（ledger、corpus_compiler、dataset_compiler） | ACT.yaml:60-62；TDD.md:4-6 | 改为「三套」 |

## 自检与提交

- 本文件只新增 `docs/blackbox-spec-rework/reviews/IMPL-04-REVIEW-R1.md`，未触碰被审工作包、规格、Schema、fixture、台账及并行线文件；`git diff --check` 无输出。
