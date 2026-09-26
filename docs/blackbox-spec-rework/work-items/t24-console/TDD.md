# TDD：T24 Web 控制台接真流程

`export LC_ALL=C.UTF-8`；`PY=.venv/bin/python`；
`TC="$PY -m unittest discover -s console_backend/tests -t ."`；在仓库根运行。

本文档只列**计划**的测试名、对应哪个 BDD 场景、断言要点，以及先红后绿的证据栏。
证据栏（Red 列）已按本次实际执行结果回填——因为本次没有写任何实现代码，*所有*计划中的新测试
现在都不存在，处于"红"的最强形式（ImportError/AttributeError：连测试文件本身都还没写）。
Green 列留空，由实现者填写。

## 0. 开工基线（本次已执行，回填证据）

```bash
export LC_ALL=C.UTF-8
.venv/bin/python -m unittest discover -s console_backend/tests -t .
```

实测输出（2026-09-26，本 worktree，`.venv` 由 `bash tools/jules_setup.sh` 装出）：

```
======================================================================
ERROR: console_backend.tests.test_api_and_ws (unittest.loader._FailedTest.console_backend.tests.test_api_and_ws)
======================================================================
ERROR: console_backend.tests.test_workbench_api (unittest.loader._FailedTest.console_backend.tests.test_workbench_api)
----------------------------------------------------------------------
Ran 6 tests in 0.001s
FAILED (errors=2)
```

根因（已查明，见 README.md §9）：`.venv` 里 `pydantic==2.13.5` 与 Python `3.14.0rc2` 的
`typing._eval_type` 不兼容，`import fastapi` 时构造 `fastapi.openapi.models.Contact` 触发
`TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`，最终以
`AssertionError` 形式向上抛出，两个测试模块都在 `from fastapi.testclient import TestClient`
这一行 import 失败。**这是本次开工基线的既有红，不是本次改动引入的**；已实测升级/降级
pydantic 均不能解决（README.md §9.1），**确切可用的修法是换 Python 解释器版本**
（README.md §9.2）：

```bash
uv venv .venv-py313 --python 3.13.12
uv pip install --python .venv-py313/bin/python -r requirements-dev.txt
export LC_ALL=C.UTF-8
.venv-py313/bin/python -m unittest discover -s console_backend/tests -t .
# 实测：Ran 22 tests in 0.297s / OK
```

这一步已列为 `act/01.yaml` 的前置修复步骤（第一步），实现者动手写 TDD.md 第 1 节的新测试前
必须先做，否则新写的测试无法跑（会在 import 阶段报同一个环境错误，而不是测出真正缺失的功能）。

其余 11 个 pipeline 包 + tools 基线（本次已执行，回填证据）：

```bash
bash tools/jules_setup.sh   # 环境搭建自带跑一次 unittest：Ran 106 tests in 8.993s / OK
```

`jules_setup.sh` 自带的 106 个测试跑在其内部选定的子集上，OK；11 个 pipeline 包与 pipeline/tools
各自单独跑（`.venv/bin/python -m unittest discover -s pipeline/<包>/tests -t .`）未在本次执行，
留给实现者开工时按 AGENTS.md 的测试命令逐包确认，作为本次文档工作不改动生产代码的旁证。

## 1. 场景 → 测试名 对照表

| 场景 | 计划测试名（`console_backend/tests/` 下新增） | 断言要点 | Red（本次实测） | Green（实现者回填） |
|---|---|---|---|---|
| S1 上传电子文本建 EditionRun | `test_create_edition_run_calls_start_edition_run` | mock/spy `orchestrator_client.start_edition_run` 被调用一次，参数含 `run_inputs={"route":"text",...}`；HTTP 响应含 `edition_run_id`/`edition_part_id` | `AttributeError`/`ModuleNotFoundError`：`console_backend.app.orchestrator_client` 不存在 | |
| S1 | `test_create_edition_run_rejects_non_text_route` | 上传时若用户选择非 text 路线，HTTP 400，不调用 start_edition_run | 同上（模块不存在） | |
| S2 自动推进到 M4 停下 | `test_auto_advance_stops_at_m4_awaiting_human` | 创建后台自动调用序列后，查状态端点返回 `stage=m4, status=awaiting_human`；`step_run_id`/`resume_token` 只在内存映射里，不出现在任何响应体或日志字符串 | 同上 | |
| S3 上传 M4 提交件 | `test_upload_m4_submission_calls_run_m4_submit` | spy `run_m4_submit` 被调用且 `edition_part_id` 一致；6 份文件对应 6 次调用；某份失败时该份状态单独显示 failed，不影响其余 5 份 | 同上 | |
| S4 M4 队列与逐条裁决 | `test_m4_queue_lists_all_disputes` | 队列端点返回的条目数与 Ledger 里 disputes 修订数一致（用测试账本造 fixture 数据） | 同上 | |
| S4 | `test_m4_ruling_submission_calls_record_category_ruling_with_user_actor` | 每次提交调用一次 `record_category_ruling`，`ruling_doc["actor_ref"]` 等于界面配置的用户身份，不等于任何 `agent:`/`ai:` 前缀 | 同上 | |
| S4 | `test_m4_resume_only_after_all_disputes_ruled` | 未裁决完时点"继续"返回 400（或队列未完成的明确错误），不调用 `human.resume` | 同上 | |
| S4 | `test_m4_resume_calls_human_resume_and_advances_to_m5` | 全部裁决完毕后点"继续"，`human.resume` 被调用一次，随后状态查询显示进入 m5 | 同上 | |
| S5 M5 自动过 | `test_m5_auto_advances_after_m4_resume` | resume 完成后无需用户操作，状态查询能看到 m5 succeeded（或如实的 gate 披露 warning 列表） | 同上 | |
| S5 | `test_m5_failure_shown_verbatim_and_blocks_m6` | 注入 M5 门禁 error，状态端点返回的失败原因字符串与后端底层返回一致（不改写措辞），且不推进到 m6 | 同上 | |
| S6 M6 审核队列 | `test_m6_queue_lists_all_candidates` | 队列条目数与 Ledger review_queue 修订一致，含 assertion/school_view/pattern 三种 kind | 同上 | |
| S6 | `test_m6_decision_submission_calls_record_decision_with_user_actor` | 每次提交调用一次 `record_decision`；`verdict=modify` 时必须带 `modified_content`，否则 HTTP 400（不让后端裸抛 `ReviewRefused` 到用户面前，界面要先挡一次并给出可读提示） | 同上 | |
| S6 | `test_m6_resume_calls_human_resume_and_completes_edition_run` | 全部决定完毕后 resume，随后 `advance` 返回 `action=="complete"`，状态端点显示 EditionRun 已收口 | 同上 | |
| S7 run_release 出 M8 | `test_run_release_after_completion_produces_publication_package` | 调用 `run_release`，状态端点返回 `knowledge_chain` 与 `publication_package_revision_id` | 同上 | |
| S7 | `test_download_publication_package_returns_sealed_bytes` | 下载端点返回的字节 sha256 与 Ledger 里该修订的 sha256 一致 | 同上 | |
| S8 失败如实显示 | `test_stage_failure_reason_matches_backend_verbatim` | 人为让某阶段返回失败，HTTP 响应里的 reason 字段与 Ledger/step_result 里的原始错误信息逐字一致（不是"处理中"或空字符串） | 同上 | |
| S8 | `test_status_query_survives_backend_restart_reads_from_ledger` | 重建一个新的 `orchestrator_client`（模拟进程重启，内存映射清空）后，状态查询仍能从 Ledger 只读入口查出 EditionRun 当前停在哪一步（stage + status），不依赖内存映射 | 同上 | |
| S8 | `test_awaiting_human_after_restart_reports_missing_resume_token_honestly` | 模拟重启后请求 resume 某个 awaiting_human 的 StepRun，界面/后端返回"需要重新获取恢复凭证"一类的明确提示，不假装成功、不抛未捕获异常 | 同上 | |
| S9 AI 预审建议展示 | `test_upload_ai_suggestion_file_validates_sha256` | 上传的建议文件 sha256 与后端重算不一致时拒绝导入并返回明确错误；一致时导入成功 | 同上 | |
| S9 | `test_m4_queue_response_includes_matched_suggestion` | 队列端点响应里每条 dispute 若有匹配建议，带 `suggestion` 子对象（choice/rationale/evidence_quotes/producer/generated_at/file_sha256 前 8 位） | 同上 | |
| S9 | `test_m4_queue_response_flags_unmatched_suggestions` | 建议文件里有队列中找不到的 `target_id` 时，响应里有单独的 `unmatched_suggestions` 列表，不影响其余条目正常返回 | 同上 | |
| S9 | `test_adopt_suggestion_does_not_auto_submit` | 前端"采纳建议"动作只是填充表单（本测试针对后端：确认存在一个"预填充"只读端点或前端纯本地行为，且它绝不触发 `record_category_ruling`/`record_decision`） | 同上 | |
| S9 | `test_ruling_rationale_appends_suggestion_provenance_when_shown` | 队列项曾返回过建议时，提交的 `ruling_doc["rationale"]` 末尾包含 `[AI预审建议] model_id=... generated_at=... suggestion_file_sha256=... adopted=<bool>` 且字段值与建议文件内容一致 | 同上 | |
| S9 | `test_ruling_rationale_has_no_suggestion_tag_when_no_suggestion_shown` | 队列项没有匹配建议时，提交的 rationale 不包含 `[AI预审建议]` 标记（防止误标） | 同上 | |
| S10 批量视图与进度 | `test_queue_endpoint_is_read_only_no_bulk_submit_route` | 契约测试：`console_backend` 路由表里不存在任何"批量提交决定"的端点（每次提交仍是单条 `queue_item_id`/`dispute_id`） | 同上 | |
| 端到端（宿主 fixture） | `test_end_to_end_qianyuan_text_host_reaches_m8_via_http_api` | 用 `pipeline/corpus/_fixture/qianyuan_ed01_text` 在临时账本上，全程只经 FastAPI `TestClient` 调用控制台端点（S1→S7 全序列，决定用测试里显式给出的裁决/审核结果，可参考
   `docs/handoff/U07-decisions_supplement.yaml` 的形状），断言最终 M8 succeeded 且能下载发布包 | 集成测试尚未写；合并 `claude/wizardly-maxwell-pqrzh9` 后 `run_inputs`/`route:text` 已在本分支存在（README §0 已核实签名），本条不再有分支阻断，直接按 README §6 的调用序列实现即可 | |
| 契约：不绕过 LedgerPort | `test_scan_ledger_internals_console_backend_is_empty`（放在 `pipeline/contract_registry/tests/`，新增一条独立用例，不是扩展 `test_modules_port_clean_*`——`modules_port_clean` 只按 `registry.yaml` 里登记的模块入口扫描，`console_backend` 不是登记模块，不会被它覆盖，需要单独调用 `scan_ledger_internals(["console_backend"])`） | `scan_ledger_internals(["console_backend"])` 返回 `[]` | **已实测基线**：改造前即为 `[]`（README §7.1），但这是"还没碰 Ledger"而不是"接了 Ledger 还干净"，红的地方是"这条回归用例本身还不存在"，不是数字不对；实现阶段接入 `orchestrator_client` 后要保证这条用例持续通过 | |
| 硬约束：resume_token 不落盘 | `test_resume_token_never_written_to_disk_or_log`（借用/仿照 `docs/handoff/t04a.report.md` 提到的 `test_resume_token_never_persisted` 思路） | 全流程跑完后，`grep -r <token明文> $TMP_LEDGER_DIR console_backend/` 与后端日志文件均无命中 | 未写 | |
| S8 恢复审核（候选 B，09-26 追加裁决） | `test_reissue_endpoint_requires_user_confirmation_reason` | 控制台"恢复审核"端点必须带 `reason` 字段（用户在确认框里填写/确认），缺失时 HTTP 400，不调用 `reissue_resume_token` | `console_backend.app.orchestrator_client` 尚不存在该端点 | |
| S8 | `test_reissue_endpoint_never_triggered_automatically` | 契约测试：状态查询端点（GET，只读）在处理请求过程中，即使发现内存映射缺 token，也不会触发任何写调用（spy 断言 `reissue_resume_token`/`record_*`/`resume` 均未被调用）——防止"查询时顺手自动重签" | 同上 | |

## 1.1 `reissue_resume_token`（LedgerPort 层，放 `pipeline/ledger/tests/`，候选 B，用户 2026-09-26 裁决）

这 5 条是**新增生产代码**（`pipeline/ledger/service.py`、`client.py`、
`pipeline/contract_registry/ports.py`，README.md §8.1/act §一之五）配套的测试，测试先行、
按 Red → Green 落地，每条都要有对应的篡改探针（探针用 `cp` 备份文件后恢复，不用
`git checkout`）：

| 测试名 | 断言要点 | 篡改探针 |
|---|---|---|
| `test_reissue_resume_token_allows_resume_with_new_token` | `await_human` 拿到 token1 后，调用 `reissue_resume_token(step_run_id, actor_ref="user:wjt", reason="后端重启")` 拿到 token2（`token2 != token1`），用 token2 调 `resume()` 成功（状态转 `running`） | 把 `reissue_resume_token` 里 `to_status` 硬编码写成 `"running"`（而不是 `"awaiting_human"` 自转）→ 本测试及 `test_reissue_rejects_when_not_awaiting_human` 转红；改回后转绿 |
| `test_old_resume_token_rejected_after_reissue` | 重签发后，用旧 token1 调 `resume()` 或 `record_human_event()` 必须抛 `InvalidResumeToken`（版本号不匹配） | 把 `reissue_resume_token` 里 `bound_version` 改成 `step["status_version"]`（不 +1）→ 本测试转红（旧 token 仍能用）；改回后转绿 |
| `test_reissue_rejects_when_not_awaiting_human` | StepRun 处于 `running`/`succeeded`/`suspended` 等非 `awaiting_human` 状态时调用，抛 `IllegalTransition`，`resume_token_hash` 不变 | 把前置条件检查删掉（或改成允许任意状态）→ 本测试转红；改回后转绿 |
| `test_reissue_writes_step_run_event_and_audit_log` | 调用后 `list_step_run_events(step_run_id)` 里出现一条 `event_type="resume_token_reissued"`，`actor_ref`/`reason` 与传入参数一致；`DirectLedgerAdapter(...).unwrap().store.count_audit()` 增加 1，且能读到 `action="reissue_resume_token"` 那一行（测试直接读 store，生产代码不许） | 删掉 `append_step_run_event`/`append_audit` 调用中的任意一处 → 本测试转红；改回后转绿 |
| `test_reissue_does_not_change_recorded_decisions` | 在 `awaiting_human` 期间先登记 1-2 条 `record_human_event`（部分裁决），调用 `reissue_resume_token`，断言 `list_human_events(step_run_id)` 前后完全一致，且用新 token 还能继续登记剩下的决定、再 resume 成功 | 让 `reissue_resume_token` 误删/清空 `human_events`（模拟实现错误）→ 本测试转红；改回后转绿 |

契约测试（`pipeline/contract_registry/tests/`）：

| 测试名 | 断言要点 |
|---|---|
| `test_ledger_port_methods_includes_reissue_resume_token` | `LEDGER_PORT_METHODS` 元组含 `"reissue_resume_token"`；`port_surface(DirectLedgerAdapter(...))` 与 `port_surface(LedgerdClientAdapter(...))` 都能看到它（回归钉住 §8.1 的"改一处、四处自动跟随"） |

## 2. 与主线 TDD 的关系

本文档不是独立验收单元；`console_backend` 目前没有加入 11 个包的验收矩阵，实现完成后应当
补一行进 `AGENTS.md` 的测试命令清单或另行说明为何不算作生产 pipeline 包（它是前端服务层，
调用 pipeline 但不属于 pipeline 内部 stage 模块）。这是 README §11 完成判据之外，留给实现者
在回报里说明的一点，本次不擅自决定。

## 3. 回归（每次改动后，实现者执行）

```bash
export LC_ALL=C.UTF-8
for pkg in intake digitization ledger review knowledge_extraction corpus_compiler validation orchestrator dataset_compiler assembly contract_registry; do
  echo "== $pkg =="
  .venv/bin/python -m unittest discover -s "pipeline/$pkg/tests" -t . 2>&1 | tail -3
done
.venv/bin/python -m unittest discover -s pipeline/tools/tests -t . 2>&1 | tail -3   # 若该目录存在
$TC 2>&1 | tail -5
cd console_frontend && npm install && npm run build   # 必须零错误
```
