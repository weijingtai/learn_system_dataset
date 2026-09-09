# D-02 L0 Machine Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement the two ACTs in order. Track every step and commit after each ACT.

**Goal:** 冻结 ArtifactRef、StepRequest、StepResult、StagePackage 四个机器可验证契约，使后续 Ledger、Orchestrator 与 M1–M8 不再自行发明信封格式。

**Architecture:** 使用 JSON Schema Draft 2020-12 表达契约，YAML 只作为人类可读 fixture。复用开源 `check-jsonschema` 做元 Schema、正例、反例及 YAML→JSON round-trip 校验，不自研 Schema 引擎。

**Tech Stack:** JSON Schema 2020-12、YAML、`check-jsonschema`、Python 标准库与现有 PyYAML。

---

状态：`READY`（转译审查 R2 通过，等待用户派发）

依赖批准：`check-jsonschema>=0.38,<0.39` 已由主 Agent 按 `openspec/subagent-delivery-gate.md` 批准，仅用于四份 L0 Schema 的离线验证，替代自研校验器。无法安装或无法离线解析本地 `$ref` 时必须停止；不得回退为自研引擎。

## Authority and dependencies

- `docs/blackbox-spec-rework/D-design.md` D-02
- `openspec/learn-system-blackbox-architecture.md` §7、§7.1、§8、§8.1、§8.2
- T-02：`ACCEPTED`；六类 ID 已冻结
- D-03：`ACCEPTED`；StepRun 生命周期已冻结
- 现有 round-trip 来源：`pipeline/corpus/bazi/qtbj_ed01/manifest.yaml`

## File map

### ACT 01

- Modify: `pipeline/requirements.txt` — 增加唯一新依赖 `check-jsonschema>=0.38,<0.39`
- Create: `openspec/schemas/artifact_ref.schema.json`
- Create: `openspec/schemas/stage_package.schema.json`
- Create: `openspec/schemas/examples/artifact_ref.valid.yaml`
- Create: `openspec/schemas/examples/artifact_ref.stage_package.valid.yaml`
- Create: `openspec/schemas/examples/artifact_ref.invalid_mixed_ids.yaml`
- Create: `openspec/schemas/examples/artifact_ref.invalid_missing_logical_id.yaml`
- Create: `openspec/schemas/examples/artifact_ref.invalid_unknown_field.yaml`
- Create: `openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml`
- Create: `openspec/schemas/examples/stage_package.invalid_stage_mismatch.yaml`
- Create: `openspec/schemas/examples/stage_package.invalid_missing_lineage.yaml`
- Create: `openspec/schemas/examples/stage_package.invalid_transformation.yaml`
- Create: `openspec/schemas/examples/stage_package.invalid_nested_ref.yaml`
- Create: `openspec/schemas/examples/stage_package.invalid_unknown_field.yaml`
- Create: `openspec/schemas/verify.sh`

### ACT 02

- Create: `openspec/schemas/step_request.schema.json`
- Create: `openspec/schemas/step_result.schema.json`
- Create: `openspec/schemas/examples/step_request.empty_inputs.valid.yaml`
- Create: `openspec/schemas/examples/step_request.invalid_missing_inputs.yaml`
- Create: `openspec/schemas/examples/step_request.invalid_latest.yaml`
- Create: `openspec/schemas/examples/step_request.supersedes.valid.yaml`
- Create: `openspec/schemas/examples/step_request.invalid_supersedes.yaml`
- Create: `openspec/schemas/examples/step_request.invalid_unknown_field.yaml`
- Create: `openspec/schemas/examples/step_result.awaiting_human.valid.yaml`
- Create: `openspec/schemas/examples/step_result.invalid_missing_resume_token.yaml`
- Create: `openspec/schemas/examples/step_result.invalid_missing_pending_queue.yaml`
- Create: `openspec/schemas/examples/step_result.invalid_stale_token.yaml`
- Create: `openspec/schemas/examples/step_result.invalid_failed_without_evidence.yaml`
- Create: `openspec/schemas/examples/step_result.invalid_unknown_field.yaml`
- Modify: `openspec/schemas/verify.sh`
- Modify: `openspec/learn-system-blackbox-architecture.md` — §7/§8 登记四份 Schema 与唯一验证命令

## Frozen contract vocabulary

所有 Schema 使用 `schema_version: "1.0.0"`，`additionalProperties: false`。Schema version 与数据中的 Revision ID 是两条独立版本轴。所有核心 ID pattern 只在 `artifact_ref.schema.json#/$defs` 定义一次；其他三份 Schema 使用本地 `$ref` 复用，禁止复制正则造成漂移。

### ArtifactRef

必填公共字段：

| 字段 | 规则 |
|---|---|
| `schema_version` | const `1.0.0` |
| `artifact_kind` | `artifact` 或 `stage_package` |
| `artifact_revision_id` | `^rev_[0-9a-f]{32}$` |
| `artifact_type` | `^[a-z][a-z0-9_]*$` |

`$defs` 必须集中定义并导出：`schemaVersion`、`artifactId`、`artifactRevisionId`、`processingRunId`、`stepRunId`、`stagePackageId`、`stage`、`artifactStatus`、`stepRunStatus`。其余三份 Schema 只能通过相对本地 `$ref` 使用这些定义。

二选一且互斥：

- `artifact_kind=artifact`：必须有 `artifact_id`，格式 `^art_[0-9a-f]{32}$`；禁止 `stage_package_id`。
- `artifact_kind=stage_package`：必须有 `stage_package_id`，格式 `^pkg_m[1-8]_[0-9a-f]{32}$`；禁止 `artifact_id`。

### StagePackage

顶层必填：`schema_version`、`stage_package_id`、`artifact_revision_id`、`stage`、`status`、`payload`、`manifest`、`validation`、`lineage`、`logs`、`failures`。

- `stage` 仅 `m1`–`m8`；`stage_package_id` 中的 stage 必须与字段值一致，用八个 `if/then` 分支确定性约束。
- `status` 使用 §8.2 五值：`draft/sealed/quarantined/invalidated/superseded`。
- `payload`：object，允许 Stage 专属字段，由后续 Stage Schema 约束。
- `manifest` 必填 `schema_version`、`processing_run_id`、`step_run_id`、`input_artifacts`、`output_artifacts`、`counts`、`content_sha256`。
- `processing_run_id`：`^prun_[0-9a-f]{32}$`；`step_run_id`：`^srun_[0-9a-f]{32}$`；SHA-256：`^[0-9a-f]{64}$`。
- `input_artifacts`、`output_artifacts`、`validation.report_artifacts`、`lineage.upstream_artifacts`、`logs`、`failures` 的每项都 `$ref` ArtifactRef。
- `validation` 必填 `passed:boolean` 与 `report_artifacts:array`。
- `lineage` 必填 `upstream_artifacts:array` 与 `transformations:array`。每个 transformation 严格只含并必填：`operation`（snake_case）、`step_run_id`、`configuration_artifact_revision_id`、`input_artifact_revision_ids`、`output_artifact_revision_ids`。输入数组可为空（M1），输出数组至少一项；两个数组均为唯一 `rev_...`。
- `counts` 允许 Stage 自定义键，但所有值必须为非负整数；其他信封对象不允许额外字段。

### StepRequest

必填 §7 五字段：

| 字段 | 规则 |
|---|---|
| `processing_run_id` | `^prun_[0-9a-f]{32}$` |
| `step_run_id` | `^srun_[0-9a-f]{32}$` |
| `input_artifact_ids` | 唯一的 `rev_...` 数组；M1 可为空，但字段不可省略 |
| `technique_profile_id` | 非空字符串 |
| `configuration_artifact_id` | `^rev_[0-9a-f]{32}$` |

另加必填 `schema_version: "1.0.0"`。这里保留 §7 已冻结字段名；所有 `*_artifact_id(s)` 都是精确 `artifact_revision_id`，不是“最新版本”或逻辑 ID。

唯一可选字段为 `supersedes_step_run_id`，格式 `^srun_[0-9a-f]{32}$`。首次运行省略；重跑时指向被取代的旧 StepRun。该字段归属 StepRequest wire contract，不另造第五份 StepRunRecord Schema。

### StepResult

必填：`schema_version`、`processing_run_id`、`step_run_id`、`status_version`，以及 §7 的 `status`、`output_artifact_ids`、`validation_report_ids`、`log_artifact_ids`、`failure_artifact_ids`。

- 四个 `*_artifact_ids` 均为唯一 `rev_...` 数组，可为空。
- `status_version` 为 `>=1` 的整数。
- `status` 使用 §8.2 六值：`running/awaiting_human/suspended/succeeded/failed/superseded`。
- `status=awaiting_human` 时必须额外包含 `resume_token`（非空、最少32字符）和至少一个 `pending_queue_artifact_ids`；其他状态禁止携带这两个字段，避免陈旧 token。
- `status=failed` 时 `failure_artifact_ids` 至少一项。

## Fixture rules

- 所有示例 ID 使用明确写死的 32 位小写 hex，禁止 `example`、`latest` 或动态占位符。
- 《穷通宝鉴》M1 StagePackage 的 `payload.source_manifest.source_id` 必须等于真实 manifest 的 `src_qtbj_ed01`，并记录原 manifest 仓库路径。
- round-trip：将有效 YAML fixture 用 PyYAML 读入，经标准库 JSON 序列化再读回，生成临时 JSON，再用同一 StagePackage Schema 校验。
- 反例必须分别证明：ArtifactRef 混用两种逻辑 ID、Stage 与 package ID 不一致、StepRequest 使用 `latest`、`awaiting_human` 缺 token 会失败。
- 还必须证明：四份信封的未知字段、StagePackage 缺六段之一、transformation 缺必填关系字段、嵌套 ArtifactRef 非法、StepRequest 省略输入字段、非等待状态携带陈旧 token、`failed` 无失败证据会失败。
- `verify.sh` 必须用 Python 标准库读取四份 Schema 结构并断言：Artifact 五状态与 StepRun 六状态集合精确相等、`status_version.minimum=1`、所有 Revision ID 数组均设 `uniqueItems:true`、StagePackage `required` 精确包含全部顶层必填字段、四份顶层及 `manifest/validation/lineage/transformation` 等闭合信封对象均为 `additionalProperties:false`；仅明确排除允许 Stage 扩展的 `payload` 与 `counts`。

## Forbidden

- 不实现 Ledger、Orchestrator、M1–M8 或业务模型。
- 不创建自研 Schema 校验器，不引入 Pydantic、数据库或 Web 服务。
- 不修改已冻结 ID、状态枚举或 §7 五个原字段名。
- 不修改 `pipeline/corpus/bazi/qtbj_ed01/manifest.yaml`。
- 不修改工作包、PLAN、HANDOFF、TODO 或现有 `verify-T.sh`。
- 不用远程 `$ref`，所有 Schema 必须离线验证。

## Stop conditions

遇到字段语义冲突、校验器无法离线解析本地 `$ref`、需要第五份 Schema、或需要修改冻结规范时停止并报告，不自行扩大范围。

## BDD → ACT mapping

- B1–B4：ACT02 的 StepRequest/StepResult 正反 fixture 与条件约束。
- B5–B8：ACT01 的 ArtifactRef/StagePackage、真实 manifest 对照与 round-trip。
- B9：两项 ACT 的未知字段反例，并由四份 Schema 的 `additionalProperties:false` 结构断言共同约束。
- B10：ACT02 的 `supersedes_step_run_id` 正反 fixture。
- B11：ACT02 的全局回归门禁。

## ACT review

转译审查 R2：`READY`，2 个 ACT 可开工。字段、失败分支、依赖批准、交接边界、验证命令与顺序均已机械化；执行 Agent 不得自行补设计。
