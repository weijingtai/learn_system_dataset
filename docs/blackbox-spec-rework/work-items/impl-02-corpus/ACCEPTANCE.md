# ACCEPTANCE：impl-02 M3 结构层

状态：J1（ACT 00/01/02）`ACCEPTED`（`1bf6687`、`0911d14`、`00dfa9f`，见 §5）；J2 `READY`（ACT 03 已补页名检查）

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
