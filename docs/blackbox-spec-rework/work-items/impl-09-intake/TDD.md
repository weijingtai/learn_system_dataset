# TDD：impl-09 M1 Source Intake + M2 Digitization 真实最薄接入

在仓库根运行。先设定：

```bash
export LC_ALL=en_US.UTF-8
PY=.venv/bin/python
TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."
TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."
TS="$PY -m unittest discover -s pipeline/source_intake/tests -t ."
TD="$PY -m unittest discover -s pipeline/digitization/tests -t ."
```

真实素材与人工输入的默认路径（D-09-02、D-09-03 裁决后以裁决为准）：

```bash
ASSETS=ocr/data_work/sanche_pages
OCRROOT=ocr/data_work
SUB=pipeline/registry/intake/src_sanche_ed01/part_p001_p010.submission.yaml
DEC=pipeline/registry/intake/src_sanche_ed01/part_p001_p010.m2_decisions.yaml
```

## 0. 开工基线（每个执行组各跑一次）

```bash
git status --short pipeline/source_intake pipeline/digitization openspec/acceptance/m1-replay.sh openspec/acceptance/m2-export-integrity.sh   # K1 开工时为空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                          # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1    # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                           # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py               # D16 OK
$TL 2>&1 | tail -1                                                            # OK（起草时 74，记录实际值）
$TC 2>&1 | tail -1                                                            # OK（以 impl-02 ACCEPTED 时的数为准，记录实际值）
bash openspec/acceptance/run_all.sh | tail -1                                 # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?                   # 2（K3、K4 开工前必须成立）
bash pipeline/corpus/_fixture/mini_ed01/verify.sh | tail -1                   # FIXTURE OK（本机有前三页页图；缺图为 exit 3，记录）
shasum -a 256 $ASSETS/page_0{01,02,03,04,05,06,07,08,09}.png $ASSETS/page_010.png   # 与 README §9 一致；不一致立即停手上报
find $OCRROOT/data $OCRROOT/logs -type f | sort | xargs shasum -a 256 | shasum -a 256 > /tmp/impl09_ocr_before.txt   # 记录 OCR 工作根总指纹
ls $SUB $DEC 2>&1                                                             # 记录是否存在（缺失不阻塞开工，只影响真实十页用例 skip）
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TS` → ImportError | `$TS` OK，用例 ≥ 18；fixture manifest 往返字节相同 |
| 01 | 新增用例全 ERROR | `$TS` OK ≥ 31；真实十页用例在本机为 ok（非 skip） |
| 02 | `$TD` → ImportError | `$TD` OK ≥ 21；expected m2 的 counts 与 content_sha256 相等 |
| 03 | 新增用例全 ERROR | `$TD` OK ≥ 39；`grep -cE 'import .*(plan|decisions|ocr_work)' pipeline/digitization/gate.py` 为 0 |
| 04 | 新增用例全 ERROR | `$TD` OK ≥ 52；`resolve_m3_inputs` 在本包 Ledger 上解析成功；OCR 工作根指纹不变 |
| 05 | 新增用例全 ERROR | `$TD` OK ≥ 59；deferred → awaiting_human；input_contract / m2_gate / internal 三类失败封存 |
| 06 | 新增用例全 ERROR（本机有页图时） | `$TD` OK ≥ 64；corpus_spans 字节 == fixture spans.yaml；无页图时 5 个 skip，原因含 BLOCKED_SOURCE_ASSET_MISSING |
| 07 | `m1-replay.sh` 不存在（exit 127）；新增用例全 ERROR | `$TS` OK ≥ 38；`m1-replay.sh` → `SUMMARY pass=5 fail=0 blocked=1`，exit 2 |
| 08 | `m2-export-integrity.sh` 不存在（exit 127）；新增用例全 ERROR | `$TD` OK ≥ 72；有 `$SUB`、`$DEC` 时 `SUMMARY pass=6 fail=0 blocked=3`，否则 `pass=5 fail=0 blocked=4`；exit 2 |

## 2. 主 Agent 验收附加判据（执行者不需要跑，但不得让其失败）

```bash
# 签名逐字：act/00–08 contract 中的函数名、参数名、返回键、检查名、CLI 输出前缀在实现中逐字存在
# 来源不可区分：本包 Ledger 上 run_m3 的 corpus_spans 字节 == fixture spans.yaml；两次独立运行（两个临时 Ledger）字节相同
# 独立性：digitization/gate.py 不 import plan/decisions/ocr_work；两个 acceptance.py 不 import 被验的 gate/plan/assets.png_size，也不读 run_m1/run_m2 返回的 gate 报告作为判定依据
# 生产代码不读 fixture：两个包非 tests、非 acceptance 的文件不出现 "_fixture"
# 不写 OCR 工作根：运行全部测试与两份验收脚本后，/tmp/impl09_ocr_before.txt 指纹不变；grep -rnE "open\(.*['\"](w|a)" pipeline/source_intake pipeline/digitization --include='*.py' | grep -v /tests/ 为空
# 不伪造：git status 不出现 $DEC；执行者提交中不含 pipeline/registry/**；无 png/jpg/pdf 新文件进入 Git
# 不执行 OCR：grep -rnE 'paddle|run_sanche10|ocr_workbench' pipeline/source_intake pipeline/digitization 为空
# 写入原子性：begin_step_run 之前被拒时，processing_runs、artifact_revisions、step_runs、audit_log 行数不变（M1 与 M2 各验一例矩阵外）
# 矩阵外篡改（主 Agent 自定，不预告）：页图字节、页 JSON、异常记录、审计日志、决定表、申报件、配置修订、human_event、Checkpoint、StagePackage 各至少 1 例
# 退出码：两份验收的 acceptance 注入异常 → 1；缺页图或缺 OCR 工作根 → 3；副本假 verify.sh → 1；m1-replay 与 m2-export-integrity 在本包都不得返回 0
# BLOCKED 行名：说明中的「M1 Source Intake」「M2 Digitization & Correction」逐字属 §19 第一列
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$TL 2>&1 | tail -1
$TC 2>&1 | tail -1
$TS 2>&1 | tail -1          # ACT 00 起
$TD 2>&1 | tail -1          # ACT 02 起
bash openspec/acceptance/run_all.sh | tail -1                  # 仍 SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?    # 仍 2（ACT 04 起必查）
find $OCRROOT/data $OCRROOT/logs -type f | sort | xargs shasum -a 256 | shasum -a 256 | diff - /tmp/impl09_ocr_before.txt   # 空
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/source_intake|pipeline/digitization|openspec/acceptance/m1-replay.sh|openspec/acceptance/m2-export-integrity.sh'   # 空（他人并行工作的文件除外，须逐一说明）
```
