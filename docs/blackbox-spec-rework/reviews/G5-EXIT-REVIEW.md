# G5 R1 总准出记录

审查者：主 Agent（Dataset 会话）｜日期：2026-09-11 ｜ 审查对象：HEAD `8839ce3` 的 `git archive` 干净树（软链 `.venv`、`pattern_knowledge_workbench/assets`；`FIXTURE_ASSET_ROOT` 指本机页图目录）

结论：**14 条准出条件中 13 条已满足并有证据；第 14 条「用户确认进入实现阶段」待用户裁定。** 用户确认后由 `work-items/g5/`（`PROMPT-G.md`）把规格文档级状态从 `REVIEW_FAILED_R1` 翻为 `R1_REWORK_CLOSED`。

## 1. 准出条件逐条对照

| # | 条件（SUBAGENT_TODO G5） | 结论 | 证据 |
|---|---|---|---|
| 1 | G1 规格内核全部 `ACCEPTED` | 满足 | D-01 `fdf1e07`+`a30a709`+`fa2b220`、D-03 `b0022d4`、T-02 `6e317cc`+`376e78c`、D-02 `08fe789`+`fa69901` |
| 2 | G2 R0 工作台数据安全全部 `ACCEPTED` | 满足 | ACT-01 `f7ffd2f`/`3d6cfd2`、ACT-02 `424dc9a`/`54c0497`、ACT-03 `ffda853`、ACT-04 `2e11932` |
| 3 | G3 T 类全部 `ACCEPTED` | 满足 | T-01～T-13；假绿经 R3/R4/R5 关闭（`1d4a6dc`、`ffe19df`、`5de99fa`、`241c38c`） |
| 4 | G4 D 类全部 `ACCEPTED` | 满足 | D-01～D-19；g4-r1 六项、g4-r2 三项、g4-r3 三项验收记录见各 `ACCEPTANCE.md` |
| 5 | BDD 总验收包完整 | 满足 | 26 个黑箱工作包目录均含 `BDD.md`；总验收入口 `openspec/acceptance/run_all.sh`（§20 十一条）+ 统一宿主 `pipeline/corpus/_fixture/mini_ed01/` |
| 6 | TDD/机器门禁可执行 | 满足 | `verify-T.sh` 61 PASS / 0 FAIL；`mutations.sh all` 109/109、selftest 41/41；`schemas/verify.sh` exit 0；`run_all.sh` `pass=0 fail=1 blocked=10` exit 1（20.7 预期 FAIL）；`check_d16.py` `D16 OK`；fixture `verify.sh` `FIXTURE OK` |
| 7 | ACT 覆盖映射无遗漏 | 满足 | 见 §3 映射表：36 个工作项每项有 ACT 文件或豁免登记 |
| 8 | 所有 Executor Prompt 已归档 | 满足（含 7 项豁免登记） | 26 个工作包目录各含 `PROMPT*.md`（g3-r2 为 `COLD_START_PROMPT.md`）；D-01/04/05/09/12/17/19 于 G0 准出制度启用（2026-09-09）前完成，无 Prompt 可归档，按台账「旧流程豁免」登记，判据见 §2 |
| 9 | `verify-T.sh` 无假绿且全部应通过项 PASS | 满足 | 61/61 PASS；假绿封闭证据 `work-items/g3-r5/ACCEPTANCE.md`（13 例矩阵外盲测、FAIL-ID 超集） |
| 10 | `run_all.sh` 可运行并逐条报告 | 满足 | 11 行 `PASS/FAIL/BLOCKED` + SUMMARY；BLOCKED 行名逐字属 §19；副本脚本不被信任（`2978ad9`） |
| 11 | 最终规格符合性审查通过 | 满足 | 见 §4 |
| 12 | 最终质量审查通过 | 满足 | 见 §4 |
| 13 | PLAN/HANDOFF 已同步 | 满足 | PLAN R1 返工节 44/44 勾选、0 未完成；D-16 映射节；HANDOFF 顶部节 |
| 14 | 用户确认进入实现阶段 | **待用户** | 确认后填入 `work-items/g5/README.md` §2 并派发 `PROMPT-G.md` |

## 2. 七项「旧流程豁免」的判据实跑（D-design.md 原判据，2026-09-11）

| 项 | 判据 | 实测 |
|---|---|---|
| D-01 | `artifact_revision_id` ≥1；原则 7 附近含该词 | 18；1 |
| D-04 | 进程模型 + 三消费者接入 + 锁策略 | §17：「单机本地进程」「本地客户端调用」「只允许一个写入者…WAL」各在；`Flutter\|Dart` 1。原判据 grep 措辞「本地服务/库内调用/文件协议」为决议前候选词，字面 0 命中，已订正 D-design 判据为定稿用词 |
| D-05 | `KnowledgeEntry` ≥3；CONTEXT.md 两词条 | 11；3 |
| D-09 | `EditionPart` ≥4；「整本/三百页」无残留矛盾 | 19；唯一命中在 §21 非目标，语义为反例，无矛盾 |
| D-12 | §11、§12 各一句工具归属 | 1；1 |
| D-17 | §19 五处存储各一个结论词 | 6 行（含 OCR 页面 JSON 行）各有 迁移/重跑/冻结为历史快照 |
| D-19 | 三层存储 ≥2；三档位 ≥2 | 12；6 |

## 3. ACT 覆盖映射

| 工作项 | ACT 文件 | 证据提交 |
|---|---|---|
| T-01～T-13 | `work-items/t01..t13/ACT.yaml` | 台账各项 |
| D-02 / D-03 / D-07 | `work-items/d02/ACT.yaml`（2 act）、`d03/ACT.yaml`、`d07/ACT.yaml` | `08fe789`/`fa69901`、`b0022d4`、`a62f225`+R4/R5 |
| D-06 / D-08 / D-10 / D-11 / D-13 / D-14 | `work-items/g4-r1/act/d{06,08,10,11,13,14}.yaml` | `e474ae4`、`07f79dd`、`015e34f`、`3598ea8`、`4086c2c`、`d36a202` |
| 前缀登记 sch_/sv_/cg_ ；pat_/ent_ | `g4-r2/act/r2-01.yaml`；`g4-r3/act/r3-02.yaml` | `851fa70`；`e306258` |
| D-15 / D-18 | `g4-r2/act/r2-02.yaml`、`r2-03.yaml` | `6fc8536`；`4884b6a`+`2978ad9` |
| D-16 | `g4-r3/act/r3-01.yaml`（+`r3-03.yaml`） | `76bc4b4`；`aa85430` |
| ACT-01～ACT-04 | `docs/blackbox-spec-rework/act/01..04.yaml`；`work-items/act01`、`act02`、`r0-dep-unlock` | 见 §1 第 2 行 |
| G3 假绿封闭 R3/R4/R5 | `work-items/g3-r3/mutations.sh`、`g3-r5/act/01,02` | `1d4a6dc`、`ffe19df`、`5de99fa`、`241c38c` |
| D-01 / D-04 / D-05 / D-09 / D-12 / D-17 / D-19 | 无 ACT（旧流程豁免） | §2 判据实跑 |

## 4. 最终规格符合性与质量审查（主 Agent）

- 结构：§1–§22 共 22 节，编号连续；§3–§18 每节一行 `状态：`（T-13 冻结映射 PASS），§22 `已确认设计`；无节标 `最终规范`。
- 占位：全文无「待用户确认 / TODO / TBD / 待定」；唯一 `TODO` 命中是 §19 对 `pipeline/TODO.md` 的路径引用。
- 标识：规格使用的 19 个前缀（`src_ ss_ ku_ as_ pr_ co_shared_ co_ hg_ art_ rev_ prun_ srun_ pkg_ rel_ sch_ sv_ cg_ pat_ ent_`）全部在 `openspec/id-prefix-registry.md` 登记；注解社区 17 个 UGC 前缀不进规格（登记册 §3.5）。
- 可判定性：§20 十一条各带 `run_all.sh 20.N` 判据；§19 十九行各有 owner（D-16）；§22 分期与 §19 第 5 列一致。
- 一致性抽查：§8.1 第 3b 节五行与登记册 §3.3/§3.4 逐字一致；§16 `AnchorContractPack` 字段与注解社区 NC-002 契约一致（C/S 会话 2026-09-11 确认）。
- 已知缺陷（不阻塞准出，首纵切第一批 ACT 先修）：`check_d16.py` R3 把表 B 行数写死为 43、R4 要求黑箱节任何新 `- [ ]` 登记进表 B，导致 PLAN 黑箱节暂时不能新增未勾选项；修法为 R3 改「≥ 43」并允许表 B 追加行（主 Agent 2026-09-11 自查发现）。
- 已知保留项（不阻塞准出）：§3、§9、§15 及 §16 一句仍为「讨论候选」，§4/§7/§8/§10–§14/§16/§17 为「待验证假设」——这是 T-13 规则下的既定标签，升级需用户批准整份规格；文档级状态仍为 `REVIEW_FAILED_R1`，由 g5-01 翻转。

## 5. 准出后第一批实现（预告，非本记录范围）

§22 首纵切内：Artifact Ledger（§17，判据 `run_all.sh 20.2 20.3`）→ M3（`20.1` 的 fixture 部分）→ M5 → M8。每批按六件套派发，主 Agent 只写 Prompt 与验收。
