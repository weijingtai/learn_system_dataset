# TDD：impl-01 Artifact Ledger

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`T="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；在仓库根运行。

## 0. 开工基线（H1 与 H2 各一次）

```bash
git status --short pipeline/ledger openspec/acceptance .gitignore docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py   # 空
ls pipeline/ledger 2>/dev/null | wc -l                                          # H1: 0；H2: 13（含 tests）
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                            # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1      # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                             # 0
bash openspec/acceptance/run_all.sh | tail -1                                   # SUMMARY pass=0 fail=1 blocked=10
$PY -c "import yaml, jsonschema; print('env ok')"                               # env ok
$PY --version                                                                   # 3.14.x
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `check_d16.py --plan 副本(表 B 44 行)` → `D16 FAIL R3 表 B 数据行数=44` | `D16 OK`；副本 42 行 → `FAIL R3 …=42` |
| 01 | `$T` → ImportError（用例名已存在） | `$T` OK，用例 ≥ 13；`ids.PATTERNS` 19 项与 ACT 逐字相等（脚本比对） |
| 02 | `$T` 新增用例全 ERROR | 用例 ≥ 26；`sqlite_master` 15 张表；`grep -Fxc 'var/' .gitignore` = 1 |
| 03 | 新增用例全 ERROR | 用例 ≥ 54；`test_checkpoint` 8 条全过 |
| 04 | 新增用例全 ERROR | 用例 ≥ 61；`cli init/status` 可用 |
| 05 | `run_all.sh` 20.2/20.3 为 BLOCKED；新增用例全 ERROR | 用例 ≥ 71；`run_all.sh` → `PASS  20.2`、`PASS  20.3`、`SUMMARY pass=2 fail=1 blocked=8`、exit 1 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 契约签名逐字：从 act/03.yaml 抽取 methods 名称，逐个在 service.py 中以 "def <name>(" 出现 1 次
# 状态表逐字：python 比对 states.ARTIFACT_TRANSITIONS / STEP_RUN_TRANSITIONS 与 ACT 01 常量
# 迁移穷举：对 5×5 与 6×6 组合逐个调 check_*，结果集合 == 表
# 半成品：在 finish_step_run 中途抛异常（monkeypatch ObjectStore.put）→ step_runs.status 仍 running、无 step_manifest 修订
# 篡改 Object：改 objects/<..> 一字节 → seal → SRC_003 + quarantined；已 sealed 修订 read_object 前 verify 失败 → HashMismatch
# 篡改 Ledger 判定：删 stage_checkpoints 一行 / 置 NULL validation_report_revision_id / 把 20_3 中某 transformation 的 outputs 清空 → acceptance 各自 FAIL
# 假绿：把 acceptance.py 的某个断言改成恒真再跑 → 主 Agent 用 sed 复制副本检查每个 PASS 名称至少对应一处 FAIL 出口（grep -c "FAIL <name>" ≥ 1）
# BLOCKED 行名：run_all.sh 输出的差距行名逐字属 §19 第一列
# 无新前缀：grep -rhoE "'[a-z]+_' *\+|\"[a-z]+_\" *\+|f'[a-z]+_\{" pipeline/ledger | 出现的前缀 ⊆ 登记册 19 个
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                            # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1      # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                             # 0
$T 2>&1 | tail -1                                                               # OK
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/ledger|openspec/acceptance/run_all.sh|^ M .gitignore|check_d16.py'   # 空
ls var 2>/dev/null; git status --short var/ | wc -l                             # 0
```
