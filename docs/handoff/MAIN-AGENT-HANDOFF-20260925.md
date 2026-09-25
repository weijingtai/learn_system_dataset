# 主 Agent 交接（2026-09-25）—— 冷启动接手 T04 的裁决工作

本文给**下一个接手的 AI Agent**，假设它对本仓库一无所知。读完本文与它指向的三份文件，就能接替本会话的角色。

## 0. 先读什么（按顺序）

1. 仓库根 `TODO.md` —— 唯一待办入口。当前主线是 **T04**；其余条目的状态以它为准。
2. `docs/handoff/T04-WINDOWS.md` —— T04 任务书（完成判据 4 条、5 个阶段、纪律）。
3. `docs/handoff/T04-WINDOWS.report.md`（在 `t04` 分支）—— Windows 执行方的回报，含全部「待裁决」记录。
4. `docs/blackbox-spec-rework/G7-RULINGS.md` 第 107、109 条 —— 最近两条直接影响 T04 的裁决。
5. `AGENTS.md` —— 仓库纪律。

## 1. 本会话的角色

本会话（名 `【LearnSystem】 Dataset`，Mac 上）**不写代码**。它做三件事：

- **裁决**：Windows 上的 T04 会话遇到需要定夺的问题，用 SendMessage 发过来，本会话查代码与账本核实事实后回复裁决；涉及改规格、改判据、真书数据、人工决定（P7）的，**必须转给用户**，不许替用户定。
- **登记**：所有新问题、决定、待用户事项写进 `TODO.md`（T 系列 = 待办，U 系列 = 待用户决定）；影响规格的裁决写进 `G7-RULINGS.md` 追加条目。
- **验收合并**：T04 完成后由本会话验收 `t04` 分支并合入主线（尚未到这一步）。

用户（wjt）的要求原话：「M1→M8 连成一条线，M8 所有问题解决，M3 不许走后门。」纪律要点：不放宽检查；先写用例证明转红再修；每个修复配篡改探针；新增公开函数必须有非测试调用点；「完成」≠「已连通」（要 `run_all.sh 20.1` PASS）；真书账本正本只读，只在副本上跑；私有数据不进公开的 GitHub。

## 2. 执行方在哪、怎么联系

- **Windows 会话**：Claude Code，会话名 `learn_system M7 Gate对勘检查实现`，跨会话地址 `bridge:session_016dUcJ1jajbm1a6MuE1zxob`（用 `ListAgents` 能看到；用 `SendMessage` 回它，`to` 填这个地址）。它是协调者，把活派给它自己的子代理或本机执行器，自己只计划 + 验收，然后合入 `t04`。
- 它**不会去问用户**；找不到主 Agent 30 分钟后会选最保守方案并标「待复核」。接手者要尽快用 `SendMessage` 告诉它「主 Agent 换人了，地址是我」。
- 它只推 `t04` 分支到 GitHub `weijingtai/learn_system_dataset`（remote 名 `github`）。主线由本会话推 `github/main`。
- 私有数据（真书账本、页图）在局域网 Gitea `http://192.168.0.165:3000/xuan/learn_system.git` 分支 `data/t04-private`；Mac 上要用 `/usr/bin/git`。**账号不写进任何文件。**

## 3. 现在到哪了（截至 2026-09-25，`t04@cfe9feb`）

| 阶段 | 状态 |
|---|---|
| 1 环境 + 基线 | 完成。Mac 红单 12 条全部复现；另 17 条 Windows 环境红（AF_UNIX、WinError 32、CRLF、verify.sh 路径），按任务书不修 |
| 2 T04A：M1→M6 由调度器连通 | **完成**。`run_all.sh 20.1` PASS、20.2 PASS；orchestrator 120 全绿；validation 123 全绿。判据①②④达成 |
| 3 T04B：M7→M8 含 T05f | **完成并合入**。M7 已登记、run_release 逐段推进 m7→m8、run_m8 真编译知识包/证据链/图投影；Q4 的 M7 人工节点续跑（方案 A）也已合入 |
| 4 真书副本 M1→M8 | **进行中，刚撞上 4 处生产代码阻断**（Q6–Q9，见下），已裁；Windows 正按裁决重做 |
| 5 收尾 | 未开始 |

### 已裁决（都已回复 Windows，回报文件里有记录）

- Q1 M4 提交不是暂停节点，缺提交件时调度器零写入 `refused`。
- Q2 登记表 m4 声明 `human_input_artifact: candidate_submission`，调度器只在每个有效运行都有该类型 sealed 修订且未写包时才调入口（附两条件：check_registry 拒绝非 human_queue 的声明；提交件不齐时模块拒绝、零写入）。
- Q3 **用户 09-24 采「乙」→ G7-RULINGS 第 109 条**：M5 截断自述门禁改两级——逐条点名的略去记 warning 披露、不阻断；未点名的仍 error。已实现（`e8ac25f`）。
- Q4 M7 增量 Release 续跑采方案 A（`resume_m7` + 登记表 `resume_entry`）。已合入。
- Q5 阶段 4 形状采 (b)：空账本 `var/ledgers/qianyuan_t04/` 新建 EditionRun，调度器从 M1 真跑到 M8；人工节点回放真书账本副本里的决定（M4 按 dispute_id，M6 按 entity_id+decision_type），对不上就停手，不造决定；回放器是真工具 `pipeline/tools/replay_human_decisions.py`。真书源文件 = 宿主夹具 `pipeline/corpus/_fixture/qianyuan_ed01_text/`（sha256 三方一致已核）。
- Q6 **M6 从不把 pattern 排进审核队列**（`pipeline/review/inputs.py:161-169`），M7 创世却要求 pattern 已审 → 真书编不出 entry。裁：不放宽 genesis；新开 **T19** 让 M6 纳入 pattern；真书那 2 条 pattern 的决定由用户给（**U07，待用户**）。
- Q7 M7 准入门禁读 m6 的 IndexError：gate 取数规则不动，`run_release` 把 EditionRun 的 handle 交给准入门禁；先红后绿；补一条登记表驱动的 fixture 全栈用例走 `run_release`。
- Q8 M8 `_fail` 返回补 `processing_run_id`，批准。
- Q9 验收 `--ledger` 批准；offset 路线两项输出 `not_applicable`（第 107 条 Q-M8-08）而非跳过；`[]`→`.get()` 否决。

### 等用户的

- **U07**（`TODO.md` 二）：真书 2 条 pattern（「去官留煞」「贪合忘煞」）accept/reject 各一句理由。拿到后写成 `decisions_supplement.yaml`（actor_ref=user:wjt）交给 Windows 的回放器。没拿到之前真书全线只能跑到 M6 `awaiting_human` 停下，判据③不算达成。
- U01–U05 是早先的旧事项，不挡 T04。

### 主线尚未合并的东西

- `t04` 分支（GitHub `github/t04`）是 T04 全部工作；主线 `codex/docs/knowledge-compilation`（= `github/main`）只有裁决文档与 Windows 兼容修复。**T04 完成后由主 Agent 验收再合**，不要提前合。
- 主线上 TODO.md 由主 Agent维护；Windows 不改 TODO.md，只写它的 report。

## 4. 接手后第一件事

1. `git fetch github && git log --oneline github/main..github/t04` 看 Windows 新推了什么；读 `docs/handoff/T04-WINDOWS.report.md` 最新的「待裁决」段。
2. 用 `SendMessage` 给 `bridge:session_016dUcJ1jajbm1a6MuE1zxob` 发一句：主 Agent 已换人，新地址是你；请把未回复的请示重发。
3. 有 U07 答复就转给 Windows；没有就等。

## 5. 验证手段（Mac 本机）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export PYTHONUTF8=1 LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/<包>/tests -t .      # 逐包
bash openspec/acceptance/run_all.sh 20.1 20.2                         # 全线判据
```

真书账本正本 `var/ledgers/qianyuan_w8/` **只读**；要查就 `cp ledger.sqlite` 到 scratchpad 再开。
