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

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TI` → ImportError | `$TI` OK，用例 ≥ 16；dump_manifest_yaml 往返字节相同 |
| 01 | 新增用例全 ERROR | `$TI` OK ≥ 23；raw_text 冻结不可变 |
| 02 | `$TD` → ImportError | `$TD` OK ≥ 14；clean_text 可发现 13 项清洗问题；patches 可逆 |
| 03 | 新增用例全 ERROR | `$TD` OK ≥ 22；gate.py 不 import cleaner/patcher/reporter/raw_text |
| 04 | 新增用例全 ERROR | `$TD` OK ≥ 30；run_m2 成功路径产出三个 revision_id |
| 05 | 新增用例全 ERROR | `$TD` OK ≥ 38；load_decisions 校验通过；check_decisions_coverage 可检出缺决定 |
| 06 | 新增用例全 ERROR | `$TD` OK ≥ 42；M1→M2 产出可被 M3 输入解析消费 |
| 07 | `m1-intake.sh` 不存在（exit 127）；新增用例全 ERROR | `$TI` OK ≥ 23；`$TD` OK ≥ 42；两份脚本 exit 2（BLOCKED） |

## 2. 用例阈值计算

| ACT | 累计用例 | 计算过程 |
|---|---|---|
| 00 | 16 | 16（test_manifest.py） |
| 01 | 23 | 16 + 7（test_step.py） |
| 02 | 37 | 23 + 14（test_cleaner.py） |
| 03 | 45 | 37 + 8（test_gate.py） |
| 04 | 53 | 45 + 8（test_step.py 增补） |
| 05 | 61 | 53 + 8（test_decisions.py） |
| 06 | 65 | 61 + 4（test_parity.py） |
| 07 | 73 | 65 + 8（test_acceptance.py ×2） |

**注意**：以上为预估阈值，以实际实现时的具名用例数为准。verify 中只断言 `用例 ≥ 预估值`，不写死 pass 总数。

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
