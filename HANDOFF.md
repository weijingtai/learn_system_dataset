# HANDOFF

## G7 W5 进行中：impl-00 act/13 ACCEPTED；impl-06 R3 复审；impl-07 G0 实现（Dataset 会话；黑箱线最新状态）

补记六（2026-09-13）：
- 已验收：impl-01 Ledger、impl-02 M3 结构层、impl-03 M5、impl-04 M8、impl-05 M4 最薄接入、impl-08 Orchestrator+Contract Registry、impl-00 act/10/12/05/**13**（`573c3fb`，ACCEPTANCE §5.4）。`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。裁决书 `G7-RULINGS.md` 至第 69 条；计划 `G7-PLAN.md`。
- 执行器按用户 2026-09-13 指令切回 **tmux + agy**（`--agent agy`，从已信任的 `/Users/jingtaiwei/Git/Public` 启动；tmux 须在沙箱外拉起）。在跑：
  - `w5r6`（已关）：impl-06 R3 `READY` `4390b6c`；主 Agent 复核阈值与 carried 条件式属实。
  - `w5h1`：impl-06 实现（`gemini-3.1-pro-high`，提示词 `~/tmux-agents/runs/prompts/w5h1.txt` 包 `PROMPT-H1.md`，K1→K2→K3 **分组停下**，回报 `w5h1.report.md`）。
  - `w5g0`：impl-07 G0 实现（`gemini-3.8-flash-high`，提示词 `w5g0.txt` 包 `PROMPT-L0.md`，**逐 ACT 停下**，回报 `w5g0.report.md`）；已预裁 §0.3 与 impl-06 §5.3 键一致（§5.3 为超集）。G0-01 `c79b36a` 已停下，主 Agent 验收中（`accept_g0.sh c79b36a g0_01_e2e.py`）。放行用 `tmux-agent.sh send --session w5g0 --text "…"`。
  - `w5h`/`w5l`/`w5x`（cmd）已完成：`c740603`、`3d97bb2`、`573c3fb`。遗留：impl-07 `BDD.md §2.3`/`act/02.yaml`（DEFERRED 完整波次）仍写 SCH_001，完整波次定稿时统一为 SCH_002。
- 监控：`tmux-watch.sh --session <名> --agent agy --interval 60 --idle-need 3 --stall 1800 --max 7200`（放后台，沙箱外）。
- 验收脚本：旧 scratchpad 已被清空，`accept_m4.sh` 等不存在；现有 `accept_act13.sh`（干净树 + 篡改 + 门禁模板）。G0 验收需另写 `accept_m7.sh`：干净树、`pipeline/assembly` 单测、`genesis`/`gate` 独立性 grep、纯函数副作用 grep、`m7-assembler.sh` 10 PASS + 6 BLOCKED exit 2、`run_all` 不变。
- 下一步顺序：w5g0 每个 ACT 验收放行；w5r6 READY → impl-06 实现；之后起草 impl-04 跟进（知识链前三段 + GraphProjectionPack，依赖 M6 正式知识与 M7 Snapshot）；impl-09、impl-10 等用户待办。
- 用户待办：真实前十页人工终态决定表（impl-09）；`expert_verified` 签发决定表（M4/M6 真实签发）；SemanticSpan ID 前缀确认（impl-10）。

## （上一节）G7 W4 收尾：impl-08 与 impl-05 均 ACCEPTED

补记四（2026-09-12）：impl-05 M4 最薄接入 `ACCEPTED`（K4 `06d1a28`，`m4-stage-gate.sh` 13 PASS + 3 BLOCKED；`impl-05-knowledge/ACCEPTANCE.md` §5.1）。W4 全部完成。W5：impl-06 M6 定稿 `981156c`，裁定 61（Snapshot 归 M7，提前 M7 创世汇编薄切片）、62（M6 不改 M4 状态）；会话 `w5h` 落实并起草 impl-00 act/13（M6 闭集），会话 `w5l` 定稿 impl-07 创世薄切片；随后 GLM 四查（会话 `w4r5`）→ 实现。

## （上一节）G7 W4：impl-08 ACCEPTED；impl-05 K3 验收中

补记三（2026-09-12）：impl-08 首切片 `ACCEPTED`（K4 `f79eafd`；§20.1/§20.10 由 run_all 计算化判定并如实 BLOCKED；`impl-08-orchestrator/ACCEPTANCE.md` §5.1）。impl-00 首纵切 ACT（10、12、05）全部 `ACCEPTED`。impl-05 M4 最薄接入 K1/K2 已验收、K3（`03f7f90`/`32192dd`）验收中，会话 `w4k`；裁定 57–59（Gate 读 YAML 包、acceptance/suites 豁免、同阶段后续运行经 supersede 续写）。下一步：impl-05 K4（m4-stage-gate.sh）→ impl-05 ACCEPTED → W4-P impl-04 GraphProjectionPack/知识链跟进定稿 → W5（M6、M1/M2 真实接入、M3 语义层，后两者需用户待办）。

## （上一节）G7 首纵切关键路径跑通：M5（impl-03）与 M8（impl-04）均 ACCEPTED

补记二（2026-09-12）：impl-04 M8 首切片 `ACCEPTED`（K3 `c36d628`/`950b77b`；干净树 125 OK、`m8-span-identity.sh` exit 2、`run_all.sh` 仅 20.4/20.8 改判仍 BLOCKED、副本篡改落点 fixture_host；`impl-04-dataset/ACCEPTANCE.md` §5.1）。用户决定首纵切维持关键路径（G7-RULINGS 第 43 条），§20.1/§20.9 如实 BLOCKED；`G7-PLAN.md` 已改为 W4（impl-08 实现、impl-05 M4 最薄接入、impl-04 GraphProjectionPack 跟进）→ W5（M6、M1/M2 真实接入、M3 语义层）→ W6（M7）。impl-08 定稿 `cd6c7a6` 四查 R1 REWORK（`5ab873c`），按第 45/46 条在 tmux 会话 `w4i` 返工，完成后由 `w4r8`（GLM）复审。

补记（2026-09-12）：impl-03 M5 首切片 `ACCEPTED`（K2 `817cd64`/`9aaccf5`/`6e21038`，CLI 返工 `8367893`；干净树 87 OK、`m5-evidence-gate.sh` exit 2、矩阵外 13 项全过；`impl-03-validation/ACCEPTANCE.md` §5.1）。M8 w3f K2 按 G7-RULINGS 第 32 条（薄 M1 经 `supersede_step_run` 接替）进行中。下文为 K1 时的记录。

更新时间：2026-09-12
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：W1 草稿补全与对账（`1f32177`、R1/R2 审查）；统一裁决 `docs/blackbox-spec-rework/G7-RULINGS.md`（P1 首纵切只走 Ledger→M3→M5→M8，M8 尾链首切片不依赖 M4–M7）；W2：impl-00 裁剪并执行 act/10 闭集登记（`ea90ca8`，已验收）；impl-04 定稿+四查 READY；impl-03 定稿、四查 REWORK→返工→R2 READY。W3：M8 K1（`a64d0e9`/`000386e`/`4a79ef5`）、M5 K1（`25b2fcc`/`48ebbfb`/`1fab5b1`/`0a77975`）主 Agent 干净树验收通过。
进行到一半的事（精确到文件和章节）：tmux 会话 `w3f`（M8，`impl-04-dataset/PROMPT-F1.md`，K2 ACT 03–06）与 `w3e`（M5，`impl-03-validation/PROMPT-E1.md`，K2 ACT 04–06），执行器 `cmd --yolo` DeepSeek V4.1 Flash；每组完成停下等主 Agent 验收放行；回报 `~/tmux-agents/runs/w3f.report.md`、`w3e.report.md`。验收脚本在会话 scratchpad `accept_m8.sh`/`accept_m5.sh`（git archive 干净树，只输出结论行）。
下一步（第一件事）：两路 K2 回报 → 跑验收脚本 → 放行 K3（M8 ACT 07–08 含 run_all 20.4/20.8；M5 K2 即收尾）→ 端到端矩阵外篡改验收 → impl-03/impl-04 `ACCEPTED` → W4（M6 薄接入、Orchestrator、M1/M2 真实接入，定稿前先按 G7-RULINGS 裁剪）。
已知的坑：agy 额度不稳（静默结束回合即没 token），已改用 cmd；cmd 回合结束会停在 `Ask your question`，派发时要求每组停下写回报。执行方可能改测试断言迁就实现，验收要读断言。起草与审查换不同厂商模型。本机 zsh 下 `echo =====` 会报错、变量后紧跟全角字符需写 `${VAR}`。用户待办：W4 前写真实前十页人工终态决定表；W5 前确认 SemanticSpan 前缀。

## G4 D 类全部 ACCEPTED：D-16 映射表与 pat_/ent_ 登记验收通过（Dataset 会话；黑箱线最新状态）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：外部 Agent 按 `work-items/g4-r3/PROMPT-F.md` 交付 `76bc4b4`（D-16：PLAN.md 只增不删加入「黑箱差距 → PLAN 条目 → owner 映射」，§19 19 行归属、43 条标注、3 条新增登记、`KnowledgeReleaseCompiler` 唯一 owner `pipeline/TODO.md`；检查脚本 `check_d16.py`）与 `e306258`（`pat_`/`ent_` 进 §8.1 第 3b 节）。主 Agent 干净树验收：门禁绿、TDD 全绿、零删行、7 例检查脚本篡改全部检出；一处执行者上报（TDD grep 尾随空格）裁定为主 Agent 笔误已订正。验收后主 Agent 勾选 PLAN 中 21 条 `superseded-by` 条目（未勾选 66 → 45），SUBAGENT_TODO D-16 `ACCEPTED`，G4 D-01～D-19 全部 `ACCEPTED`。
进行到一半的事（精确到文件和章节）：G5 总准出记录已写（`reviews/G5-EXIT-REVIEW.md`，13/14 满足）；`work-items/g5/` 六件套 READY，**等用户书面确认进入实现阶段**后填 README §2 日期并派发 `PROMPT-G.md`（规格头部 `REVIEW_FAILED_R1` → `R1_REWORK_CLOSED`，不动节标签）。D-design D-04 判据措辞已订正。
下一步（第一件事）：拿到用户确认 → 派发 g5-01 → 验收 → `PROJECT_COLD_START_HANDOFF.md` 状态改 `IMPLEMENTATION_PHASE` → 写首纵切第一批（Artifact Ledger，§17，判据 `run_all.sh 20.2 20.3`）六件套；之后 M3 → M5 → M8，判据 `run_all.sh 20.N` 由 BLOCKED 变 PASS。
已知的坑：PLAN.md 时间窗已向 C/S 解除；PLAN 的 D-16 节要求「零删行」，今后改 PLAN 只能追加或把 `- [ ]` 改 `- [x]` 并附取代者；验收仍在 `git archive` 导出树上跑。 **`check_d16.py` 刚性缺陷**：R3 把表 B 行数写死为 43、R4 要求黑箱节任何新 `- [ ]` 都登记进表 B，因此现在无法往 PLAN 黑箱节新增未勾选项（G5 记录条目因此只写在 SUBAGENT_TODO/HANDOFF）；首纵切第一批 ACT 必须先把 R3 改为「≥ 43」并允许表 B 追加行，再往 PLAN 加实现条目。

## G6 NC-003 ACCEPTED；NC-009 R2 复核中；NC-010 契约已写；NC-015 待执行（C/S 会话）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：NC-003 act/06 验收通过（REST 仓 `5730ed9`，守卫 0、69 测试、原样 3.1 盲测六项全过，交付报告 `work-items/nc-003/DELIVERY_REPORT.md` 未入库），NC-003 ACCEPTED，NC-009 派发前置满足。NC-010 客户端契约 `contracts/community_client.md` 已写（独立 `CommunityDatabase`、`IdTokenProvider` 注入、命令队列状态机与 payload_hash 跨端参考值 `c8e2c2b0…b72b5`、作者视角八档文案、四屏七状态、D-NC010-01～07）。
进行到一半的事（精确到文件和章节）：NC-009 验收 R1 判 REWORK（act/01～04 全量 450/5/9、规则 65、守卫 0、盲测 9 项通过；快照未按 Schema 校验、畸形 If-Match 412、503 泄露异常 → 契约 §10 D-NC009-15～17 + act/05，全量目标 457，PROMPT 末尾追加），等 act/05 报告；NC-010 执行中；NC-015 执行方尚未提交。
下一步（第一件事）：收 NC-009 执行报告 → 按 ACCEPTANCE 验收（Emulator 盲测七项，失败集合须等于基线 5 个）。NC-010 四查回来 → 落实返工 → READY → 交用户派发（可与 NC-009 并行，NC-010 全用 MockClient）。NC-015 报告回来按 ACCEPTANCE 七项篡改盲测。
已知的坑：工作树里 `pipeline/ledger/*` 的未提交改动属 Dataset 会话，不要暂存；python 批量替换脚本任一处不匹配会中途退出但已写入前面的修改，务必检查 `git status` 后再提交。
已知的坑：PLAN.md 今后只能追加或把 `- [ ]` 改 `- [x]`（D-16 零删行判据；`check_d16.py` 只查黑箱侧条目，不查 G6 节）；G6 新条目不需登记进 D-16 映射表。一次性 Dart 盲测需 `import 'package:drift/drift.dart'` 才能用 `interceptWith`；执行方报告在 reading-notes 根目录未跟踪，验收不入库。

## G4 第二批验收通过：D-15 fixture、D-18 §20 判据化、前缀登记（Dataset 会话；黑箱线最新状态）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户把 `work-items/g4-r2/` 的 PROMPT-D / PROMPT-E / PROMPT-E2 交外部 Agent 执行，四个提交：r2-01 前缀登记 `851fa70`（§8.1 第 3b 节 sch_/sv_/cg_，§12.2 去占位）、r2-02 D-15 fixture `6fc8536`（`pipeline/corpus/_fixture/mini_ed01/`，43 span / 5 batch / 230 字框锚点，页图不进 Git，`verify.sh` V1–V8）、r2-03 D-18 `4884b6a` + 返工 `2978ad9`（§20 十一条各带判据，`openspec/acceptance/run_all.sh` 当前 `pass=0 fail=1 blocked=10`，20.7 因旧库 `original_text` 全空为 FAIL 属预期）。主 Agent 在 `git archive` 干净树上独立验收：三门禁绿、TDD §1–§3 全绿、8 例矩阵外 fixture 篡改全部命中、假 `verify.sh` 副本不被信任。三件执行者上报裁定（哈希环 = ACT 缺陷、严格 offset、`fx()` 一律用规范脚本）记于 `work-items/g4-r2/ACCEPTANCE.md` §5.1 并回写 ACT。
进行到一半的事（精确到文件和章节）：无。G4 仅剩 D-16（PLAN 映射表与唯一 owner），六件套未写；已向 C/S 会话请求 `PLAN.md` 写入时间窗。
下一步（第一件事）：与 C/S 约定时间窗后写 `work-items/g4-r3/`（D-16），派发、验收；随后 G5 总准出（BDD 总验收包、机器门禁、ACT 覆盖映射复核）。`pat_`/`ent_` 前缀（登记册 §3.4）仍待用户确认，不阻塞。
已知的坑：验收要在 `git archive <hash>` 导出树上跑（软链 `.venv`、`pattern_knowledge_workbench/assets`，`FIXTURE_ASSET_ROOT` 指本机页图目录），否则同工作树里 C/S 的未提交 `openspec/schemas/community_*` 会混入门禁；`build_fixture.py` 的 `--asset-root` 只影响 `path_ref` 字面，重放必须用默认值；`verify-T.sh` 仍需 `LC_ALL=en_US.UTF-8`。

## G6 NC-004 达 READY（C/S 会话）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：NC-004 两轮四查（R1 REWORK 10 项 + 7 建议；R2 READY，记录 `reviews/NC-004-REVIEW-R1.md`）。关键裁定：去重规则按 DESIGN §7.2 重写为 ①投影全等→unchanged（无论 touched）②仅说明不同且未碰→unchanged ③其余→saved；失败注入改用 Drift `QueryInterceptor`；严格 JSON 扫描器四条规则写死；ACT 拆五步（250 分钟，35 个测试）；新增本地错误 `MentionCountExceeded`/`FieldLengthExceeded`；`example/` 推迟 NC-010。SUBAGENT_TODO 记 NC-004 `READY`。
进行到一半的事（精确到文件和章节）：无。等待用户把 `work-items/nc-004/PROMPT.md` 交外部 Agent。
下一步（第一件事）：收到 NC-004 执行报告后按 `work-items/nc-004/ACCEPTANCE.md` 验收（`nc004_guard.sh --require-impl` 会在 reading-notes 内运行 `flutter analyze` 与 `flutter test`）。等待期间准备 NC-005 六件套（编辑器 SM-1、Markdown 预览、`flutter_markdown_plus 1.0.12`、注入/外部图片安全测试）。
已知的坑：`nc004_guard.sh --require-impl` 需要 PATH 内有 `/Users/jingtaiwei/flutter/bin`（守卫内部已注入）；宿主机需能加载 libsqlite3。

## G6 NC-002 验收通过；NC-004 审查返工中（C/S 会话）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：NC-002 由用户派发的外部 Agent 完成六个提交（learn_system `0d27ea8`→`7ee2c45`，SERVER `30a868c`）；主 Agent 亲自验收通过（详见 `work-items/nc-002/ACCEPTANCE.md` 验收记录），SUBAGENT_TODO 记 `ACCEPTED`。产物：12 个 `community_*.schema.json` + 62 示例 + `verify_community.sh`；`tools/validate_fixtures.py`；SERVER `xuan/community_hash.py` + 一致性测试。社区 17 前缀入登记册 §3.5（`bb750db`）。NC-004 契约 `contracts/local-persistence.md` 与六件套（`ab11e28`）第一轮四查 REWORK 10 项（含 §5.1 去重规则与 DESIGN §7.2 的一处冲突、FailingExecutor 需包装 TransactionExecutor、merge 测试构造步骤违反头校验、README 缺 outbox 二选一声明、严格 JSON 扫描器规则未写死）。
进行到一半的事（精确到文件和章节）：NC-004 返工落实中（契约 §2.1/§3/§5.1/§5.2/§6、README、TDD §5、BDD）。
下一步（第一件事）：落实 NC-004 十项返工 → 第二轮四查 → READY → 把 `work-items/nc-004/PROMPT.md` 交用户派发。之后准备 NC-005（编辑器/Markdown）六件套。
已知的坑：执行方交付报告若不在仓库内，Red 原文无法核验，只能以提交构成为据；NC-004 的 `flutter test` 依赖宿主机 libsqlite3，验收时用真文件库。

## G6 NC-002 达 READY（C/S 会话；黑箱之外全部归本线）

更新时间：2026-09-11
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户明确分工——黑箱规格与实现归 Dataset 会话，其余（注解社区前后端、APP 消费接入、Tag 展示）归本线；编码一律外派、我只写 Prompt 与契约，调研用最省 token 的模型。用户决定 Firebase 去留暂缓（账号模型未成型）。NC-002 规格侧产物由我编写：`openspec/annotation-community/contracts/community-models.md`、`state-machines.md`、`tools/nchash_reference.py`（含解析层 `load_snapshot_json`）、`fixtures/community/` 9 文件 198 项；六件套 `work-items/nc-002/`（act/01～06：Schema×4 步、fixture 校验器、SERVER nchash/v2）；守卫 `reviews/nc002_guard.sh`。三轮独立四查（R1 20 项、R2 9 项、R3 READY），记录 `reviews/NC-002-REVIEW-R1.md`。裁定：不改 `openspec/schemas/verify.sh`（D-NC002-11，应 Dataset 要求）；本地错误类名闭集 D-NC002-10；`-0`/重复键/NaN 在解析层拒绝；CLIENT Dart 一致性测试推迟 NC-004；CommandRecord 按操作成对 Schema 推迟 NC-003。黑箱侧 AnchorContractPack 已落地（e474ae4），与本线 target_kind/AnchorRef 一致。
进行到一半的事（精确到文件和章节）：NC-002 待用户把 `work-items/nc-002/PROMPT.md` 交外部 Agent 执行；社区 17 个前缀尚未写入 `openspec/id-prefix-registry.md`（已向 Dataset 提出追加 §3.5，等回复）。
下一步（第一件事）：收到 NC-002 执行报告后按 `work-items/nc-002/ACCEPTANCE.md` 验收（`nc002_guard.sh --require-impl` 0、参考编码器交叉复算、Schema/校验器盲测）。并行可做：NC-004 六件套准备（CLIENT 建仓 + Drift 修订 + Dart 一致性测试第一条 ACT）。
已知的坑：本机无可用 pytest，SERVER 测试用 unittest 写法；`openspec/schemas/verify.sh` 全线不改；执行者若报契约歧义，由我裁定。

## G4 第一批六项规格验收通过（Dataset 会话；黑箱线最新状态）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户把 `work-items/g4-r1/` 的三份 Prompt 交外部 Agent 串行执行，产生六个规格提交（D-13 `4086c2c`、D-10 `015e34f`、D-11 `3598ea8`、D-06 `e474ae4`、D-08 `07f79dd`、D-14 `d36a202`）。主 Agent 独立验收：门禁 0 FAIL / 109/109 / schemas 0 / diff --check 通过；TDD 26 条判据 25 条符合、1 条为主 Agent 期望笔误已勘误；75 行 ACT 文本逐字命中；243 行 diff 逐句审查无偏差。六项 `ACCEPTED`，证据 `work-items/g4-r1/ACCEPTANCE.md`。
进行到一半的事（精确到文件和章节）：G4 还剩 D-15（mini fixture）、D-16（PLAN 映射表）、D-18（§20 判据化 + `openspec/acceptance/run_all.sh`），均 `BACKLOG`，第二批工作包未写。
下一步（第一件事）：等用户拍板三件事后写第二批：① `school_id`/`school_view_id` 前缀（登记 §8.1）；② §22 分期方案（首纵切内 = Artifact Ledger、M3、M5、M8）是否认可，认可后 §22 状态改「已确认设计」；③ D-15 fixture 的《三辰通载》page_001..003 派生页图是否进 Git（建议不进，走本地 Object Store 引用）。D-16 改 `PLAN.md` 前须与 C/S 会话约定时间窗。
已知的坑：仓库内残留主 Agent 早先停掉的空 worktree `.claude/worktrees/agent-ad7f6f7bb2ae5215e`（无提交，分支停在 `cb175c4`），导致 `git status` 出现 `?? .claude/`；AGENTS.md 禁止 `git branch -D`，清理由用户决定。外部 Agent 的六个提交未带 `Co-Authored-By`，非验收项。

## G6 NC-001-01 验收通过（C/S 会话）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：Sonnet 执行 Agent 按 `work-items/nc-001/PROMPT.md` 完成四个提交（`272fb60`→`11b4e46`→`d75afb1`→`11edbc7`），只含两个工具文件。主 Agent 亲自验收：32 测试 OK；local 恰为 `LOCAL_PREPARATION_PASS`；integrated 与契约 §7 的 23 行逐字一致；`nc001_r2_guard.sh --require-impl` 0；方法集合与 TDD 相等、103 条必填键字面量与 TDD 相等；3 个必做变异 + 17 个矩阵外盲测全部符合契约（含退出 2 分支、根非 object、半填、form-feed 注入）；输入未被修改。执行方自报第 4 步先实现后补测试并还原取 Red 的流程偏差，已记入 ACCEPTANCE。NC-001-01 `ACCEPTED`；NC-001 总项仍 `PREPARING`。
进行到一半的事（精确到文件和章节）：无。
下一步（第一件事）：准备 NC-002 六件套（`openspec/annotation-community/TASKS.md` NC-002 条目；前缀表已由托管主 Agent 整表采用，需在 SUBAGENT_TODO 与 `READINESS_REVIEW.md` §3 写明）。NC-001-02 联调取证工作包需用户先决定 Firebase 去留。
已知的坑：下一份 PROMPT 要明确「先写测试再改实现，违反即停」。`openspec/annotation-community/tools/__pycache__/` 由运行测试产生，已删除，不要提交。

## G6 NC-001-01 达 READY 并派发（C/S 会话）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户全权托管后，主 Agent 代为拍板「CLIENT 用独立 Git 仓库」与 NC-002 十七个前缀整表采用。NC-001 R1 返工由 Sonnet 执行 Agent 落实（`aadd1fc`，14 文件，`nc001_r1_guard.sh` 0，主 Agent 亲自复跑）。随后三轮独立 wjt-react 四查：R2 判 REWORK 6 项、R3 判 REWORK 3 项 + 5 建议、R4 判 READY；返工由主 Agent 本人落实（`7ba3f35`、`3e5d1d8`、`cb1e3e9`），记录见 `reviews/NC-001-REVIEW-R2.md`，守卫改为 `reviews/nc001_r2_guard.sh`（K02/K03 核对 `aadd1fc`，永久为真；新增 K09～K11）。关键裁定：§4 状态闸门只管 §4 增量、§3 半填两档保留；根非 object 输出 `root`；103 条必填键逐字写死；ACT 拆四步（40/50/55/55 分钟）；共享守卫失败判外部。SUBAGENT_TODO 已登记 NC-001-01 `DISPATCHED`。
进行到一半的事（精确到文件和章节）：Sonnet 执行 Agent 正按 `work-items/nc-001/PROMPT.md` 实现 `openspec/annotation-community/tools/check_integration_baseline.py` 与测试，四个提交（act/01～04）。
下一步（第一件事）：收到执行报告后按 `work-items/nc-001/ACCEPTANCE.md` 亲自验收：四提交只含两文件、32 方法全跑、local 恰为 `LOCAL_PREPARATION_PASS`、integrated 与契约 §7 逐字相同、`nc001_r2_guard.sh --require-impl` 为 0、至少三个矩阵外变异、无 skip/永真/从输出生成期望。通过后 SUBAGENT_TODO 记 NC-001-01 `ACCEPTED`（总项仍 PREPARING，等 NC-001-02）。然后准备 NC-002 六件套。
已知的坑：`nc001_r1_guard.sh` 已被 R2 守卫取代，直接跑它会因 K02/K03 对当前工作树失败，属预期。执行者若报告契约歧义，是我的责任，不让其自行裁定。

## G3 R5 完成与验收（Dataset 会话；G3 线最新状态）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：主 Agent 复现三类区域边界假绿并写 `work-items/g3-r5/` 六件套（`4d68634`）；执行 Agent 先红 `5de99fa`（11 例新变异，98/109）、后绿 `241c38c`（区域提取、表格 17 行封闭、§16.3.1 序列相等）；主 Agent 独立验收：正常规格 0 FAIL、selftest 41/41、矩阵 109/109、13 例矩阵外盲测全部命中指定 FAIL ID、FAIL ID 超集测试通过、只读 Agent 复跑一致。G3 状态 `ACCEPTED`。
进行到一半的事（精确到文件和章节）：无。`g3-r3/` 89 例草稿已标 `SUPERSEDED` 并归档；过时指针（G3-REVIEW-R3、g3-r2、SUBAGENT_TODO G3 节）已修正。
下一步（第一件事）：由用户决定是否启动 G4；若启动，从 `SUBAGENT_TODO.md` G4 节选第一项准备六件套，主 Agent 仍只写规格/BDD/TDD/ACT/Prompt 并独立验收。
已知的坑：`verify-T.sh` 的 `T-06s` 在 `LC_ALL=C` 下误报，验收须 `export LC_ALL=en_US.UTF-8`；两个主 Agent 会话并行，本线只显式暂存 G3 文件，不碰 G6 注解社区路径。

## G6 注解社区线接管（C/S 会话；G3 由并行 Dataset 会话负责）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：按根 `AGENT_TAKEOVER_PROMPT.md` 冷启动并发出首次汇报。亲自复跑：`verify-T.sh` 在 UTF-8 locale 下 0 FAIL、selftest 37/37、固定矩阵 98/98 rejected；用临时副本盲测 R5-1a/1b、R5-2、R5-3 四类变异在 HEAD 上仍全部 exit 0，阻断属实。`nc001_r1_guard.sh` 当前 5 项 FAIL（K02/K03/K04/K06/K07），即 NC-001 R1 返工尚未落实；v1.5 守卫与 verify.sh 均 0。根 README 注解社区入口改指 v1.5 规格与接手 Prompt（`fe83bd8`）。分工：两个主 Agent 会话并行，`【LearnSystem】Dataset` 负责 G3 R5（`work-items/g3-r5/` 六件套由其编写）；本会话 `【LearnSystem】C/S` 只做 G6，不读写 G3 文件。
进行到一半的事（精确到文件和章节）：NC-001 R1 返工（`docs/blackbox-spec-rework/reviews/NC-001-REVIEW-R1.md` §3：8 个整文件 + 18 处逐字替换，§5 的 14 个文件一次提交）等待用户确认「CLIENT 用独立 Git 仓库」（该文 §6 第 1 项）后派发；NC-002 的 `DESIGN.md` §2.1 十七个 UGC 前缀已一次性列给用户确认。
下一步（第一件事）：用户不反对 → 派执行 Agent 按 NC-001-REVIEW-R1 §2/§5 落实返工并使 `nc001_r1_guard.sh` 为 0 → 未参与编写者做 wjt-react 四查 → READY 后在 SUBAGENT_TODO 登记并派发 `work-items/nc-001/PROMPT.md`（act/01 → act/02）→ 按 ACCEPTANCE.md 与 `--require-impl` 验收。
已知的坑：本机 shell 未设 LANG（默认 C locale），`verify-T.sh` 在 `LC_ALL=C` 下 T-06s 误报 FAIL、退出 1，须用 UTF-8 locale；注解社区两个守卫反而须 `LC_ALL=C`。`work-items/nc-001/act/` 在返工落实前不存在。Firebase 去留最迟在 NC-001-02 或 NC-009 前决定，此前服务端规格一律供应商无关。`SUBAGENT_TODO.md` 有他人未提交的 G3 改动，本线不暂存该文件。

## 项目冷启动总交接（当前最高优先级）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：停止 G3 R4 验收并写出项目级冷启动交接；`ffe19df` 的正常门禁、37 项 selftest 与 98 个固定变异通过，但矩阵外盲测确认三类结构假绿。
进行到一半的事（精确到文件和章节）：`verify-T.sh` 的 D-07 START 间隙未封闭、T-07 表格不拒绝额外列、T-08 不拒绝重复块标题；G3 保持 `REWORK_REQUIRED`。
下一步（第一件事）：完整阅读根 `PROJECT_COLD_START_HANDOFF.md`，按其 §6 下发只改两个脚本的 R5 Prompt。
已知的坑：未提交 `work-items/g3-r3/` 是过时 89 例草稿；NC-001 review 文件属于其他工作线；不得批量暂存或覆盖。

## NC-001 首包补齐

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；本仓库当前工作树。
刚完成：六件套同步 v1.5 十项要求，新增 VALIDATION_CONTRACT.md 与 REMAINING_DELIVERABLES.md，机器基线增加注销事件未验证登记；Terra 只读缺口意见已纳入。
进行到一半的事（精确到文件和章节）：NC-001-01 仍 PREPARING/NOT_EXECUTED；补齐文稿未替代正式独立 ACT 审查。
下一步（第一件事）：独立复核 nc-001 全包，达到 READY 后派发两个校验工具文件；后续 NC-001-02、NC-002 文档落点及剩余证据见剩余交付清单。
已知的坑：local 放行计划目录不代表完整 NC-001 通过；书籍继续暂缓；不夹带 G3 改动。

## 注解社区 v1.5 同步

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：按 FIX_V1_5.md 的 V5-01～11 完成 40 处精确替换，覆盖 9 份文件；新增 R-21、NC-026 和行为事件规范。逐字重放核对通过，LC_ALL=C 下 review_v1_5_guard.sh 与 verify.sh 通过，格式检查通过。
进行到一半的事（精确到文件和章节）：v1.5 文档已同步，待独立语义抽查；未实现业务代码、采集服务或机器 Schema。
下一步（第一件事）：按 FIX_V1_5.md 复核；NC-001 工作包及 INTEGRATION_BASELINE.md/JSON 当前仍是 v1.4 九项基线，进入 READY 前须同步新增的第十项“宿主账号注销事件来源、投递与测试”。
已知的坑：本机守卫须使用 LC_ALL=C 避免中文汇总行的 Bash 变量解析问题；结构守卫通过不代表业务验收通过。G3 并发改动不纳入本次提交；书籍盘点继续暂缓。

## 注解社区：NC-001 开工准备

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：两位Terra完成只读模块调查，主线程抽查并决定独立reading_notes包、Drift复用、host scope身份与普通社交通知组件边界；新增INTEGRATION_BASELINE.md/JSON及nc-001六件套草稿。
进行到一半的事（精确到文件和章节）：NC-001 PREPARING，六件套只覆盖NC-001-01本地规划基线校验；完整联调设备/账号/规则/真实测试缺证保留。尚未正式ACT审查，不可派发业务编码。
下一步（第一件事）：独立审查nc-001包，落实基线checker；随后NC-002本地模型契约。书籍盘点/整理与NC-020a本轮按用户指令暂缓。
已知的坑：notebook是圈画不是永久笔记库；xuan-migration父目录不是git仓；Profile实际参数为PlaygroundUserId而非appUserId；SDK仅读缓存元数据，依赖未解析、外部测试未跑。不得将本地规划校验当完整NC001通过。

## 注解社区：多角色整体准入验收

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户确认 v1.4 已验收；三个只读角色从 UX、产品、OpenSpec/执行准入汇总，新增 openspec/annotation-community/READINESS_REVIEW.md。结论可进入工作包准备，尚不可整套业务编码。
进行到一半的事（精确到文件和章节）：NC 六件套与装配/机器契约尚未产出；没有新 READY/ACCEPTED。下方历史“待抽查”由用户本轮确认与 R4 通过记录取代。
下一步（第一件事）：按准入报告 §4/§5 准备 NC-001 与 NC-020a 六件套，再审查与派发。
已知的坑：七状态需逐屏落地；NC-004 outbox、NC-009 纯文本子范围、NC-007 Undo 依赖和 NC-001 新工程顺序需在工作包闭合。外部链路局部阻塞不等于整体停工；G3 并发工作不纳入此提交。

## 注解社区 v1.4 一次性修复

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：严格按 FIX_V1_4.md 执行 FIX-01～18，共 56 处逐字替换；六份目标文件已验证只含指定替换。总守卫与 verify.sh 均 0，git diff --check 通过。
进行到一半的事（精确到文件和章节）：无未完成替换；第 4 节账本保留策略未变，仍 UUIDv4/永久保留；文档头保持待抽查确认。
下一步（第一件事）：复核人按 FIX_V1_4.md §5 抽查；账本策略如需更改由用户另行决定。
已知的坑：本机 C.UTF-8 下两个守卫的汇总行会报 total 未绑定；使用 LC_ALL=C bash openspec/annotation-community/review_final_guard.sh 正常退出 0，未改脚本。其他 Agent 的 G3 改动不纳入本次提交。

## 注解社区 v1.3 六项返工

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：按审查提交 29c4ba3 补齐 RW-1～6，修订模型/数组规范化与 NC-010/017/019 命令恢复验收。
进行到一半的事（精确到文件和章节）：正文 v1.3 等待独立语义复核，无业务实现验收声明。
下一步（第一件事）：按 REVIEW_R2_RESULT.md §4 与 REVIEW_R2_CHECKLIST.md 再次复核。
已知的坑：review_r2_guard.sh 是存在性守卫；G3 并发改动保持，不纳入本次提交。

## 注解社区 v1.2 五项协议修订（优先于下方历史结论）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户授权的 R2-01～05 已写回 PRD/DESIGN/PLANS/TASKS，更新 REVIEW_R2_FOLLOWUP.md 并新增 REVIEW_R2_CHECKLIST.md 简短复核入口。
进行到一半的事（精确到文件和章节）：五项状态为 DOC_REVISED_PENDING_REVIEW；未编写业务实现、机器 Schema 或实测 fixture。
下一步（第一件事）：另一位 Agent 按 openspec/annotation-community/REVIEW_R2_CHECKLIST.md 只读复核；再准备相应 NC 工作包。
已知的坑：可信 notifier ID 映射仍需真实契约证据；上游 selector 类型与密钥协议前置保持，不凭结构检查关闭。其他 Agent 的 G3 工作不在本次修订范围。

## 注解社区线四份文档 R1 审查与补全

更新时间：2026-09-10（环境日期）
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：以四个只读角色（OpenSpec 规范、用户体验、BDD/TDD 就绪度、技术契约可行性）并行审查 `openspec/annotation-community/` 的 PRD/DESIGN/PLANS/TASKS v1.0，共 43 条阻断级缺陷（去重后 37 条），全部在 v1.1 中处置；新增 `REVIEW_R1.md` 缺陷台账与 `verify.sh` 结构校验器（FAIL 0）；24 个 NC 任务已登记进唯一监控表 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 的 G6 节，并新增 NC-025、拆分 NC-020a/b。
进行到一半的事（精确到文件和章节）：`DESIGN.md` §2.1 的 15 个 UGC ID 前缀标为「需用户确认后冻结」，未确认前 NC-002 不得离开 `PREPARING`；四份文档尚无任何工作包六件套，也无 READY 任务。
下一步（第一件事）：取得用户对 `DESIGN.md` §2.1 UGC ID 前缀的确认，然后按 `PLANS.md` §5 的首批顺序为 NC-001 生成工作包六件套。
已知的坑：`xuan-server/functions-py/tests/conftest.py` 强制局域网 Emulator（192.168.0.165），且此前不在任何任务白名单内；`repository-rest-adapter` 既有 `openapi_validation_test.dart` 有 8 处断言要求非法的 operation 级 `headers:`，修正结构必然弄红；`xuan-storage` 的 firebase BlobGateway 自述为内存 fake，生产实现由新增的 NC-025 承接；`xuan-server/notifier` 是文档此前未提及的第 8 个仓库，持有 3.0.3 权威契约，与本系统 3.1 契约必须分开。

## 上下游生产交付核对

更新时间：2026-09-09（环境日期）
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：两份消费协议的只读并行核对及主线程证据复核，逐项回执见 `docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md`。
进行到一半的事（精确到文件和章节）：U/A 回执为协调建议，未改写消费草案或发布政策；尚无真实生产包和云端联调证据。
下一步（第一件事）：联合确认纯 EPUB/TXT 的生产证据要求，再收敛 D-06 选区/迁移与共同交付 Schema。
已知的坑：当前 PUBLIC_RELEASE 强制字框；旧 unit 编号按排序重建；OCR corpus 导出不含完整定位资产。当前有其他 Agent 并发修改协调文档与草案，提交只包含本次回执及本节增补。

## 注解社区线交接（独立于下方 G3 线）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：按用户要求输出 `openspec/annotation-community/PRD.md`、`DESIGN.md`、`PLANS.md`、`TASKS.md`，包含确认默认规则、Undo/Redo、24 个本期工作项及需求/依赖/测试映射；完整键盘方案标为当前缺失且后续 F-01 承接。旧接入细化标为历史输入，冷启动入口更新。
进行到一半的事（精确到文件和章节）：四份总文档已产出；未生成机器 Schema/OpenAPI 或 READY 六件套，未写业务代码。书籍 U/A 和密钥恢复仍是明确前置任务，不再将自动保存/回收站/图片等已确认默认值称候选。
下一步（第一件事）：从 TASKS 的 NC-001 准备真实工程/宿主装配基线，再 NC-002 模型契约及本地笔记任务；NC-015 密钥协议与 NC-020 上游共同 Schema 并行准备。CLIENT 拟为 xuan-migration/reading-notes，须 NC-001 确认，现 xuan-migration/learn_system 无 Flutter pubspec，不能误写。
私人存储新发现：有真实 Firestore/RTDB row SDK 和 generic upsert，但当前 RecordOutboxMapper 明文 JSON 不能用于私人正文；云 blob 生产适配、长期备份和跨设备密钥恢复未见完整实现。IM guard 当前未比较传入设备 ID/指纹，不能直接当笔记授权证明。
已知的坑：Notification 管线有实现，生产业务接线不足；ReceiptRejected 是停止整批并报告；旧通知查重非原子且不适用多收件人。notebook 保存覆盖旧 committed，内存降级仍返回成功，不可当永久修订库。既有 OpenAPI 有 operation headers 非规范结构，字段断言测试不代表合规。D-06 未冻结；收回只能阻止后续访问，公共媒体不能发绕过 ACL 的永久 URL。
书籍新增边界：权威架构 PUBLIC_RELEASE 当前强制 glyphbox_level/OcrPage，原生来源分支尚未获批；不能由消费稿绕过。旧 EPUB 去空格/重组换行无原件映射、旧 unit 按排序重编号；两者不能直接作稳定生产锚点。原件档位、运输方式、capability 与正式发布门禁分开。

## G3 线交接（R3 复核未通过，暂不进入 G4）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：G3 R3 交叉复核；R2 的 10 个指定变异已修复，但新增 7 个等价变异仍可假绿：
  - T-04：G1–G7 完整语义门禁与防假绿（提交 `9b6194b` / `b15c25d`）
  - T-06：完整有序证据链（提交 `3768064`）
  - T-11：差距表现状事实与二元判据（提交 `6f62189`）
  - T-13：章节状态映射与 §16 局部候选标签（提交 `e3b1570`）
  - D-07：TechniqueProfilePack 与 QueryContractPack 规约冻结（提交 `f6be483`）
  - T-07：§16.2 表格 15 目录严格映射与 query-contract 归属修正（提交 `a62f225`）
  - T-08：Tag 三接口与五字段承接、Tag G4 命名空间化、排除 M5 生产者身份（提交 `045a0ab`）
  - G3 R3 结论：D-07/T-07/T-08 为 `REWORK_REQUIRED_R3`，详见 `docs/blackbox-spec-rework/reviews/G3-REVIEW-R3.md`。
进行到一半的事（精确到文件和章节）：T-04/T-06/T-11/T-13 保持通过；D-07/T-07/T-08 需改为精确肯定句、精确接口名和唯一供给关系门禁。
下一步（第一件事）：本节已被文件顶部“项目冷启动总交接”取代；现行入口是根 `PROJECT_COLD_START_HANDOFF.md`。
已知的坑：此处记录的是 R3 历史状态；不得派发未提交的旧 `work-items/g3-r3/PROMPT.md`，现行阻断与 R5 门禁见项目冷启动总交接。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
