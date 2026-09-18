# TDD：impl-04 M8 Dataset Compilation 首切片

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；
`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；
`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；
`TD="$PY -m unittest discover -s pipeline/dataset_compiler/tests -t ."`；在仓库根运行。

## 0. 开工基线（K1、K2、K3 各一次）

```bash
git status --short pipeline/dataset_compiler openspec/acceptance/m8-span-identity.sh    # 空
ls pipeline/dataset_compiler 2>/dev/null | grep -v __pycache__ | wc -l                   # K1: 0；K2: 7（__init__ canonical errors gate levels packs tests）；K3: 11（再加 shim inputs step __main__）
ls openspec/acceptance                                                                    # K1/K2/K3: m3-coverage.sh run_all.sh
grep -n "impl-02：" docs/blackbox-spec-rework/SUBAGENT_TODO.md | head -1                  # K2/K3 前必须含 ACCEPTED；否则停手上报
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                                      # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1                # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                                       # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py                           # D16 OK
$TL 2>&1 | tail -1                                                                        # OK
$TC 2>&1 | tail -1                                                                        # OK
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?                               # 2
bash openspec/acceptance/run_all.sh | tail -1                                             # SUMMARY pass=2 fail=1 blocked=8
bash openspec/acceptance/m8-span-identity.sh >/dev/null 2>&1; echo $?                     # K1/K2: 127；K3 ACT 08 前: 2
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml                               # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
ls ocr/data_work/sanche_pages/page_001.png ocr/data_work/sanche_pages/page_002.png ocr/data_work/sanche_pages/page_003.png | wc -l   # K2/K3: 3；不是 3 则停手上报（集成测试会 skip）
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TD` → ImportError（目录不存在或无模块） | `$TD` OK，用例 ≥ 18 |
| 01 | 新增用例全 ERROR（`packs` 不存在） | `$TD` OK ≥ 45；fixture 上 41/2/230/39 键碰撞数字逐字出现在断言中 |
| 02 | 新增用例全 ERROR | `$TD` OK ≥ 73；gate 不 import packs/canonical/levels/step |
| 03 | 新增用例全 ERROR | `$TD` OK ≥ 84，无 skipped；shim CLI 缺图退出 3 |
| 04 | 新增用例全 ERROR | `$TD` OK ≥ 90；`resolve_m8_inputs` 前后 Ledger 行数不变 |
| 05 | 新增用例全 ERROR | `$TD` OK ≥ 102；`run_m8` fixture 成功，counts 与第 6.1 条一致 |
| 06 | `DEV_SEARCH`/`PUBLIC_RELEASE` 用例失败（ACT 05 在 begin 之前拒绝）；`compile`/`internal` 用例失败（异常外抛）；CLI 用例 ERROR | `$TD` OK ≥ 112 |
| 07 | `m8-span-identity.sh` 不存在（exit 127）；新增用例全 ERROR | `$TD` OK ≥ 124；`m8-span-identity.sh` → `SUMMARY pass=7 fail=0 blocked=1`、exit 2 |
| 08 | `run_all.sh 20.4` 输出仍为 `前置缺失: M8 Dataset Compilation；PublicationPackage 反向追溯未实现` | 20.4/20.8 为 `前置缺失: M4 Knowledge Extraction；…`；注入副本 20.4 FAIL；SUMMARY 不变 |
| 09 | `$TD` 9 条全 ERROR（`build_graph_projection_pack` 不存在） | `$TD` OK ≥ 134；GraphProjection 8 键严格匹配，边无 ID，节点与三元组严格排序 |
| 10 | `$TD` 6 条 FAIL/ERROR（`reference_and_hash_only` 未放行、`build_evidence_chain` 不存在、`parse_span_identity` 拒 offset） | `$TD` OK ≥ 143；`reference_and_hash_only` 放行且脱敏 null，offset 证据链恰 7 键，经 ids.py 校验 |
| 11 | `$TD` 9 条全 ERROR（`build_knowledge_data_pack` 不存在、`entry_ids` 不可导入） | `$TD` OK ≥ 152；主体双轨不推断（`assertion_without_subject` 如实返回）、`ent_` 只取发号表缺号抛 ID_001、EvidenceLink 偏移 I-11 绝对逐字透传、同发号表字节确定 |

## 2. 主 Agent 验收附加判据（执行者不需要跑，但不得让其失败）

```bash
# 签名逐字：act/00–08 contract 中的函数名、参数名、返回键、检查名、artifact_type、task_id 在实现中逐字存在
# 独立性：gate.py 不 import packs/canonical/levels/step；acceptance.py 不 import packs/gate，不读取 run_m8 summary["gate"]
# 宿主有效性：legacy_collision_exposed 的数字由 fixture 重算（39/4/43），不是常量
# 生产代码不读文件：pipeline/dataset_compiler 非 tests 文件中，除 shim/m1_shim_source_assets.py 与 acceptance.py 外，不出现 open( / read_bytes / read_text / "_fixture"
# fail-closed：DEV_SEARCH、PUBLIC_RELEASE 失败运行后 Ledger 中上述四类子包修订数为 0；不存在第二个 m8 StepRun
# 披露不少报：fixture 上 known_defects 代码恰为六个；任何 entry.watermark 为 false 即 Gate 失败
# 矩阵外篡改（主 Agent 自定，不预告）：页图对象、OCR 页对象、corpus_spans、m3 StagePackage、m8 Checkpoint、ReleaseManifest、配置修订各至少 1 例
# 写入原子性：begin_step_run 之前被拒时 processing_runs、artifact_revisions、step_runs、audit_log 行数不变（resolve 阶段拒绝）
# 退出码：acceptance 注入异常 → 1；缺 fixture / 缺页图 / 缺依赖 → 3；m8-span-identity.sh 在副本假 verify.sh 下 → 1
# BLOCKED 行名：mentions_mapping、knowledge_chain 与 run_all 20.4/20.8 的「M4 Knowledge Extraction」「测试宿主匮乏」逐字属 §19 第一列
# 永不 PASS：run_all.sh 中不存在对 20.4、20.8 的 pass_line 调用
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py
$TL 2>&1 | tail -1
$TC 2>&1 | tail -1
$TD 2>&1 | tail -1          # ACT 00 起；K2 起不得出现 skipped
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?     # 2（不受本包影响）
bash openspec/acceptance/run_all.sh | tail -1                   # SUMMARY pass=2 fail=1 blocked=8
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/dataset_compiler|openspec/acceptance/m8-span-identity.sh|openspec/acceptance/run_all.sh'   # 空（run_all.sh 仅 ACT 08 允许出现）
```
