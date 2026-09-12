# TDD：impl-02 M3 结构层

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；在仓库根运行。

## 0. 开工基线（J1 与 J2 各一次）

```bash
git status --short pipeline/corpus_compiler pipeline/ledger openspec/acceptance docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py   # 空
ls pipeline/corpus_compiler 2>/dev/null | grep -v __pycache__ | wc -l   # J1: 0；J2: 6（__init__ compiler errors gate serialize tests）
ls openspec/acceptance                                                   # J1/J2: 只有 run_all.sh
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                     # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1   # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                      # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py          # D16 OK
$TL 2>&1 | tail -1                                                       # OK（73）
bash openspec/acceptance/run_all.sh | tail -1                            # SUMMARY pass=2 fail=1 blocked=8
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml              # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | 副本勾选 Artifact Ledger → `D16 FAIL R5 新节 C 未勾选项数=2（应 3）` | 副本 A `D16 OK`；副本 B/C `FAIL R5` |
| 01 | `$TC` → ImportError | `$TC` OK，用例 ≥ 16；金标字节相等 |
| 02 | 新增用例全 ERROR | `$TC` OK，用例 ≥ 37 |
| 03 | 新增用例全 ERROR | `$TL` OK ≥ 74；`$TC` OK ≥ 50；`run_all.sh` 不变 |
| 04 | `m3-coverage.sh` 不存在（exit 127）；新增用例全 ERROR | `$TC` OK ≥ 58；`m3-coverage.sh` → `SUMMARY pass=8 fail=0 blocked=1`、exit 2 |
| 05（返工） | 新增 8 个用例失败；`test_missing_fixture_exit_3` 失败 | `$TC` OK ≥ 67；三类冻结输入对象篡改 → `input_contract`；begin 后异常 → `internal` 且 StepRun failed；缺 fixture exit 3；`m3-coverage.sh` 仍 exit 2 |
| 06（跟进） | `test_missing_yaml_exit_3` 失败 | `$TC` OK = 68；缺 PyYAML → exit 3；四个失败用例直查 `stage_packages` m3 行数 0；`m3-coverage.sh` 仍 exit 2 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/01–04 contract 中的函数名、参数名、返回键、检查名在实现中逐字存在
# 金标：Ledger 中 corpus_spans 修订字节 == fixture spans.yaml；两次独立 run_m3（两个临时 Ledger）字节相同
# 独立性：gate.py 与 acceptance.py 不 import compiler；acceptance.py 不读取 run_m3 返回的 gate 报告作为判定依据
# 生产代码不读 fixture：pipeline/corpus_compiler 非 tests 文件不出现 "_fixture" 字符串（acceptance.py 读金标除外，且只经 --fixture 参数）
# 矩阵外篡改（主 Agent 自定，不预告）：页 JSON、终态、人工事件、批次、Checkpoint、StagePackage、配置修订各至少 1 例
# 写入原子性：begin_step_run 之前被拒时 Ledger 行数（artifact_revisions、step_runs、audit_log）不变
# 退出码：acceptance 注入异常 → 1；缺 fixture → 3；m3-coverage.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：semantic_layer 说明中的「M3 Corpus Compilation」逐字属 §19 第一列
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$TL 2>&1 | tail -1
$TC 2>&1 | tail -1          # ACT 01 起
bash openspec/acceptance/run_all.sh | tail -1
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/corpus_compiler|pipeline/ledger/fixture_ingest.py|pipeline/ledger/tests/test_ingest.py|openspec/acceptance/m3-coverage.sh|check_d16.py'   # 空
```
