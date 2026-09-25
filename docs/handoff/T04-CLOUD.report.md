# T04 阶段 4 云端回报（2026-09-25，云端 Claude 会话）

> 接手背景：本地主 Agent（Mac）与 Windows 协调会话都已额度用尽停手，交接见 `docs/handoff/MAIN-AGENT-HANDOFF-20260925.md`（main）与 `docs/handoff/T04-WINDOWS-HANDOFF.md`（t04）。用户让云端接着做。
> 分支：`claude/wizardly-maxwell-pqrzh9`，自 `t04@37599da` 快进；PR 目标 `t04`（不直接进 main）。
> 云端没有页图、没有真书账本：**真书副本全线（判据③）与阶段 5 的真数据回归只能在本机做**，本回报末尾写明交接。

## 一、进度（阶段 / 判据 / 百分比）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | 环境 + 基线 | ✅ |
| 2 | T04A：M1→M6 调度器连通（20.1 PASS） | ✅ |
| 3 | T04B：M7→M8 含 T05f | ✅ |
| 4 | 真书 M1→M8 | ⏳ 6 小步做完 4 步：Q8 ✅ Q7 ✅ Q9 ✅ T19 ✅；剩「真书跑到 M6 停」（本机）、「U07 后跑到 M8」（本机 + 用户决定） |
| 5 | 收尾：真数据 11 包回归、正本指纹、合并 | 未开始（本机） |

完成判据：① ✅ ② ✅ ④ ✅（20.1、20.2 云端复跑 PASS） ③ ⏳。整体约 **80%**（阶段 1–3 约占 70%，阶段 4 的代码部分已完）。

## 二、云端基线（`t04@37599da`，Python 3.14，`LC_ALL=C.UTF-8`，已补 `en_US.UTF-8` locale 与 `sqlite3`，见 TODO T15）

```
assembly 305 OK (skipped=2) | contract_registry 51 FAILED (failures=5) | corpus_compiler 167 OK
dataset_compiler 264 OK (skipped=53) | digitization 88 OK | intake 40 OK | knowledge_extraction 155 OK
ledger 106 OK | orchestrator 120 OK | review 174 OK | validation 123 OK
```

contract_registry 的 5 红逐条核实：
- 3 条（`test_modules_port_clean_passes_after_t03`、`test_repository_yields_four_pass_one_blocked_exit_2`、`test_shell_exit_2`）+ `test_20_10_blocked_line_computed`：**t04 上的真回归**——`7e2dd3f`（20.1 改到电子文本宿主）在 `pipeline/orchestrator/acceptance.py:467` 新增 `service.objects.get`，`modules_port_clean` 由 PASS 退为 FAIL（`FAIL modules_port_clean Orchestrator 越过 LedgerPort: pipeline/orchestrator/acceptance.py:467`）。Windows 回报把这几条归为环境红，漏看了。
- `test_full_summary_unchanged`：快照停在 T04 之前（期望 `pass=2 fail=1 blocked=8`，实得 `pass=3 fail=2 blocked=6`：20.1 转 PASS、20.10 被上一条拖成 FAIL）。

原 T14 的 6 条页图红在 t04 上已不再红（contract_registry 51 条修后全绿，orchestrator 120 全绿）。

## 三、逐项（每项先红后绿 + 篡改探针）

### 0. 后门回归（新发现，`352a9a8`）
- `orchestrator/acceptance.py:467` `objects.get` → `read_object`；`test_full_summary_unchanged` 同步 20.1 进展：改前 有账本 3/1/7、无账本 2/1/8 → 改后 有账本 4/1/6、无账本 3/1/7（**有账本一支云端测不到，须本机复验**）。
- 红：既有守护用例本来就红（上面原文）。绿：`contract_registry Ran 51 … OK`；`run_all.sh` 全局 `SUMMARY pass=3 fail=1 blocked=7`（20.1/20.2/20.3 PASS、20.7 FAIL、其余 BLOCKED 理由均为实测缺口）。
- 探针：改回 `objects.get` → `FAIL: test_modules_port_clean_passes_after_t03`。

### Q8 M8 失败返回补 `processing_run_id`（`046c026`）
- 红（电子文本路线，不依赖页图）：`KeyError: 'processing_run_id'`（经登记表 m8 绑定走 `run_legacy`）；`AssertionError: 'processing_run_id' not found in {'status': 'failed', …}`。
- 绿：两条均 OK；`dataset_compiler Ran 266 OK (skipped=53)`。
- 探针：值换成 `None` → 两条 FAIL。

### Q7 发布准入读 EditionRun 的 m6；Gate 按显式上游句柄判血缘；Gate 不过即停（`ce862a9`）
- **云端复现**（电子文本宿主，调度器推完 M1→M6 后按生产登记表 `run_release`）：m7 Gate `upstream_lineage` 在 M7 自建的 release run 里找 m6，永远找不到；m8 同样在自己的运行里找 m1–m3、m7；`run_release` 只看 StepRun 状态不看 Gate，照样推进到 m8。裁决 Q7 只点了 m6 一处；m7/m8 上游的查找位置与「Gate 不过即停」两点**经用户 09-25 确认**：显式告诉 Gate 上游在哪个运行、发布段 Gate 不过即停。
- 实现：`run_release(port, registry, edition_handle)` 先判 EditionRun 的 m6 Gate，不过即拒收、零写入；`evaluate_stage_gate(..., upstream_handles=None)` 只决定血缘去哪个运行找上游（仍只按句柄的运行号取数，不按 EditionPart 回退；不给时行为不变）；发布段某段 Gate 不 passed 即停。
- 红：5 条新用例 `TypeError: run_release() takes 2 positional arguments but 3 …`。绿：`orchestrator Ran 125 OK`。
- 探针：去掉准入 → `test_release_refused_zero_write_when_edition_m6_gate_not_passed` ERROR；Gate 忽略 `upstream_handles` → `test_release_reads_m6_from_edition_run_and_lineage_across_runs` FAIL；去掉「Gate 不过即停」→ `test_release_stops_when_m7_gate_blocked` FAIL。
- 改写既有用例（改前/改后/为什么写在用例旁）：两条桩 release 用例改为先推 EditionRun 到 m6；`test_t04b_m7_to_m8.py::TestReleaseSegmentThroughRegistry` 原在合成账本（M6 落在合成 release_run、无 M5，不是 EditionRun）上断言成功，Q7 下该世界本就该被准入拒收，改为断言拒收、零写入（不再依赖页图，dataset_compiler skip 53→52）；经登记表从真实 EditionRun 推 M7→M8 的全栈路径由新用例 `test_edition_run_text_chain.py::test_run_release_takes_the_edition_run_through_registered_m7_and_m8` 覆盖。

### Q9 M8 验收 `--ledger` 与 offset 档不适用披露（`3746aa1`）
- (i) `--ledger`：`LedgerReader`（mode=ro）只读判定既有账本，不装配宿主、不跑 M8；账本不存在 → BLOCKED 退出码 3。(ii) offset 档 `evidence_chain_closure` 的 `span_page_binding`、`glyph_anchor_closure` 事先声明不适用，以 `NOT_APPLICABLE` 写进判据说明，不静默跳过、不计通过。(iii) 未加任何 `.get()` 容错。
- 红：`SystemExit: 2`（未知参数）×2；`'span_page_binding: span_id 无法解析' unexpectedly found`。绿：3 条 OK；`dataset_compiler Ran 269 OK (skipped=52)`，`contract_registry Ran 51 OK`。
- 探针：`--ledger` 改为可写并跑 M8 → FAIL；去掉不适用披露 → FAIL。

### T19 M6 审核队列纳入 pattern（`8d81337`）
- 按裁决：`inputs.py` candidate_objects 加 pattern（kind="pattern"，entity_id=pattern_id）；`ENTITY_ID_KINDS`/`CANDIDATE_KINDS` 加 pattern；决定类型沿用 `required_decision_types`（pattern 得 `review_source_fidelity`，`school_ids` 非空另加学派归属）；`step.py`（关审 Gate 候选、modify 查原对象、carried 决定、reviewed_candidate 归属）、`rework.py`（两处候选清单）、`console.py`（查目标）同步；M6 验收「队列来自上游」的独立推导加 pattern；测试桩 `upstream_stub` 从数据文件读 patterns（缺省空，既有用例不变）。INTERFACES §3.5 卡片与 impl-06 README §5.1–§5.3 同步。`genesis.py` 一字未改。
- evidence_closure 覆盖 pattern：已审 pattern 须至少引一条本次已审断言。**这条规则是执行者提议（裁决只说「一并覆盖」），文档已标【讨论候选】，待复核。**
- 红：`'pat_qizheng_000001#review_source_fidelity' not found in [...]` 等 4 条。绿：`test_pattern_review` 5 条 OK。
- 探针（裁决指定）：只从审核队列删掉 pattern → `close_review` 失败，`reason: queue_coverage,outcome_consistency,package_counts`；M6 验收独立推导去掉 pattern → `队列项集合与独立推导不符: ['pat_qizheng_000001#review_source_fidelity']`。

### 全量回归（本分支 `8d81337` 之上，11 包）

```
assembly 305 OK (skipped=2) | contract_registry 51 OK | corpus_compiler 167 OK
dataset_compiler 269 OK (skipped=52) | digitization 88 OK | intake 40 OK | knowledge_extraction 155 OK
ledger 106 OK | orchestrator 125 OK | review 179 OK | validation 123 OK
```

对照基线：contract_registry 5 红 → 0；新增用例 dataset_compiler +5（Q8 2、Q9 3）、orchestrator +5（Q7）、review +5（T19）；skip 53→52（Q7 改写的用例不再依赖页图）；其余包条数与结果不变。T16 两条偶发用例本轮未出现。

## 四、新发现 / 待裁决

1. **【待裁决】offset 档 M8 验收 `evidence_chain_closure` 停在 `text_offsets`**：`KeyError: 'line_index'`（`dataset_compiler/acceptance.py:_check_text_offsets` 比对 `line_index`，电子文本 span 没有该字段）。候选：(a) offset 档只比对 offset/text/quote/content_status，`line_index` 与页子步同样声明不适用；(b) M3 电子文本 span 补 `line_index`；(c) 维持 FAIL。`.get()` 容错按 Q9 (iii) 否决。
2. **【待裁决】offset 档 `watermark_disclosure` `KeyError: 'highlight_level'`**：即 Q9 (iii) 被否决的那处，现如实 FAIL。需要定：电子文本路线的水印披露该有哪些字段。
3. **【待复核】T19 的 pattern 证据闭合规则**（见上）。
4. **【新缺口】返工传播不经 pattern 的 `assertion_ids` 传递**：`rework.py` 与 M6 验收的可达性只看 evidence/source_refs/subject/claim_refs，pattern 无 evidence，其引的断言被返工时 pattern 的审核决定仍会被沿用（carried）。T19 前 pattern 不入队，无此问题。建议入 TODO 新条目。
5. **电子文本宿主 `qianyuan_ed01_text` 的 M4 pattern 提交件为空**（`submission_pattern_a/b.yaml` `items: []`）：夹具全线 M7 Snapshot 0 条 pattern，M8 `publication_gate` 如实失败（`knowledge_chain, chain_closure`）。这不是 T19 能修的；真书账本里有 2 条 pattern（U07）。
6. **须本机复验**：`test_full_summary_unchanged` 有账本一支；`test_t04b_m7_to_m8.py` 其余依赖页图的用例（本次未改其断言，但 `run_release` 签名已变，页图用例里已无旧签名调用——云端 grep 核过）。

## 五、交给本机（真书）的下一步

1. 把本分支（经 PR 合进 `t04`）拉到 Windows 主克隆；**丢弃 `D:\Programme\t04w\s4` 里执行者擅改的 4 个生产文件**（Q7/Q8/Q9 已在本分支按裁决重做；`genesis.py` 的放宽本就被否决）。
2. `win/s4@22219b1` 上的回放工具 `pipeline/tools/replay_human_decisions.py` 与驱动 `run_real_book_t04.py` **只在 Windows 上，未推 GitHub**：合到本分支之上再跑。注意 `run_release` 新签名：`run_release(port, registry, edition_handle)`，传 EditionRun 句柄。
3. 真书跑到 M6：M6 队列现在会多出 2 个 pattern 项（`pat_qizheng_000001`「去官留煞」、`pat_qizheng_000002`「贪合忘煞」），账本副本里没有这两项的决定 → 按回放规则停在 M6 `awaiting_human`，等 **U07**（用户给决定，写成 `decisions_supplement.yaml`，actor_ref=user:wjt）。
4. U07 到手后跑到 M8：`python -m pipeline.dataset_compiler.acceptance --fixture pipeline/corpus/_fixture/qianyuan_ed01_text --check publication --ledger var/ledgers/qianyuan_t04`；上面第 1、2 条待裁决会在真书上同样出现。
5. 阶段 5：11 包真数据回归、真书正本指纹（`875139ae…f75b`）、`run_all.sh 20.1 20.2`、合并。
