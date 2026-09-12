# TDD：impl-00 跨模块契约与金标

状态：`DEFERRED`（W2-C1 按 `G7-RULINGS.md` §9 裁剪：本文档整体属**纵切后**；首纵切唯一 ACT 为 `impl-00/10`）

## 纵切后（DEFERRED）

- 本文件 §0–§3 描述的 ACT 00–09（契约检查器、Schema、金标、`verify.sh` 扩项与篡改矩阵、`fixture_ingest` 灌入 m1–m8）**首纵切内一律不执行**，整体移入「纵切后」（P1/P3/P9；README §5）。
- 首纵切唯一 ACT `impl-00/10` 的 Red→Green 与回归见其 `act/10.yaml` 的 `tests_first`/`verify`；它只写 `INTERFACES.md`、`check_interfaces.py`、`tests/`，不触 `openspec/schemas/`、fixture、`pipeline/ledger/`。
- 下文原文逐字保留，供纵切后执行。

---

（以下为纵切后执行的原文，逐字保留）

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`W=docs/blackbox-spec-rework/work-items/impl-00-interfaces`；`FX=pipeline/corpus/_fixture/mini_ed01`；在仓库根运行。

## 0. 开工基线（K1、K2、K3 各一次）

```bash
git status --short openspec/schemas $FX pipeline/ledger/fixture_ingest.py pipeline/ledger/tests/test_ingest.py $W   # 空（本目录草案文件已提交后）
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                          # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1    # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                           # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py               # D16 OK
$PY -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | tail -1         # OK
$PY -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | tail -1   # OK
bash openspec/acceptance/run_all.sh | tail -1                                 # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?                   # 2
bash $FX/verify.sh | tail -1                                                  # FIXTURE OK
shasum -a 256 $FX/manifest.yaml $FX/spans.yaml $FX/expected/m1.stage_package.yaml $FX/expected/m2.stage_package.yaml $FX/expected/m3.stage_package.yaml
# 613d33e0772fa737c3ad161760f3720efbc4c681e9317983c65cdb7971e364c7  manifest.yaml
# ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef  spans.yaml
# 65bd10f595259685806d7ad7597cb92cab4fd4bc4c9b97aaa95c5271dc91e6d2  m1
# f327fda69027be903b7389117a9ba0970173d4578a4d88f831e575b345d561f6  m2
# e016c3fe4aa38b19b8026adb801eee241668957d977a8d6110837db8b57be935  m3
T=$(mktemp -d) && $PY $FX/tools/build_fixture.py --out $T/r >/dev/null && diff -r --exclude=tools --exclude=README.md $T/r $FX; echo diff=$?   # diff=0
```

impl-02 ACT 05 返工若同时进行，corpus_compiler 用例数会变化；门禁只看 `OK`，不钉用例数。

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$PY $W/check_i00.py` → No such file（exit 2） | `$PY -m unittest discover -s $W/tests -t $W` OK ≥ 8；`check_i00.py --upto 00` → `PASS C00`、9 行 SKIP、exit 0；`--upto 01` → `FAIL C01` |
| 01 | `check_i00.py --upto 01` → `FAIL C01` | `--upto 01` exit 0；`openspec/schemas/verify.sh` exit 0 且新增 9 行 `PASS candidate_set_*` |
| 02 | `--upto 02` → `FAIL C02` | `--upto 02` exit 0；verify.sh 新增 gate_results/review_decision/reviewed_edition/rework_impact_report 的 PASS 行 |
| 03 | `--upto 03` → `FAIL C03` | `--upto 03` exit 0 |
| 04 | `--upto 04` → `FAIL C04` | `--upto 04` exit 0；`--check-metaschema` 覆盖全部 18 份新增 Schema |
| 05 | `--upto 05` → `FAIL C05 expected/m4.candidate_set.yaml 缺失` | `--upto 05` exit 0；重放 diff=0；五个基线哈希不变；`verify.sh` 仍 8 项 PASS |
| 06 | `--upto 06` → `FAIL C06` | `--upto 06` exit 0；重放 diff=0 |
| 07 | `--upto 07` → `FAIL C07` | `--upto 07` exit 0；`SHA256SUMS` 行数 == expected 下除自身外文件数（24 = m1–m3 三份 + m4/m5/m7 各二 + m6 七 + m8 八） |
| 08 | `bash $W/fixture_mutations.sh` → No such file；`verify.sh` 只有 8 行 PASS | `verify.sh` 12 行 PASS + `FIXTURE OK`；`MUTATIONS 20/20`；重放 diff=0 |
| 09 | `test_ingest.py` 新增 5 例 ERROR | `$PY -m unittest discover -s pipeline/ledger/tests -t .` OK；`check_i00.py --upto 09` exit 0；`run_all.sh` 不变 |

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 契约逐字：act/01–04 contract 中的 $defs 名、必填键、枚举值在 Schema 中逐字存在（grep 计数与 contract 列表数相等）
# ID 正则同源：contract_common 13 个 ID 正则 == ids.py PATTERNS 同名项（脚本比对，不靠目测）
# 独立性：verify.sh 模板中的 V9–V12 不调用生成器函数（生成器 build_* 函数名在 VERIFY_SH 文本中计数为 0）
# 零伪造：m4 金标的每个 quote 都能在 source/transcript_v1.md 中 grep 到整行；命题中引号内的文字均为目录行原文
# 金标冻结：记录 sha256(expected/SHA256SUMS)；另起临时目录重生成，得到相同哈希
# 矩阵外篡改（主 Agent 自定，不预告）：m4 concept layer、m5 validators、m6 scope_consumption_level、m7 proposals、m8 query_contract 各至少 1 例，verify.sh 须 FAIL
# Schema 反向：把 12 份内容 Schema 的 additionalProperties 临时改为 true，至少 12 个 invalid_unknown_field 样例由失败变为通过（证明样例确实在测未知字段）
# L0 未动：git diff --stat openspec/schemas/{artifact_ref,stage_package,step_request,step_result}.schema.json 为空
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$PY -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | tail -1
$PY -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | tail -1
$PY -m unittest discover -s $W/tests -t $W 2>&1 | tail -1                     # ACT 00 起
$PY $W/check_i00.py --upto <本 ACT 号> | tail -1                               # I00 SUMMARY … fail=0
bash $FX/verify.sh | tail -1                                                  # FIXTURE OK
bash openspec/acceptance/run_all.sh | tail -1                                 # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?                   # 2
shasum -a 256 $FX/manifest.yaml $FX/spans.yaml $FX/expected/m1.stage_package.yaml $FX/expected/m2.stage_package.yaml $FX/expected/m3.stage_package.yaml   # 同 §0
git diff --check
git status --short | grep -v '^??' | grep -vE "openspec/schemas/|$FX/|pipeline/ledger/fixture_ingest.py|pipeline/ledger/tests/test_ingest.py|$W/"   # 空
```
