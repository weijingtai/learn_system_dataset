# T04 Windows 协调者交接（冷启动用，2026-09-25）

接手者：任何 AI Agent。读完本文件即可继续，不需要之前的对话。协调者的职责是**计划 + 验收**：写任务书派给外部 Agent（tmux 里的 Freebuff / agy / OpenCode），验收它们的 diff、测试输出、篡改探针；自己只修花费极少的 bug。命令与测试尽量交给外部 Agent 跑，节省协调者 token。

## 1. 当前状态一句话

T04 五个阶段中 1、2、3 已完成并推送到 `t04@cfe9feb`；`run_all.sh 20.1` 已 PASS。**阶段 4（真书副本 M1→M8）卡在 4 处待裁决（Q6–Q9），已发主 Agent，等回复。** 阶段 5 未开始。

完成判据（TODO.md T04 行）：① 登记表 M1–M8 生产模块 ✅ ② 调度器 M1→M8、仅 M4/M6/M7 人工节点暂停 ✅ ③ 真书副本跑通 ⏳（Q6） ④ 20.1 PASS、20.2 PASS ✅

## 2. 目录与分支（本机 Windows 11）

| 路径 | 用途 | 分支 / 状态 |
|---|---|---|
| `D:\Programme\learn_system_dataset\learn_system` | **主克隆**，唯一推送点，有私有数据（页图 `ocr/data_work/`、真书正本 `var/ledgers/qianyuan_w8/` **只读**） | `t04@cfe9feb`，已推 GitHub `origin/t04` |
| `D:\Programme\t04w\t04a` | T04A 执行者 worktree | `win/t04a@31c2a12`，**已全部合入 t04**，可删 |
| `D:\Programme\t04w\t04b` | T04B 执行者 worktree | `win/t04b@cb62223`，**已全部合入 t04**，可删 |
| `D:\Programme\t04w\s4` | **阶段 4 执行者 worktree**（自 `t04@b38051d`） | `win/s4@22219b1`（回放工具已提交）；**未提交**：`pipeline/tools/run_real_book_t04.py`（驱动）+ 4 个生产文件改动（见 §5，裁决前不许提交）。`var/ledgers/qianyuan_w8/` 是正本副本（只读来源），`var/ledgers/qianyuan_t04/` 是真书新账本（可重建） |
| `D:\Programme\t04w\int` | 协调者集成试跑目录（detached，有 `.venv`、页图联接） | 可删 |
| `D:\Programme\learn_system_dataset\t04data` | 私有数据克隆（Gitea `data/t04-private@c35a020`） | 只读 |
| `D:\Programme\learn_system_dataset\learn_system_m7_gitea`、`learn_system_crlf_discard` | 旧克隆 | 可删 |

各 worktree 的 `.venv` 是指向主克隆 `.venv` 的目录联接；`_brief/` 目录不进 git（`.git/info/exclude`），里面是任务书和执行者回报。

## 3. 环境

Git Bash 里：`export PYTHONUTF8=1 LC_ALL=C.UTF-8 LANG=C.UTF-8`，用 `.venv/bin/python`（`.venv/bin` → `.venv/Scripts` 联接）。Python 3.14.4（uv）。逐包测试：`.venv/bin/python -m unittest discover -s pipeline/<包>/tests -t .`；contract_registry 约 15 分钟，assembly 约 4 分钟。

**Windows 环境红（17 条，不修，任务书第五节已列）**：AF_UNIX×10（ledger daemon、contract_registry 3 条）；WinError 32 临时目录删 `ledger.sqlite`×5（knowledge_extraction 3、contract_registry 2）；`intake` 的 `test_read_source_files_reads_utf8`（write_text CRLF）；`test_20_10_blocked_line_computed`（verify.sh 传 Git Bash 路径给原生 Python）；`test_full_summary_unchanged`（`run_all.sh:84` `paste -sd '；'` 多字节分隔符，Linux/Mac 也会撞）。详见 `docs/handoff/T04-WINDOWS.report.md`「基线」。

## 4. 外部 Agent 与 tmux

- 权限：用户已在 `~/.claude/settings.json` 放行 `Bash(tmux:*)`、`freebuff:*`、`agy:*`、`command-code:*`、`opencode:*`。**command-code 目前不可用**（用户说）。
- 可用：`freebuff --cwd <dir>`（选 DeepSeek V4.1 Flash，1 小时额度，到点会静默退出、窗口变空白）；`agy --model gemini-3.8-flash-medium --dangerously-skip-permissions`（首次要回车确认信任目录；简单任务用 `gemini-3.8-flash-low`；Claude 模型额度已用尽）；`opencode run`（未用过）。
- tmux 会话 `t04`（psmux）：窗口 `t04a`（agy，空闲）、`t04b`（agy，空闲）、`s4`（agy，**停手等裁决**）。看进度：`tmux capture-pane -p -t t04:<窗口> | tail`。发指令：`tmux send-keys -t t04:<窗口> -l '<文字>'; sleep 1; tmux send-keys -t t04:<窗口> Enter`——发完 10 秒后**必须**捕屏确认「thinking/working」，长时间空闲后第一次发送常被吞掉，重发即可。
- 执行者回报在各 worktree `_brief/*-worker.report.md`；协调者回报是仓库里的 `docs/handoff/T04-WINDOWS.report.md`（每步追加、随 t04 提交）。

## 5. 阶段 4 现场与待裁决（已于 2026-09-25 发主 Agent，等回复）

主 Agent 裁决 Q5 采 (b)：空账本新建 EditionRun 真跑 M1→M8，人工节点回放正本副本里的 24 条 M4 类别裁决 + 26 条 M6 审核决定（对位规则、只走公开入口、对不上就停手），回放器为真工具。任务书全文 `D:\Programme\t04w\s4\_brief\STAGE4-brief.md`。

执行者跑真书时改了 4 个生产文件（未提交），协调者判断与建议（已发主 Agent）：
- **Q6 `pipeline/assembly/genesis.py`**：真书 M6 只审核了断言，没有 pattern 审核 → M7 创世 pattern 为空 → M8 知识链闭合失败。执行者想改成「未被拒绝即准入」= **放宽，不收**。建议按 G7-RULINGS 第 107 条如实失败，判据③记为「真书 M6 缺 pattern 审核，待用户补决定」。
- **Q7 `pipeline/orchestrator/gate.py`**：`run_release` 新建 release ProcessingRun，`evaluate_release_admission` 在其中找 m6 → `IndexError`（gate.py:124）。T04B 接线真 bug。建议改 `run_release` 把 EditionRun 句柄交给准入门禁读 m6，**不**在 gate 里加按 edition_part 回退。先红后绿。
- **Q8 `pipeline/dataset_compiler/step.py`**：`_fail` 返回缺 `processing_run_id`（runner 约定必有）。真 bug，小改，建议批准。
- **Q9 `pipeline/dataset_compiler/acceptance.py`**：`--ledger` 参数合理；offset 路线跳过 `span_page_binding`/`glyph_anchor_closure` 应改为 `not_applicable`（Q-M8-08）而非跳过；`.get()` 容错 = 放宽，不收。

**主 Agent 已裁（2026-09-25，原文已追加到 `s4/_brief/STAGE4-brief.md` 末尾），执行顺序 Q8 → Q7 → Q9 → T19 → 跑真书到 M6 停下**：
- Q6：否决执行者的放宽；也否决「如实失败记为待补」。根源是 **M6 从来没把 pattern 排进审核队列**（`review/inputs.py:161-169` 只收 assertions/school_views，`model.py:11 ENTITY_ID_KINDS` 无 pattern）。新开 **T19（M6 审核队列纳入 pattern）**，划入阶段 4：`inputs.py candidate_objects` 加 patterns（kind="pattern"，entity_id=pattern_id）；`ENTITY_ID_KINDS` 加 pattern→pattern_id；`required_types` 对 pattern 给 `review_source_fidelity`；`reviewed_edition` 的 approved/rejected/decisions 与 M6 gate 的 `queue_coverage`/`package_counts`/`evidence_closure` 一并覆盖 pattern；INTERFACES §5.3 接口卡片同步登记。先写「含 pattern 的 candidate_set 过 M6 后 reviewed_edition 里没有该 pattern」用例转红；探针：把 pattern 从队列删掉，M6 gate `queue_coverage` 必须转红。review 包既有用例只许收紧；T16 两条偶发不碰；**`genesis.py` 一个字不改**。真书回放时 M6 会多 2 个 pattern 队列项（pat_qizheng_000001「去官留煞」、pat_qizheng_000002「贪合忘煞」），账本副本里没有决定——**由用户给**，主 Agent 去要，拿到后以 `decisions_supplement.yaml`（actor_ref=user:wjt，含 verdict+rationale）交给回放器；回放器规则不变：对不上的项只许从该补充文件取，文件里没有就停手。用户没给之前，全线跑到 M6 `awaiting_human` 停下、如实回报，③先不算达成。
- Q7：采协调者方案。gate 取数规则不动；`run_release` 把 EditionRun 的 handle 交给 `evaluate_release_admission` 读 m6，release run 只承载 m7/m8。先写「release 准入必须读 EditionRun 的 m6，不读 release run」用例转红再改；再补一条登记表驱动用例证明 fixture 全栈也走 `run_release` 而不是直调 `run_m7`。
- Q8：批准，`_fail` 返回补 `processing_run_id`，先红后绿。
- Q9：(i) 批准 `--ledger`；(ii) 按 Q-M8-08 输出 `status: not_applicable`（两项在 `_CHECK_NAMES` 声明适用级别，测试断言 `not_applicable` 而非缺席）；(iii) 否决 `.get()` 容错。
- 执行者擅改的 4 个文件**全部还原**（让它手工改回或 `git restore <单个文件>`），按上面逐条重做。

**接手者第一件事**：把上面这段作为指令发给 tmux `s4` 窗口的 agy（或新开 Freebuff），要求按顺序、先红后绿、分文件提交、回报追加；然后验收。原「裁决到后怎么做」：把裁决原文追加到 `STAGE4-brief.md` 末尾，在 tmux `s4` 窗口发给 agy：按裁决逐项先红后绿、配探针、分文件提交；被否决的改动用 `git diff` 反向确认已撤（不许 `git checkout -- .`/`reset --hard`，让执行者手工改回或 `git restore <单个文件>`）；然后继续跑真书全线，交付回报要求见任务书「交付」3。协调者验收：在主克隆合入 `win/s4`，用真数据跑 `python -m pipeline.dataset_compiler.acceptance --ledger var/ledgers/qianyuan_t04 --check publication`，核对正本指纹（§7）。

## 6. 之前的裁决（全部已落地，勿重开）

Q1 M4 提交不是暂停节点（缺件 → `refused` 零写入）；Q2 A2 收窄版（`human_input_artifact`，三护栏 + 两条件用例）；Q3 用户裁「乙」= M5 `adapter_notes` 两级门禁（依第 109 条；逐条点名 → warning 不阻断）；T18 去重；Q4 M7 续跑方案 A（`resume_m7` + `resume_entry`）；gate.py I-11/§3.8 两处改动复核通过；环境三条建议已落地。原文见 `T04-WINDOWS.report.md`「待裁决」各段。

## 7. 收尾（阶段 5）清单

1. 11 包全套回归（主克隆，真数据），与基线表对照，只许 Windows 环境红。
2. 核对真书正本未动：`find var/ledgers/qianyuan_w8 -type f -printf '%s %T@ %p\n' | sort -k3 | sha256sum` 应等于 `875139aef3e4d5cfea546de09439e68efa172701b3f4d913ad396fde27f9f75b`（361 个文件；原始清单在协调者 scratchpad `t04/ledger_master_fingerprint.txt`，丢了就以此哈希为准）。
3. `T04-WINDOWS.report.md` 加「## 验证」：完成判据逐条附证据。**TODO.md 由主 Agent 维护，不要改。**
4. 只推 `t04`：`git push origin t04`。通知主 Agent（第一行「T04 Windows 完成：t04 @ <提交号>」）。

## 8. 沟通

主 Agent 会话名 `【LearnSystem】 Dataset`，地址 `bridge:session_01EHvFZWgL4ihAUsPAsqM35t`（`SendMessage`；`ListAgents` 里可能看不到它，直接发这个地址；它不在线时投递会 409）。消息第一行要能独立看懂：事实（SHA、测试原文）在前，候选与推荐在后。用户不盯细节，**不要问用户**，问主 Agent；用户偶尔会问进度，用中文按「阶段 / 判据 / 百分比」答。

## 9. 纪律（违反即返工）

不放宽任何检查；先红后绿 + 探针；人工节点只走公开入口、不直写账本、不手写金标；真书正本只读；不许 `git reset --hard` / `checkout -- .` / `clean -f` / `push --force` / `rebase` / `branch -D`；只推 `t04`；提交信息末尾 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。
