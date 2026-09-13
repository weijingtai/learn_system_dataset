# ACCEPTANCE：impl-05 M4 Knowledge Extraction 最薄接入（无模型候选提交与类别裁决）

本文件只写**审查要点与判据**，不写任何验收结论；结论与验收记录由主 Agent 填写（§5）。

## 0. 转译审查要点（主 Agent 四查）

- **忠实性**：`README.md` §1 目标、`BDD.md` 1–9、各 `act/*.yaml` 的 contract 与 `G7-RULINGS.md` §1 P1–P9、§3 impl-05、§9 第 2/10/13/17/21 条、§9.2 第 27 条、§9.3 第 43 条逐条对应。
  - P1/§9.3 第 43 条：M4 首纵切外、最薄接入；`cross_model_extraction` / `semantic_span_input` / `term_layering_scan` 恒 BLOCKED，不伪造 PASS。
  - P2/D-10：新 artifact_type **只提名**（`candidate_submission`、`candidate_lane_set`、`dispute_queue`、`candidate_set`、`candidate_package`），登记由该波独占 ACT 写 `INTERFACES.md` §4；实现前以 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 核对（末行 `fail=0` 且 exit 0，且上述 M4 五类型各自的 PASS 行存在；第 54 条，不写死 pass 总数）。旧命名（`candidate_batch`/`model_run`/`candidate_diff_report`）未清理属 README §10 N1。
  - P3/D-10：内容结构为代码草案 `schema_version: "0.1.0-draft"`；不新增 `openspec/schemas/` 文件。
  - P4/D-02：fixture `m4/` 金标与 `verify.sh` V5/V6 扩展是与实现分离的独占 ACT（主 Agent）；K4 以之为强制前置。
  - P5/D-15：上游只认所属 StepRun `succeeded` 且 `Transformation operation == compile_corpus` 的 m3 包；输出经 `result_json["output_artifact_ids"]` + `artifacts.artifact_type` 定位（不依赖 `list_transformations` 返回输出）。
  - P6/D-01：零模型调用；渠道只收 `fixture_gold` / `task_pipeline_manual`。
  - P7/D-07/D-08：`expert_verified` 不得伪造；签发归属 M6；依赖真实签发的判定 BLOCKED。
  - D-13：被拒候选不阻断 Gate、只计数、进 `rejected`。
  - D-06：只校验不扫描；`term_layering` 恒 BLOCKED。
- **覆盖性**：BDD 各条都能在某个 `act/*.yaml` 的 `tests` 用例名或 `verify` 命令上找到落点；K1–K5 的串行前置与 `depends_on` 一致；`README.md` §1 完成判据覆盖单测（≥131）、`m4-stage-gate.sh`、`run_all.sh` 基线、`m3-coverage.sh` 基线、`import_legacy_candidates.py` 不存在五项。
- **可执行性**：每个 ACT 有 `scope.write`、先红后绿的具名用例名、contract（函数签名/规则/检查名/退出码）、精确 `verify`、`commit.add`/`message`；用例数阈值等于具名用例累计（16/41/65/81/95/108/120/131/136）；ACT 时长 ≤ 110 分钟；回归取行用 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。
- **独立性**：`gate.py` 不 import `assemble`/`submission`；`acceptance.py` 不 import `assemble`/`gate`/`submission`，不读 `run_m4` 返回的 gate；`assemble.py`/`review_events.py` 不读文件、不访问 Ledger。
- **写范围**：仅 `pipeline/knowledge_extraction/**` 与 `openspec/acceptance/m4-stage-gate.sh`；与 impl-08（`pipeline/orchestrator/`、`pipeline/contract_registry/`）零交集；不写 `run_all.sh`、fixture、`pipeline/ledger`、`pipeline/corpus_compiler`、`pipeline/validation`、`pipeline/dataset_compiler`。

派发前核对（主 Agent 脚本，定稿时执行）：9 份 ACT YAML 可解析；`ACT.yaml` 的 `acts` 与 `act/*.yaml` 一一对应；`impl-02` 状态 `ACCEPTED`；`python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 末行 `fail=0` 且 exit 0 且 §4 已含本包 M4 五类型（各自 PASS 行存在，第 54 条）；`m4-stage-gate.sh` 尚不存在（exit 127）；fixture `spans.yaml` sha256 = `ec6d77b9…44ef`；`pipeline/tools/import_legacy_candidates.py` 不存在。

## 1. 范围核对

每个提交只含该 ACT `commit.add` 路径；`pipeline/knowledge_extraction/` 之外仅 `openspec/acceptance/m4-stage-gate.sh`（ACT 07）；`run_all.sh`、`m3-coverage.sh`、规格、Schema、fixture、`pipeline/ledger`、`pipeline/corpus_compiler`、`pipeline/validation`、`pipeline/dataset_compiler`、`pipeline/orchestrator`、`pipeline/contract_registry`、台账文件未动；无 `var/`、`__pycache__`；`git diff --check` 通过。

## 2. 门禁与判据（`git archive` 干净树）

- `ACT.yaml` 全部 `gates` 绿；三套 `unittest`（ledger、corpus_compiler、knowledge_extraction）全过且用例数达 `TDD.md` §1 阈值；`m4-stage-gate.sh` → `SUMMARY pass=13 fail=0 blocked=3`、exit 2；`run_all.sh` → 与 `BASELINE_RUN_ALL` 逐字相同（20.6 BLOCKED、20.7 FAIL）；`m3-coverage.sh` → 与 `BASELINE_M3` 相同。
- `TDD.md` §2 附加判据逐条实跑；`README.md` §1 完成判据逐条复现。

## 3. 语义与质量审查清单

- 纯函数性：`assemble.py`/`gate.py`/`submission.py`/`review_events.py` 不读文件、不访问 Ledger、不取时间；随机性只经 `id_factory` 注入。
- 状态上限 / P7：金标全路径后 Ledger 中 m4 修订字节不含 `expert_verified` / `cross_model_reviewed`；无签发 StepRun；`derive_content_status` 的 `expert_verified` 分支只由合成测试替身覆盖。
- 事务序列与 §17 一致；submit StepRun 冻结输入恰 `{M3 包, corpus_spans}`；assemble 冻结输入 = 4 个上游修订 + 全部提交件；begin 之前的拒绝无写入；begin 之后的失败封存完整（检查名 ∈ {`input_contract`,`assemble`,`candidate_gate`,`internal`}）。
- 上游定位：`resolve_m3_outputs` 只认 succeeded 且 `compile_corpus` 的 m3 运行，输出经 `result_json` + artifact_type；`fixture_ingest` 灌入的 m3 包（无 `spans_revision_id`）被拒绝。
- 契约一致性：提交件 `layer ∈ {general, case, editorial}`；证据 `start_offset/end_offset` 为页块绝对偏移；坐标键名与 INTERFACES §3.1/§6 I-11 的差异已登记（README §10 N3）。
- 独立重算：Gate 与验收判定均不依赖被验实现自身产出的 gate 报告；`acceptance.py` 不信任被验目录自带 `verify.sh`（永远调用仓库内规范脚本）。
- 中文注释；无 `except: pass`；不新增依赖、ID 前缀、模型调用；不写 `import_legacy_candidates` 工具。

## 4. 结论规则

- K1、K2、K3、K4 各自通过后，由主 Agent 在 §5 记名并写 `ACCEPTED`；执行者不得自记。K5 可选，仅在主 Agent 明确要求时做。
- 任一 FAIL 视为未通过，返工另立 ACT；`cross_model_extraction`、`semantic_span_input`、`term_layering_scan` 三项 BLOCKED 不视为失败，但必须确属 §19 第一列差距；20.6/20.7 的 BLOCKED/FAIL 不视为失败。
- 全部通过后，由主 Agent 同步 `SUBAGENT_TODO.md`、`HANDOFF.md` 并据此勾选 `PLAN`/`G7-PLAN` 相应项。

## 5. 验收记录

§5 验收记录由主 Agent 填写。
