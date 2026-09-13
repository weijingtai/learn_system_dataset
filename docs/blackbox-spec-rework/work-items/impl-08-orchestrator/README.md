# impl-08：Local Orchestrator + Contract Registry（§5/§6.1/§7/§7.1/§17）首切片

状态：`READY_FOR_REVIEW`（W4-I 定稿 2026-09-12，依 `G7-RULINGS.md` §1 原则 P1–P9 与 §6 impl-08 裁决；未经实现；派发前置见 §8）

本包取代起草稿（`DRAFT`）。§4「主 Agent 决定」执行者不重议；§4.1「待主 Agent 裁决」未裁前不得据此实现。

## 1. 目标

在 `pipeline/contract_registry/` 与 `pipeline/orchestrator/` 落地规格 §19 拓扑中的 L2 `Local Orchestrator` 与 L2' `Contract Registry` 的**首纵切最薄可用切片**。

**首纵切串联链路（P1）**：`fixture ingest m1/m2（imported，只判 Gate）→ 薄 M1 页图登记（m1_shim，准备阶段）→ M3（legacy run_m3）→ M5（legacy run_m5）→ M8（legacy run_m8，独立 release_run）`。M4/M6/M7 Module 与 ReleaseRun 状态机（§6.2）标 `DEFERRED`（§9）。

1. **Contract Registry**：声明式登记表记录四份 L0 Schema（路径、`schema_version`、sha256）、各 Stage Module 描述（consumes/produces、绑定、入口）、端口与 Adapter；提供一致性检查与「同一端口换 Adapter 后相邻 Module Interface 不变」的替换判定（§20 第 10 条）。
2. **统一 Module Interface 适配**：`execute(StepRequest) → StepResult` 落在 `runner.execute_step`；加工 Module 实现 `plan`/`execute` 返回 `StepOutcome`，StepRun 的建立与终态迁移由 Orchestrator 独占。另设 `legacy_self_driving`（挂接 `run_m3`/`run_m5`/`run_m8` 这类自建 StepRun 的入口）与 `imported`（只判 Gate，不执行）。
3. **EditionRun**：按首纵切计划逐阶段执行、独立判定 Stage Gate、阻断未完成任务向下游流动；支持人工队列挂起与恢复（`awaiting_human`/`resume_token`）、操作者暂停与基础设施对账（`suspended`/`recover`），并通过 Ledger `recover_from_checkpoint` 从 Checkpoint 重跑。
4. **六项只读查询**（§5 闭集）：`RunStatus`、`StageProgress`、`PendingQueue`、`BlockingReasons`、`ReworkImpact`、`ThroughputEstimate`。
5. **可执行判据**：把 `run_all.sh` 中 20.1 与 20.10 的硬编码 BLOCKED 改为计算得出；能在宿主上判定的部分（桩模块串联、真实 m1/m2 → m3 → m5 → m8 链、存储端口替换）先判定并如实报 PASS/FAIL，缺前置 Module 的部分报 BLOCKED 并写明首个缺失的 §19 行名。

完成判据（本批唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
bash openspec/acceptance/orchestrator-gate.sh; echo exit=$?
# 期望 6 行 + 末行：
#   PASS gate_blocks_incomplete
#   PASS gate_chain_stub_m1_m6
#   PASS edition_conjunction
#   PASS recovery_via_orchestrator
#   PASS real_chain_mini_ed01
#   BLOCKED registered_modules_m1_m6 前置缺失: M4 Knowledge Extraction；Local Orchestrator 首切片已串联 m1–m3、m5 Gate，m4/m6 未登记生产 Module
#   SUMMARY pass=5 fail=0 blocked=1
# exit=2
bash openspec/acceptance/contract-registry.sh; echo exit=$?
# 期望 5 行 + 末行：
#   PASS l0_schemas_verified
#   PASS registry_consistent
#   PASS storage_port_substitutable
#   BLOCKED modules_port_clean 前置缺失: Contract Registry；m3.corpus_structural、m5.automatic_validation、m8.dataset_compilation 入口直接访问 Ledger 内部（…:行号 列表）
#   BLOCKED other_ports_adapters 前置缺失: Contract Registry；ocr/model/index 端口 Adapter 数不足 2（ocr=0, model=0, index=0）
#   SUMMARY pass=3 fail=0 blocked=2
# exit=2
.venv/bin/python -m unittest discover -s pipeline/contract_registry/tests -t . 2>&1 | tail -3   # OK；用例数逐 ACT 阈值见 TDD §1
.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t . 2>&1 | tail -3        # OK；用例数逐 ACT 阈值见 TDD §1
bash openspec/acceptance/run_all.sh 20.1 20.10
# 期望：BLOCKED  20.1  前置缺失: M4 Knowledge Extraction；Local Orchestrator 首切片已串联 m1–m3、m5 Gate，m4/m6 未登记生产 Module
#       BLOCKED  20.10  前置缺失: Contract Registry；m3.corpus_structural、m5.automatic_validation、m8.dataset_compilation 入口直接访问 Ledger 内部（…）
bash openspec/acceptance/run_all.sh | tail -1   # SUMMARY pass=2 fail=1 blocked=8（条数不变；20.1/20.10 改为计算值）
```

`registered_modules_m1_m6` 判 **BLOCKED** 而非 PASS：EDITION_STAGES 中 m4 无登记非桩 Module（§22.3 要求 §20.1 成立，与本包 P1 裁剪冲突，见 §4.1 N-1）。M4/M6 登记并通过真实链后该项自动转 PASS；**不改脚本，只改登记表**。

## 2. 依据（只读来源，文件:行号）

- 裁决 `docs/blackbox-spec-rework/G7-RULINGS.md`：§1 P1–P9；§6 impl-08；§9 第 13/25/26 条（Ledger 读缺口、错误码缺口）；§9.1 第 32 条（薄 M1 supersede）；§9.2 第 27 条（回归命令取行）。
- `G7-PLAN.md`：W4-I 写范围与出口（§20.1/20.10 由 BLOCKED 转判；`run_all.sh` 改动集中给 I）；§1 并行规则。
- 规格 `openspec/learn-system-blackbox-architecture.md`：§5 `:96–130`（Orchestrator 职责 `:116`、六项查询 `:117–127`、五个专用队列 `:119–124`、Registry 职责 `:128`）；§6.1 `:136–151`（阶段推进条件 `:149`）；§6.2 ReleaseRun `:153–175`；§7 `:177–207`（StepRequest `:187–193`、只读冻结输入 `:207`）；§7.1 `:209–226`；§8 `:228–246`；§17 `:817–836`（suspended 对账 `:828`、事务序列 `:836`）；§17.1 `:838–846`（人工决定即时落盘 `:843`、恢复语义 `:845`）；§19 拓扑 `:865–871`、主表 `:873–893`、§19.0 `:899–918`；§20 第 1/10 条 `:937,:946`；§21 `:949–956`；§22.1 `:964–969`、§22.3 `:986–992`、§22.4 `:995–1001`。
- 已验收模块入口与返回键（只读）：
  - `pipeline/corpus_compiler/step.py:35` `run_m3(service, edition_part_id, *, batch_size=10)`；返回 `step_run_id`/`stage_package_id`/`package_revision_id`/`spans_revision_id` 等（`:379–403`）。
  - `pipeline/validation/step.py:59` `run_m5(service, edition_part_id, *, target_consumption_level="INTERNAL_DEMO")`；返回 `step_run_id`/`validation_package_revision_id`/`gate`/`counts` 等（`:332–357`）；StagePackage `validation.passed = gate["passed"]`（`:275`），fixture 上 `gate.passed=true`（impl-03 README §1）。
  - `pipeline/dataset_compiler/step.py:194` `run_m8(service, edition_part_id, *, consumption_level, min_app_version=None, release_id=None)`；自建 `release_run`（`:212`）并返回其 `processing_run_id`（`:212,600`）；StagePackage `manifest.output_artifacts = [publication_package]`（`:535`）。
  - `pipeline/ledger/fixture_ingest.py:255` `ingest(fixture_dir, service, asset_root=None, *, stages=STAGES)`，`STAGES=("m1","m2","m3")`（`:40`），`STAGE_OUTPUT_TYPES`（`:43–47`）。
  - `pipeline/dataset_compiler/shim/m1_shim_source_assets.py:250` `register_source_assets(service, edition_part_id, asset_root)`，以 `supersede_step_run` 接替 m1（`:286,313`），只登记 `source_asset_page`/`source_asset_register`，**不登记 StagePackage**（`:180–234`）。
- L0 Schema：`openspec/schemas/step_request.schema.json`（顶层无 `stage` 字段）、`step_result.schema.json`、`stage_package.schema.json`、`artifact_ref.schema.json`；目录内另有 community 系 Schema，首纵切一字不动（P3）。
- Ledger（impl-01 ACCEPTED，只读引用、本批不改）：`pipeline/ledger/service.py` `_live_step_run:253`、`_configuration_stage:295`、`create_processing_run:319`、`begin_step_run:405`、`supersede_step_run:412`、`register_stage_package:718`、`await_human:885`、`record_human_event:922`、`resume:965`、`suspend:991`、`recover:1033`、`_seal_step_manifest:1082`、`finish_step_run:1132`、`fail_step_run:1187`、Checkpoint 封存守卫 `:1280–1285`、`write_checkpoint:1364`、`recover_from_checkpoint:1430`、`LedgerReader.read_object:1606`；`pipeline/ledger/client.py:451`（`LedgerClient.read_object`）。`LedgerReadMixin`（`:111–164`）无 `frozen_inputs`/`artifacts.artifact_type`/按 `step_run_id` 取 sealed `stage_package` 的公开方法。
- impl-00：`INTERFACES.md` §1 通用约定、§2 阶段卡、§4 artifact_type 临时闭集、§6 对账清单；`README.md` §5.2 缺口清单（Ledger 读缺口 + 错误码缺口，impl-08 唯一登记处）。
- impl-04（只读）：`dataset_compiler/README.md` §5.8（`reader.store.conn` 只读 SELECT）、§7（m8 StagePackage `manifest.content_sha256 = release_manifest` 字节哈希、`output_artifacts = publication_package`）。
- 模板：`work-items/impl-02-corpus/`（README/BDD/TDD/ACT.yaml/PROMPT-J1/ACCEPTANCE）。
- 现状：`pipeline/orchestrator/`、`pipeline/contract_registry/` 均不存在；`openspec/acceptance/` 现有 `run_all.sh`、`m3-coverage.sh`、`m5-evidence-gate.sh`（`m8-span-identity.sh` 由 impl-04 ACT 07 新建）。

## 3. 范围

写（全部新建，另有标注者除外）：`pipeline/contract_registry/**`、`pipeline/orchestrator/**`、`openspec/acceptance/orchestrator-gate.sh`（ACT 07）、`openspec/acceptance/contract-registry.sh`（ACT 08），以及 `openspec/acceptance/run_all.sh`（**仅 ACT 09**，只新增一个 `accept_check` 函数并改 20.1/20.10 两个 case 体）。

禁止：

- 改 `pipeline/ledger/**`（P9）、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`openspec/schemas/**`、规格正文、`openspec/id-prefix-registry.md`、`pipeline/corpus/_fixture/**`、`verify-T.sh`、`mutations.sh`、`PLAN.md`/`HANDOFF.md`/`SUBAGENT_TODO.md`/`G7-*.md`、任何 `ACCEPTANCE.md` §5、其他 work-items；
- 与本波并行写者（impl-04 写 `pipeline/dataset_compiler/**`、`openspec/acceptance/m8-span-identity.sh`、`run_all.sh`）重叠：ACT 09 与 impl-04 ACT 08 互斥，须待 impl-04 ACT 08 验收后执行（P4）；
- 新增依赖（只用标准库 + PyYAML + jsonschema）、新增 ID 前缀（`module_id`/`port_id`/`adapter_id` 是登记表标签）；
- 调用模型 API（P6）；生产代码读 fixture 路径（`acceptance.py` 经 `--fixture` 参数读取除外）；
- Orchestrator 与 Registry 非测试源码不得 import 任何加工 Module 包，只能经 `importlib` 解析登记表 `entry` 或经 `modules=` 注入；
- 生产登记表 `registry.yaml` 不得出现 `kind: stub`；不得写 `ACCEPTED` 或台账。

## 4. 主 Agent 决定（执行者不重议）

本节含 `G7-RULINGS.md` §6 已裁条目与可由 P1–P9 直接推出者；推导随条写出。

| # | 原条目 | 决定 | 依据 / 推导 |
|---|---|---|---|
| D-1 | StepRequest 缺 stage 字段 | **A：维持 L0 现状**，由配置修订内容 `"stage"` 键推导（`service.py:295–310`）；Orchestrator 另要求配置含 `"module_id"`，写入前校验 `config.stage == 登记 stage` | P3「首纵切内 L0 四份不动」直接排除 B/C（改 `step_request.schema.json` 或 `verify.sh`/`mutations.sh`）；A 已闭合，无需 L0 变更 |
| D-2 | Module 入口控制反转 | **A+C**：本包只用 `legacy_self_driving` 挂接 `run_m3`/`run_m5`/`run_m8`；为 impl-02/03/04 登记「迁移到 `step_request` 绑定」的后续 ACT（不属本包写范围） | P9「不改已验收模块行为」直接排除 B（改 `run_m3`）；`step.py:35` 自建配置与 StepRun，本包不得改 |
| D-3 | StepRun 终态迁移归属 | **A**：Module 返回 `StepOutcome`，由 Orchestrator 转 L0 StepResult 并调用 `finish_step_run`/`fail_step_run`/`await_human` | 规格 §5:116「Local Orchestrator：执行阶段状态机」+ P9（新 Module 只需产出，状态迁移集中一处） |
| D-4 | Stage Gate 报告是否落盘 | **本包取 B（写下游 StepRun 首个 artifact）但复用已登记类型**；是否新提名 `stage_gate_report` 见 §4.1 N-4 | P9 排除 C（改 `RUN_ARTIFACT_TYPES`，`service.py:66`）；P2 要求新类型先入 `INTERFACES.md` §4，本包不自命名未登记类型 |
| D-5 | StageManifest 与 StepManifest | **A**：首切片按「一个 EditionPart × Stage（含 supersedes 链）只有一条有效 StepRun」，`succeeded` 且 `result_json` 非空即视 StepManifest 已原子封存（`finish_step_run` 同事务，`service.py:1183`） | P9：Ledger 只有 `step_manifest`（`service.py:1082–1130`），run 级 `stage_manifest` 需改 Ledger，本批不做 |
| D-10 | §19.0 缺 Orchestrator/Registry 判据行 | **A**：本包新建 `orchestrator-gate.sh` 与 `contract-registry.sh`；登记进 §19.0 由主 Agent 另立规格包 | 规格 §19.0:899–918 无此两行，但 §22.3:992 要求「各行 §19.0 判据 exit 0」；先例 impl-02 `m3-coverage.sh`、impl-03 `m5-evidence-gate.sh` |
| D-11 | 新 artifact_type | **按 P2**：`INTERFACES.md` §4 是唯一登记处；本包**不新增** artifact_type，Gate 报告复用已登记的 `validation_report` | G7-RULINGS §6「D-11 按 P2」；P2「未入闭集的类型名，实现不得使用」 |
| D-12 | 登记表载体 | **A**：仓库内声明式 `pipeline/contract_registry/registry.yaml`（Git 跟踪），格式由 `check_registry` 规则定义，不出 JSON Schema | P3（不向 `openspec/schemas/` 新增文件）排除 B；P9（不改 Ledger）排除 C |
| D-13 | 进度事件 | **A**：以 StageCheckpoint 落盘与 `step_run_events` 为进度来源，不建新机制 | §17.1:843（每 task / 每次人工决定落盘）+ P9（Ledger 不新增 `progress` API） |
| D-14 | Edition 级合取 Part 清单来源 | **A**：由调用方给出 Part 句柄清单，`edition_status` 做合取；首纵切单 Part | G7-RULINGS §9 第 4 条（首纵切单 Part，`edition_part_id` 取该 Part）+ P1 |
| D-15 | ReleaseRun | **A（裁剪版）**：本包只做 EditionRun 与首切片 release 段（单个 M8 legacy 步）；§6.2 ReleaseRun 状态机（M7 与多 Part 汇编）标 `DEFERRED`（§9） | P1「首纵切 = Ledger → M3 → M5 → M8」；M8 以其 legacy 入口执行，prun 边界见 §4.1 N-3 |
| D-17 | 人工决定后由谁写 Checkpoint | **A**：Orchestrator 在 `record_human_event` 后复制本 StepRun 链上最新 Checkpoint、追加决定号并立即落盘 | §17.1:843「每次人工决定被 Ledger 接受后即时落盘」直接要求；`pending_queue` 缩减交给 Module 可选钩子 `resolve_pending` |
| D-18 | 与 impl-02 的时序 | **解除**：impl-02 已 `ACCEPTED`（`SUBAGENT_TODO.md`），K1–K4 可派发 | G7-RULINGS §6「D-18 与 impl-02 时序已解除（impl-02 ACCEPTED）」 |

**首纵切裁剪（P1）**：Orchestrator 串联 m1/m2（`imported`）→ m3 → m5（EditionRun 段）+ m8（release 段）；薄 M1 `m1_shim` 为准备阶段；M4/M6/M7 Module 与 ReleaseRun 状态机 `DEFERRED`。

## 4.1 待主 Agent 裁决

未裁前不得据此实现；每条给选项、推荐与理由、证据。

**N-1 §22.3 要求 §20.1 成立与 P1 冲突**（`openspec/...:991` 期望「§20 第 1、3、4、8、9 条成立」；P1「M4/M6/M7 首纵切内不接，判 BLOCKED」；`run_all.sh:937`）
- A：维持 BLOCKED，20.1 在 M4 登记并过真实链后自动转 PASS（推荐）。理由：P1 明令不伪造；20.1 的 BLOCKED 由登记表数据决定，M4 落地即转 PASS，不改脚本。
- B：把 20.1 判据从「M1–M6 阶段 Gate」收窄为「首纵切声明阶段（m1/m2/m3/m5）Gate 完成」。理由：可判 PASS，但改写了 §20 第 1 条的 M1–M6 语义，需改规格正文。
- C：本包实现 M4/M6 最薄桩模块以满足 M1–M6。理由：与 P1 冲突，且桩不得计入 `registered_modules_m1_m6`（D-11/§5.8），实则仍 BLOCKED。
- 推荐 A。

**D-4 Gate 报告落盘**（`service.py:66,253–262`；§5:128）
- A：不落盘，每次查询重算。
- B：Gate 通过后写入下游 StepRun 首个 artifact（推荐）。理由：零 Ledger 改动，留下「先过 Gate 才建下游 StepRun」的证据；上游 Gate 无处可写（m1）与最后一个阶段（m8）只能重算。
- C：扩展 `RUN_ARTIFACT_TYPES` 以 run 级封存。理由：血缘最强，但改 impl-01（违反 P9）。
- 推荐 B；若主 Agent 同意 B，请一并裁 N-4（类型名）。影响 ACT 04/07。

**N-4 Gate 报告的 artifact_type 命名**（`INTERFACES.md` §4；P2）
- A：复用已登记 `validation_report`，内容带 `{"kind": "stage_gate", "stage": ..., "gate": ...}` 判别（推荐）。理由：P2 下零登记负担，M5 已有复用先例（§9.1 第 24 条）。
- B：新提名 `stage_gate_report` 入 `INTERFACES.md` §4，由某一波的登记 ACT 一次写入。理由：类型语义更清晰，但 W4-I 无权写 `INTERFACES.md` §4（P2 单写者），须先裁登记波次。
- 推荐 A。影响 ACT 00/04/07。

**D-6 Ledger 只读接口缺口**（`service.py:111–164`；`INTERFACES.md` §5.2 清单）
- A：本包不改 Ledger；EditionRun 三元组由调用方提供并交叉校验；StagePackage 按 `get_revision()["schema_id"]=="stage_package"` 识别；`DirectLedgerAdapter` 自补 `read_object`（推荐）。
- B：按 §9.1 第 25 条由 impl-08 追加 LedgerReader 公开读方法（`frozen_inputs`、`artifacts.artifact_type`、按 `step_run_id` 取 sealed `stage_package`），再回改 impl-03/impl-04 调用方。
- 冲突：G7-RULINGS §9.1 第 25 条要求 impl-08 补读方法；P9 与本批禁令禁止改 `pipeline/ledger/**`。本包按 A 交，B 列 `DEFERRED` ACT（见 `act/10.yaml`）。请裁 B 的归属波次。
- 推荐 A（本批）+ 把 B 单列后续包。

**D-7 §20.1 是否计入 `imported`（fixture m1/m2）与 `legacy_self_driving`（m3/m5/m8）绑定**（`m3-coverage.sh` 先例；§22.3:991「薄用」）
- A：计入，PASS 行说明披露绑定类型（推荐）。理由：§22.3 明确 M1/M2 以最薄可用形态接入；本批 20.1 仍 BLOCKED（M4 缺），只影响未来何时转 PASS。
- B：只计入 `step_request` 绑定。理由：绑定越弱，证据越弱；但会使 M1/M2/M3/M5/M8 在迁移前永不计入，20.1 转 PASS 推迟到全部迁移完成。
- 推荐 A。影响 ACT 07。

**D-8 §20.10 判定口径**（`openspec/...:946`；§20 总则:935「绝不把不可判定项写成 PASS」）
- A：任一端口可替换即 PASS。
- B：四类端口全部可替换才 PASS。
- C：四类逐项判定，存储端口 PASS、其余不足者 BLOCKED，合成结果为 BLOCKED（推荐）。理由：既不把不可判定写成 PASS，又保留已证实部分的证据；与 §20 总则和 P1「BLOCKED 而非伪造」一致。
- 推荐 C。影响 ACT 08。

**D-9 M3 入口越过端口访问 Ledger 内部**（`corpus_compiler/inputs.py:101,103,122`、`step.py:431,446,534`；换 `ledgerd` Adapter 后 M3 无法运行）
- A：20.10 判 FAIL。
- B：`modules_port_clean` 报 BLOCKED（前置缺失: Contract Registry），逐条列 文件:行号，由 impl-02 后续 ACT 迁移到 LedgerPort（推荐）。
- C：本包直接改 M3（越界，违反 P9）。
- 推荐 B；理由：端口约束首次成文，impl-02 当时经 `act/03.yaml:17` 获许可，不宜追溯判 FAIL。本批 `modules_port_clean` 将同时列出 m3/m5/m8 三个已登记生产 Module 的越界点。若主 Agent 认为已知缺陷不应以 BLOCKED 呈现，选 A，则 `run_all` 的 fail 将变 2。

**N-2 薄 M1 `m1_shim` supersede 与 Orchestrator Gate/lineage 的交互**（`m1_shim_source_assets.py:313` supersede m1、`:180–234` 不写 StagePackage；`service.py:1280–1285`；`step.py:35` M3 冻结的 manifest 属被接替的 m1 运行）
- A：`effective_step_runs` 只在「接替者（链上）为本 stage 承载 StagePackage」时移除被接替运行；`upstream_lineage` 接受任一 `succeeded`（含被接替）上游运行的产出（推荐）。理由：m1_shim 不产 StagePackage、M3 冻结的 manifest 属于被接替的 m1 运行（G7-RULINGS §9.1 第 32 条附加要求「登记页图前后 `resolve_m3_inputs` 的 `manifest_revision_id` 不变」）；只认 succeeded 不放松 P5。
- B：把 m1/m2 声明为 `imported` 前置，`advance` 从 m3 起判；m1/m2 Gate 不进首纵切判据。理由：绕开交互，但 §20.1 的「M1–M6 阶段 Gate」链证据变弱。
- C：本包为 m1_shim 补一个 m1 StagePackage（改 impl-04 写范围，越界）。
- 推荐 A。影响 ACT 03/04/07。

**N-3 M8 legacy 入口的 ProcessingRun 边界与必填 kwarg**（`dataset_compiler/step.py:194,212` run_m8 自建 `release_run`；`corpus_compiler/step.py:35`、`validation/step.py:59` 均在调用方 processing_run 内）
- A：`legacy_self_driving` 描述符增加可选 `entry_kwargs`（如 m5 `{target_consumption_level: INTERNAL_DEMO}`、m8 `{consumption_level: INTERNAL_DEMO}`）；入口自有 ProcessingRun 的绑定（`owns_processing_run: true`）不比对 `handle.processing_run_id`，改以入口返回的 `processing_run_id` 建/取 release 段句柄（推荐）。
- B：只把 m8 当 release 段黑箱：Orchestrator 不解析其 StepRun，只以退出状态报 `executed`。理由：最简，但放弃对 M8 的 Gate 判定（Gate 是 §20.1 的证据来源）。
- C：给 `run_m8` 增加 `processing_run_id` 参数（改 impl-04，越界，违反 P9）。
- 推荐 A。影响 ACT 00/04/07。

**D-16 ReworkImpact / ThroughputEstimate 口径**（`openspec/...:126–127,:641–642`）
- A：ReworkImpact 按 StepRun 粒度血缘可达性估算（`estimate: true`；`needs_review_count` 取可达人工事件数；30% 比例阈值记 `not_evaluated`）；ThroughputEstimate 按已 succeeded StepRun 历时均值（推荐）。
- B：两项只返回 `not_evaluated` 占位。
- 推荐 A。影响 ACT 06。

## 5. 设计要点

1. **依赖方向**：`contract_registry` ← `orchestrator` → 各 Module。Module 由登记表 `entry` 经 `importlib` 解析；测试与验收经 `modules={module_id: 对象}` 注入桩。Orchestrator 源码不出现任何加工 Module 包名。
2. **三种绑定**：`step_request`（标准形态，Orchestrator 建 StepRun，Module 实现 `plan`+`execute`）；`legacy_self_driving`（先判上游 Gate，再调 `entry(service, edition_part_id, **entry_kwargs)`，事后从 Ledger 重建 StepResult 并校验 L0 Schema；要求 `port.unwrap()` 直连，`ledgerd` Adapter 下拒绝）；`imported`（不执行，只判 Gate）。
3. **§17 事务序列映射**（`step_request`）：建 StepRun（`put_run_artifact(configuration)` + `begin_step_run`）→ 冻结输入（`begin_step_run` 完成）→ 验输入 Contract（Module）→ 执行/存原始输出与日志/哈希/验输出/记录 Transformation（Module）→ 封存 StepManifest 与终态（Orchestrator）。Module 抛异常或 `StepOutcome` 违约时，Orchestrator 封存 `failure_report` 并 `fail_step_run`。
4. **advance 推导**：EditionRun 不另存状态，从 Ledger 事实推导。`advance(..., stages=FIRST_SLICE_EDITION_STAGES)` 依序处理：该 stage 有 running/awaiting_human/suspended → `waiting`；有 failed → `blocked`（须显式重跑）；有效运行全 succeeded 但 Gate 未过 → `blocked`；无登记 Module → `refused`（reason 含 §19 行名）；否则执行一步 → `executed`。除 `executed` 外一律零写入。`stages=EDITION_STAGES`（默认）为纵切后完整模式。
5. **Stage Gate 八项**（`gate.py` 独立实现，名称与顺序固定）：`tasks_present`、`all_tasks_succeeded`、`stage_package_valid`、`output_contract`、`validation_passed`、`failures_zero`、`no_pending_work`、`upstream_lineage`。
6. **人工恢复**：`record_human_event` 后立即写 Checkpoint；`resume` 消费 token 后以 `mode="resumed"` 再次 `execute`，只带最初冻结输入与已登记事件（`:220`）；`suspend` 来源 `operator`；`reconcile_after_outage` 把非终态 running 转 `suspended(infrastructure)`，终态不改写（`:828`）；`rerun_from_checkpoint` 走 Ledger `recover_from_checkpoint`，已完成任务不重做（`:845`）；全程无超时自动失败（`:222`）。
7. **§20.10 与端口**：端口闭集 `ocr`/`model`/`index`/`storage`。`LedgerPort` 方法闭集以 `LedgerClient` 公开方法为准（`client.py:108–451`），存储端口两个 Adapter 为 `DirectLedgerAdapter` 与 `LedgerdClientAdapter`。替换判定三步：同一桩套件在两个 Adapter 上跑出去 ID、去时间的规范化结果相等；相邻 Module 的 `interface_fingerprint` 相同；Module 源码不越过端口。
8. **桩隔离**：桩 `kind` 恒为 `stub`，只在测试与验收内以 `Registry.from_dict(..., allow_stub=True)` 构造；`registered_modules_m1_m6` 只认生产登记表的非桩 Module；生产表出现桩时 `check_registry` 报 `stub_in_production`。

## 6. 接口契约

### 6.1 上游输入契约（Orchestrator 读取的 Ledger 事实）

| 来源 | 字段 / 读法 | 用途 |
|---|---|---|
| `get_step_run(srun)` | `stage`、`status`、`status_version`、`request_json.input_artifact_ids`、`result_json.output_artifact_ids`/`failure_artifact_ids`、`supersedes_step_run_id`、`created_at`/`updated_at` | 有效 StepRun、Gate、血缘估算、吞吐 |
| `run_status(prun)["step_runs"]` | 本运行全部 StepRun | 按 stage 分组 |
| `list_step_run_events(srun)` | `await_human.payload.pending_queue`、`human_event.payload.event_revision_id`、`suspended.from_status` | PendingQueue、resume 上下文 |
| `latest_checkpoint(ep, stage)` / `list_checkpoints` | `completed_tasks`、`human_decisions`、`pending_queue`、`next_pointer`、`step_run_id` | `no_pending_work`、重跑计划、人工决定落盘 |
| `get_revision(rev)` + `read_object(sha256)` | `status`、`schema_id`、`step_run_id`；StagePackage 内容 JSON | Gate 识别并校验 StagePackage |
| StagePackage 内容（L0） | `stage`、`manifest.processing_run_id`/`step_run_id`/`output_artifacts[].artifact_type`、`validation.passed`、`failures` | `stage_package_valid`/`output_contract`/`validation_passed`/`failures_zero` |

各 Stage 在登记表中声明的 `produces`（= 该 Stage 的 StagePackage `manifest.output_artifacts` 自述的 artifact_type 集合；LedgerPort 读不到 `artifacts.artifact_type`，见 §2 依据）：

| Stage | produces | 依据 |
|---|---|---|
| m1 | `source_manifest` | `fixture_ingest.py:43–47`、`expected/m1.stage_package.yaml` |
| m2 | `ocr_page_set` | 同上 |
| m3 | `corpus_package` | `corpus_compiler/step.py:329` |
| m5 | `validation_package` | `validation/step.py:264` |
| m8 | `publication_package` | `dataset_compiler/step.py:535` |
| 所有成功 StepRun | 恰 1 个 `stage_package` | `register_stage_package`（`service.py:753`） |

`consumes` 的 artifact_type 只进文档与指纹；Gate 只按 `from_stage` 判血缘。

### 6.2 对下游的输出契约

- `runner.execute_step(...)` 返回的 dict 逐字过 `step_result.schema.json`（§7 `execute(StepRequest) → StepResult`）。
- 上游 Gate 证据修订内容为 `json.dumps(gate, sort_keys=True, ensure_ascii=False)`，其中 `gate = {"kind": "stage_gate", "stage", "edition_part_id", "processing_run_id", "gate": "passed"|"blocked", "checks": {名: {"ok", "detail"}}, "effective_step_run_ids"}`（N-4 A）。
- 六项查询返回结构见 `act/06.yaml`；PendingQueue 五键逐字取自 §5:120–124 且恒存在。
- CLI 末行与退出码见 `act/06.yaml`；验收脚本行格式 `PASS <名>` / `FAIL <名> <原因>` / `BLOCKED <名> 前置缺失: <§19 行名>；<说明>`，末行 `SUMMARY`。

### 6.3 对并行 Module 草案的接口假设（主 Agent 对账用）

1. Module 以登记条目描述自己：`module_id`、`stage`、`kind`、`binding`、`entry`、`version`、`consumes[{artifact_type, from_stage}]`、`produces[{artifact_type}]`、`human_queue`、`supports_recovery`、可选 `entry_kwargs`、可选 `owns_processing_run`。
2. `step_request` 需暴露 `plan(port, *, edition_part_id, processing_run_id, technique_id, upstream) -> {"input_artifact_ids", "configuration"（含 "stage" 与 "module_id"）}` 与 `execute(port, request, context) -> StepOutcome`。
3. Module **不得**调用 `create_processing_run`/`begin_step_run`/`supersede_step_run`/`recover_from_checkpoint`/`finish_step_run`/`fail_step_run`/`await_human`/`resume`/`suspend`/`recover`（Orchestrator 独占），也**不得**访问 `store`/`objects`，只能使用 `LedgerPort` 闭集方法（`legacy_self_driving` 入口由 Orchestrator 经 `port.unwrap()` 传入直连服务，是唯一例外）。
4. 每个成功 StepRun 封存恰 1 个 StagePackage，过 L0 Schema，`validation.passed` 如实反映 Module 自带 Gate，并列入 `output_artifact_ids`。M5 的 ValidationPackage 若 `validation.passed=false`，Orchestrator Gate 必 blocked（P5 / §9 第 21 条）。
5. 冻结输入必须包含登记 `consumes` 中每个 `from_stage` 的上游有效运行产出修订。
6. 每完成一个 task 写一个 Checkpoint；需人工处理时返回 `awaiting_human` 与已封存 `pending_queue_artifact_ids`；恢复时从 `context.human_event_revision_ids` 读取事件；`supports_recovery=true` 的 Module 必须跳过 `context.recovery_plan["completed_task_ids"]`。
7. M7/M8 属 ReleaseRun；首切片只执行 M8（`legacy_self_driving`），M7 与多 Part 汇编 `DEFERRED`。

## 7. 目录（落地后）

```text
pipeline/contract_registry/
  __init__.py        REGISTRY_TOOL / REGISTRY_TOOL_VERSION
  errors.py          RegistryInvalid
  registry.yaml      声明式登记（L0 Schema、stage 行名、专用队列名、Module、端口与 Adapter）
  catalog.py         load_registry / Registry / check_registry / interface_fingerprint
  ports.py           LEDGER_PORT_METHODS / DirectLedgerAdapter / LedgerdClientAdapter / PortGuard
  conformance.py     normalize_outcome / substitution_report
  __main__.py        python -m pipeline.contract_registry check
  acceptance.py      §20.10 五项判定
  tests/
pipeline/orchestrator/
  __init__.py        ORCH_TOOL / ORCH_TOOL_VERSION / EDITION_STAGES / RELEASE_STAGES / FIRST_SLICE_EDITION_STAGES / DEFERRED_STAGES
  errors.py          OrchestratorRefused
  module.py          StepContext / validate_outcome / bind_module / 三种绑定
  stubs.py           StubModule（kind=stub）
  gate.py            effective_step_runs / evaluate_stage_gate（独立实现）
  runner.py          execute_step / finalize_outcome / run_legacy（§7 execute 落点）
  edition_run.py     start_edition_run / adopt_edition_run / advance / advance_release / run_until / edition_status
  human.py           record_human_event / resume / suspend / recover / reconcile_after_outage / rerun_from_checkpoint
  queries.py         六项只读查询
  suites.py          stub_edition_suite（存储端口一致性套件，ACT 08）
  __main__.py        python -m pipeline.orchestrator
  acceptance.py      §20.1 六项判定
  tests/
openspec/acceptance/orchestrator-gate.sh
openspec/acceptance/contract-registry.sh
openspec/acceptance/run_all.sh（仅 ACT 09：一个 accept_check 函数 + 20.1/20.10 case 体）
```

## 8. 分组与时序

- K1 = ACT 00–01（Registry 目录与端口）；K2 = ACT 02–04（Module 接口、Gate、EditionRun/release 段）；K3 = ACT 05–06（人工恢复、六项查询与 CLI）；K4 = ACT 07–08（`orchestrator-gate.sh`、`contract-registry.sh`）、ACT 09（`run_all.sh`）。
- 每组 `ACCEPTED` 后再派下一组。K1–K3 只用桩与假入口，不依赖 impl-02/03/04；K4 的 `real_chain_mini_ed01` 需 impl-02 `ACCEPTED`、impl-03 `ACCEPTED`、impl-04 `ACCEPTED`。
- **ACT 09 前置**：impl-04 ACT 08 已验收（P4：`run_all.sh` 每波至多一个写者；W3 内为 impl-04 ACT 08，W4-I 为其后唯一写者）。开工前确认无并发改 `run_all.sh`。
- `act/10.yaml`（Ledger 公开读方法）状态 `DEFERRED`，不在 `executor_groups` 内，见 §9 与 §4.1 D-6。

## 9. 纵切后 DEFERRED（保留文件内容，不入 `executor_groups`）

| 项 | 内容 | 推迟到 | 理由 |
|---|---|---|---|
| M4/M6/M7 Module 登记 | `registry.yaml` 增 `m4`/`m6`/`m7` 条目（impl-05/06/07） | 对应波次 | P1：首纵切不接；`DEFERRED_STAGES` 声明其为已声明缺口 |
| ReleaseRun 状态机 | §6.2 M7→M8 多 Part 汇编、`CanonicalKnowledgeSnapshot` | W5 及以后 | P1 + D-15：M8 首切片以 legacy 单步执行，非完整 ReleaseRun |
| `act/10.yaml` Ledger 公开读方法 | `frozen_inputs`、`artifacts.artifact_type`、按 `step_run_id` 取 sealed `stage_package` | 主 Agent 裁定后（D-6 B） | P9：本批不改 `pipeline/ledger/**` |
| M4/M6/M7 stub 登记表 | 桩 `kind=stub` 表仅存测试与验收场景 | 不需实现 | D-11 / §5.8：桩不得进生产登记表，`registered_modules_m1_m6` 不认桩 |
