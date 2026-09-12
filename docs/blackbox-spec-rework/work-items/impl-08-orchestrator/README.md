# impl-08：Local Orchestrator + Contract Registry（§5/§6.1/§7/§7.1/§17）首切片

状态：`DRAFT`（起草 Agent 2026-09-11；§4 共 18 条待主 Agent 裁决；未经 `wjt-react`；不含 PROMPT 与 ACCEPTANCE）

## 1. 目标

在 `pipeline/contract_registry/` 与 `pipeline/orchestrator/` 落地规格 §19 拓扑中的 L2 `Local Orchestrator` 与 L2' `Contract Registry` 的**最薄可用切片**：

1. **Contract Registry**：用声明式登记表记录四份 L0 Schema（路径、`schema_version`、sha256）、各 Stage 的 Module 描述（consumes/produces、绑定方式、入口）、端口与 Adapter；提供一致性检查，以及「同一端口换 Adapter 后相邻 Module 的 Interface 不变」的替换判定（§20 第 10 条）。
2. **统一 Module Interface 适配**：Orchestrator 把 §7 的 `execute(StepRequest) → StepResult` 落在 `runner.execute_step` 上。加工 Module 只需实现 `plan` / `execute`，返回 `StepOutcome`；由 Orchestrator 独占 StepRun 的建立与终态迁移。另设 `legacy_self_driving` 绑定，把 `run_m3` 这类自建 StepRun 的旧入口挂上来；再设 `imported` 绑定，只对 fixture 灌入的 M1/M2 做 Gate 判定，不执行。
3. **EditionRun**：按 m1→m6 逐阶段执行、独立判定 Stage Gate、阻断未完成任务向下游流动；支持人工队列挂起与恢复（`awaiting_human`/`resume_token`）、操作者暂停与基础设施对账（`suspended`/`recover`），并通过 Ledger 的 `recover_from_checkpoint` 从 Checkpoint 重跑。
4. **六项只读查询**（§5 闭集）：`RunStatus`、`StageProgress`、`PendingQueue`、`BlockingReasons`、`ReworkImpact`、`ThroughputEstimate`。
5. **可执行判据**：把 `run_all.sh` 中 20.1 与 20.10 的**硬编码 BLOCKED 改为计算得出**。能在宿主上判定的部分（桩模块串联、真实 m1–m3 串联、存储端口替换）必须先判定，并如实报 PASS/FAIL；缺前置 Module 的部分报 BLOCKED，写明首个缺失的 §19 行名。

完成判据（本批唯一的「做完」定义；前提是 impl-02 已 `ACCEPTED`，见 §8）：

```bash
export LC_ALL=en_US.UTF-8
bash openspec/acceptance/orchestrator-gate.sh; echo exit=$?
# 期望 6 行 + 末行：
#   PASS gate_blocks_incomplete
#   PASS gate_chain_stub_m1_m6
#   PASS edition_conjunction
#   PASS recovery_via_orchestrator
#   PASS real_chain_mini_ed01
#   BLOCKED registered_modules_m1_m6 前置缺失: M4 Knowledge Extraction；Local Orchestrator 已串联 m1–m3 Gate，m4–m6 未登记生产 Module
#   SUMMARY pass=5 fail=0 blocked=1
# exit=2
bash openspec/acceptance/contract-registry.sh; echo exit=$?
# 期望 5 行 + 末行：
#   PASS l0_schemas_verified
#   PASS registry_consistent
#   PASS storage_port_substitutable
#   BLOCKED modules_port_clean 前置缺失: Contract Registry；m3.corpus_structural 入口直接访问 Ledger 内部（…:行号 列表）
#   BLOCKED other_ports_adapters 前置缺失: Contract Registry；ocr/model/index 端口 Adapter 数不足 2
#   SUMMARY pass=3 fail=0 blocked=2
# exit=2
bash openspec/acceptance/run_all.sh 20.1 20.10
# 期望：BLOCKED  20.1  前置缺失: M4 Knowledge Extraction；Local Orchestrator 已串联 m1–m3 Gate，m4–m6 未登记生产 Module
#       BLOCKED  20.10  前置缺失: Contract Registry；m3.corpus_structural 入口直接访问 Ledger 内部（…）
bash openspec/acceptance/run_all.sh | tail -1     # SUMMARY pass=2 fail=1 blocked=8（条数不变；20.1/20.10 改为计算值）
```

**§20.1 从 BLOCKED 变 PASS 的路径**：本批完成后，20.1 的 BLOCKED 由 `registered_modules_m1_m6` 一项决定：取 m1–m6 中首个没有登记非桩 Module 的 Stage，报其 §19 行名。M4（首纵切后）、M5（impl-03）、M6 依次登记并通过真实链后，这一项自动转为 PASS；其余五项继续作为防回退判据。届时 `real_chain_mini_ed01` 的判定范围也从 m1–m3 扩到 m1–m6。**不改脚本，只改登记表**，20.1 就会变为 PASS；登记桩模块不计入（§5.8）。

**§20.10 从 BLOCKED 变 PASS 的路径**：需同时满足两点。其一，已登记的生产 Module 全部只经 `LedgerPort` 访问 Ledger（M3 迁移后 `modules_port_clean` 转 PASS）。其二，ocr/model/index/storage 四类端口各有 ≥2 个 Adapter，且一致性套件通过（§4 第 8 条口径待定）。

## 2. 依据（只读来源）

- 规格 `openspec/learn-system-blackbox-architecture.md`：
  - §2 原则 `:31–40`（单机、Module 只经 Artifact ID 交换、存储皆 Adapter）；
  - §5 总体组织 `:96–130`（Orchestrator 职责 `:116`，六项查询闭集 `:117–127`，五个专用队列逐字 `:120–124`，Contract Registry 职责 `:128`）；
  - §6.1 EditionRun `:136–151`（阶段推进条件 `:149`）、§6.2 ReleaseRun `:153–175`；
  - §7 统一 Module Interface `:177–207`（StepRequest 字段 `:187–193`，只读冻结输入 `:207`）；§7.1 `:209–226`（一个 StepRun 覆盖一个任务及其人工队列 `:211`，token `:215–220`，无自动超时 `:222`，suspended `:224`，进度事件 `:226`）；
  - §8 `:228–251`、§8.1 `prun_`/`srun_`/`pkg_` `:296–298`、§8.2 StepRun 状态与迁移 `:406–430`；
  - §10.1 M2 Gate `:482–494`、§11 M3 Gate `:521`、§13 M5 Gate `:606`、§14 M6 输出 `:631`、§14.1 失效传播与 ReworkImpact/阈值告警 `:633–645`；
  - §17 `:821–836`（suspended 对账 `:828`，事务序列 `:836`）、§17.1 StageCheckpoint `:838–846`（人工决定即时落盘 `:843`，恢复语义 `:845`）；
  - §19 拓扑 `:865–871`、差距行 `:883–885`、§19.0 判据表 `:899–918`（无 Orchestrator/Registry 行）；
  - §20 第 1 条 `:937`、第 10 条 `:946`；§21 非目标 `:949–956`；§22.3 分期 `:991–992`、§22.4 Orchestrator 不入首纵切 `:1000`。
- `openspec/id-prefix-registry.md:41–43`（`prun_`/`srun_` 生产者为 Local Orchestrator，`pkg_` 由各 Module 生产）、`:91–97`（不得新增前缀）。
- L0 Schema：`openspec/schemas/step_request.schema.json:5,34–41`（顶层 `additionalProperties:false`，**无 stage 字段**）；`step_result.schema.json:75–122`（`awaiting_human` 必带 `resume_token` 与 `pending_queue_artifact_ids`，其他状态禁带；`failed` 必须 ≥1 个失败修订）；`stage_package.schema.json`；`openspec/schemas/verify.sh`。
- Ledger（impl-01 ACCEPTED，只读引用、本批不改）：`pipeline/ledger/service.py`
  - `RUN_ARTIFACT_TYPES` `:66`、`_live_step_run` `:253–262`（只有 running/awaiting_human 可写）、`_configuration_stage` `:295–310`（stage 由配置修订内容推导）、`create_processing_run` `:319–345`（必须带 `edition_part_id`）；
  - `begin_step_run` `:405`、`supersede_step_run` `:412`、`register_stage_package` `:718–776`（artifact_type=`stage_package`、schema_id=`stage_package`）；
  - `await_human` `:885`、`record_human_event` `:922`、`resume` `:965`、`suspend` `:991`、`recover` `:1033`、`_seal_step_manifest` `:1082–1130`、`finish_step_run` `:1132`、`fail_step_run` `:1187`；
  - Checkpoint「阶段被 succeeded 运行封存后只有 supersedes 链可续写」`:1280` 附近、`recover_from_checkpoint` `:1430–1482`；`LedgerReader.read_object` `:1606`（`LedgerService` 无此方法）；
  - `pipeline/ledger/client.py:451`（`LedgerClient.read_object`）、`pipeline/ledger/store.py:78–86`（`processing_runs` 单 `edition_part_id`）、`pipeline/ledger/fixture_ingest.py:43–47,255–278`。
- M3（impl-02 返工中，只读引用）：`pipeline/corpus_compiler/step.py`（工作树版本）。`run_m3` 在 `:32–61` 自行解析输入，在 `:85–111` 自建配置与 StepRun，在 `:390,396` 直接访问 `service.objects`，在 `:472` 直接访问 `service.store.conn`。`docs/blackbox-spec-rework/work-items/impl-02-corpus/act/03.yaml:17` 许可了 `reader.store.conn` 只读 SELECT。
- 验收：`openspec/acceptance/run_all.sh:34–42`（`ledger_check` 模式）、`:160–179`（20.1 现行规则）、`:278–284`（20.10 现行规则）；`openspec/acceptance/m3-coverage.sh`（退出码纪律与规范 `verify.sh` 调用方式）。
- 现状：`pipeline/runner/run_task.py`（任务目录脚本 + mock/manual/API 三种模型调用，未接 Ledger，不是 Module Interface）；`pipeline/schemas/`（零散规范，§19 `:885`「Contract Registry 当前实现」）。

## 3. 范围

写（全部新建，另有标注的除外）：`pipeline/contract_registry/**`、`pipeline/orchestrator/**`、`openspec/acceptance/orchestrator-gate.sh`（ACT 07）、`openspec/acceptance/contract-registry.sh`（ACT 08），以及 `openspec/acceptance/run_all.sh`（ACT 09，只新增 `accept_check` 函数并改 20.1 与 20.10 两个 case 体）。

禁止：
- 不得改 `pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`openspec/schemas/**`、规格正文、`openspec/id-prefix-registry.md`、fixture 目录、`verify-T.sh`、`mutations.sh`、`PLAN.md`/`HANDOFF.md`/`SUBAGENT_TODO.md`，也不得改其他 work-items；
- 不得新增依赖（只用标准库 + PyYAML + jsonschema）、新增 ID 前缀（`module_id`、`port_id`、`adapter_id` 是登记表标签，不是 ID 家族）、调用模型 API；
- Orchestrator 与 Registry 不得 import 任何加工 Module 包，只能经 `importlib` 解析登记表中的 `entry`；`gate.py` 不得 import `runner.py`/`module.py`/`stubs.py`；
- 生产代码只读 Ledger 冻结修订，不读 fixture 路径（`acceptance.py` 经 `--fixture` 参数读取除外）；
- 生产登记表 `registry.yaml` 不得出现 `kind: stub`。

## 4. 待主 Agent 裁决

每条列出选项、「推荐」与理由；ACT 草案按「推荐」写成，裁决不同时须回改所列 ACT。

1. **StepRequest 缺 stage 字段**（`step_request.schema.json:5,34–41`；`service.py:295–310`；规格 `:187–193` 写的是「至少包含」）
   - A：维持现状，由配置修订内容的 `"stage"` 键推导；Orchestrator 另要求配置含 `"module_id"`，写入前校验 `config.stage == 登记 stage`；
   - B：L0 增加**可选** `stage` 字段，需同改规格 §7、Schema、`verify.sh` 示例、`mutations.sh`，并补 Ledger 交叉校验；
   - C：L0 增加**必填** `stage`，会破坏既有 fixture 常量与已灌入的 StepRequest。
   - 推荐 A。理由：本包无需 L0 变更即可闭环，B 会牵动 impl-01 已验收代码与三套回归门禁；若日后需要，B 应单独立 L0 包。影响 ACT 02/04。
2. **Module 入口控制反转**（规格 `:181–207` 要求 Orchestrator 下发 StepRequest；登记册 `:41–42` 规定 `srun_` 由 Orchestrator 生产；`step.py:85–111` 中 `run_m3` 自建配置与 StepRun）
   - A：本包仅用 `legacy_self_driving` 绑定挂接；
   - B：本包直接把 `run_m3` 改为 `plan`/`execute`，属于越界写 impl-02；
   - C：本包按 A 挂接，另为 impl-02 登记后续 ACT，迁移到 `step_request` 绑定。
   - 推荐 C。影响 ACT 04/07。
3. **StepRun 终态迁移归属**
   - A：Module 返回 `StepOutcome`，由 Orchestrator 转成 L0 StepResult，并调用 `finish_step_run`/`fail_step_run`/`await_human`；
   - B：Module 自行 finish，Orchestrator 事后读取。
   - 推荐 A。理由：规格 `:116` 把状态机归 Orchestrator；新 Module（impl-03 M5、M4、M6）只需实现产出，Gate 前的状态迁移集中在一处。影响 ACT 02/04 及所有并行 Module 草案。
4. **Stage Gate 报告是否落盘**（`RUN_ARTIFACT_TYPES` 仅含 configuration/technique_profile，`service.py:66`；终态 StepRun 不可再写，`:253–262`）
   - A：不落盘，每次查询重算；
   - B：Gate 通过后，把上游 Gate 报告写成下游新 StepRun 的首个 artifact（新 artifact_type `stage_gate_report`）。缺口是 legacy 绑定与最后一个阶段无处写，只能重算；
   - C：扩展 Ledger 的 `RUN_ARTIFACT_TYPES`，以 run 级封存，并作为下游冻结输入。
   - 推荐 B。理由：零 Ledger 改动，且留下「先过 Gate 才建下游 StepRun」的证据；C 的血缘最强，但要改 impl-01。影响 ACT 04/07。
5. **StageManifest 与 StepManifest**（规格 `:149,:840` 要求 StageManifest；Ledger 只有 `step_manifest`，`service.py:1082–1130`；同 Stage 被 succeeded 运行封存后第二个 StepRun 无法续写 Checkpoint，`:1280` 附近）
   - A：首切片按「一个 EditionPart × Stage 只有一条有效 StepRun（含 supersedes 链）」处理，以 `succeeded` 且 `result_json` 非空，代表 StepManifest 已原子封存（`finish_step_run` 同事务），从而视为 StageManifest；
   - B：Gate 通过后由 Orchestrator 另封存 `stage_manifest`，需要 run 级 artifact，即 C 类 Ledger 改动。
   - 推荐 A。等多任务阶段真实出现时，与 Ledger 的 Checkpoint 规则一并裁决。影响 ACT 03。
6. **Ledger 只读接口缺口**：没有 `get_processing_run`（查 kind/edition_part_id/technique_id），没有「按 StepRun 列修订」或「按修订查 artifact_type」，`LedgerService` 也没有 `read_object`（仅 `LedgerReader:1606` 与 `client.py:451` 有）
   - A：本包不改 Ledger。EditionRun 三元组由调用方提供并交叉校验；StagePackage 按 `get_revision()["schema_id"] == "stage_package"` 识别；`DirectLedgerAdapter` 自补 `read_object`；
   - B：在 Ledger 追加只读方法（`ledgerd` 会自动暴露）；
   - C：沿用 impl-02 先例，用 `reader.store.conn` 执行 SELECT，但这会破坏端口可替换性。
   - 推荐 A，B 列为 Ledger 后续包。影响 ACT 01/03/04。
7. **§20.1 PASS 是否计入 `imported`（fixture 灌入的 M1/M2）与 `legacy_self_driving`（M3）绑定**
   - A：计入（依 §22.3 `:991` 薄用），PASS 行说明披露绑定类型；
   - B：只计入 `step_request` 绑定。
   - 推荐 A。本批 20.1 仍 BLOCKED（M4–M6 缺），此项只影响未来何时转 PASS。影响 ACT 07。
8. **§20.10 判定口径**（`:946` 列举 OCR、模型、索引、存储四类 Adapter）
   - A：任一端口可替换即 PASS；
   - B：四类端口全部可替换才 PASS；
   - C：四类逐项判定，存储端口 PASS、其余不足者 BLOCKED，合成结果为 BLOCKED。
   - 推荐 C。理由：不可判定项不得写成 PASS，C 同时保留已证实部分的证据。影响 ACT 08。
9. **M3 入口越过端口访问 Ledger 内部**（`step.py:390,396,472`；`inputs.py` 的 SELECT 经 impl-02 `act/03.yaml:17` 许可），换用 `ledgerd` Adapter 后 M3 无法运行
   - A：20.10 判 FAIL；
   - B：`modules_port_clean` 报 BLOCKED（前置缺失: Contract Registry），逐条列出文件:行号，由 impl-02 后续 ACT 迁移到 LedgerPort；
   - C：本包直接改 M3（越界）。
   - 推荐 B，并在 impl-02 后续工作中登记迁移项。理由：这是端口约束首次成文，impl-02 当时获许可，不宜追溯判 FAIL。若主 Agent 认为已知缺陷不应以 BLOCKED 呈现，选 A，此时 `run_all` 的 fail 将变为 2。影响 ACT 08。
10. **§19.0 缺 Local Orchestrator / Contract Registry 两行判据**（表 `:903–918` 无此两行，但 §22.3 `:992` 要求「各行 §19.0 判据 exit 0」）
    - A：本包新建 `openspec/acceptance/orchestrator-gate.sh` 与 `contract-registry.sh`，由主 Agent 另立规格包登记进 §19.0；
    - B：不建脚本，只走 `run_all.sh 20.1/20.10`。
    - 推荐 A。影响 ACT 07/08。
11. **新 artifact_type 与配置键**：`stage_gate_report`（Gate 报告）、`failure_report`（沿用 M3 已用名，Orchestrator 以自身 producer 写入），配置 JSON 新增必含键 `module_id`
    - A：由 Registry 登记为已知 artifact_type，内容格式在 ACT contract 中逐字规定；
    - B：先出 JSON Schema 再使用。
    - 推荐 A。影响 ACT 04。
12. **登记表自身的契约与载体**
    - A：仓库内声明式 `pipeline/contract_registry/registry.yaml`（Git 跟踪），格式由 `check_registry` 规则定义，不出 JSON Schema；
    - B：新增 `openspec/schemas/contract_registry.schema.json`，需给 `verify.sh` 增项；
    - C：把登记表快照作为 Ledger 修订封存，并冻结为 StepRun 输入（与 §5 `:128`「canon/homographs 作为 M4 冻结输入」同路）。
    - 推荐 A，C 随 M4 接入 canon 时做。影响 ACT 00。
13. **进度事件**（`:226`）
    - A：以 StageCheckpoint 写入与 `step_run_events` 作为进度来源，不建新机制；
    - B：Ledger 新增 `progress` 事件 API。
    - 推荐 A。影响 ACT 06 与并行 Module 草案（每 task 必写 Checkpoint）。
14. **Edition 级合取的 Part 清单来源**（`:149,:937`；`store.py:78–86` 中一个 ProcessingRun 只绑一个 Part）
    - A：由调用方给出 Part 句柄清单，`edition_status` 做合取（本包用桩测）；
    - B：由 M1 SourcePackage 声明 Part 清单，Orchestrator 读取。
    - 推荐 A，B 随 M1 正式化。影响 ACT 04/07。
15. **ReleaseRun**（`:153–175`；`create_processing_run` 强制 `edition_part_id`，`service.py:319–327`；M7/M8 未实现）
    - A：本包只做 EditionRun（m1–m6），ReleaseRun 另立包，依赖 M7/M8 与 Ledger 放宽；
    - B：本包先做桩骨架。
    - 推荐 A。理由：没有真实消费者就定型骨架，接口会反复返工。**对 impl-04 M8 草案的假设**：M8 不在本包 EditionRun 串联内。
16. **ReworkImpact / ThroughputEstimate 口径**（`:126–127,:641–642`）
    - A：ReworkImpact 按 StepRun 粒度的血缘可达性估算（`estimate: true`，`needs_review_count` 取可达人工事件数，30% 比例阈值记为 `not_evaluated`）；ThroughputEstimate 按已 succeeded StepRun 的历时均值计算；
    - B：两项查询本包只返回 `not_evaluated` 占位。
    - 推荐 A。影响 ACT 06。
17. **人工决定后由谁写 Checkpoint**（`:843`；Ledger 补写逻辑见 `service.py:1400`）
    - A：Orchestrator 在 `record_human_event` 后复制本 StepRun 链上最新 Checkpoint、追加决定号并立即落盘；`pending_queue` 的缩减交给 Module 可选钩子 `resolve_pending`，默认不变；
    - B：Module 在 resume 时补写。
    - 推荐 A（满足「每次人工决定即时落盘」）。影响 ACT 05。
18. **与 impl-02 的时序**（`step.py` 正在返工，工作树有未提交修改）
    - A：K1–K3（ACT 00–06，只用桩与假入口）现在即可派发，K4（ACT 07–08）等 impl-02 `ACCEPTED` 后再派；
    - B：全部等待。
    - 推荐 A。

## 5. 设计要点（草案；§4 定案后转为「主 Agent 决定」）

1. **依赖方向**：`contract_registry` ← `orchestrator` → 各 Module。Module 由登记表 `entry` 经 `importlib` 解析，Orchestrator 源码不出现任何加工 Module 包名；测试与验收只经 `modules={module_id: 对象}` 注入桩。这样 Orchestrator 可与 M4/M5/M6/M8 并行开发，只依赖 §6 的接口约定。
2. **三种绑定**：
   - `step_request`：新 Module 的标准形态。Orchestrator 建 StepRun，Module 实现 `plan` + `execute`；
   - `legacy_self_driving`：Orchestrator 先判上游 Gate，再调用 `entry(service, edition_part_id)`，事后从 Ledger 读取该 StepRun，重建 StepResult 并校验 L0 Schema。它要求直连 Ledger（`port.unwrap()`），在 `ledgerd` Adapter 下拒绝执行；
   - `imported`：不执行，只判 Gate。
3. **§17 事务序列映射**（`step_request` 绑定）：
   - 创建 StepRun：Orchestrator 调用 `put_run_artifact(configuration)` 与 `begin_step_run`；
   - 冻结输入：`begin_step_run` 完成；
   - 验证输入 Contract：Module 在 `execute` 内部完成；
   - 执行、保存原始输出与日志、计算哈希、验证输出、记录 Transformation：Module 完成，经 `put_artifact`/`seal_revision`/`write_checkpoint`/`record_transformation`/`register_stage_package`；
   - 封存 StepManifest、写入最终状态：Orchestrator 调用 `finish_step_run`/`fail_step_run`/`await_human`；
   - Module 抛异常或 `StepOutcome` 违约时，由 Orchestrator 封存 `failure_report` 并调用 `fail_step_run`。
4. **advance 推导**：EditionRun 自身不另存状态，状态从 Ledger 事实推导，不引入 §8.2 之外的新状态轴。按 m1→m6 找到首个 Gate 未过的 Stage，再按下表处理：
   - 该阶段有 running/awaiting_human/suspended 的 StepRun：返回 `waiting`；
   - 有 failed 且无后继：返回 `blocked`，须显式重跑；
   - 全部 succeeded 但 Gate 未过：返回 `blocked`；
   - 无任务且未登记 Module，或绑定为 `imported`：返回 `refused`；
   - 否则执行一步，返回 `executed`；
   - m1–m6 全部通过：返回 `complete`。
   - 除 `executed` 外，一律零写入。
5. **Stage Gate 八项**（`gate.py` 独立实现，名称与顺序固定）：`tasks_present`、`all_tasks_succeeded`、`stage_package_valid`、`output_contract`、`validation_passed`、`failures_zero`、`no_pending_work`、`upstream_lineage`。前四项对应规格 `:149` 的「全部任务完成 / StageManifest 封存 / 输出 Contract 通过」；`validation_passed` 承接各 Module 自带 Gate（M2 `:490–494`、M3 `:521`、M5 `:606`）的判定结果；`upstream_lineage` 保证「未完成任务不能流入下一阶段」（`:937`）。
6. **人工恢复**：
   - `record_human_event`：写入事件，并立即写 Checkpoint；
   - `resume`：消费 token 后以 `mode="resumed"` 再次调用 `execute`，只带最初冻结的输入与已登记事件（`:220`）；
   - `suspend`：来源为 operator；
   - `reconcile_after_outage`：把非终态的 running 转为 `suspended(infrastructure)`，是否继续由操作者决定（`:828`）；
   - `rerun_from_checkpoint`：走 Ledger `recover_from_checkpoint`，已完成任务不重做（`:845`）；
   - 全程没有超时自动失败（`:222`）。
7. **Contract Registry 与 §20.10**：端口闭集为 `ocr`/`model`/`index`/`storage`。`LedgerPort` 方法闭集以 `LedgerClient` 公开方法为准，存储端口的两个 Adapter 为 `DirectLedgerAdapter`（LedgerService）与 `LedgerdClientAdapter`（ledgerd + LedgerClient）。替换判定分三步：同一桩套件在两个 Adapter 上跑出**去 ID、去时间**的规范化结果须相等；相邻 Module 的 `interface_fingerprint`（consumes/produces + 四份 L0 Schema 哈希）须相同；Module 源码不得越过端口。「无第二 Adapter」按端口逐个计算，不再硬编码。
8. **桩隔离**：桩的 `kind` 恒为 `stub`，只在测试与验收场景内以 `Registry.from_dict(..., allow_stub=True)` 构造。`registered_modules_m1_m6` 只认生产登记表中的非桩 Module；生产登记表出现桩时，`check_registry` 报 `stub_in_production`。

## 6. 接口契约

### 6.1 上游输入契约（Orchestrator 读取的 Ledger 事实）

| 来源 | 字段 / 读法 | 用途 |
|---|---|---|
| `get_step_run(srun)` | `stage`、`status`、`status_version`、`request_json.input_artifact_ids`、`result_json.output_artifact_ids`/`failure_artifact_ids`、`supersedes_step_run_id`、`created_at`/`updated_at` | 有效 StepRun、Gate、血缘估算、吞吐 |
| `run_status(prun)["step_runs"]` | 本运行全部 StepRun | 按 stage 分组 |
| `list_step_run_events(srun)` | `await_human.payload.pending_queue`、`human_event.payload.event_revision_id`、`suspended.from_status` | PendingQueue、resume 上下文 |
| `latest_checkpoint(ep, stage)` / `list_checkpoints` | `completed_tasks`、`human_decisions`、`pending_queue`、`next_pointer`、`step_run_id` | `no_pending_work`、重跑计划、人工决定落盘 |
| `get_revision(rev)` + `read_object(sha256)` | `status`、`schema_id`、`step_run_id`；StagePackage 内容 JSON | Gate 识别并校验 StagePackage |
| StagePackage 内容（L0） | `stage`、`status`、`manifest.processing_run_id`/`step_run_id`/`output_artifacts[].artifact_type`、`validation.passed`、`failures` | `stage_package_valid`/`output_contract`/`validation_passed`/`failures_zero` |

各 Stage 在登记表中声明的 produces（artifact_type）：

| Stage | produces |
|---|---|
| m1 | `source_manifest` |
| m2 | `ocr_page`、`ocr_page_set`、`human_event` |
| m3 | `corpus_package`、`corpus_spans`、`coverage_report` |
| 所有成功 StepRun | 恰 1 个 `stage_package` |

以上与 `fixture_ingest.py:43–47`、`_stage_tasks`、`step.py` 一致；m4–m6 由各 Module 包在登记时声明。

### 6.2 对下游的输出契约

- `runner.execute_step(...)` 返回的 dict **逐字过** `step_result.schema.json`（§7 的 `execute(StepRequest) → StepResult`）。
- `stage_gate_report` 修订内容为 `json.dumps(gate, sort_keys=True, ensure_ascii=False)`，其中 `gate = {"stage", "edition_part_id", "processing_run_id", "gate": "passed"|"blocked", "checks": {检查名: {"ok", "detail"}}, "effective_step_run_ids"}`。
- 六项查询的返回结构见 `act/06.yaml`。PendingQueue 的五个键逐字取自规格 `:120–124`，且恒存在。
- CLI 末行与退出码见 `act/06.yaml`；验收脚本行格式为 `PASS <名>` / `FAIL <名> <原因>` / `BLOCKED <名> 前置缺失: <§19 行名>；<说明>`，末行 `SUMMARY`。

### 6.3 对并行 Module 草案的接口假设（主 Agent 对账用）

1. Module 以登记表条目描述自己：`module_id`、`stage`、`kind`、`binding`、`entry`、`version`、`consumes[{artifact_type, from_stage}]`、`produces[{artifact_type}]`、`human_queue`（布尔）、`supports_recovery`（布尔）。
2. `step_request` 绑定需暴露两个方法：
   - `plan(port, *, edition_part_id, processing_run_id, technique_id, upstream) -> {"input_artifact_ids": [...], "configuration": {...含 "stage" 与 "module_id"}}`，其中 `upstream = {stage: [有效 succeeded StepRun 的 dict]}`；
   - `execute(port, request, context) -> StepOutcome`。
3. Module **不得**调用 `create_processing_run`、`begin_step_run`、`supersede_step_run`、`recover_from_checkpoint`、`finish_step_run`、`fail_step_run`、`await_human`、`resume`、`suspend`、`recover`，这些由 Orchestrator 独占；也**不得**访问 `store`/`objects`，只能使用 `LedgerPort` 闭集方法。
4. 每个成功 StepRun 封存恰 1 个 StagePackage：`stage` 等于本阶段，过 L0 Schema，`validation.passed` 如实反映 Module 自带 Gate，并列入 `output_artifact_ids`。M5 的 ValidationPackage 若 `passed=false`，Orchestrator Gate 必然 blocked。
5. 冻结输入必须包含登记 consumes 中每个 `from_stage` 的上游有效 StepRun 产出修订。
6. 每完成一个 task 写一个 Checkpoint；需要人工处理时返回 `awaiting_human` 与已封存的 `pending_queue_artifact_ids`。恢复时从 `context.human_event_revision_ids` 读取事件；`supports_recovery=true` 的 Module 必须跳过 `context.recovery_plan["completed_task_ids"]`。
7. M7/M8 属 ReleaseRun，不在本包串联内（§4 第 15 条）。

## 7. 目录（落地后）

```text
pipeline/contract_registry/
  __init__.py        REGISTRY_TOOL / REGISTRY_TOOL_VERSION
  errors.py          RegistryInvalid
  registry.yaml      声明式登记（L0 Schema、stage 行名、专用队列名、Module、端口与 Adapter）
  catalog.py         load_registry / Registry / check_registry / interface_fingerprint
  ports.py           LEDGER_PORT_METHODS / DirectLedgerAdapter / LedgerdClientAdapter / PortGuard
  conformance.py     normalize_outcome / substitution_report
  suites.py          stub_edition_suite（存储端口一致性套件，ACT 08）
  __main__.py        python -m pipeline.contract_registry check
  acceptance.py      §20.10 五项判定
  tests/
pipeline/orchestrator/
  __init__.py        ORCH_TOOL / ORCH_TOOL_VERSION / EDITION_STAGES
  errors.py          OrchestratorRefused
  module.py          StepContext / validate_outcome / bind_module / 三种绑定
  stubs.py           StubModule（kind=stub）
  gate.py            effective_step_runs / evaluate_stage_gate（独立实现）
  runner.py          execute_step / finalize_outcome（§7 execute 落点）
  edition_run.py     start_edition_run / adopt_edition_run / advance / run_until / edition_status
  human.py           record_human_event / resume / suspend / recover / reconcile_after_outage / rerun_from_checkpoint
  queries.py         六项只读查询
  __main__.py        python -m pipeline.orchestrator
  acceptance.py      §20.1 六项判定
  tests/
openspec/acceptance/orchestrator-gate.sh
openspec/acceptance/contract-registry.sh
openspec/acceptance/run_all.sh（仅 20.1、20.10 case 体）
```

## 8. 分组与时序

- K1 = ACT 00–01（Registry 目录与端口），K2 = ACT 02–04（接口、Gate、EditionRun），K3 = ACT 05–06（人工恢复、查询与 CLI），K4 = ACT 07–08（真实链验收、Registry 验收、`run_all.sh`）。
- 每组 `ACCEPTED` 后再派下一组。K1–K3 只用桩与假入口，不依赖 impl-02；K4 依赖 impl-02 `ACCEPTED`（§4 第 18 条）。
