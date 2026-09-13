# impl-08 四查复审 R2（独立审查者，W4-R8）

- 被审对象：返工提交 `559a359`（docs(impl-08): address four-check R1）相对 `cd6c7a6` 的全部改动；裁定依据 `G7-RULINGS.md` §9.5 第 45、46 条（另核对中间提交 cf6f61b/950b77b 对 run_all.sh 的 impl-04 侧改动，属他包写者，不计入本包）。
- 方法：逐文件读返工 diff；对 F1 用真实 m1_shim 链路逐步推演并核对代码行号；全包 grep 残留引用；实跑 `run_all.sh` 验证基线；重算全部用例数阈值。

## 一、R1 发现逐条闭合核对

**F1（阻断）→ 已闭合。** act/03.yaml:28-31 `stage_package_valid` 按第 45 条重写：有效运行中「承载恰 1 个本 stage StagePackage 修订」的 carrier 恰 1（0 或 >1 失败）；每个有效运行 ≤1 包；不承载包的有效运行不计入包判定，但须 `succeeded` 且 supersedes 链可回溯到 carrier；output_contract 改以 carrier 的包为准（:34-36）。真实链可达性（代码证据）：m1_shim 以 `supersede_step_run` 接替 fixture m1 运行（shim/m1_shim_source_assets.py:286、:313），不写 StagePackage（:180–234 无 stage_package 引用），以 `finish_step_run` 封存 succeeded（:221、:228）；Ledger 落 `supersedes_step_run_id`（service.py:412）。于是 eff(m1)={fixture 运行（1 包，carrier），shim 运行（0 包，succeeded，链回溯 carrier）}→ carrier 恰 1 → m1 Gate passed，act/07.yaml:30「m1 有 2 个有效运行、承载者恰 1」的 real_chain 期望可达。负例不破：0 carrier（test_blocked_when_stage_package_missing，act/03:53）与 wrong_stage（内容 stage 校验 :30）仍失败；BDD 4.2/4.4（BDD.md:30-32）、TDD §2 F1 判据（TDD.md:65）同步。

**F2（阻断）→ 已闭合。** (1) `stage_gate_report` 作为类型/产物的引用全删，包内仅存 TDD.md:66-67 的「非 tests 源码不含该串」负向断言（本意即防残留）。(2) act/04.yaml:45-47 advance 返回键增 `gate_reports`（本次调用累计、含上游与当前阶段），:63-64 删除「put_artifact 写 Gate 证据修订」整段，改为注释「不写任何上游 Gate 证据修订」；run_release 返回 `gate_reports={"m8": gate}`（:75）；run_until 各项为 advance 返回（:78-79）。(3) act/06.yaml:36-37 CLI 在 advance 结果前按 stage 升序打印 `ORCH GATE <stage> <passed|blocked>`，新增 test_cli_advance_prints_gate_lines（:67）。(4) act/07 gate_chain_stub_m1_m6 改为「逐次 advance 返回项 + Ledger 读接口重算，不查任何 Gate 证据修订」（:21-22），real_chain 独立重算同步（:30-31）。(5) 落盘另立 act/11.yaml：`status: DEFERRED`、`depends_on: [impl-08/10]`、不在 executor_groups（ACT.yaml:45-48），其契约即为 R1 建议的 validation_report_ids 首位方案，且由描述符键 `persist_gate_report` 门控、生产表默认不落盘。README §4 D-4/D-11（:92-93,:95）、§4.1 D-4/N-4 标已裁（:110）、§5.5（:163）、§6.2（:197）、BDD 5.1、TDD §2、PROMPT-I1、ACCEPTANCE §0 全部同步一致。

**F3（重要）→ 已闭合。** act/00.yaml:81 新增 `test_module_stage_out_of_closed_set_detected`（module.stage="m9" → stage_invalid），BDD 1.2 具名引用（BDD.md:8），阈值 15→16 两处同步（act/00.yaml:92、TDD.md:45）。

**F4（重要）→ 已闭合。** TDD §0:26-29、§3:86-91、ACT.yaml gates:65-67、README §1:42-43、PROMPT-I1 开工前提、act/00–10 全部 verify 的 unittest 命令统一为 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。全包 grep 复核：unittest 命令无 `tail` 取行残留；verify-T.sh / mutations.sh / run_all.sh 的 `tail -1` 为 shell 脚本 SUMMARY 取行，属第 27 条针对 unittest 的另一语境，保留合理。

**F5（重要）→ 已闭合。** act/08.yaml:40-42 命中清单改为运行时 grep 生成（模块包目录递归、排除任意层级 tests/、docstring 行计入、不写死行号），BLOCKED 行每模块最多 5 处超出写「等共 <n> 处」（n 运行时计数）；verify 改为三条模式匹配断言（:63-65，m3/m5/m8 各一，不比对具体行号）。已推演模式与运行时语义相符：m3 前 5 处含 `corpus_compiler/step.py:431`；m5 前 5 处为 context.py/inputs.py（匹配 `[a-z]*\.py`）；m8 前 5 处为 inputs.py（shim 子目录排在其后不计入前 5）。BDD 9.1 同步（BDD.md:75）。

## 二、返工引入问题的检查（新阻断排查）

- **阈值可达**：具名用例累计 TR=16（ACT00）/30（+01）/40（+08）/45（+09），对阈值 16/25/34/38；TO=16/32/58/70/86/96（ACT02–07），对阈值 15/30/46/55/66/74（ACT08 未回退 ≥72）——全部可达且等于具名累计（ACT00 恰 16=16），无凑数空间。act/10、act/11 均 DEFERRED 不设阈值（TDD.md:55）。
- **写范围**：`git show 559a359 --stat` 只含本包 18 个文件，未触碰代码/规格/Schema/fixture/台账/run_all.sh。注意一项非阻断事实：act/11 的 writes（edition_run.py、test_edition_run.py）与 act/04 重叠，但 act/11 DEFERRED 且依赖链（11←10←08←…←04）保证顺序在其后，本批内无并行冲突；建议主 Agent 将来派发 act/11 时同步重开 act/04 的验收面。
- **依赖无环**：act/11 depends_on impl-08/10，全链 00→01→…→09 线性，10/11 为 DEFERRED 尾挂，无环。
- **基线实测**：`bash openspec/acceptance/run_all.sh` 现输出 `SUMMARY pass=2 fail=1 blocked=8`，与 act/04:117、act/07:64、act/08:67、act/09:54、TDD §0:30/§3:92 的期望一致；20.1/20.10 仍硬编码 BLOCKED（run_all.sh:197、:322，即 act/09 两处替换目标行，逐字存在）；impl-04 已 ACCEPTED（cf6f61b），ACT 09 前置可满足。20.4/20.8 已由 impl-04 接入 m8 判定并如实 BLOCKED，不影响本包 SUMMARY 期望。
- **一致性抽查**：advance 的 legacy/step_request 两分支的当前阶段 gate 均在循环顶计算并计入 gate_reports，无漏项；run_release 的 gate_reports 自洽；act/07 registered_modules_m1_m6 补 PASS 行绑定披露模板（:39-40，兼闭 F8）；ACT.yaml global_rules 同步第 46 条与 F7 桩类型说明（:53-54）。

## 三、判定

**READY**。F1–F5 全部闭合，未发现新阻断；遗留一项跨波备忘（act/11 与 act/04 写范围重叠，DEFERRED 顺序保证，派发时重审）与 R1 建议 F6–F9 已随返工一并处置（F6 阈值统一为 25、F7 桩类型说明入 ACT.yaml/act/02/README §5.8、F8 PASS 行模板、F9 act/05 改键访问）。

（本复审未修改被审工作包与任何代码/规格/Schema/fixture/台账；仅新增本文件。）
