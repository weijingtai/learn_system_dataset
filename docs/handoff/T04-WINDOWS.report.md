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
