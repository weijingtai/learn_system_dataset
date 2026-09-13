# IMPL-07 G0（创世薄切片）四查审查 R1（独立审查者 W4-R5）

- 审查对象：`work-items/impl-07-assembly/` 执行组 G0（act/g0-01～g0-05 及 ACT.yaml/TDD/BDD/ACCEPTANCE/PROMPT-L0 的 G0 部分），定稿 `91e5348` + 第 63–66 条落实 `78e21cc`，以 HEAD（`a56ff34`）文本为准；只审 G0，DEFERRED 组（F/J1–J4，act/00–10）不在本次范围。
- 依据：G7-RULINGS §1 P1–P9、§5 impl-07、§9.11 第 58 条、§9.12 第 61 条、§9.13 第 63–66 条、第 54 条；impl-06 定稿 README §5.3（上游契约）；已验收代码 `pipeline/knowledge_extraction/`（candidate_set 实际字段）；`INTERFACES.md` §4 M7 行；`pipeline/ledger/`。

## 一、忠实性

- 第 63 条：每 technique 一个 Snapshot Artifact，`base_snapshot_revision_id` 非 None 即拒（「纵切后」），同 technique 重复创世拒（「已汇编」）——g0-04 步骤 begin 前拒绝 + 用例覆盖。
- 第 64 条：保留 M4 已发 `pat_`（R02），`pattern_id: null` 才补发（R03e）；补发只从**配置修订登记的 `id_range`** 确定性取号、跳过已占用值、区间不足拒「号段不足」；号段与补发清单写入 Snapshot 修订（`knowledge.id_range`/`allocated_pattern_ids`）——g0-02 contract、g0-04 配置与步骤、BDD G0.2、6 个具名用例（`test_genesis_allocates_from_config_id_range`/`skips_ids_already_used_by_m4`/`preserves_m4_id_outside_range`/`id_range_exhausted_refused`/`id_allocation_monotonic`/`knowledge_carries_id_range_and_allocation_list`）逐项落实；不新增前缀（P8）。
- 第 65 条：创世缩水（patterns `concept_id` 恒 null、`rules=[]`、`recognition_rule_status="not_captured"`、无号 new_concept_candidates 进 `excluded_unbound` 不入 Snapshot）；缺口以接口需求登记于 README §0.7（实测在），不在 M7 补造内容。
- 第 66 条：合成宿主 `pipeline/assembly/tests/data/`，不改共享 fixture（写范围证实）；合成决定标 `synthetic_fixture: true`（BDD G0.12、g0-04/g0-05 具名用例）；`upstream_m6_real` 恒 BLOCKED 且说明逐字含「impl-06 实现并验收前」（BDD G0.13 + `test_upstream_m6_real_blocked_until_impl06_accepted`）。
- 第 58 条：`begin_or_supersede(service, edition_part_id, stage, configuration_revision_id)` 具名 helper + `test_begin_or_supersede_uses_existing_succeeded_run`（经读接口查最近 succeeded，不写死号）。
- 第 54 条：前提与门禁均为「`check_interfaces.py` 末行 `fail=0` 且 exit 0」，无写死 pass 数（实测当前 pass=24 fail=0）。
- P2：只用 §4 M7 行已登记类型 `canonical_snapshot`/`assembly_package`（`INTERFACES.md:349` 实测在册；状态列「纵切后」的更新为不阻塞建议）；operation `assemble_knowledge` 与 INTERFACES §2.7 卡片一致（:186）。
- P7：本切片无人工回路、无 `human_event` 产出（TDD §G0.2 判据）；Snapshot 不计 `expert_verified`。
- 忠实性发现：F1（candidate_set 字段引用与已验收代码不一致，见下）。

## 二、覆盖性

- BDD §G0.1–G0.13 每条均有具名用例或 verify 落点（1–7→g0-01/02/03，8–10→g0-04，11→g0-05 脚本，12–13→g0-04/05 合成与 BLOCKED 判据）；ACCEPTANCE 引用「§G0.1–G0.13」属实。
- 用例阈值与具名用例累计**完全一致**（awk 实测）：G0-01=28（8+20）、G0-02=18、G0-03=13（2+11 篡改矩阵）、G0-04=12、G0-05=10；累计 28/46/59/71/81 == TDD §G0.1 阈值 == README §0.2「阈值等于具名用例累计」。
- m7-assembler.sh：10 项 PASS（genesis_snapshot/configuration_and_scope/package_lineage/identity_and_allocation/provenance_and_fidelity/no_silent_fold_and_display/upstream_immutable/checkpoints/closed_set_types/no_model_calls）+ 6 项 BLOCKED（incremental_multi_edition/edition_collation/identity_delta/rework_replacement/upstream_m6_real/run_all_20_5）= 16 项，`SUMMARY pass=10 fail=0 blocked=6`、exit 2 可达（.venv 在、宿主 mini_ed01 verify 实测可过）；ACT.yaml 门禁、TDD §G0.1、g0-05 verify、BDD G0.11 四处口径一致。
- 依赖串行 G0-01→05 无环；时长 75/90/75/110/110 全部 ≤110（两个 110 贴上限，合规）。

## 三、可执行性

- 上游契约逐字核对：g0-01 `validate_reviewed_package` 必填 9 键与 `validate_reviewed_edition` 必填 13 键 = impl-06 README §5.3 的 `reviewed_edition_package`/`reviewed_edition` 键集逐字一致（含 `unresolved_count`、`correction_request_revision_ids`、`rework_impact_report_revision_id`）；approved/rejected 元素五键一致。
- g0-04 `resolve_m7_inputs` 的解析链字段全部存在：`reviewed_edition_package.reviewed_edition_revision_id`、`reviewed_edition.candidate_package_revision_id`、`candidate_package.candidate_set_revision_id`（`knowledge_extraction/step.py:265-285` 实测 13 键）；m6 包 `manifest.output_artifacts` 恰 1 个 `reviewed_edition_package`、`lineage.upstream_artifacts` 含 candidate_package（impl-06 act/06 步骤 6/7 契约）；P5 succeeded 校验与 m4 StepRun 校验成立。
- Ledger 事务与已验收方法吻合：`put_run_artifact`（配置含 `id_range`，第 64 条）、`begin_step_run`/`supersede_step_run`（第 58 条）、`register_stage_package(stage="m7")`、`record_transformation(operation="assemble_knowledge")`、`write_checkpoint`（链 `propose_r1 → seal_snapshot`）、`finish_step_run`（输出 [stage_package, canonical_snapshot, assembly_package]）；`stage_package.schema.json` 可校验（payload 自由键先例 m4/m6 同）。
- 基线实测：`bash openspec/acceptance/run_all.sh | tail -1` == `SUMMARY pass=2 fail=0→blocked=8`（实测 `pass=2 fail=1 blocked=8`，与 ACT.yaml:51、TDD §G0.0、g0-05 verify 三处声明逐字一致）；本切片不改 run_all.sh。
- 独立重算：`gate.py` 只 import canonical/model/ids/states、禁 genesis（grep + AST 用例）；`acceptance.py` 判定允许 canonical/model/gate、禁 genesis、不以 run_m7 返回报告为据（AST 用例）；`test_no_upstream_mutation`/`upstream_immutable` 防改上游。
- 可执行性发现：F1（阻断）。

## 四、独立性

- 写范围仅 `pipeline/assembly/**` + `openspec/acceptance/m7-assembler.sh`；与 pipeline/review、knowledge_extraction、dataset_compiler、orchestrator、ledger、fixture、run_all.sh 零写交集；DEFERRED 组（含写 run_all.sh 的 act/10、写 m7-assembler.sh 的 act/09）本波不派发，无共享面冲突。
- `fixture_seed.py` 与 `acceptance.py` 为仅有的两个可读 tests/data 的非测试模块且只经参数（verify grep 判据）；生产代码不出现 `_fixture`。
- 合成宿主独立于共享 fixture（P4/第 66 条）；Gate/acceptance 双重不信任 assembler。

## 发现（编号｜严重度｜文件:行号｜问题｜依据 文件:行号｜修改建议）

- F1｜阻断｜act/g0-01.yaml:42-43（validate_candidate_set）｜对 `candidate_set` 的校验引用了 impl-05 **已验收代码中不存在**的字段：`assertions[].subject`（「subject 必须等于本视图内某 pattern_id、candidate_key 或 concept_id」）、`assertions[].school_view_ids`、`patterns[].candidate_key`（「pattern_id 为 null 时必须有 candidate_key」「同一 candidate_key 重复 → ID_002」）。已验收 `pipeline/knowledge_extraction/assemble.py` 实测：assertion 键为 `assertion_id/proposition_id/proposition/relation/evidence/conditions/exceptions/concept_refs/school_ids(:438)/layer/content_status/origin`，**无 subject、无 school_view_ids**；pattern 恒发 `pat_` 号（`:484`）**无 candidate_key**。后果：真实 M4 candidate_set 在该校验下行为两种理解（缺字段视为空转通过、或 REF_001/SCH_002 失败），合成 `genesis_package.json` 被迫携带偏离 impl-05 形状的字段，与「消费 impl-05 candidate_set」的上游声明冲突；执行者按 on_fail「contract 两种理解→停手上报」｜assemble.py:427-445（assertion 键）、:484-500（pattern 键与 `assertion_ids`）；对照 act/g0-02.yaml:37-39（`assertion_ids`/`school_view_ids` 的知识侧落点未给真实数据的推导来源）｜按已验收键重写该校验：断言↔Pattern 关联以 `patterns[].assertion_ids` 为唯一来源（g0-02 的 `subject_entity_id` 解析、knowledge assertion 的 `school_view_ids` 由 `school_views[].subject_entity_id`/`claim_refs` 反解，需在 contract 写明）；`candidate_key`/`pattern_id: null` 分支移入 README §0.7 接口需求（第 65 条）或显式标注「仅合成扩展」，并同步 BDD G0.2 与相关用例名。
- S1｜建议｜act/g0-01.yaml:16｜G0 的 `canonical_json` 带尾部 `\n`，与 impl-05/impl-00 act/05 的无换行口径不同；包内自洽（knowledge 字节、canonical_hash 均同一函数），但跨包复用哈希时易误用｜对照 impl-05 act/00.yaml:33｜在 contract 注明「本包规范字节含尾部换行，不与 M4 candidate_set 字节互比」。
- S2｜建议｜README.md §0.2｜完成判据含 `m3-coverage.sh` 基线，但 `ACT.yaml` `gates` 未列该命令（其余判据均在门禁）｜ACT.yaml:43-52｜ACT.yaml gates 补 `bash openspec/acceptance/m3-coverage.sh | tail -1  # == 基线`。

## 判定

**REWORK**（阻断 1：F1；建议 2：S1、S2。F1 为 G0-01 校验契约与已验收 M4 数据形状的对齐问题，属文本级重写；阈值、m7-assembler 期望、第 63–66 条落位、独立性均达标，修复后可达 READY。）

（审查者：W4-R5；以 HEAD `a56ff34` 只读核查；`git diff --check` 无输出。）
