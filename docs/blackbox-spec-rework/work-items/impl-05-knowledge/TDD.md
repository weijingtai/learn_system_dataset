# TDD：impl-05 M4 Knowledge Extraction 最薄接入

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；`TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."`；`TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."`；`TK="$PY -m unittest discover -s pipeline/knowledge_extraction/tests -t ."`；在仓库根运行。回归取行统一用 `2>&1 | grep -E "^(Ran|OK|FAILED)"`（G7-RULINGS §9.2 第 27 条）。

## 0. 开工基线（K1–K5 每组各一次；数字记入执行报告，后续回归与之逐字比较）

```bash
git status --short pipeline/knowledge_extraction openspec/acceptance/m4-stage-gate.sh   # 空
ls pipeline/knowledge_extraction 2>/dev/null | grep -v __pycache__ | wc -l   # K1: 0；K2: 起始应含 K1 文件
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                          # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1    # 与基线相同
bash openspec/schemas/verify.sh >/dev/null; echo $?                           # 0
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py; echo exit=$?   # 末行 fail=0 且 exit 0，且 candidate_submission/candidate_lane_set/dispute_queue/candidate_set/candidate_package 五个 PASS 行存在（第 54 条；不写死 pass 总数）
$TL 2>&1 | grep -E "^(Ran|OK|FAILED)"                                         # OK（记录用例数）
$TC 2>&1 | grep -E "^(Ran|OK|FAILED)"                                         # OK（K2 起必须是 impl-02 ACCEPTED 之后的值）
bash openspec/acceptance/run_all.sh | tail -1                                 # 记为 BASELINE_RUN_ALL
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?                   # 记为 BASELINE_M3
shasum -a 256 pipeline/corpus/_fixture/mini_ed01/spans.yaml                   # ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef
test ! -e pipeline/tools/import_legacy_candidates.py; echo $?                 # 0
ls pipeline/corpus/_fixture/mini_ed01/m4 2>/dev/null                          # K4 前必须列出附录 A 四个文件（D-02 独占 ACT，由主 Agent 落地），否则停手
grep -c 'for stage in ("m1", "m2", "m3")' pipeline/corpus/_fixture/mini_ed01/verify.sh  # K4 前须为 0（V5/V6 已扩展到 m4），否则停手上报
```

## 1. 逐 ACT 的 Red → Green

| ACT | Red（实现前） | Green（实现后） |
|---|---|---|
| 00 | `$TK` → ImportError | `$TK` OK，用例 ≥ 16 |
| 01 | 新增用例全 ERROR | `$TK` OK ≥ 41；金标装配 counts 与附录 A 一致；两次字节相同 |
| 02 | 新增用例全 ERROR | `$TK` OK ≥ 65；gate.py 无 `assemble`/`submission` import |
| 03 | 新增用例全 ERROR | `$TK` OK ≥ 81；`$TL`、`$TC` 与基线相同 |
| 04 | 新增用例全 ERROR | `$TK` OK ≥ 95；CLI assemble 三种退出码 0/2/4 |
| 05 | 新增用例全 ERROR | `$TK` OK ≥ 108；金标全路径 succeeded |
| 06 | 新增用例全 ERROR | `$TK` OK ≥ 120 |
| 07 | `m4-stage-gate.sh` 不存在（exit 127）；新增用例全 ERROR | `$TK` OK ≥ 131；`m4-stage-gate.sh` → `SUMMARY pass=13 fail=0 blocked=3`、exit 2 |
| 08（可选） | 新增用例全 ERROR | `$TK` OK ≥ 136；20.7 仍 FAIL |
| R82a | 新增 offset 级用例全 ERROR | `$TK` OK ≥ 145（新增 12 条：gate 5、assemble 4、acceptance 3）；`m4-stage-gate.sh` 输出与改前逐字一致（`pass=13 fail=0 blocked=3`，exit 2） |
| R82b | 新增真书端到端用例 ERROR | `$TK` OK ≥ 146；真书 M1→M2→M3（696 条 `offset_level` 片段）→ M4 五份提交登记 |

用例数阈值为该 ACT 完成后 `pipeline/knowledge_extraction/tests` 的**具名用例累计**；数值以 ACT 文件 `tests` 段列名逐条计数，实现不得少于该数。

## 2. 主 Agent 验收附加判据（执行者不需跑，但不得让其失败）

```bash
# 签名逐字：act/00–08 contract 中的函数名、参数名、返回键、检查名、task_id、artifact_type 在实现中逐字存在
# 独立性：gate.py 不 import assemble / submission；acceptance.py 不 import assemble / gate / submission，且不读取 run_m4 返回的 gate 报告作判定依据
# 生产代码不读 fixture：pipeline/knowledge_extraction 非 tests 文件不出现 "_fixture"（acceptance.py 只经 --fixture 参数读）
# 不调模型：grep -rE '^\s*(import|from) (requests|openai|anthropic|httpx)' pipeline/knowledge_extraction → 0；channel=model_adapter 在 begin 前拒收
# 状态上限 / P7：金标全路径后 Ledger 中 m4 修订的内容字节里不出现 "expert_verified" 与 "cross_model_reviewed"；无任何签发 StepRun
# 上游定位：resolve_m3_outputs 经 result_json["output_artifact_ids"] + artifacts.artifact_type 定位，不依赖 list_transformations 返回输出
# 路间隔离：每个 submit StepRun 的 frozen_inputs 恰为 {M3 包, corpus_spans}
# 写入原子性：begin_step_run 之前被拒时 artifact_revisions、step_runs、audit_log 行数不变
# 字节确定：两个临时 Ledger 独立跑金标全路径，candidate_set 字节相同，sha256 等于 expected/m4 manifest.content_sha256
# 20.7：run_all.sh 20.7 仍 FAIL；pipeline/tools/import_legacy_candidates.py 不存在；20.6 仍 BLOCKED
# 矩阵外篡改（主 Agent 自定，不预告）：提交件、technique_profile、corpus_spans、dispute_queue、human_event、Checkpoint、StagePackage、配置修订各至少 1 例
# BLOCKED 行名：三行说明中的「M4 Knowledge Extraction」「M3 Corpus Compilation」「Contract Registry」逐字属 §19 第一列
# D-06 证据复现：canon 全部字面对 mini_ed01 43 条 Span 子串匹配 → 6 次命中且全为误命中（5×「辰」、1×「胎」）
# 坐标一致性：candidate_set 证据 start_offset/end_offset 为页块绝对偏移（见 README §6.3 与 §10 N3）
```

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1
bash openspec/schemas/verify.sh >/dev/null; echo $?
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py; echo exit=$?   # 末行 fail=0 且 exit 0；M4 五类型 PASS 行存在（第 54 条）
$TL 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TC 2>&1 | grep -E "^(Ran|OK|FAILED)"
$TK 2>&1 | grep -E "^(Ran|OK|FAILED)"
bash openspec/acceptance/run_all.sh | tail -1            # == BASELINE_RUN_ALL
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo $?   # == BASELINE_M3
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/knowledge_extraction|openspec/acceptance/m4-stage-gate.sh'   # 空（只看本批改动；其他 Agent 的并行改动由主 Agent 甄别）
```
