# TDD：T06 M4 本机模型适配器

`export LC_ALL=en_US.UTF-8`；`PY=.venv/bin/python`；
`TK="$PY -m unittest discover -s pipeline/knowledge_extraction/tests -t ."`；在仓库根运行。

本文档只覆盖**阶段 C**（实现阶段）的单测；阶段 A（探测）不产生代码，用 §1 的记录
格式代替测试；阶段 B（渠道开放）是用户决定，不是测试对象。阶段 C 的单测**不得真调
模型**——用可执行的假命令（写死输出的脚本，放 `pipeline/knowledge_extraction/tests/
data/fake_models/`）验证 Adapter 的调用协议、字段填写、失败处置；真模型只在
`act/01.yaml` 阶段 C 第 6 步「验收」里手工跑一次，不进 CI/单测。

## 0. 开工基线

```bash
git status --short pipeline/knowledge_extraction docs/blackbox-spec-rework/work-items/t06-model-adapter   # 空（除本次新建的三份任务文档）
ls pipeline/knowledge_extraction/adapters                                                                  # __init__.py registry.py task_pipeline.py（无 freebuff.py / opencode.py）
grep -n "model_adapter" pipeline/knowledge_extraction/__init__.py                                          # 17: CHANNELS 含；18: ACCEPTED_CHANNELS 不含
$TK 2>&1 | tail -1                                                                                          # 记录当前 OK 数（用作后续「用例数只增不减」的基线）
bash openspec/acceptance/m4-stage-gate.sh 2>&1 | tail -1                                                   # SUMMARY pass=13 fail=0 blocked=3（cross_model_extraction 在内）
python -c "import yaml; r=yaml.safe_load(open('pipeline/contract_registry/registry.yaml')); print([a for a in r['ports'] if a['port_id']=='model'])"   # adapters: []
```

`docs/handoff/ASK-2026-09-26.reply.md` 已随 `claude/wizardly-maxwell-pqrzh9`
（提交 `7ddea59`）合入当前分支，直接读文件即可：

```bash
sed -n '/^## 3\./,/^## 4\./p' docs/handoff/ASK-2026-09-26.reply.md
```

若在某个更旧的 worktree/分支上执行本文档、上述文件读不到，先按协调者指示
`git merge claude/wizardly-maxwell-pqrzh9`（本地分支，只 merge、不 rebase、不
reset），再重新核实本文档与 `README.md`/`act/01.yaml` 里的每个路径和行号——
不要在缺这次合并的基线上照抄行号。

## 1. 阶段 A（探测）：记录格式，不是测试

对 FreeBuff、OpenCode 各跑同一个固定 prompt 三次（不用 tmux 附着、不用屏幕抓取），
每次记录进 `docs/handoff/T06-phase-a.md`，逐项：

| 字段 | 要求 |
|---|---|
| 命令 | 完整命令行（含所有参数），可复制重跑 |
| 退出码 | 三次分别记录；不一致要停手写「不确定性可复现」|
| 耗时 | 三次分别记录（秒） |
| 原始输出前 200 行 | 逐字贴出，不截断到"看起来完整"就停 |
| 是否确定性可复现 | 三次输出内容是否一致或语义一致（模型输出允许措辞不同，但**格式**必须每次都能被脚本解析）|
| 结论 | 「可非交互调用」/「不可非交互调用，原因：…」|

**停手条件**（写入 §0.6 场景 2）：FreeBuff 与 OpenCode 都不可非交互调用 → 停手，
不进入阶段 B/C，`docs/handoff/T06.report.md` 顶部写明「T06 阶段 A 不通过」。

## 2. 阶段 C 契约（供以下测试对照，非规格新增，Phase B 批准后才落地）

```python
# pipeline/knowledge_extraction/adapters/freebuff.py（结构对 opencode.py 完全对称，
# 唯一差异是默认命令模板与默认 model_id）
class AdapterCallFailed(ExtractionRefused):
    """Model Adapter 调用失败（超时/非零退出/非法输出），fail-closed，不吞错。"""

class FreeBuffModelAdapter:
    def __init__(self, *, command, model_id, timeout_seconds=120):
        # command：可执行文件路径或参数列表模板；测试传入假脚本路径
        ...

    def extract(self, *, prompt_bytes, task_id, category, lane, technique_id,
                seg_span_map=None):
        """调用命令行工具，返回已校验的提交件 dict（validate_submission 之后的形态）。

        失败（超时/非零退出/非 UTF-8/非法 YAML・JSON/normalize_task_output 拒绝）
        一律抛 AdapterCallFailed，不返回部分结果、不吞掉候选。
        成功时 producer = {
            "kind": "model", "name": "freebuff:<model_id>",
            "model_id": <实际调用的模型名，来自命令输出或构造参数>,
            "prompt_sha256": sha256_hex(prompt_bytes),
            "response_sha256": sha256_hex(<命令原始 stdout 字节>),
        }
        """
```

## 3. 逐条测试

### 3.1 `pipeline/knowledge_extraction/tests/test_model_adapter_freebuff.py`（新建）

| 测试名 | 准备 | 动作 | 断言 | 先红原因 | 篡改探针 |
|---|---|---|---|---|---|
| `test_extract_calls_fake_command_and_returns_submission` | 假脚本 `data/fake_models/freebuff_ok.sh`：读 stdin 的 prompt，写死输出一份合法 YAML（`assertion: [...]`，1 条候选）到 stdout，`exit 0` | 用假脚本路径构造 `FreeBuffModelAdapter`，调 `extract(prompt_bytes=..., task_id="t1", category="assertion", lane="a", technique_id="qizheng")` | 返回值通过 `validate_submission`；`items` 长度为 1；`channel == "model_adapter"` | `freebuff.py` 不存在 → `ImportError` | cp 备份假脚本，改成输出空 stdout；测试须转红（返回值不再有 1 条候选或抛异常而非静默返回 `items: []`），验证后 `cp` 恢复 |
| `test_producer_fields_are_filled_from_real_bytes` | 同上假脚本，prompt_bytes 用固定字节 `b"PROMPT-FIXTURE"` | 调 `extract(...)` | `producer["kind"] == "model"`；`producer["prompt_sha256"] == sha256_hex(b"PROMPT-FIXTURE")`；`producer["response_sha256"] == sha256_hex(<假脚本实际 stdout 字节>)`；`producer["model_id"]` 等于构造 Adapter 时传入的 `model_id`（不是空、不是占位符） | 函数不存在或 producer 字段为 `null` | 改假脚本让 stdout 多加一个换行 → `response_sha256` 断言必须跟着变（证明是真算的哈希，不是写死值）；验证后恢复 |
| `test_timeout_raises_adapter_call_failed` | 假脚本 `freebuff_hang.sh`：`sleep 5` | 用 `timeout_seconds=1` 构造 Adapter，调 `extract` | 抛 `AdapterCallFailed`；异常信息含"超时"或"timeout"字样；**不返回**任何提交件 | 超时处理未实现 → 测试挂起或直接返回垂悬结果 | 把 `timeout_seconds` 改成 10（大于 sleep 时长）→ 测试须转红（不再抛异常）；验证后改回 1 |
| `test_nonzero_exit_raises_adapter_call_failed` | 假脚本 `freebuff_fail.sh`：`echo "boom" >&2; exit 7` | 调 `extract` | 抛 `AdapterCallFailed`；异常信息含退出码 `7` 与 stderr 片段 `boom` | 未检查退出码 → 静默返回空/半份结果 | 改假脚本 `exit 0` → 测试须转红（不再抛异常）；验证后改回 `exit 7` |
| `test_invalid_yaml_output_raises_not_silently_dropped` | 假脚本 `freebuff_garbage.sh`：`echo "{not: valid: yaml::"` | 调 `extract` | 抛 `AdapterCallFailed`（或底层 `SchemaViolation` 被包装转发），异常链可追溯到"解析失败"；**不允许**返回 `items: []` 当作"没有候选" | 未做 YAML 解析异常处理 → 崩溃在别处或被吞掉 | 改假脚本输出合法但空文档 `assertion: []` → 这次必须**不抛异常**、返回 `items: []`（区分"解析失败"与"如实空产出"两种情况的护栏），验证两条边界后恢复 |
| `test_pattern_category_round_trips_through_task_pipeline` | 假脚本输出顶层键 `pattern: [{name: 测试格局, assertion_propositions: [...], evidence: [...]}]` | 调 `extract(..., category="pattern", ...)` | 返回提交件 `category == "pattern"`，`items[0]["name"] == "测试格局"` | `normalize_task_output` 目前只支持 assertion/concept_mention（`task_pipeline.py:125-134`），传 `category="pattern"` 会抛 `SchemaViolation(SCH_002)` — **这是本测试的先红证据**，必须在实现 `_pattern_items` 后才转绿 | 删掉 `_pattern_items` 里对 `name`/`assertion_propositions`/`evidence` 任一必填键的检查 → 缺键输入不再报 `SchemaViolation`，测试须能检出（需另加一条缺键用例，见下） |
| `test_pattern_missing_required_key_raises_sch_001` | 假脚本输出 `pattern: [{name: 测试格局}]`（缺 `assertion_propositions`/`evidence`） | 调 `extract(..., category="pattern", ...)` | 抛 `SchemaViolation`，`code == "SCH_001"` | 同上，缺键检查未写 | 去掉 `assertion_propositions` 的必填检查一行 → 该测试须转红；验证后恢复 |

### 3.2 `pipeline/knowledge_extraction/tests/test_model_adapter_opencode.py`（新建，对称）

与 3.1 逐条对称（`OpenCodeModelAdapter`、假脚本目录
`data/fake_models/opencode_*.sh`），额外一条护栏证明「两个 Adapter 不是同一个类的
别名」：

| 测试名 | 准备 | 动作 | 断言 | 先红原因 | 篡改探针 |
|---|---|---|---|---|---|
| `test_freebuff_and_opencode_are_distinct_adapter_classes` | 两个 Adapter 都已实现 | `FreeBuffModelAdapter is not OpenCodeModelAdapter`；分别构造后 `type(a) != type(b)` | 两者是不同类，且默认 `model_id` 不同 | 若 T06 图省事把 OpenCode 实现为 FreeBuff 的子类换个默认参数，本测试仍应通过（只要求类不同、默认模型不同）；若直接 `opencode = freebuff` 起别名，本测试失败 | 把 `OpenCodeModelAdapter = FreeBuffModelAdapter` 起别名 → 测试转红；验证后恢复 |

### 3.3 `pipeline/knowledge_extraction/tests/test_task_pipeline_adapter.py`（既有文件，新增用例）

在既有 `_assertion_items` / `_concept_mention_items` 测试旁新增：

| 测试名 | 准备 | 动作 | 断言 | 先红原因 | 篡改探针 |
|---|---|---|---|---|---|
| `test_normalize_task_output_supports_pattern_category` | `doc = {"pattern": [{"name": "甲", "assertion_propositions": ["p1"], "evidence": [{"source_span_id": "ss_x", "support_type": "direct"}]}]}` | `normalize_task_output(doc, category="pattern", lane="a", channel="task_pipeline_manual", technique_id="qizheng", producer={...})` | 返回提交件通过 `validate_submission`；`items[0]["name"] == "甲"` | 当前 `normalize_task_output` 对 `category="pattern"` 直接抛 `SchemaViolation(SCH_002)`（`task_pipeline.py:130-134`）| 把新增的 `_pattern_items` 分支删掉一行必填键检查 → 上面 3.1 的缺键用例转红，本测试仍应绿（正常输入不受影响），用于确认改动只加能力不破坏形状校验 |

### 3.4 `pipeline/knowledge_extraction/tests/test_submit.py`（既有文件，新增用例；仅当
Phase B 选定「新增 model_adapter 渠道」方案后才写）

| 测试名 | 准备 | 动作 | 断言 | 先红原因 | 篡改探针 |
|---|---|---|---|---|---|
| `test_run_m4_submit_accepts_model_adapter_channel` | 临时 Ledger，走 M1→M2→M3（用 `test_qianyuan_text_host.py` 或 mini_ed01 的既有 setUp 套路）；提交件 `channel="model_adapter"`，`lane="a"` | 调 `run_m4_submit(...)` | `status == "succeeded"`；`collect_submissions` 能看到 `assertion/a` | 改动前 `ACCEPTED_CHANNELS` 不含 `model_adapter`（`__init__.py:18`），会在 `submit.py:84` 抛 `ExtractionRefused` | 把 `ACCEPTED_CHANNELS` 改回只含两项 → 本测试须转红；验证后恢复为含三项（`fixture_gold, task_pipeline_manual, model_adapter`） |
| `test_run_m4_submit_still_rejects_lane_c_unless_approved` | 同上，`lane="c"` | 调 `run_m4_submit(...)` | 若 Phase B 未批准开放 lane c：仍抛 `ExtractionRefused`（`submit.py:84` 的 `doc["lane"] == "c"` 分支不变）；若 Phase B 已批准开放 lane c（需额外用户批准，见 README §3）：改为另一条测试断言接受 | 视 Phase B 结论二选一，执行者按 `act/01.yaml` 实际批准结果写死其一，不许同时写两种断言互相矛盾 | 把 `submit.py:84` 的 `or doc["lane"] == "c"` 删掉 → 若测试断言"仍拒绝"，测试须转红；验证后恢复 |

### 3.5 `pipeline/knowledge_extraction/tests/test_acceptance.py`（既有文件，新增用例）

| 测试名 | 准备 | 动作 | 断言 | 先红原因 | 篡改探针 |
|---|---|---|---|---|---|
| `test_cross_model_extraction_computed_when_two_model_lanes_present` | 在 mini_ed01 金标基础上追加两份 `channel="model_adapter"` 的 lane a/b 提交件（producer.model_id 不同），跑 `pipeline.knowledge_extraction.acceptance.main(["--fixture", ...])` | 断言输出里 `PASS cross_model_extraction`（不再是 `BLOCKED`）；`SUMMARY` 的 `blocked` 数比开工基线少 1 | 当前 `cross_model_extraction` 在 `BLOCKED_CHECKS` 静态元组里（`acceptance.py:92-96`），`main()` 对它无条件打印 BLOCKED（`acceptance.py:658-660`），不读任何实际提交件 | 把新写的判定函数改成恒定 `return []`（恒 PASS，不再检查 lane 是否真为两个不同模型）→ 需另加一条"只有一路 model_adapter 也判 PASS 就是假绿"的用例（见下一行）来抓这种回退 |
| `test_cross_model_extraction_stays_blocked_with_only_one_model_lane` | 只追加一份 `channel="model_adapter"` 提交件（lane a），lane b 仍是 `fixture_gold` | 跑 `acceptance.main(...)` | 输出仍是 `BLOCKED cross_model_extraction`（理由改为「只有一路接入 Model Adapter，未满足 A/B 两路独立抽取」或等价明确文案），不得是 `PASS` | 若判定函数写成"只要出现过一次 `model_adapter` 渠道就 PASS"，这是假绿——本测试专门抓这种偷懒实现 | 把判定条件从"两个不同 producer.model_id 且各自 lane∈{a,b}"放宽成"至少一次 model_adapter"→ 本测试须转红；验证后恢复严格条件 |

## 4. 篡改探针的通用规矩

- 每条探针前 `cp` 备份被改的文件（`cp X X.bak`），改完跑对应测试确认转红，再
  `cp X.bak X` 恢复、删 `.bak`、重跑确认转绿。**不使用 `git checkout --`
  或 `git stash`**（AGENTS.md Git 安全铁律第 2 条禁止后者；`cp` 备份/恢复不受影响）。
- 假脚本（`data/fake_models/*.sh`）本身要在测试目录里登记 sha256（沿用
  `impl-05-knowledge` 的 `SHA256SUMS` 惯例），防止假脚本被静默改动而测试却不察觉。
- 任何一条篡改探针「改了却没转红」，视为测试本身是假的，必须重写测试直到探针
  能可靠转红，不许跳过或删探针。

## 5. 回归（每个 Phase C 子步骤后）

```bash
$TK 2>&1 | tail -1                                                    # OK，用例数只增不减；skipped 数不得从 0 变为非 0
bash openspec/acceptance/m4-stage-gate.sh 2>&1 | tail -1              # SUMMARY：cross_model_extraction 若已改判定则 pass+1 blocked-1；
                                                                       # semantic_span_input / term_layering_scan 两项必须仍是 BLOCKED，逐字理由不变
python -m pipeline.contract_registry.acceptance 2>&1 | tail -3        # other_ports_adapters 一行的 model= 计数应仍为旧值（T06 不改 registry.yaml，
                                                                       # 计数变化是 T03b 的事；本命令只用于确认 T06 没有意外碰到这个文件）
git status --short pipeline/contract_registry pipeline/ledger pipeline/dataset_compiler pipeline/orchestrator openspec   # 空
git diff --check
```
