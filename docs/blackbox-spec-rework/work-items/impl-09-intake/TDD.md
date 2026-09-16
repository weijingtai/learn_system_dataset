# TDD：impl-09 M1 电子文本入库 + M2 电子文本清洗

在仓库根运行。先设定：

```bash
export LC_ALL=en_US.UTF-8
PY=.venv/bin/python
TI="$PY -m unittest discover -s pipeline/intake/tests -t ."
TD="$PY -m unittest discover -s pipeline/digitization/tests -t ."
```

## 0. 开工基线（每个执行组各跑一次）

```bash
git status --short pipeline/intake pipeline/digitization openspec/acceptance/m1-intake.sh openspec/acceptance/m2-sanitization.sh   # J1 开工时为空
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # I00-IF SUMMARY pass=36 fail=0
bash openspec/acceptance/run_all.sh 2>&1 | tail -1   # SUMMARY pass=2 fail=1 blocked=8
bash openspec/schemas/verify.sh >/dev/null; echo $?    # 0
git diff --check
```

## 1. 逐 ACT 的 Red → Green

| ACT | 套 | Red（实现前） | Green（实现后） |
|---|---|---|---|
| 00 | intake | `$TI` → ImportError | `$TI` OK，用例 ≥ 24；dump_manifest_yaml 往返字节相同 |
| 01 | intake | 新增用例全 ERROR | `$TI` OK ≥ 32；raw_text 冻结不可变 |
| 02 | digitization | `$TD` → ImportError | `$TD` OK ≥ 31；clean_text 可发现 13 项清洗问题；patches 可逆 |
| 03 | digitization | 新增用例全 ERROR | `$TD` OK ≥ 40；gate.py 不 import cleaner/patcher/reporter/raw_text |
| 04 | digitization | 新增用例全 ERROR | `$TD` OK ≥ 48；run_m2 成功路径产出三个 revision_id |
| 05 | digitization | 新增用例全 ERROR | `$TD` OK ≥ 57；load_decisions 校验通过；check_decisions_coverage 可检出缺决定 |
| 06 | digitization | 新增用例全 ERROR | `$TD` OK ≥ 61；M1→M2 产出可被 M3 输入解析消费 |
| 07 | 两套 | `m1-intake.sh` 不存在（exit 127）；新增用例全 ERROR | `$TI` OK ≥ 35；`$TD` OK ≥ 67；两份脚本 exit 2（BLOCKED） |

## 2. 用例阈值计算（按 act 文件 grep -c "^\s*- test_" 实数）

> **本节的「累计」列是阈值的唯一权威出处**；§1 的 Green 列与各 `act/*.yaml` 的 `verify` 注释一律引用本表，不得各写各的（第 86 条）。

### intake 套（$TI，pipeline/intake/tests）

> 「累计」= 该套测试目录的**实际用例总数**（`.venv/bin/python -m unittest discover` 的 `Ran N`），不是 act 文件的条目数；两者的差额来自主 Agent 另行指定补测的用例，已在「计算」列标明。

| ACT | 本 act 用例 | 累计 | 计算 |
|---|---|---|---|
| 00 | 24 | 24 | test_manifest.py 24 条＝act/00 `tests` 列 19 + J2 指定补测 1 + J1b（第 94 条 D4）新增 4 |
| 01 | 8 | 32 | + test_step.py 8 条＝act/01 `tests` 列 7 + 主 Agent 指定补测 1 |
| 07 | 3 | 35 | + test_acceptance.py intake 侧 3 条 |

### digitization 套（$TD，pipeline/digitization/tests）

| ACT | 本 act 用例 | 累计 | 计算 |
|---|---|---|---|
| 02 | 31 | 31 | test_cleaner.py 31 条 |
| 03 | 9 | 40 | + test_gate.py 9 条 |
| 04 | 8 | 48 | + test_step.py 8 条 |
| 05 | 9 | 57 | + test_decisions.py 9 条 |
| 06 | 6 | 63 | + test_parity.py 6 条＝act/06 `tests` 列 4 + J4（第 94 条 D3）新增 2 |
| 07 | 4 | 67 | + test_acceptance.py digitization 侧 4 条 |

**各 act grep -c 实数**：

```
$ for f in docs/blackbox-spec-rework/work-items/impl-09-intake/act/*.yaml; do echo "$(basename $f): $(grep -c '^\s*- test_' $f)"; done
00.yaml: 23
01.yaml: 7
02.yaml: 31
03.yaml: 9
04.yaml: 8
05.yaml: 9
06.yaml: 4
07.yaml: 7  （intake 侧 3 + digitization 侧 4）
```

## 3. 回归（每个 ACT 后）

```bash
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # I00-IF SUMMARY pass=36 fail=0
bash openspec/acceptance/run_all.sh 2>&1 | tail -1   # 仍 SUMMARY pass=2 fail=1 blocked=8
bash openspec/schemas/verify.sh >/dev/null; echo $?    # 0
$TI 2>&1 | tail -1          # ACT 00 起
$TD 2>&1 | tail -1          # ACT 02 起
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/intake|pipeline/digitization|openspec/acceptance/m1-intake.sh|openspec/acceptance/m2-sanitization.sh'   # 空
```
