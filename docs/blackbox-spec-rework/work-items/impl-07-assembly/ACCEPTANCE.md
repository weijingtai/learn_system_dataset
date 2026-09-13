# ACCEPTANCE：impl-07 M7 创世汇编薄切片（空基底 + 单个 ReviewedEditionPackage → CanonicalKnowledgeSnapshot 修订）

本文件只写**审查要点与判据**，不写任何验收结论；结论与验收记录由主 Agent 填写（§5）。

## 0. 转译审查要点（主 Agent 四查）

- **忠实性**：`README.md` §0、`BDD.md` §G0、各 `act/g0-*.yaml` 的 contract 与 `G7-RULINGS.md` §1 P1–P9、§5 impl-07、§9.11 第 58 条、§9.12 第 61 条、§9.13 第 63–66 条逐条对应。
  - 第 61 条：Snapshot 归 M7，创世薄切片先行；M6/M8 不承担 M7 职责；只做「空基底 + 单个 ReviewedEditionPackage → Snapshot 修订」，多 Edition 增量/合并提案/跨 Release 保号/§20.5 保持 `DEFERRED`。
  - 第 63–66 条（R1–R4 裁定）：每个 technique 一个 Snapshot Artifact（63）；pattern 补发只从配置修订登记的 `id_range` 确定性取号、号段与补发清单写入 Snapshot（64）；缺口登记为对 M4/M6 的接口需求（65，README §0.7）；包内合成宿主 + 合成决定含 `synthetic_fixture: true` 且不计 `expert_verified` + 「消费真实 M6 产出」项在 impl-06 验收前 BLOCKED（66）。
  - P2/D-0-3：只用已登记名 `canonical_snapshot`、`assembly_package`，不新增 artifact_type；`check_interfaces.py` 末行 `fail=0` 且 exit 0（第 54 条，不写死 pass 总数）。
  - P3：内容结构为代码草案 `schema_version: "0.1.0-draft"`；不新增 `openspec/schemas/` 文件。
  - P5：上游 m6 StagePackage 及其血缘 candidate_package 只认所属 StepRun `succeeded`。
  - P6：零模型调用；无 `requests`/`openai`/`anthropic`/`httpx` import。
  - P7：无人工回路、无 `human_event`；合成输入标 `synthetic: true`，不计为真实 `expert_verified`。
  - 第 58 条：同阶段后续运行经 `supersede_step_run`（`begin_or_supersede` helper + 具名用例）。
  - §6.2:175：不改任何已封存 m6 StagePackage / `reviewed_edition` 修订状态。
- **覆盖性**：`BDD.md` §G0.1–G0.14 各条都能在某个 `act/g0-*.yaml` 的 `tests` 用例名或 `verify` 命令上找到落点；G0-01→G0-05 的串行前置与 `depends_on` 一致；`README.md` §0.2 完成判据覆盖单测、`m7-assembler.sh`、`run_all.sh` 基线、`m3-coverage.sh` 基线、`git diff --check`。
- **可执行性**：每个 ACT 有 `scope.write`、先红后绿的具名用例名、contract（函数签名/规则/检查名/退出码）、精确 `verify`、`commit.add`/`message`；用例数阈值等于具名用例累计（30/51/64/77/87）；ACT 时长 ≤ 110 分钟；回归取行用 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。
- **F1/S1/S2（四查 R1 返工项）**：F1——`validate_candidate_set` 按 impl-05 已验收 `candidate_set` 真实键（`assemble.py:637-651`）重写：assertion 无 `subject`/`school_view_ids`、用 `school_ids`；pattern 恒有 `pat_`、无 `candidate_key`；断言↔Pattern 关联经 `patterns[].assertion_ids`；合成宿主同形；`candidate_key`/`pattern_id: null` 移入 §0.7 接口需求 5，R03e 为防御分支。S1——G0 canonical 字节带尾部换行，写明不与 M4 字节互比。S2——`ACT.yaml` gates 补 `m3-coverage.sh` 基线。
- **独立性**：`genesis.py`/`gate.py`/`acceptance.py` 不读文件、不访问 Ledger（`gate.py` 与 `acceptance.py` 不 import `genesis`）；`inputs.py` 只读 Ledger；`step.py` 是唯一写 Ledger 的模块。
- **写范围**：仅 `pipeline/assembly/**` 与 `openspec/acceptance/m7-assembler.sh`；与 `pipeline/review/`、`pipeline/dataset_compiler/`、`pipeline/orchestrator/`、`pipeline/ledger/`、`pipeline/knowledge_extraction/`、`pipeline/validation/` 零交集；不写 `run_all.sh`、fixture、Schema。

## 1. 范围核对

每个提交只含该 ACT `commit.add` 路径；`pipeline/assembly/` 之外仅 `openspec/acceptance/m7-assembler.sh`（G0-05）；`run_all.sh`、`m3-coverage.sh`、规格、Schema、fixture、`pipeline/ledger`、`pipeline/review`、`pipeline/dataset_compiler`、`pipeline/orchestrator`、台账文件未动；无 `var/`、`__pycache__`；`git diff --check` 通过。

## 2. 门禁与判据（`git archive` 干净树）

- `ACT.yaml` 全部 `gates` 绿；三套 `unittest`（ledger、assembly）全过且用例数达 `TDD.md` §G0.1 阈值；`m7-assembler.sh` → `SUMMARY pass=10 fail=0 blocked=6`、exit 2；`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`（与基线逐字相同）。
- `TDD.md` §G0.2 附加判据逐条实跑；`README.md` §0.2 完成判据逐条复现。
- 6 项 BLOCKED（`incremental_multi_edition`/`edition_collation`/`identity_delta`/`rework_replacement`/`upstream_m6_real`/`run_all_20_5`）确属未实现的 `DEFERRED` 项，逐字属 §19:911 差距与 §15:655/§16:732 范围，未被写成 PASS；其中「消费真实 M6 产出」（`upstream_m6_real`）在 impl-06 实现并验收前判 BLOCKED（第 66 条）。

## 3. 语义与质量审查清单

- 纯函数性：`genesis.py`/`gate.py` 不读文件、不访问 Ledger、不取时间、不用随机数（发号只经注入的 `id_factory`）。
- 上游契约：`inputs.py` 只认 `succeeded`；m6 包 `manifest.output_artifacts` 恰 1 个 `reviewed_edition_package`；candidate_package 在 m6 包 `lineage.upstream_artifacts` 内；`reviewed_edition`/`reviewed_edition_package` 的 `unresolved_count == 0`。
- 事务序列与 §17:836 一致；begin 之前的拒绝无写入；begin 之后的失败封存完整（检查名 ∈ {`input_contract`,`genesis_gate`,`internal`}）。
- 内容成熟度：`knowledge` 的 `content_status` 等于 `reviewed_edition.approved` 原值，无合成；Pattern/Concept 顶层无 `content_status`（§8.2:440）。
- 下游契约：Snapshot `assertions[].proposition` 与 `evidence[]`（`start_offset/end_offset/quote_sha256`）足以供给 M8 的 KnowledgeEntry/Assertion/EvidenceLink 与 GraphProjectionPack（§16:661-662、§16:705-713、§16:725）。
- 独立重算：Gate 与验收判定均不依赖被验实现自身产出的 report；`acceptance.py` 永远调用仓库内规范 `mini_ed01/verify.sh`，不接受被验目录自带脚本。
- 待裁决 R1–R4（`README.md` §0.6）未被实现方自行取舍；若实现中触及其中任一条，停手上报。
- 中文注释；无 `except: pass`；不新增依赖、ID 前缀、模型调用。

## 4. 结论规则

- G0-01、G0-02、G0-03、G0-04、G0-05 各自通过后，由主 Agent 在 §5 记名并写 `ACCEPTED`；执行者不得自记。
- 任一 FAIL 视为未通过，返工另立 ACT；6 项 BLOCKED 不视为失败，但必须确属 §19:911 差距与 `DEFERRED` 范围。
- 全部通过后，由主 Agent 同步 `SUBAGENT_TODO.md`、`HANDOFF.md` 并据此勾选 `PLAN`/`G7-PLAN` 相应项。

## 5. 验收记录

§5 验收记录由主 Agent 填写。

### 5.1 G0-01（2026-09-13，主 Agent 独立验收，`git archive c79b36a` 干净树）

执行者：tmux 中的 agy（Gemini 3.8 Flash High），会话 `w5g0`；工作包 R2 READY `e2c8d79`，S3 修订 `3d97bb2`。

- 范围：`c79b36a` 恰为 `pipeline/assembly/` 下 7 文件（`__init__`、`errors`、`canonical`、`model`、`tests/__init__`、`tests/test_canonical`、`tests/test_model`），无越界。
- Red（执行方原文）：两个测试模块 `ModuleNotFoundError`，`FAILED (errors=2)`。
- 复验：`pipeline/assembly/tests` `Ran 30 tests` OK（阈值 ≥ 30）；具名用例 30 个与 act/g0-01 `tests` 逐字一致；`test_model.py` 断言错误码 36 处；`pipeline/ledger/tests` 74 OK、`pipeline/knowledge_extraction/tests` 133 OK；`check_interfaces.py` `pass=29 fail=0`；`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；`run_all.sh` `pass=2 fail=1 blocked=8`。
- 静态：`canonical.py`/`model.py`/`errors.py`/`__init__.py` 副作用与网络调用 0、引用 `_fixture` 0、裸 except 0；纯函数模块不触 Ledger、不开文件。
- 矩阵外（`g0_01_e2e.py`）：`reviewed_edition` 带 impl-06 §5.3 超集键（第 69 条 carried 字段、`candidate_set_revision_id`、`validation_package_revision_id`、`approved[].decision_revision_ids` 等，取合法 ID）→ PASS；`reviewed_edition_package` 超集键 → PASS；缺 `evidence_links[].quote_sha256`、缺 `school_views[].changes_current_judgment`、缺 `candidate_package_revision_id` → 均 `SCH_001`；校验不改输入；**真实 m4 金标 `candidate_set.yaml` 校验 PASS**；`make_key` 全 kind 不命中 Ledger 前缀、确定且区分主体；`canonical_json` 键序无关、UTF-8 不转义、带尾换行；`nfc_key` 组合/分解等价。
- 发现：`empty_snapshot_knowledge(..., {"pattern": [...]})` 被 `validate_snapshot_knowledge` 拒（要求 `pat_<technique>` 键）。实现忠实于 act/g0-01:59；根因为工作包 g0-02 输入层与存储层键形未定义转换 → 第 70 条裁定（两层分立，g0-02 写回时改键），G0-01 不返工。

G0-01 `ACCEPTED`。

### 5.2 G0-01a 与 G0-02（2026-09-13，主 Agent 独立验收，`git archive 749fc04` 干净树）

执行者：agy 会话 `w5g0`（G0-02 中途按用户要求由 Gemini 3.8 Flash High 切换为 Medium，续接原对话）。G0-02 执行中停手上报 `allocated` 与活对象重叠检查阻断 → 裁定 71（`9979657`）。

- G0-01a `8f9917f`：范围恰为 `model.py`、`tests/test_model.py`；改动只删「allocated 与活对象号重叠」拒绝、改为只与 retired 比，新增 `patterns[].pattern_id` 互异（ID_002）；未删既有断言，新增具名用例 `test_snapshot_allocated_id_alive_pattern_allowed`、`test_snapshot_duplicate_alive_pattern_id_ID_002`。Red（执行方原文）`FAILED (failures=1, errors=1)`，Green `Ran 32` OK。
- G0-02 `749fc04`：范围恰为 `genesis.py`、`tests/test_genesis.py`；具名用例 21 个与 act/g0-02 逐字一致。Red（执行方原文）`Ran 21 … FAILED (errors=21)`。
- 复验：`pipeline/assembly/tests` `Ran 53` OK（阈值 ≥ 53）；ledger 74 OK、knowledge_extraction 133 OK；`genesis.py` 不开文件、不触 Ledger、无随机/时间/网络、裸 except 0；`check_interfaces` `fail=0`；`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；`run_all.sh` `pass=2 fail=1 blocked=8`。
- 矩阵外（干净树内联脚本）：同输入两次 `knowledge_bytes` 相同；输入未被修改；`knowledge.id_range` 存储键为 `{"pat_qizheng": [1, 100]}`（第 70 条改键）；输入 `id_range` 缺 `pattern`、`start > end`、负数、非列表四种均 `AssemblyRefused(SCH_002)`；Assertion `content_status` 与 `approved` 原值一致；Pattern/Concept 顶层无 `content_status`。
- 备注：Red 顺序（测试先于实现）无法由 git 独立证明（测试与实现同提交，第 56 条既有局限）；G0-02 实现在裁定 71 前已写出，裁定后仅补 G0-01a，未见事后删改断言。

G0-01a、G0-02 `ACCEPTED`。
