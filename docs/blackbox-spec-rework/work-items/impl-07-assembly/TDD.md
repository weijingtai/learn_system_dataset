# TDD：impl-07 M7 增量汇编

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TA="$PY -m unittest discover -s pipeline/assembly/tests -t ."`；`FR=pipeline/corpus/_fixture/mini_release01`；在仓库根运行。

## 0. 开工基线（每组开工各一次）

```bash
git status --short pipeline/assembly pipeline/corpus/_fixture/mini_release01 openspec/acceptance/m7-assembler.sh   # 空
ls pipeline/assembly 2>/dev/null | grep -v __pycache__ | wc -l
#   F: 0；J1: 0；J2: 7（__init__ canonical errors model matcher apply tests）；J3: 9（+incremental gate）；J4: 13（+fixture_seed inputs step __main__）
ls $FR 2>/dev/null | wc -l                                    # F(ACT 00): 0；其余组: 7（README.md decisions editions expected manifest.yaml tools verify.sh）
bash docs/blackbox-spec-rework/verify-T.sh | tail -1         # FAIL 合计: 0
bash openspec/schemas/verify.sh >/dev/null; echo $?          # 0
bash pipeline/corpus/_fixture/mini_ed01/verify.sh | tail -1  # FIXTURE OK（缺页图时 exit 3 亦可）
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml  # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
$TL 2>&1 | tail -1                                           # OK
bash openspec/acceptance/run_all.sh | tail -1                # SUMMARY pass=2 fail=1 blocked=8
bash $FR/verify.sh | tail -1                                 # J1 起：FIXTURE OK
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `bash $FR/verify.sh` → No such file（exit 127） | 构建器重放 `diff -r` 无输出；`verify.sh` 5 项 PASS（expected 缺失项此时报 `BLOCKED expected_pending`，exit 3） |
| 01 | `verify.sh` → `BLOCKED expected_pending` exit 3 | `verify.sh` 7 项 PASS、`FIXTURE OK` exit 0；副本改 `snapshot_s2` 一字节 → `FAIL manifest_sha256` exit 1 |
| 02 | `$TA` → ImportError | `$TA` OK，用例 ≥ 18 |
| 03 | 新增用例全 ERROR | `$TA` OK ≥ 40；第 1、2 轮提案与 `proposals_r2.json` 相等 |
| 04 | 新增用例全 ERROR | `$TA` OK ≥ 52；s1、s2 字节相等 |
| 05 | 新增用例全 ERROR | `$TA` OK ≥ 62；s3 字节相等；增量 = 全量 |
| 06 | 新增用例全 ERROR | `$TA` OK ≥ 80；篡改矩阵 ≥ 16 例全部命中指定检查 |
| 07 | 新增用例全 ERROR | `$TA` OK ≥ 90；`$TL` 不变；`run_all.sh` 不变 |
| 08 | 新增用例全 ERROR | `$TA` OK ≥ 100 |
| 09 | `m7-assembler.sh` exit 127；新增用例全 ERROR | `$TA` OK ≥ 108；`m7-assembler.sh` → `SUMMARY pass=13 fail=0 blocked=1`、exit 2 |
| 10 | `run_all.sh 20.5` → `BLOCKED … M7 Incremental Assembly` | 按 D-13：A → `BLOCKED … M6 Review Workbench`；B → `PASS  20.5` |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/02–09 contract 中的函数名、参数名、返回键、检查名、rule_id 在实现中逐字存在
# 金标：Ledger 中 Snapshot 修订内容的 knowledge 段规范 JSON 字节 == expected/snapshot_s{1,2,3}.knowledge.json；两个临时 Ledger 独立跑两次字节相同
# 独立性：gate.py 与 acceptance.py 不 import matcher/apply/incremental；acceptance.py 不以 run_m7 返回的 gate/report 作为判定依据
# fixture 独立性：mini_release01/tools/build_fixture.py 与 verify.sh 不 import pipeline.assembly；F 组与 J 组提交作者（Agent）不同
# 生产代码不读 fixture：pipeline/assembly 非 tests 文件中 "_fixture" 只出现在 fixture_seed.py 与 acceptance.py，且只经 --fixture 参数
# 提案键不像登记 ID：Ledger 中全部 proposal_key/relation_key 经 pipeline.ledger.ids.kind_of 返回 None
# 不改上游：任一 run_m7/resume_m7 前后，m6 包与 reviewed_edition_knowledge 修订的 status、sha256、revision_status_events 行数不变
# 写入原子性：begin_step_run 之前被拒时 artifact_revisions、step_runs、audit_log 行数不变
# 矩阵外篡改（主 Agent 自定，不预告）：视图、决定、提案集、Snapshot、IdentityDelta、Checkpoint、StagePackage、配置修订各至少 1 例
# 无模型调用：grep -rE '^\s*(import|from) (requests|openai|anthropic|httpx|urllib\.request)' pipeline/assembly → 0
# 退出码：acceptance 注入异常 → 1；缺 fixture → 3；m7-assembler.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：upstream_m6_real 说明中的「M6 Review Workbench」逐字属 §19 第一列
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
bash pipeline/corpus/_fixture/mini_ed01/verify.sh >/dev/null; echo $?     # 0 或 3
bash $FR/verify.sh >/dev/null; echo $?                                    # ACT 01 起 0
$TL 2>&1 | tail -1
$TA 2>&1 | tail -1                                                        # ACT 02 起
bash openspec/acceptance/run_all.sh | tail -1                             # ACT 10 前恒为 SUMMARY pass=2 fail=1 blocked=8
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/assembly|pipeline/corpus/_fixture/mini_release01|openspec/acceptance/m7-assembler.sh|openspec/acceptance/run_all.sh'   # 空（run_all.sh 只在 ACT 10 出现）
```
