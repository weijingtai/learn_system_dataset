# T04 任务书（Windows 设备，2026-09-24）

> 派单人：本地主 Agent（Mac 上的 Claude Code 会话 **`【LearnSystem】 Dataset`**）。
> 执行人：Windows 设备上的 Claude Code 会话（就是你）。你可以自己写代码，也可以自己再派子任务，但**对结果负全责**。
> **读完本文件再读仓库根 `TODO.md`（唯一待办入口）的 T04 行。**

---

## 一、T04 要做成什么

**M1→M8 由调度器连成一条线。**完成判据（`TODO.md` T04 行原文，逐条都要达到）：

1. 登记表 `pipeline/contract_registry/registry.yaml` 里 M1–M8 **全部是生产模块**（fixture 导入只留作测试宿主，不在生产线上）
2. 调度器由 M1 推到 M8：只在规格规定的人工节点（**M4 提交、M6 审核、M7 裁决**）以 `awaiting_human` 暂停，经人工接口处理后自动续跑；**除这些节点外不需要任何手动推进**
3. 真书《乾元秘旨》在**账本副本**上由调度器从 M1 跑到 M8，产出 `knowledge_chain=compiled` 的 PublicationPackage（人工节点回放真书账本里已有的决定）
4. `bash openspec/acceptance/run_all.sh 20.1` PASS；20.2 保持 PASS

## 二、起点

- 代码：GitHub `weijingtai/learn_system_dataset`，分支 **`t04`**（主 Agent 已把两个半成品 `wip/t04a-handoff`、`wip/t04b-handoff` 合到最新主线上，没有冲突）。
- 挡着 T04 的 T03c（各阶段不许直接读账本内部）**已完成**，守护用例 `pipeline/contract_registry/tests/test_acceptance.py::test_t03c_packages_have_no_ledger_internals` 看着它。**你新写的代码也不许走后门**，这条用例会抓。
- 起点的测试红单见第六节。

## 三、分阶段（按顺序，每阶段结束提交并推送 `t04`）

| # | 阶段 | 要点 |
|---|---|---|
| 1 | 环境 | 第五节。跑一遍 11 包，和第六节红单对照，差异写进回报 |
| 2 | **T04A：M1→M6** | 读 `docs/handoff/t04a-ruling1.md`（4 条裁决，**必须照做**）与 `docs/handoff/t04a.report.md` 末尾「交接」。剩余：登记 M3（`run_m3_text`）、M4、M6（含 `resume_entry`）；把 M4 需要的 `technique_profile` 等运行配置接进 `pipeline/orchestrator/run_inputs.py`；按裁决 4 改写 20.1 判据与旧口径用例（每条写改前/改后/为什么）；`test_resume_token_never_persisted` |
| 3 | **T04B：M7→M8（含 T05f）** | 读 `docs/handoff/t04b.report.md` 末尾「交接」的「下一步」清单（18 项）与 `docs/handoff/t04b.md`。要点：登记 M7；`run_m8` 以 M7 Snapshot 为输入；把 `packs.build_knowledge_data_pack` / `build_graph_projection_pack` / `build_evidence_chain` 接进 `run_m8`（现在只有测试在调）；让 `pipeline/dataset_compiler/tests/test_t04b_m7_to_m8.py` 转绿。**阶段 2、3 文件基本不重叠，可以并行** |
| 4 | **全线集成 + 真书复验** | 调度器 M1→M8 全线用例（fixture `qianyuan_ed01_text`）；然后在真书账本**副本**上跑 M1→M8，人工节点回放账本里已有的决定；`run_all.sh 20.1` PASS |
| 5 | 收尾 | 11 包全套回归、`TODO.md` 更新 T04（完成判据逐条附证据）、推送 `t04`、通知主 Agent |

## 四、纪律（这条线踩过的坑换来的，违反即返工）

1. **不许放宽任何检查来换绿**：不改检测器范围、不写死期望值、不把 FAIL 改成 BLOCKED、不删不跳用例。
2. **先写测试确认转红（贴原文），再实现**；每个修复配篡改探针（把修复撤掉，指定用例必须转红）。
3. **R15**：每阶段至少一条**真实形状输入、从头走到尾**的用例；手工构造输入的单测只证明函数本身没错。
4. **新增的公开函数必须在非测试代码里有调用点**；只有测试在调的一律视为「没接上」（M8 那三个函数就是这个问题）。
5. **「各模块过了自己的验收」≠「已连通」**。说连通之前必须 `run_all.sh 20.1` PASS。
6. 测试不许默认宿主有什么：依赖真书账本、页图的用例按实际宿主算期望或 skip 并写明原因。
7. 真书账本 `var/ledgers/qianyuan_w8/` 是**只读正本**：一律复制到临时目录再跑，跑完核对正本 mtime/size 未变。
8. 不许推送或改写 `main`；只推 `t04`。合并由主 Agent 验收后做。
9. 人工节点只能走公开入口（M4 提交入口、`review/console.py` 公开 API、M7 裁决入口），**不许直接写账本伪造人工结果，不许手写金标**。

## 五、Windows 环境（必须在 Git Bash 里做）

```bash
git clone -c core.autocrlf=false -b t04 https://github.com/weijingtai/learn_system_dataset.git learn_system && cd learn_system   # 关 CRLF 转换：金标逐字节比对；先检出 main 会得到 2835 个 CRLF 文件
git switch t04
bash tools/setup_windows.sh                 # uv + Python 3.14 + .venv/bin 联接 + 冒烟
export PYTHONUTF8=1 LC_ALL=C.UTF-8 LANG=C.UTF-8   # 之后每次开 Git Bash 都要先执行
```

**私有数据**（真书账本 + 页图，**不在公开仓库**，在局域网私有 Gitea）：

```bash
git clone --depth 1 -b data/t04-private http://192.168.0.165:3000/xuan/learn_system.git ../t04data
(cd ../t04data && sha256sum -c SHA256SUMS)
mkdir -p var/ledgers && tar -xzf ../t04data/qianyuan_w8_ledger.tar.gz -C var/ledgers/
tar -xzf ../t04data/ocr_data_work.tar.gz -C ocr/
```

Gitea 要账号时向用户要，**不许写进任何文件**。连不上 Gitea（不在同一局域网）：阶段 1–3 照做，阶段 4 只做 fixture 全线，真书复验写进回报「待主 Agent 本机复验」。

**已知的 Windows 环境差异**（遇到先对照这里，不是你改坏的就记进回报、不要修）：

- 测试里会调 `bash` 子进程：必须从 Git Bash 启动，否则可能调到 WSL 的 bash 或找不到。
- 账本守护进程用 Unix 套接字（`AF_UNIX`）：`pipeline/ledger/tests/test_daemon.py` 等在 Windows 上可能红。流水线各阶段在同一进程里直接调账本服务，不受影响。
- `contract_registry` 的 20.7 需要 `sqlite3` 命令行：没有就会多一条红（TODO T15）。可以 `winget install SQLite.SQLite`。
- review 包有 2 条偶发失败的既有用例（TODO T16）：`test_console_rework_line`、`test_close_with_pending_exit_2`。

## 六、起点红单（主 Agent 在 Mac 上实测 `t04` 分支，有页图、有真书账本）

`t04` @ `0090a59`，Mac，有页图、有真书账本。**共 12 条红，全部是半成品带来的预期红**，其余 8 个包全绿、0 skip：

| 包 | 结果 | 红的用例 | 原因 |
|---|---|---|---|
| orchestrator | Ran 101，1 ERROR + 6 FAIL | `test_scheduler_drives_m1_to_m6_with_public_human_entries`（ERROR） | T04A 新全线用例；跑到 M4 报 `ExtractionRefused: 缺少 technique_profile`（运行配置未接进 `run_inputs`） |
| | | `test_blocked_line_exact_text_m4`、`test_fixture_yields_five_pass_one_blocked_exit_2`、`test_real_chain_reaches_m5_and_m8`、`test_shell_exit_2_on_fixture`、`test_first_slice_plan_runs_m1_m2_m3_m5_and_reports_gap`、`test_imported_stage_without_tasks_refused` | 锁着「首纵切 m1/m2/m3/m5」「m2 imported」「5 PASS 1 BLOCKED」等旧口径，按裁决 4 要改写 |
| contract_registry | Ran 47，3 FAIL | `test_imported_with_entry_forbidden` | T04A 改了登记表（M1/M2 不再是 fixture 导入），旧用例依赖旧条目 |
| | | `test_20_1_blocked_line_computed`、`test_full_summary_unchanged` | 20.1 的判据与汇总会随 T04 改变，按裁决 4 改写 |
| dataset_compiler | Ran 236，2 FAIL | `test_r15_full_stack_m7_to_m8_acceptance`、`test_run_m8_compiles_knowledge_graph_and_evidence_chains` | T04B 测试先行写的红用例，`run_m8` 尚未接 M7 与三个构建函数 |

其余：assembly 296、corpus_compiler 167、digitization 88、intake 40、knowledge_extraction 149、ledger 106、review 174、validation 118，全部 OK。

**T04 完成时这 12 条必须全部转绿**（改写旧口径的，每条在回报里写改前/改后/为什么；不许靠删除或 skip）。

## 七、沟通

- **主 Agent 会话名 `【LearnSystem】 Dataset`**：用 `ListAgents` 找到它，用 `SendMessage` 发消息。它能做设计裁决、能在 Mac 上复验真书。
- **什么时候发**：①环境搭好（一句话：基线与红单是否一致）；②遇到需要裁决的问题（见下）；③每个阶段完成（提交号 + 测试结果一行）；④全部完成。
- **需要裁决时**：在回报「## 待裁决」写清证据和候选方案、你倾向哪个，然后 `SendMessage` 给主 Agent，**等回复再动那一处**，其余不相关的继续做。
  超过 30 分钟没回复：选**最保守**的方案（不放宽检查、不改规格、不改冻结文件）继续做，在回报里标「未经裁决，待主 Agent 复核」。
- **需要停手问的情况**：要改只读或冻结的模块；规格有两种读法；要放宽某条检查才能过；真书复验结果与预期不符且判断不了原因。
- 回报文件：`docs/handoff/T04-WINDOWS.report.md`（随代码一起提交推送），按「## 环境」「## 阶段 N」「## 待裁决」「## 验证」组织，每做完一步追加，**证据贴原文**。
- 用户不会盯这件事，**不要去问用户**。所有问题找主 Agent。
