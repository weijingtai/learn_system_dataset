# TDD：impl-08 Local Orchestrator + Contract Registry

在仓库根运行。先设置以下变量：

```bash
export LC_ALL=en_US.UTF-8
PY=.venv/bin/python
TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."
TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."
TV="$PY -m unittest discover -s pipeline/validation/tests -t ."
TD="$PY -m unittest discover -s pipeline/dataset_compiler/tests -t ."
TR="$PY -m unittest discover -s pipeline/contract_registry/tests -t ."
TO="$PY -m unittest discover -s pipeline/orchestrator/tests -t ."
```

## 0. 开工基线（K1–K4 各一次）

```bash
git status --short pipeline/orchestrator pipeline/contract_registry openspec/acceptance   # K1: 空；K4: 空
ls pipeline/orchestrator pipeline/contract_registry 2>/dev/null | grep -v __pycache__ | wc -l   # K1: 0
ls openspec/acceptance                                                   # K1–K3: m3-coverage.sh m5-evidence-gate.sh run_all.sh；K4: 加 m8-span-identity.sh
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                     # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1   # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                      # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py          # D16 OK
$TL 2>&1 | tail -1                                                       # OK
$TC 2>&1 | tail -1                                                       # OK
$TV 2>&1 | tail -1                                                       # OK
$TD 2>&1 | tail -1                                                       # OK
bash openspec/acceptance/run_all.sh | tail -1                            # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/run_all.sh 20.1 20.10                           # BLOCKED 20.1 …Local Orchestrator…M4–M6 Gate 未实现；BLOCKED 20.10 …Contract Registry…无第二 Adapter 可做替换验证
# 仅 K4 追加：
grep -n 'impl-0[234]' docs/blackbox-spec-rework/SUBAGENT_TODO.md | head -3   # impl-02/03/04 均含 ACCEPTED
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?              # 2
bash openspec/acceptance/m5-evidence-gate.sh >/dev/null; echo $?         # 2
```

K4 开工基线中若 impl-02/impl-03/impl-04 任一不是 `ACCEPTED`，停手上报，不开工。

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TR` → ImportError | `$TR` OK，用例 ≥ 15；`python -m pipeline.contract_registry check` 末行 `REGISTRY OK modules=5 ports=4` |
| 01 | 新增用例全部 ERROR | `$TR` OK，用例 ≥ 25；ledgerd 冒烟用例通过 |
| 02 | `$TO` → ImportError | `$TO` OK，用例 ≥ 15 |
| 03 | 新增用例全部 ERROR | `$TO` OK，用例 ≥ 30 |
| 04 | 新增用例全部 ERROR | `$TO` OK，用例 ≥ 46；`run_all.sh` 不变 |
| 05 | 新增用例全部 ERROR | `$TO` OK，用例 ≥ 55 |
| 06 | 新增用例全部 ERROR | `$TO` OK，用例 ≥ 65；CLI 退出码用例通过 |
| 07 | `orchestrator-gate.sh` 不存在（exit 127）；新增用例全部 ERROR | `$TO` OK，用例 ≥ 74；`orchestrator-gate.sh` → `SUMMARY pass=5 fail=0 blocked=1`，exit 2 |
| 08 | `contract-registry.sh` 不存在（exit 127）；新增用例全部 ERROR | `$TR` OK，用例 ≥ 34；`contract-registry.sh` → `SUMMARY pass=3 fail=0 blocked=2`，exit 2；`run_all.sh` 未改 |
| 09 | `run_all.sh 20.10` 仍输出硬编码「无第二 Adapter 可做替换验证」；`test_run_all.py` 用例失败 | `$TR` OK，用例 ≥ 38；`run_all.sh` 仍为 pass=2 fail=1 blocked=8，20.1/20.10 说明为计算值；其余九条输出与基线逐字相同 |

（用例数阈值按 §1 具名用例累计，不得凑数；`act/10.yaml` 为 `DEFERRED`，不设阈值。）

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/00–09 contract 中的函数名、参数名、返回键、检查名、CLI 末行格式在实现中逐字存在
# 依赖方向：
grep -rnE 'corpus_compiler|validation\.step|dataset_compiler|pipeline\.ledger\.fixture_ingest' pipeline/orchestrator pipeline/contract_registry --include='*.py' | grep -v '/tests/' | grep -vE 'acceptance\.py|registry\.yaml|suites\.py'   # 空
grep -nE '^\s*(from|import) .*(runner|module|stubs|edition_run)' pipeline/orchestrator/gate.py   # 空
grep -rnE '\.store\b|\.objects\b' pipeline/orchestrator --include='*.py' | grep -v '/tests/'      # 空
# 桩隔离：registry.yaml 无 "kind: stub"；registered_modules_m1_m6 不因注入桩登记表而 PASS
# 零写入：advance 返回 waiting/blocked/refused/complete 时，artifact_revisions、step_runs、audit_log 行数不变
# StepResult：runner.execute_step 的全部返回值过 step_result.schema.json（含 awaiting_human 与 failed）；run_legacy 重建的 StepResult 亦过
# 独立性：acceptance.py 的 real_chain_mini_ed01 不调用 gate.evaluate_stage_gate，而是自行从 Ledger 重算
# 首纵切链：生产表下 m3/m5 Legacy 一步各 succeeded；run_release 调 run_m8 且 consumption_level=INTERNAL_DEMO；m8 属独立 release_run（owns_processing_run）
# 矩阵外篡改（主 Agent 自定，不预告）：Gate 八项各至少 1 例；token 重放；终态被 recover 改写；桩混入生产登记表；登记表哈希；legacy 入口在 ledgerd 下
# 退出码：两个 acceptance 注入异常 → 1；缺 fixture/依赖 → 3；两个 .sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：逐字属于 §19 第一列（M4 Knowledge Extraction / M1 Source Intake / Contract Registry）
# run_all.sh：diff 只触及 20.1、20.10 两个 case 体与一个 accept_check 函数；其余九条的输出与基线逐字相同
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$TL 2>&1 | tail -1
$TR 2>&1 | tail -1          # ACT 00 起
$TO 2>&1 | tail -1          # ACT 02 起
$TC 2>&1 | tail -1          # K4
$TV 2>&1 | tail -1          # K4
$TD 2>&1 | tail -1          # K4
bash openspec/acceptance/run_all.sh | tail -1
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/orchestrator|pipeline/contract_registry|openspec/acceptance/(orchestrator-gate|contract-registry|run_all)\.sh'   # 空（并行 Agent 的文件除外，须逐一核对归属）
```
