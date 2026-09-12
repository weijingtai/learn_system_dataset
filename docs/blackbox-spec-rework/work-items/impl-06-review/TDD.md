# TDD：impl-06 M6 Review & Curation（草案）

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；`TR="$PY -m unittest discover -s pipeline/review/tests -t ."`；在仓库根运行。

## 0. 开工基线（每组派发前各一次）

```bash
git status --short pipeline/review openspec/acceptance/m6-data-fields.sh   # 空
ls pipeline/review 2>/dev/null | grep -v __pycache__ | wc -l                # K1: 0；K2: 5（__init__ errors gate model propagation）+ tests；K3: 在 K2 基础上 +inputs step console __main__ testing
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                        # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1  # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                         # 0
$TL 2>&1 | tail -1                                                          # OK（起草时实测 74）
$TC 2>&1 | tail -1                                                          # OK（起草时 impl-02 J3 返工中，实测 1 个失败；K2 派发前必须为 OK）
bash openspec/acceptance/run_all.sh | tail -1                               # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh | tail -1                           # SUMMARY pass=8 fail=0 blocked=1
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml                 # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 01 | `$TR` → ImportError | `$TR` OK，用例 ≥ 16 |
| 02 | 新增用例全 ERROR | `$TR` OK ≥ 36；`grep -E '^(from|import) .*(model|propagation|step)' pipeline/review/gate.py` 为空 |
| 03 | 新增用例全 ERROR | `$TR` OK ≥ 50；BDD 3.1 计数逐字相等 |
| 04 | 新增用例全 ERROR | `$TR` OK ≥ 58；`$TC`、`$TL` 不变 |
| 05 | 新增用例全 ERROR | `$TR` OK ≥ 70；5 个 Checkpoint 成链 |
| 06 | 新增用例全 ERROR | `$TR` OK ≥ 80；m6 StagePackage 过 `stage_package.schema.json` |
| 07 | 新增用例全 ERROR | `$TR` OK ≥ 88；`python -m pipeline.review --help` 退出 0 |
| 08 | 新增用例全 ERROR | `$TR` OK ≥ 98；报告计数 6/3/2 |
| 09 | 新增用例全 ERROR | `$TR` OK ≥ 104 |
| 10 | 新增用例全 ERROR（依 D-01；未采纳 A 则跳过本 ACT） | `$TR` OK ≥ 110 |
| 11 | `m6-data-fields.sh` 不存在（exit 127）；新增用例全 ERROR | `$TR` OK ≥ 116；脚本 `SUMMARY pass=12 fail=0 blocked=2`、exit 2 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/01–11 contract 中的函数名、参数名、返回键、检查名、输出行格式在实现中逐字存在
# 独立性：gate.py 与 acceptance.py 不 import model/propagation/step/rework；acceptance.py 不读取 close_review 返回的 gate 报告作为判定依据
# 非生产隔离：grep -rE 'testing' pipeline/review --include='*.py' | grep -vE '/tests/|/testing/|acceptance.py' 为空
# 生产代码不读 fixture：pipeline/review 非 tests/testing 文件不出现 "_fixture"（acceptance.py 只经 --fixture 参数）
# 人工决定粒度：每条 review_decision 事件恰好对应 1 个 Checkpoint；Checkpoint 数 == 1 + 决定数 + 人工事件数（CorrectionRequest、阈值确认）
# 精确失效：rework 之后 Ledger 中 status='invalidated' 的修订集合 == 报告 invalidated 中 kind=candidate 的修订集合（逐个相等，不多不少）
# 写入原子性：open_review/record_decision/close_review/open_rework_review 的前置拒绝前后 artifact_revisions、step_runs、human_events、stage_checkpoints、audit_log 行数不变
# 矩阵外篡改（主 Agent 自定，不预告）：决定事件内容、队列修订、候选修订、校验包 gate、Checkpoint human_decisions、ReworkImpactReport 计数、StagePackage 各至少 1 例
# 退出码：acceptance 注入异常 → 1；缺 fixture → 3；m6-data-fields.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：「M6 Review Workbench」「M4 Knowledge Extraction」（ACT 10 未做时「M7 Incremental Assembly」）逐字属 §19 第一列
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
$TL 2>&1 | tail -1
$TC 2>&1 | tail -1
$TR 2>&1 | tail -1          # ACT 01 起
bash openspec/acceptance/run_all.sh | tail -1
bash openspec/acceptance/m3-coverage.sh | tail -1
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/review|openspec/acceptance/m6-data-fields.sh'   # 空
```
