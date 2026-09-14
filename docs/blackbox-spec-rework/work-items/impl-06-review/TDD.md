# TDD：impl-06 M6 Review & Curation（READY_FOR_REVIEW）

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；`TK="$PY -m unittest discover -s pipeline/knowledge_extraction/tests -t ."`；`TV="$PY -m unittest discover -s pipeline/validation/tests -t ."`；`TR="$PY -m unittest discover -s pipeline/review/tests -t ."`；在仓库根运行。

## 0. 开工基线（每组派发前各一次）

```bash
git status --short pipeline/review openspec/acceptance/m6-data-fields.sh   # 空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                        # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1  # 与基线相同
bash openspec/schemas/verify.sh >/dev/null; echo $?                         # 0
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py; echo exit=$?  # 末行 fail=0 且 exit 0，且本包新类型 PASS 行存在（第 54 条）
$TL 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TC 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TK 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TV 2>&1 | grep -E "^(Ran|OK|FAILED)"
bash openspec/acceptance/run_all.sh | tail -1                               # == BASELINE_RUN_ALL
bash openspec/acceptance/m3-coverage.sh | tail -1                           # == BASELINE_M3
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml                 # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
test ! -e openspec/acceptance/m6-data-fields.sh; echo $?                    # K1–K3: 0（尚未创建）
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 01 | `$TR` → ImportError | `$TR` OK，用例 ≥ 23 |
| 02 | 新增用例全 ERROR | `$TR` OK ≥ 48；`gate.py` 无 model/propagation/step/rework 的 import（`grep -nE` 检查为空） |
| 03 | 新增用例全 ERROR | `$TR` OK ≥ 63；BDD 3.1 计数逐字相等（3/3/3/4/0.75） |
| 04 | 新增用例全 ERROR | `$TR` OK ≥ 71；`$TK`、`$TV`、`$TL`、`$TC` 不变 |
| 05 | 新增用例全 ERROR | `$TR` OK ≥ 86；6 个 Checkpoint 成链 |
| 06 | 新增用例全 ERROR | `$TR` OK ≥ 98；m6 StagePackage 过 `stage_package.schema.json` |
| 07 | 新增用例全 ERROR | `$TR` OK ≥ 107；`python -m pipeline.review --help` 退出 0 |
| 08 | 新增用例全 ERROR | `$TR` OK ≥ 121；报告计数 3/3/3 |
| 09 | 新增用例全 ERROR | `$TR` OK ≥ 135 |
| 10 | WITHDRAWN（第 61 条：Snapshot 归 M7）——不派发 | — |
| 11 | `m6-data-fields.sh` 不存在（exit 127）；新增用例全 ERROR | `$TR` OK ≥ 144；脚本 `SUMMARY pass=11 fail=0 blocked=3`、exit 2 |

阈值 = 各 ACT 具名用例（`- test_` 行）实际累计：23/48/63/71/86/98/107/109(06a，第 72 条)/121/124(09a，第 74 条)/135/144（F4；ACT 10 WITHDRAWN 不计）。

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/01–11 contract 中的函数名、参数名、返回键、检查名、输出行格式在实现中逐字存在
# 事件形态：review_decision 事件逐字由 pipeline.knowledge_extraction.review_events.build_review_decision 产出（不新造顶层键）
# 独立性：gate.py 与 acceptance.py 不 import model/propagation/step/rework；acceptance.py 不读取 close_review 返回的 gate 报告作为判定依据
# 非生产隔离：grep -rE 'testing' pipeline/review --include='*.py' | grep -vE '/tests/|/testing/|acceptance.py' 为空
# 生产代码不读 fixture：pipeline/review 非 tests/testing 文件不出现 "_fixture"（acceptance.py 只经 --fixture 参数）
# 人工决定粒度：每个 m6 StepRun 的 Checkpoint 数 == 1 + 该运行 human_event 数
# 失效传播：M6 生产代码除 rework.py 外不出现 invalidate_revision；D-08 取 B 时 rework.py 也不出现（只在报告登记）
# 写入原子性：open_review/record_decision/close_review/open_rework_review 的前置拒绝前后各表行数不变
# 退出码：acceptance 注入异常 → 1；缺 fixture → 3；m6-data-fields.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：「M6 Review Workbench」「M4 Knowledge Extraction」逐字属 §19 第一列
# 第 61 条豁免：snapshot_projection 的说明「前置缺失: M7 创世汇编」非 §19 第一列，经第 61 条授权，只有该行的说明不经 §19 行名校验
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
$TL 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TC 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TK 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TV 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TR 2>&1 | grep -E "^(Ran|OK|FAILED)"      # ACT 01 起
bash openspec/acceptance/run_all.sh | tail -1
bash openspec/acceptance/m3-coverage.sh | tail -1
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/review|openspec/acceptance/m6-data-fields.sh'   # 空
```
