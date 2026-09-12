# TDD：impl-10 M3 语义层

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；`TS="$PY -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t ."`；`SFX=pipeline/corpus/_fixture/mini_ed01_semantic`；在仓库根运行。

## 0. 开工基线（J1 与 J2 各一次）

```bash
grep -c '^状态：`ACCEPTED`' docs/blackbox-spec-rework/work-items/impl-02-corpus/README.md   # 1（否则停手：impl-02 未验收）
git status --short pipeline/corpus_compiler pipeline/ledger pipeline/corpus/_fixture openspec/acceptance   # 空
ls pipeline/corpus_compiler/semantic 2>/dev/null | grep -v __pycache__ | wc -l   # J1: 0；J2: 10（__init__ errors proposer proposals rules anchors reconcile assemble semantic_gate tests）
ls $SFX 2>/dev/null | wc -l                                                     # J1: 0；J2: 8
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                            # FAIL 合计: 0
bash openspec/schemas/verify.sh >/dev/null; echo $?                             # 0
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'                                           # OK
$TC 2>&1 | grep -E '^(Ran|OK|FAILED)'                                           # OK，≥ 67（记下精确值 N_TC）
bash openspec/acceptance/m3-coverage.sh | tail -1; echo exit=$?                 # SUMMARY pass=8 fail=0 blocked=1；exit=2
bash openspec/acceptance/run_all.sh | tail -1                                   # SUMMARY pass=2 fail=1 blocked=8
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml                     # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
git grep -c '\bsem_' -- pipeline openspec | wc -l                               # 0（D1 选 A 时）
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `bash $SFX/verify.sh` → exit 127 | exit 0，末行 `SEMANTIC FIXTURE OK`；五类副本篡改各 exit 1；生成器重放 `diff -r` 无输出 |
| 01 | `$TS` → ImportError | `$TS` OK，≥ 16 |
| 02 | 新增用例全 ERROR | `$TS` OK，≥ 32；`compile_semantic` 字节 == `$SFX/semantic_spans.yaml` |
| 03 | 新增用例全 ERROR | `$TS` OK，≥ 52 |
| 04 | 新增用例全 ERROR | `$TS` OK，≥ 64；`$TC` == N_TC 且 OK |
| 05 | 新增用例全 ERROR | `$TS` OK，≥ 78；CLI 三段式跑通 |
| 06 | `m3-coverage.sh` exit 2；新增用例 ERROR | `$TS` OK，≥ 84；`$TC` OK（== N_TC + 2）；`m3-coverage.sh` → `SUMMARY pass=9 fail=0 blocked=0`、exit 0 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/01–06 contract 中的函数名、参数名、返回键、检查名、artifact_type、失败检查名在实现中逐字存在
# 金标：Ledger 中 semantic_spans 修订字节 == $SFX/semantic_spans.yaml；两次独立 run→decide→resume（两个临时 Ledger）字节相同
# 金标独立性：$SFX/tools/build_semantic_fixture.py 不 import pipeline.*
# Gate 独立：semantic_gate.py 不 import compiler/serialize/rules/proposals/proposer/reconcile/anchors/assemble
# 验收独立：semantic/acceptance.py 不 import semantic_gate/assemble/reconcile/anchors/rules，且不读 run 返回的 gate 报告作为判定依据
# 零网络：grep -rE '^\s*(import|from) (socket|urllib|http|requests|httpx|openai|anthropic)' pipeline/corpus_compiler/semantic --include='*.py' | grep -v '/tests/' → 0
# 开关唯一：grep -rn 'LEARN_SYSTEM_ALLOW_MODEL_CALLS' pipeline --include='*.py' | grep -v '/tests/' → 只在 semantic/proposer.py
# 录制诚实：$SFX/recordings.yaml 顶层 synthetic: true 与 origin: hand_authored_replay_fixture
# 结构层零改动：git diff --stat 相对开工基线，pipeline/corpus_compiler 下只有 acceptance.py 与 tests/test_acceptance.py 两个已有文件变化（ACT 06）
# 写入原子性：begin_step_run 之前被拒时 artifact_revisions、step_runs、audit_log 行数不变
# 矩阵外篡改（主 Agent 自定，不预告）：录制、裁决事件对象、审核队列对象、语义金标、Checkpoint、StagePackage、配置修订各至少 1 例
# 退出码：semantic acceptance 注入异常 → 1；缺 recordings.yaml → 3；m3-coverage.sh 在语义副本假 verify.sh 下 → 1
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'
$TC 2>&1 | grep -E '^(Ran|OK|FAILED)'
$TS 2>&1 | grep -E '^(Ran|OK|FAILED)'      # ACT 01 起
bash pipeline/corpus/_fixture/mini_ed01/verify.sh | tail -1
bash $SFX/verify.sh | tail -1               # ACT 00 起
bash openspec/acceptance/m3-coverage.sh | tail -1   # ACT 06 前：pass=8 blocked=1；ACT 06 后：pass=9 blocked=0
bash openspec/acceptance/run_all.sh | tail -1       # 恒为 SUMMARY pass=2 fail=1 blocked=8
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/corpus_compiler/semantic|pipeline/corpus/_fixture/mini_ed01_semantic|pipeline/corpus_compiler/acceptance.py|pipeline/corpus_compiler/tests/test_acceptance.py|openspec/acceptance/m3-coverage.sh'   # 空
```
