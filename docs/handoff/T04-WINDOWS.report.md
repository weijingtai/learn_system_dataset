# T04 回报（Windows 设备）

执行：Windows 11 上的 Claude Code 会话（协调者），子任务派给同会话的 Claude 子代理，结果由协调者复核后合入 `t04`。
任务书：`docs/handoff/T04-WINDOWS.md`。

---

## 环境

### 搭建过程（与任务书第五节的差异，逐条）

1. **克隆后 2835 个文件是 CRLF。** `git clone` 先检出默认分支 `main`（没有 `.gitattributes`），系统级 `core.autocrlf=true` 把它们转成了 CRLF；`git switch t04` 只重写了两分支之间有差异的 20 个文件，其余仍是 CRLF（`git ls-files --eol`：`i/lf w/crlf` 2835 条）。AGENTS.md 禁 `git reset --hard` / `git checkout -- .`，所以改为重新克隆：
   `git clone -c core.autocrlf=false -b t04 https://github.com/weijingtai/learn_system_dataset.git`，之后 `i/lf w/lf` 2855、`w/crlf` 0。
   **建议**：任务书第五节的 clone 命令加 `-c core.autocrlf=false -b t04`，否则 Windows 上会静默得到 CRLF 工作树。
2. **`uv python install 3.14` 在本机报错**（`Failed to create Python minor version link directory … os error 4390`），但 3.14.4 实际已装好；重跑仍报同样的错，`set -e` 使脚本中止。改为手工执行脚本的其余步骤（`uv venv .venv --python 3.14`、装依赖、`mklink /J .venv\bin .venv\Scripts`）。属本机 uv 的链接目录问题，未改 `tools/setup_windows.sh`。
3. **`requirements-dev.txt` 里的 `uvloop==0.22.1` 在 Windows 上装不上**（`RuntimeError: uvloop does not support Windows at the moment`），导致整份依赖安装失败。仓库代码里没有任何地方 import uvloop（只出现在 requirements-dev.txt），所以装了除它之外的全部依赖。**建议**：给该行加 `; sys_platform != "win32"` 环境标记。
4. **私有数据**：Gitea `data/t04-private` 克隆成功（未要账号）。`SHA256SUMS` 在本机被 autocrlf 转成 CRLF，`sha256sum -c` 读到带 `\r` 的文件名而失败；去掉 `\r` 后校验：`ocr_data_work.tar.gz: OK`、`qianyuan_w8_ledger.tar.gz: OK`。
5. **tar 包里带 592 个 macOS AppleDouble 伴生文件**（`._*`，内容是 `com.apple.provenance` 扩展属性；其中 558 个落在账本 `objects/` 下，如 `objects/._00`）。它们不是数据，但会混进账本对象目录，已在解压后删除（只删 `._*`、小于 8 KB 的文件）。**建议**：打包时用 `COPYFILE_DISABLE=1 tar …`。
6. 真书账本正本 `var/ledgers/qianyuan_w8/`：解压后立即记下全部 361 个文件的 size + mtime 指纹（协调者 scratchpad `ledger_master_fingerprint.txt`），收尾时核对。

Python 3.14.4（uv 管理），`.venv/bin` → `.venv/Scripts` 目录联接。所有测试在 Git Bash 下以 `PYTHONUTF8=1 LC_ALL=C.UTF-8 LANG=C.UTF-8` 运行。

### 基线（`t04@505fcb0`，Windows，有页图、有真书账本）

命令：逐包 `.venv/bin/python -m unittest discover -s pipeline/<包>/tests -t .`

| 包 | Windows 结果 | 与 Mac 红单（第六节）对照 |
|---|---|---|
| assembly | Ran 296 OK | 一致 |
| contract_registry | Ran 47，6 FAIL + 3 ERROR | Mac 的 3 条全在（`test_full_summary_unchanged` 在 Windows 上是 ERROR，见下 W5）；另 6 条 Windows 环境红 |
| corpus_compiler | Ran 167 OK（中间 `FAIL m3_acceptance …` 为已知噪声） | 一致 |
| dataset_compiler | Ran 236，2 FAIL | 一致（`test_r15_full_stack_m7_to_m8_acceptance`、`test_run_m8_compiles_knowledge_graph_and_evidence_chains`） |
| digitization | Ran 88 OK | 一致 |
| intake | Ran 40，1 FAIL | 多 1 条 Windows 环境红（W3） |
| knowledge_extraction | Ran 149，3 ERROR | 多 3 条 Windows 环境红（W2） |
| ledger | Ran 106，7 FAIL | 多 7 条 Windows 环境红（W1） |
| orchestrator | Ran 101，1 ERROR + 6 FAIL | 一致（7 条名单逐一相同） |
| review | Ran 174 OK | 一致（T16 的两条偶发本次未出现） |
| validation | Ran 118 OK | 一致 |

**结论：Mac 红单 12 条在 Windows 上全部复现；另有 17 条 Windows 环境红，均非代码改动造成，按任务书不修，逐类如下。**

- **W1 `AF_UNIX`（10 条）**：`ledger/tests/test_daemon.py` 7 条（`ledgerd 未创建 socket 文件`）；`contract_registry` 的 `test_ledgerd_adapter_smoke`、`test_repository_yields_four_pass_one_blocked_exit_2`、`test_shell_exit_2`（`storage_port_substitutable ledgerd_client: AttributeError: module 'socket' has no attribute 'AF_UNIX'`，退出码 1≠2）。任务书第五节已列。
- **W2 Windows 不能删除仍打开的文件（5 条 ERROR）**：`knowledge_extraction` 的 `test_register_profile_is_sealed_run_artifact`、`test_resolve_refuses_fixture_only_m3`、`test_resolve_refuses_without_m3`，`contract_registry` 的 `test_suite_covers_human_resume_path`、`test_normalize_outcome_strips_ids_and_times`。全部是 `TemporaryDirectory.__exit__` 删 `ledger.sqlite` 时 `PermissionError: [WinError 32]`；traceback 首段就是清理异常，没有断言失败（用例体已跑完，只是 Ledger 连接未在清理前关闭）。
- **W3 `write_text` 的换行转换（1 条）**：`intake` 的 `test_read_source_files_reads_utf8`。helper `pipeline/intake/tests/helpers.py:24` 用 `Path.write_text`，Windows 文本模式把 `\n` 写成 `\r\n`，读回的字节多了 `\r`。
- **W4 `verify.sh` 的路径（1 条）**：`contract_registry` 的 `test_20_10_blocked_line_computed`。`openspec/schemas/verify.sh` 把 Git Bash 路径 `/d/Programme/…/.venv/bin/check-jsonschema` 传给原生 Windows Python 的 `subprocess.run`，`FileNotFoundError: [WinError 2]`，20.10 因此 FAIL。
- **W5 GNU `paste` 的多字节分隔符（使 1 条 Mac 红变成 ERROR）**：`test_full_summary_unchanged` 在 Windows 上报 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xef in position 1631`。原因：`run_all.sh:84` 用 `paste -sd '；'` 拼接 M8 的多条 BLOCKED 理由；GNU paste 把 3 字节的「；」当 3 个单字节分隔符轮流使用，输出里出现孤立的 `\xef`（实测字节：`…T05f\xef\xbc\x89\xefgraph_projection…`）。Linux 上同样会发生；该行不在 20.1 段，按裁决 4 不改。

`run_all.sh` 全量（基线）：`SUMMARY pass=3 fail=3 blocked=5`，退出码 3。20.1 FAIL（旧口径 `EditionRun 段未按 m3→m5 推进`）、20.2 PASS、20.7 FAIL（`ge_ju_rules original_text 非空 0/496`，数据问题，本机有 sqlite3）、20.10 FAIL（W4）。

### 派工方式

用户要求用 tmux + Freebuff / command-code / agy / OpenCode 作执行者。Claude Code 自动模式把「在本仓库上启动第三方 AI 编程工具」判为数据外发并硬拦截（公开的 GitHub 副本、不含私有数据的 worktree 也拦），只有用户在自己的设置里加权限规则才能放开，已告知用户。
因此阶段 2、3 改由**同会话的 Claude 子代理**执行：各自一个 git worktree（`D:\Programme\t04w\t04a` 分支 `win/t04a`、`D:\Programme\t04w\t04b` 分支 `win/t04b`，均从 `t04@505fcb0` 分出），任务书在各自 worktree 的 `_brief/`（不进 git）。协调者复核（重跑测试、篡改探针、读 diff）后合入 `t04`。

---

## 待裁决

### Q1：M4「提交」节点怎么暂停（2026-09-24 13:10 发给主 Agent，发送失败：会话名不可达、旧 bridge 地址 409 失效）

**证据**

- `pipeline/knowledge_extraction/step.py` 的 `run_m4`：0 份提交件时，在 `begin_m4_step_run` 之前抛 `ExtractionRefused("没有已登记的提交件", code="REF_001")`；`pipeline/orchestrator/runner.py` 的 `run_legacy` 把它转成 `OrchestratorRefused` 异常抛出——不是暂停。
- M4 只在提交件齐了、`reconcile_lanes` 出现类别分歧时才 `await_human`（`step.py` `_run_after_begin`），登记表的 M4 队列名也是「M4 类别分歧」。
- T04A 半成品用例 `test_scheduler_drives_m1_to_m6_with_public_human_entries` 的形状：`run_until` 到 m3 停下 → 调度器空闲时经 `run_m4_submit` 交 6 份提交件 → `advance` 进 M4 → 因分歧停 `awaiting_human`。

**候选**

- (a) 保持该形状：提交件是 M4 开跑前的人工输入，M4 唯一的 `awaiting_human` 是分歧裁决；另让调度器在 M4 缺提交件时零写入返回 `refused`（理由写明「等待 M4 提交：经 `run_m4_submit` 公开入口交件」），不再抛异常。只改调度器 / 薄适配。
- (b) 把「M4 提交」做成真正的 `awaiting_human` 节点：M4 先开 StepRun、停下等提交件，交齐后 resume。要改 `knowledge_extraction` 的模块契约。

**倾向** (a)。**未裁之前**按最保守的做：保持现状形状（提交件在 m3 之后、m4 之前经公开入口交入），不实现任何「等提交」机制。标「未经裁决，待主 Agent 复核」。

### Q2：交完 M4 提交件后 `advance` 在 m4 永远 `blocked`（T04A 执行者 14:0x 上报；主 Agent 不可达，**协调者按最保守可行方案定，未经裁决，待主 Agent 复核**）

**证据**（执行者在 `win/t04a@cc0179f` 临时 Ledger 实测）

```
m4 StepRun 数: 6 状态: ['succeeded']
advance: blocked m4 reason= stage_package_valid step_result= None
   stage_package_valid False 承载 StagePackage 的有效运行数 = 0（须恰 1）
   output_contract False 缺少 produces 类型: ['candidate_package']
```

- `run_m4_submit` 每交一份提交件就开一个 stage=m4 的 StepRun；`knowledge_extraction/submit.py:26-35` 的 `begin_m4_step_run` 让同阶段第 2 个及以后的运行 `supersede` 前一个（G7-RULINGS 第 32/58 条，「续写而非替换」），所以交完 6 份后本阶段唯一的有效运行是最后一份提交件的运行。
- 真书账本副本核对同形：m4 七个 StepRun 依次 supersede，前 6 个各只写 `candidate_submission` + `stage_checkpoint` + `step_log` + `step_manifest`，第 7 个（assemble）才写 `candidate_package` 与 `stage_package`。
- `orchestrator/edition_run.py` 的 `advance`：有效运行非空、Gate 未过、无 waiting、无 failed → 一律 `blocked`，不调登记入口。Gate 判得对，不动。

**候选**（执行者给出）：A1 所有 stage 放行「成功无包」；A2 仅对描述符声明的 stage 放行；B 把「M4 提交」做成暂停（改 M4 模块契约）；C 提交件改为运行输入（取消人工节点，违背判据 ②）。

**协调者决定：A2 的收窄版**
- 登记表 m4 条目显式声明人工输入件类型（`candidate_submission`）；只许 `human_queue: true` 的模块声明，`check_registry` 校验。
- `advance` 只在以下全部成立时调登记入口：该 stage 描述符有此声明；每个有效运行都有该类型的 sealed 修订；没有任何有效运行写过描述符 `produces` 里的类型或 `stage_package`；无 failed、无 waiting。其余一律照旧 `blocked`（零写入）。
- Gate 不动；「成功但漏登记包」的模块（写过 produces 类型）照旧 `blocked`，不会被反复调起。
- 理由：A1 放宽面太大；B 改模块契约；C 违背判据 ②。本方案只让调度器认得 M4 既有的 supersede 续写设计，撤回只需删一个登记字段与一个分支。

### Q3：M1→M6 全线在宿主 `qianyuan_ed01_text` 上被 M5 的 adapter_notes 门禁必然卡死（T04A 执行者上报；**协调者不裁，升级主 Agent**）

**证据**（执行者在 `win/t04a@2b48aa9` 临时 Ledger 实测，全文见其回报「停手」段）

- Q2 修好后 M4 已通；`advance` 执行 m5 succeeded 后，下一步在 m5 返回 `blocked`（reason=`validation_passed`）。m5 Gate 八项只有 `validation_passed` 为假：M5 StagePackage `validation.passed=false`，`gate_results` `severe_error_count=384`、`pending_rework_count=1`。
- 384 条 error 全来自 `m5_adapter_notes` / `adapter_notes_truncation`（`pipeline/validation/adapter_notes.py`，W8 ACT 19 Q3 加的门禁：扫 M4 提交件 `adapter_notes` 的截断自述词表，命中即 error，明文「不得静默通过」）。
- 宿主 `m4/submission_{assertion,pattern,concept_mention}_b.yaml` 各含 4 条命中；既有用例 `validation/tests/test_adapter_notes.py::test_real_book_submission_notes_are_flagged` 断言 `submission_assertion_b.yaml` 恰命中 4 条——宿主与门禁互相锁死。
- 协调者补查真书账本副本：真书 M5 的 StagePackage `validation.passed=True`，但它是 2026-09-17 跑的，早于该门禁；按上述既有用例，**真书提交件在今天的 M5 上同样会命中**，阶段 4 的真书复验大概率卡在同一处。
- 附带发现（非根因）：`adapter_notes.submission_documents` 重复计数——38 个 m4 Checkpoint 都指向同一 assemble 运行，同一份提交件被登记 32 次（192 行 / 6 唯一，384 = 12×32）；去重后仍 12 条 error，门禁照样败。属 M5 侧真实缺陷，建议记 TODO。

**候选**（执行者给出）：P1 M5 门禁失败记录不阻断 `advance`（放宽调度器语义）；P2 全线判据降为 M1→M5（改裁决 4 判据 2）；P3 换一批不含截断自述的提交件（造数据，禁止）；P4 M4 人工节点确认截断自述（改规格，禁止）。

**协调者处理**：四个候选分别是放宽检查、改判据、造数据、改规格，没有一个是任务书允许我自选的「最保守方案」，且该门禁是主 Agent 自己在 ACT 19 Q3 定的口径——由主 Agent 裁。裁决前 T04A 只做不依赖 M5 的项；第 4/6 项与依赖新 20.1 口径的用例暂停。

---

## 阶段 3：T04B（M7→M8，含 T05f）—— 已合入 `t04`

执行：外部 Agent（agy，Claude Opus 4.6 → 额度用尽后换 Gemini 3.8 Flash Medium 收尾），分支 `win/t04b`，6 个提交（`255b584`→`f466b0a`）。执行者回报全文在其 worktree `_brief/T04B-worker.report.md`（不进 git），要点：

- 第 1 项 `255b584`：登记 `m7.incremental_assembly`（`human_queue: true`，薄适配 `pipeline/assembly/entry.py` 取该 EditionPart 最新 M6 包走创世）；M8 `consumes` 加 M7 `canonical_snapshot`；`RELEASE_STAGES=("m7","m8")`；`run_release` 逐段推进、某段未 succeeded 即停。5 条探针全部转红。
- 第 2 项 `5bf5cd7`+`6cd3a29`：`run_m8` 以 M7 Snapshot 为输入，实际调用 `entry_ids.allocate_entry_ids` → `packs.build_knowledge_data_pack` → `build_evidence_chain` → `build_graph_projection_pack`，三样 put/seal 进 Ledger 并入发布包，`knowledge_chain=compiled`。非测试调用点：`step.py:376`、`:681` 等（grep 已贴）。
- 第 3 项 `9c85b00`（协调者逐条核对了引用的规格原文）：`quote_hash_integrity` 按 I-11 绝对偏移（INTERFACES.md:559、G7-RULINGS 第 106 条 D1，删「猜局部」而非兼容两种）；`no_assertion_bypass` 与 `chain_closure` 同口径（第 107 条 Q-M8-01），无主体断言只在 `known_defects` 逐条如实披露时不判违约（INTERFACES §3.8）。新用例 `test_quote_hash_integrity_rejects_local_offsets_no_guessing` 在旧代码上**通过了 Gate**，改后失败——是收紧。**实际效果是更多合法情形判通过，标给主 Agent 复核。**
- 第 4 项 `1707301`：M8 验收 `knowledge_chain` / `graph_projection` 的「内容校验未实现 → FAIL」占位换成真校验（几十条失败路径，全过才 PASS）；`identity_migration` 按任务书保留 FAIL 占位并说明。
- 第 5 项 `f466b0a`：登记表驱动的 M7→M8 全栈用例（R15）。
- 第 6 项（只调研）：M7 人工节点续跑五处断裂（`step.py:121` 丢弃 resume_token；`entry.py` 只走创世；登记表无 `resume_entry`；`run_release` 无续跑；创世不暂停——这条是对的）。三个候选设计，倾向 A（仿 M4/M6 加 `resume_m7` + `resume_entry`）。见「## 待裁决」Q4。

**协调者验收（带页图，独立集成目录 `D:\Programme\t04w\int`）**：`test_t04b_m7_to_m8` Ran 20 OK；dataset_compiler Ran 264 OK（0 skip）；`python -m pipeline.dataset_compiler.acceptance --fixture mini_ed01 --check publication` → `SUMMARY pass=8 fail=0 blocked=3`（knowledge_chain / graph_projection / identity_migration 因该夹具无 M7 输入而 BLOCKED，与基线相同；BLOCKED 文案里「run_m8 尚未产出 KnowledgeDataPack（TODO.md T05f）」已过时，建议改成「本次运行无 M7 Snapshot 输入」）。执行者回归：assembly 298 OK(skip 2)、orchestrator 103 红 7 条（全部归 T04A）、contract_registry 48 红 9 条（= 3 T04A 旧口径 + 6 Windows 环境）。

### Q4：M7 人工节点（增量 Release）的暂停与续跑（待主 Agent 裁）

真书首个 Release 走创世路径不暂停，阶段 4 不受影响；但完成判据 ② 列了「M7 裁决」为人工节点。候选：A 仿 M4/M6 加 `resume_m7` + 登记表 `resume_entry`（动登记条目，不改 consumes/produces）；B 沿用现有 `decisions` 重跑整轮（旧 awaiting_human StepRun 成孤儿，需 supersede）；C 同 A 但在旧 StepRun 内重跑 assemble。执行者倾向 A。未实现。
