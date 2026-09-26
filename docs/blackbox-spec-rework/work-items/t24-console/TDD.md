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
这一行 import 失败。**这是本次开工基线的既有红，不是本次改动引入的**；实现者动手前必须先处理
（见 README.md §9 修法候选），否则新写的测试无法跑。

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
   `docs/handoff/U07-decisions_supplement.yaml` 的形状），断言最终 M8 succeeded 且能下载发布包 | 集成测试尚未写；且见 README §0——本分支缺 T04 基础设施，此测试要求的 `run_inputs`/`route:text` 支持在本分支尚不存在，实现者必须先解决 README §0 的分支阻断，否则这条测试连"红"都红不对（会红在"入口不支持该参数"而不是"功能未实现"） | |
| 契约：不绕过 LedgerPort | `test_scan_ledger_internals_console_backend_is_empty`（放在 `pipeline/contract_registry/tests/`，扩展现有 `test_modules_port_clean_*` 同类用例，把 `console_backend` 纳入扫描目标） | `pipeline.contract_registry.acceptance` 的扫描器对 `console_backend/` 返回空列表 | 尚未确认 `scan_ledger_internals`/`modules_port_clean` 当前扫描目标是否已含 `console_backend`（README §7 已列为待核实）；若扫描器只扫 `pipeline/` 目录，需要新增一条把 `console_backend` 纳入扫描范围的用例（这属于扩展契约注册表，不算"改 pipeline 生产代码逻辑"，但改动前要停手确认这不会被算作放宽检查） | |
| 硬约束：resume_token 不落盘 | `test_resume_token_never_written_to_disk_or_log`（借用/仿照 `docs/handoff/t04a.report.md` 提到的 `test_resume_token_never_persisted` 思路） | 全流程跑完后，`grep -r <token明文> $TMP_LEDGER_DIR console_backend/` 与后端日志文件均无命中 | 未写 | |

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
