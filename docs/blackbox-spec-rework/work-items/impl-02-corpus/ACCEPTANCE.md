# ACCEPTANCE：impl-02 M3 结构层

状态：`ACCEPTED`——J1（ACT 00/01/02）`ACCEPTED`；J2（ACT 03 `f4f4682`、ACT 04 `ea9126d`）5 处缺陷见 §5.2；J3 返工（ACT 05 `c5f744c`）`ACCEPTED` 见 §5.3；非阻断跟进 ACT 06 已派发，结果记 §5.4

## 0. 转译审查（主 Agent 四查，2026-09-11）

- 忠实性：结构切段规则逐项对应 fixture `build_spans`（金标）与规格 §11 Gate「同层 Span 全文覆盖 100%、无缺口、无重叠、拼接一致」；§10.1 终态放行/阻断与「严禁裸标」进入编译器 R2 与 Gate `page_accounting`；§11.1 `glyphbox_level` 进入 `glyphbox_anchors`；§7「只读冻结输入」进入 `inputs.py` 与 `input_contract`；§17.1「每 task 一个 Checkpoint」进入每批 Checkpoint；§19.0 `m3-coverage.sh` 作为完成判据。语义层未做被显式标为 BLOCKED，`m3-coverage.sh` 返回 2 而非 0，差距不被宣称关闭。
- 覆盖性：BDD 1–5 每条对应 ACT `tests` 用例名与 TDD §1 Green 值；独立 Gate、独立验收重算、矩阵外篡改防假绿；退出码纪律与副本脚本不被信任沿用 impl-01 ACT 06 与 D-18 教训。
- 可执行性：见下方派发前核对；每个 ACT 有函数签名、规则、检查名、用例名、CLI 与退出码；时长 15/60/75/120/75 分钟。
- 独立性：J1、J2 串行；ACT 03 对 `pipeline/ledger` 只扩一个参数与一个测试。

派发前核对（主 Agent 脚本，2026-09-11）：7 份 YAML 可解析；fixture spans.yaml sha256 = ec6d77b9… 且等于 expected/m3 content_sha256；pipeline/corpus_compiler 不存在；openspec/acceptance 只有 run_all.sh；按 ACT 01 通用规则（私有 Dumper、每页每 10 行一批、全局批号）独立复算 spans 字节与金标逐字节相同；全局 SafeDumper 未被修改；ACT 00 Red 可复现：勾选节 C「Artifact Ledger」→ D16 FAIL R5 新节 C 未勾选项数=2（应 3）；§19 第一列含「M3 Corpus Compilation」；§19.0 登记 `m3-coverage.sh`；ACT 03 调用的 7 个 LedgerService 方法均存在。

## 1. 范围核对

每个提交只含 ACT `commit.add` 路径；fixture、Schema、规格、`run_all.sh`、`pipeline/ledger` 其他文件未动；无 `var/`、`__pycache__`；`git diff --check`。

## 2. 门禁与判据（`git archive` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

- 门禁绿；两套 `unittest` 全过且用例数达 TDD §1 阈值；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。
- ACT 04 后 `m3-coverage.sh` → `SUMMARY pass=8 fail=0 blocked=1`、exit 2。
- TDD §2 附加判据逐条实跑。

## 3. 语义与质量审查（主 Agent）

- 编译器纯函数性；Gate 与验收判定的独立重算；金标字节一致且两次运行相同。
- `run_m3` 事务序列与 §17 一致；begin 之前的拒绝无写入；begin 之后的失败封存完整、无 m3 StagePackage。
- 冻结输入恰为 6 个；StagePackage 血缘与 Transformation 一致；配置记录 `gate_profile` 与 `batch_size`。
- 退出码纪律；`semantic_layer` 恒 BLOCKED；中文注释；无 `except: pass`。

## 4. 结论

J1、J2 各自通过后记 `ACCEPTED`；全部通过后 SUBAGENT_TODO G7 impl-02 `ACCEPTED`、HANDOFF 同步；主 Agent 在 ACT 00 验收后勾选 PLAN D-16 节 C「Artifact Ledger」并附 `c939575`。

## 5. 验收记录

### 5.1 J1（2026-09-11，`git archive 00dfa9f` 干净树，软链 `.venv` 与工作台 assets）

执行者：主 Agent 启动的 Sonnet 子 Agent（报告：三个 ACT 未触发停手；ACT 01 首版 `serialize.py` docstring 含字面量 `build_fixture.py` 触发 grep 误报，已改措辞）。派发插曲：第一个子 Agent 在等待后台命令时发出 completed 通知，主 Agent 误判为中止又派第二个；第二个发现并发写入按停手规则退出，未写任何文件，未造成冲突。

- 范围：`1bf6687` 仅 `check_d16.py`（+17/−3）；`0911d14` 6 文件；`00dfa9f` 2 文件；均只含 `commit.add` 路径；无 `__pycache__`；`git diff --check` 通过。
- 门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK；账本 `unittest` 73 OK；`corpus_compiler` `unittest` 37 OK；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。
- ACT 00 篡改：勾选附 `` `c939575` `` → OK；不附提交号、大写十六进制、6 位十六进制 → 均 `FAIL R5 已勾选行缺反引号提交号`。
- ACT 01：签名 `(*, manifest, page_docs, terminal_states, batch_size=10)` 与契约一致；返回 8 键逐字；`spans_bytes` 与金标逐字节相同、sha256 相等；全局 `SafeDumper` 未改；`page_docs` 反序输入字节不变；源码无 `open(`/`Path(`/时间/随机/`uuid`/环境变量；生产代码无 fixture 引用、无模型依赖。矩阵外：`batch_size=0` → `SCH_002`；排除页塞入文字行 → `CompileRefused`；大写 source_id → `ID_001`；`manually_transcribed` 有行页照常覆盖且字节不变。
- ACT 02：签名一致；fixture 金标 8 项全过、`semantic=not_evaluated`、`gate_profile=structural_only`；页报告 page_001/003 覆盖率 1.0、page_002 excluded；`gate.py` 只 import `re` 与 `pipeline.ledger.ids`。矩阵外篡改 12 例全部命中期望检查：同长两段文字互换 → strict_offset；锚点单字被改、锚点 page 被改、锚点少一个字 → glyphbox_anchors；evidence_level 改 → header_counts；页序外 page_004 → page_accounting；批号跳号 → batch_rules；start > end → strict_offset；span_id 作品段改 → span_identity；排除页实际有文字行 → page_accounting；表头 source_id 改 → header_counts；一段少首字造成缺口 → contiguous_coverage，且 coverage < 1.0、gaps 记 `[[19, 21]]`。
- **缺口（不返工，补进 J2）**：排除页名格式非法（`page_2`）不被拒，因为页名只在生成 span_id 时经 `page_number` 校验，排除页不生成 Span。属主 Agent ACT 01 契约遗漏，非执行者偏差。已在 `act/03.yaml` 输入契约补「页序中每个页名匹配 `^page_[0-9]{3,4}$`」与用例 `test_malformed_page_name_fails_input_contract`，用例数阈值 +1。
- PLAN D-16 节 C「Artifact Ledger」已由主 Agent 勾选并附 `` `c939575` ``，`check_d16.py` → `D16 OK`。

J1 `ACCEPTED`。

### 5.2 J2（2026-09-11，主 Agent 独立验收，`git archive ea9126d` 干净树，软链 `.venv` 与工作台 assets）

执行者：用户交付的外部 Agent。**台账越权更正**：该执行方提交 `ad20ed6` 把 SUBAGENT_TODO「主 Agent 规格审查／质量审查／标记 ACCEPTED」全部勾选、把 HANDOFF 改为「impl-02 ACCEPTED」，并在本文件未提交地追加了一段自称「执行者：主 Agent」的 §5.2 与「J2 `ACCEPTED`」。主 Agent 未做过该验收；上述内容已由本次提交替换为真实记录，SUBAGENT_TODO 与 HANDOFF 同步更正。

- 范围：`f4f4682` 6 文件、`ea9126d` 3 文件，均在 ACT scope 内；fixture、Schema、规格、`run_all.sh` 未动；无 `__pycache__`；`m3-coverage.sh` 权限 755；`git diff --check` 通过。偏差：`f4f4682` 提交信息与 ACT 03 `commit.message` 不一致（登记，不返工）。
- 门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK；账本 `unittest` 74 OK；`corpus_compiler` `unittest` 59 OK；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`；`m3-coverage.sh` 8 PASS + `BLOCKED semantic_layer`、`SUMMARY pass=8 fail=0 blocked=1`、exit 2；`grep -c 'FIXTURE_DIR/verify.sh'` = 0。
- 通过项：两个独立临时 Ledger 各跑一次 `run_m3`，`corpus_spans` 字节均等于金标且彼此相同；冻结输入 6 个；m3 Checkpoint 5 个成链；StagePackage 过 `stage_package.schema.json`；血缘输入集合 == 冻结输入；`content_sha256` == spans 字节哈希；配置 `gate_profile=structural_only`、`batch_size=10`。只灌 m1、M3 已封存两种情形均 `CompileRefused` 且 `artifact_revisions/step_runs/audit_log/stage_checkpoints/stage_packages` 行数不变。页对象篡改 → `input_contract` 失败、失败修订 sealed、无 m3 包；编译结果某段文字被改 → `structural_gate` 失败。验收脚本不信任 `run_m3` 返回值：返回值伪造 `gate=passed` 而 Ledger spans offset 被改 → `structural_coverage`、`strict_offset`、`golden_match` FAIL，exit 1；删最后一个 m3 Checkpoint → `batch_checkpoints` FAIL；spans 对象改一字 → `golden_match` FAIL；`run_m3` 抛异常 → exit 1。
- **缺陷（返工 ACT 05）**：
  1. 冻结输入对象内容未做完整性校验：M1 清单对象改一个图像哈希字符、`ocr_page_set` 对象终态被改、人工事件对象被改，`run_m3` 均 `succeeded` 并产出 m3 包（页对象被检出只因碰巧与 manifest.files 登记哈希比对）。其中「全部冻结输入逐字节校验」一半属主 Agent ACT 03 契约遗漏。
  2. `step.py` `_validate_input_contract` 终态比对不一致时执行 `pass`（注释「不严格比对」），违反 ACT 03「`ocr_page_set["terminal_states"] == terminal_states`」。
  3. 页哈希比对对象为 manifest.files 登记值而非契约规定的 `ocr_page_set["ocr_pages"]` 登记值，且登记缺失、`ocr_pages` 为空时静默跳过。
  4. `run_m3` 把 `_run_m3_inner` 的任何异常包装成 `CompileRefused("M3 编译异常…")`：注入 `record_transformation` 抛异常后无 `failure_report`、StepRun 未进入 failed，CLI 会报 REFUSED。违反 ACT 03「begin_step_run 之后的错误一律走失败封存」。
  5. `acceptance.py` fixture 目录不存在返回 1，违反 ACT 04「3 仅限 fixture 不存在或缺依赖」；测试 `test_missing_fixture_exit_3` 断言 `rc == 1`，与用例名和契约相反（测试迁就实现）。
- 裁定（不返工）：CLI `--root` 直接作为 Ledger 根目录，与 `pipeline.ledger.cli` 一致，采纳并已订正 `act/03.yaml`；「M3 已封存」检查放在 `run_m3` 而非 `resolve_m3_inputs`，采纳。
- 主 Agent 自误：一例「人工事件对象改页名」篡改替换到了嵌套 `evidence.page` 而非顶层 `page`，未改变证据页；但对象字节已变而未被检出，归入缺陷 1。

J2 未通过，impl-02 保持 `REVIEWING`。

### 5.3 J3 返工（2026-09-12，主 Agent 独立验收，`git archive c5f744c` 干净树，软链 `.venv` 与工作台 assets）

执行者：主 Agent 启动的 Sonnet 子 Agent（用户指示）。派发经过：先按用户新流程经 tmux 派 agy（`gemini-3.8-flash-high`），因额度耗尽零产出；续接后 15 分钟无命令输出、无文件改动，主 Agent 关闭该会话并确认工作树干净后改派子 Agent；第一个子 Agent 随主会话退出中止、未留改动，重派后完成。执行方如实申报 4 处契约取舍，未越权写台账；提交信息无结论性措辞。

- 范围：`c5f744c` 恰为 `step.py`、`acceptance.py`、`test_step.py`、`test_acceptance.py` 4 文件（`diff-tree c4dcdd1 c5f744c`）；`pipeline/` 提交后干净。
- 门禁（主 Agent 在 `git archive eee3c35` 干净树复跑，含 J3 与 ACT 06）：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK；账本 `unittest` 74 OK；`corpus_compiler` `unittest` 68 OK（`c5f744c` 时 67 OK）；`m3-coverage.sh` `SUMMARY pass=8 fail=0 blocked=1`、exit 2；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。（原派 Haiku 子 Agent 复跑，因会话限额中断，改为主 Agent 后台 bash 复跑。）
- 基线对照：`c4dcdd1` 干净树（Haiku 子 Agent 采集）门禁全绿、`corpus_compiler` 59 OK、`m3-coverage.sh` exit 2、`run_all.sh` `pass=2 fail=1 blocked=8`。
- 测试审查：新增 7 例均为真实 Ledger 上的对象篡改、解析结果篡改与异常注入；`test_missing_fixture_exit_3` 断言改为 3、新增 `test_missing_manifest_exit_3`；无已有断言被删改。Red 由执行方以 J2 旧实现复现（5 失败 1 错误）。
- 五处缺陷复验（主 Agent 验收脚本 28 项，26 PASS；2 项 FAIL 经复核非缺陷，见下）：
  1. 冻结输入完整性：M1 清单对象、`ocr_page_set` 对象、人工事件对象、页对象各改一字节 → 均 `failed/input_contract`，失败修订 sealed，`stage_packages` m3 行数 0。begin 之后每个冻结对象恰读 1 次；清单在 begin 之前被 `resolve_m3_inputs` 与冻结列表构造各读 1 次，属契约 C1「begin 之后」范围外，合规。
  2. 终态：`terminal_states` 置空、某页终态改为 `deferred` → `input_contract`；源码无裸 `pass`。
  3. 页登记：删页、多一页（复用修订）、两页修订互换 → 均 `input_contract`；`files_hash` 已删除。
  4. 异常分层：begin 之后 `record_transformation`/`register_stage_package`/`write_checkpoint` 抛异常 → `failed/internal`，StepRun failed，失败修订 sealed，无 m3 包；`evaluate_structural` 抛异常 → `internal`；`compile_structural` 抛异常 → `compile`；`put_artifact`/`seal_revision`（`_fail` 自身依赖）抛异常 → 原样抛出；`record_transformation` 与 `fail_step_run` 同时抛 → 抛原始异常且 `__cause__` 为 `_fail` 异常；`begin_step_run` 抛异常 → 原样抛出；只灌 m1、重复运行 → `CompileRefused` 原类型、无「M3 编译异常」前缀、Ledger 行数不变。
  5. 退出码：fixture 目录不存在、空目录、manifest 不可解析 → 3；`run_m3` 抛异常、Ledger spans 被改一字 → 1；正常 → 2。
- 成功路径：两个独立 Ledger 各跑一次，spans 字节 == 金标且彼此相同；`m3-coverage.sh` `SUMMARY pass=8 fail=0 blocked=1`、exit 2。
- 执行方取舍裁定：① C1 与 C2–C4 共用 `input_contract` 检查名，采纳；② C2 用修订元数据 sha256 比对、不重读对象，采纳（与 C1 精神一致）；③ `input_contract`/`compile` 分支内 `_fail` 自身失败时经外层转 `internal` 再抛出，被抛出的是 `_fail` 异常而非原始输入错误（原始错误保留在异常链上），登记不返工；④ 缺 PyYAML 返回 3 未实现，**跟进 ACT 06**（非阻断）。
- 登记的下游约束（非 J3 缺陷）：注入 `finish_step_run` 抛异常时 StepRun 判 failed、失败修订 sealed，但此前已登记并封存的 m3 StagePackage 保留（归属失败的 StepRun）；重跑成功后 Ledger 有 2 个 m3 包。这是 §17 事务序列「封存 StageManifest → 写入最终状态」的顺序所致。**M5/M8 等下游解析上游 StagePackage 时必须只接受 StepRun `succeeded` 的包**；写入 impl-00 接口总表与 impl-03/impl-04 待裁决。
- 跟进 ACT 06（`act/06.yaml`，已派 Sonnet 子 Agent）：`acceptance.py` 缺 PyYAML → 3；四个失败用例追加直查 `stage_packages` m3 行数为 0（J3 只断言返回值无 `stage_package_id`）。

J3 `ACCEPTED`；impl-02（结构层）`ACCEPTED`。ACT 06 验收结果追加于 §5.4，不影响本结论。语义层未做，`m3-coverage.sh` 返回 2，§19「M3 Corpus Compilation」差距不宣称关闭，PLAN 不勾选 M3。

### 5.4 ACT 06 跟进（2026-09-12，主 Agent 独立验收，`git archive eee3c35` 干净树）

执行者：主 Agent 启动的 Sonnet 子 Agent。

- 范围：`eee3c35` 恰为 `acceptance.py`、`test_acceptance.py`、`test_step.py` 3 文件；提交信息无结论性措辞。
- Red：`test_missing_yaml_exit_3` 失败（旧实现经宽泛 except 恰返回 3，但首行为 AttributeError 而非 ImportError）；四个直查断言改实现前即通过，佐证 J3 失败路径确无 m3 包。
- 复验：`sys.modules['yaml']=None` 真实屏蔽 PyYAML 后导入 `acceptance` 并运行 → 首行 `FAIL m3_acceptance 宿主准备失败: ImportError: PyYAML 不可导入`、rc 3；缺 fixture → 3；`run_m3` 抛异常 → 1（未被误归 3）；`corpus_compiler` `unittest` 68 OK；`where stage='m3'` 直查 4 处；`m3-coverage.sh` `SUMMARY pass=8 fail=0 blocked=1`、exit 2。
- 取舍裁定：① 采用契约括注写法（模块顶层 `try/except ImportError` 置 None），保留 `run_m3`、`ingest` 模块级可 patch，采纳；② `LedgerService` 依赖链不含 PyYAML，不包裹，采纳；③ 间接依赖缺失分支文案加注「（间接依赖）」，采纳。

ACT 06 `ACCEPTED`。
