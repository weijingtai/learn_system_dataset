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

### 5.1 W4-G 实现（2026-09-12，主 Agent 独立验收，`git archive` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w4k`，按 K1–K4 分组停下待验收（K5 可选 legacy 准入未派发）。定稿 `8cedae2`（裁定 47–50）→ 四查 R1 REWORK `1a7919e` → 返工 `d982dd6`（裁定 53–55）→ R2 READY `930c972`；前置 impl-00 act/12 `b8db05d`、act/05 `7d805e6` 均已验收。

- K1（`fab45cb`、`5ba7049`、`d16eccf`）：范围仅 `pipeline/knowledge_extraction`；65 OK；gate.py 不 import assemble/submission；serialize/submission/assemble/gate 无副作用；无模型 API。
- K2（`ca42ee9`、`2d46155`）：97 OK（阈值 95 + 第 58 条 2 例）。第 58 条：同阶段后续运行经 `supersede_step_run` 续写。矩阵外 9 项：三路提交依次接替且 `collect_submissions` 列出 3 份；重复提交与无 m3 均 begin 前拒绝无写入；assemble 接替第 3 路并因 a/b 分歧 `awaiting_human`、无 m4 包；不经接替续写被 Ledger `IllegalTransition` 拒绝。
- K3（`03f7f90`、`32192dd`）：122 OK；review_events 无副作用；生产代码 `_fixture` 字样仅为 `synthetic_fixture` 字段。矩阵外 9 项：合成裁决事件保留 `synthetic_fixture: true` 与 `actor_ref`；`resume_m4` 同一运行 succeeded 且恰 1 个 m4 包、未另起运行；重复 resume/重复裁决/第 7 键/错误 token 均拒；仅四键裁决可登记（第 53 条）。
- K4（前置对齐 `a8172f8`，ACT 07 `06d1a28`）：`a8172f8` 将 TXT_001 文案回正为 act/01 契约原文并同步附录 A 测试数据（第 60 条登记程序偏差）。133 OK（阈值 131 + 2）；acceptance.py 独立；`m4-stage-gate.sh` `SUMMARY pass=13 fail=0 blocked=3`、exit 2，BLOCKED 为 `cross_model_extraction`（无模型薄接入）、`semantic_span_input`（SemanticSpan 未实现）、`term_layering_scan`（术语表缺失）；输出无 `expert_verified` 计入。矩阵外：fixture 副本 `candidate_set.yaml` 改一字节 → `FAIL fixture_host`、exit 1；副本放置恒真 `verify.sh` 仍 `FAIL fixture_host`（D-18，不信任副本脚本）。
- 全部门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK、`check_interfaces.py` 24 PASS、`m3-coverage.sh` exit 2、`run_all.sh` `pass=2 fail=1 blocked=8`。

impl-05（M4 最薄接入，无模型、合成裁决金标）`ACCEPTED`。真实 `expert_verified` 签发依赖用户撰写决定表（P7），相关判定保持 BLOCKED；§20.4/20.8 仍 BLOCKED（M6 正式知识未接入）。

### 5.2 W8 8.2 返工 R82a + 宿主 R82b（2026-09-16，主 Agent 独立验收，`git archive 7838d59` 干净树）

判定：**R82a（`71c913f`，cmd DeepSeek V4.1 Flash）与 R82b（`7838d59`，cmd 完成、agy Gemini 3.8 Flash Medium 提交）ACCEPTED**。真书 M4 如实停在 `awaiting_human`，**等待用户裁决 24 组两路分歧**（第 104 条 D1）。

- 过程：R82a 按 `evidence_level` 分派引文定位基准（`gate.py` `_quote_basis`：offset 用片段自身 `text`/`start_offset`，OCR 页块路径逐字不变）。R82b 首轮真书产生 35 条分歧并停手请示 → 主 Agent 查明第 100 条 D4 与规格 §12:572 冲突（系主 Agent 起草错误），且抽取说明允许自由截取引文致证据键无法对齐 → 第 104 条：分歧由用户裁决、抽取协议 v2（证据以整片段为单位）、两路重新盲抽、空类别如实提交 → 分歧 24 组（assertion 22、pattern 2；concept_mention 两路一致）。
- 用例审计（AST）：`test_gate.py`、`test_assemble.py`、`test_acceptance.py` 删 0、改 0、仅新增；`test_qianyuan_text_host.py` 新增 4 条（六份提交件登记含空类别、终态 `awaiting_human` 且分歧数 = 24、不写 `candidate_set`、不登记 m4 阶段包；临时 Ledger；宿主缺失 `skipIf` 写明原因）。未写任何 `ruling_*.yaml`，未调用 `resume_m4`。
- 干净树：knowledge_extraction `Ran 149 OK`；宿主 `m4/SHA256SUMS` 校验全部 OK；`m4-stage-gate.sh`（mini_ed01）`SUMMARY pass=13 fail=0 blocked=3`，与改前同；`run_all.sh` 基线不变。
- **主 Agent 篡改**（临时副本）：offset 基准起点由片段 `start_offset` 改为 0 → `test_offset_level_candidate_set_all_twelve_checks_pass` 转红。
- 持久 Ledger `var/ledgers/qianyuan_w8/`（不入库）：M4 `step_run_id = srun_bafd749946aa4cc1b0312cbb3ee1fa8e`；残留 0 字节 `writer.lock` 经 agy 只读分析为 `fcntl.flock` 进程锁（`pipeline/ledger/lock.py:25-37`），进程退出即释放，不阻塞后续导入。
- 用户待办：`var/ledgers/qianyuan_w8_review/m4_rulings.yaml`（主 Agent 从 `dispute_queue` 原样导出，未预填、无建议）。
