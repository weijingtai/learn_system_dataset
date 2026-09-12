# TDD：impl-03 M5 首切片

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；`TV="$PY -m unittest discover -s pipeline/validation/tests -t ."`；在仓库根运行。

## 0. 开工基线（K1、K2、K3 各一次）

```bash
git status --short pipeline/validation openspec/acceptance pipeline/corpus_compiler pipeline/ledger   # 空
ls pipeline/validation 2>/dev/null | grep -v __pycache__ | wc -l     # K1: 0；K2: 11（ACT 00–03 的 10 个文件 + tests）；K3: 16
ls openspec/acceptance                                              # K1/K2: m3-coverage.sh run_all.sh；K3 同
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1   # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                 # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py     # D16 OK
$TL 2>&1 | grep -E '^(Ran|OK)'                                      # OK（≥ 74）
$TC 2>&1 | grep -E '^(Ran|OK)'                                      # OK（≥ 67，impl-02 J3 已合入）
grep -cE '^\s+pass\s*$' pipeline/corpus_compiler/step.py            # 0（J3 返工已落地；非 0 → 停手上报，不得开工）
bash openspec/acceptance/m3-coverage.sh | tail -1; echo exit=$?     # SUMMARY pass=8 fail=0 blocked=1；exit=2
bash openspec/acceptance/run_all.sh | tail -1                       # SUMMARY pass=2 fail=1 blocked=8
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml         # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
```

## 1. 逐 ACT 的 Red → Green

每个 BDD 场景与 ACT `tests` 用例名、本表的对应关系见 `BDD.md` §8。

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TV` → ImportError | `$TV` OK，用例 ≥ 10；注册表 14 项；`fixture_context()` 43 条 Span、17 个修订 |
| 01 | 新增用例全 ERROR | `$TV` OK ≥ 26；fixture 上 G1 发现恰 4 条（2 `unresolved_glyph` + 2 `unproofread_glyphs`） |
| 02 | 新增用例全 ERROR | `$TV` OK ≥ 40；fixture 上 G2 发现 0；`g2_coverage.py` 无 `corpus_compiler` |
| 03 | 新增用例全 ERROR | `$TV` OK ≥ 57；fixture 上 G3 发现恰 3 条；`g3_evidence.py` 无 `corpus_compiler` |
| 04 | 新增用例全 ERROR | `$TV` OK ≥ 63；真实链路冻结 17 个；M3 StepRun 为 failed 时拒绝并抛 ValidationRefused；拒绝时 Ledger 行数不变 |
| 05 | 新增用例全 ERROR | `$TV` OK ≥ 75；`run_m5` succeeded、14 Checkpoint、`level_verdicts {passed, failed, failed}`；`$TL`、`$TC` 用例数不变 |
| 06 | `m5-evidence-gate.sh` 不存在（exit 127）；新增用例全 ERROR | `$TV` OK ≥ 84；脚本 `SUMMARY pass=9 fail=0 blocked=5`、exit 2；`run_all.sh` 与 `m3-coverage.sh` 末行不变 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/00–06 contract 中的函数名、参数名、返回键、validator_id、检查名、artifact_type 在实现中逐字存在
# 独立性：
grep -rnE 'corpus_compiler' pipeline/validation/g1_source.py pipeline/validation/g2_coverage.py pipeline/validation/g3_evidence.py | wc -l   # 0
grep -rnE 'corpus_compiler' pipeline/validation --include='*.py' | grep -vE '/tests/|replay.py|inputs.py|acceptance.py' | wc -l          # 0
grep -nE 'from pipeline\.validation\.(g1_source|g2_coverage|g3_evidence|replay)|import (g1_source|g2_coverage|g3_evidence|replay)' pipeline/validation/acceptance.py | wc -l   # 0
# 不改输入：run_m5 前后，M1–M3 全部修订的 status、sha256 与 artifact_revisions 行数（除 M5 新增行外）不变
# 不读 fixture：pipeline/validation 非 tests 文件不出现 "_fixture"（acceptance.py 只经 --fixture 参数除外）
# 不调模型：grep -rE '^\s*(import|from) (requests|openai|anthropic|httpx)' pipeline/validation | wc -l   # 0
# 错误码闭集：registry.CHECK_CODES 的值 ⊆ ERROR_CODES ∪ {None}；缺口清单见 README §5.5
# artifact_type 闭集：本包新类型仅 gate_results、validation_package（先由 W2-C 登记入 INTERFACES §4）
grep -rnE '"(validator_report|gate_report)"' pipeline/validation --include='*.py' | wc -l   # 0
# 新内容 schema_version：gate_results / validation_package / Validator 报告恒 "0.1.0-draft"（P3）
# §9 第 21 条：m5 StagePackage validation.passed 如实等于 gate.passed；gate 未过时 StepRun 仍 succeeded 但下游不得放行
# 矩阵外篡改（主 Agent 自定，不预告）：页 JSON、终态、人工事件、批次、m3 包 ArtifactRef、m3 配置、字框坐标各至少 1 例，M5 必须命中且不得 gate.passed 于受影响级别
# fail-closed：注入任一 Validator 抛异常 → 该 task errored、三级 failed；g1_frozen_bytes error → 其余 13 个 skipped_fail_closed
# 写入原子性：begin_step_run 之前被拒时 Ledger 行数（artifact_revisions、step_runs、audit_log）不变
# 退出码：acceptance 注入异常 → 1；缺 fixture → 3；m5-evidence-gate.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：逐字属 §19 第一列（M4 Knowledge Extraction / M3 Corpus Compilation）
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'
$TC 2>&1 | grep -E '^(Ran|OK|FAILED)'
$TV 2>&1 | grep -E '^(Ran|OK|FAILED)'          # ACT 00 起
bash openspec/acceptance/m3-coverage.sh | tail -1
bash openspec/acceptance/run_all.sh | tail -1
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/validation|openspec/acceptance/m5-evidence-gate.sh'   # 空（本包不改任何已跟踪文件）
```
