# TODO —— learn_system 待办总表（唯一追踪入口）

建立：2026-09-23。起因：用户 4 天前要求清掉所有问题，至今仍有大量遗留——**根因是没有任务追踪**，事情散在对话、PLAN.md、HANDOFF.md、CHARTER 里，边做边掉。

## 使用规则（每个 Agent 必须遵守）

1. **本文件是唯一的待办入口。** 任何新发现的问题，先写进本表，再动手。不许只在对话里说一句"记为已知缺口"。
2. **一次只做一条**，按「执行顺序」从上往下。做完立刻改状态、填提交号和日期，然后才开始下一条。
3. 每条都有「完成判据」——判据没达到，不许标完成。标完成必须附证据（命令 + 结果）。
4. 状态只用这几个：`待办` / `进行中` / `完成` / `待用户决定` / `待核实` / `不做（附理由）`。
5. 发现某条已经过时或已被别人做完，改成 `完成` 或 `不做` 并写明证据，不许直接删行。
6. 会话结束前（包括额度到点前），把「进行中」那条的进度写进它的备注。

---

## 一、执行顺序（本线：G3 黑箱 / 生产 dataset）

**总目标（用户 2026-09-23 重申）：M1→M8 连成一条线，M8 所有问题解决，M3 不许走后门。** 顺序：T02 → T03 → T04 → T05 → T06 → 其余。

| # | 状态 | 事项 | 完成判据 | 来源 / 依赖 |
|---|---|---|---|---|
| T01 | 待用户决定 | **回复 XUAN 产品经理的奇门底本请求**（首发阻断项 LB-01，已拖延）。回答三件事：最早交付日期与能交付哪几部书；是否与本线冲突；按 `~/Documents/ai-integration-design-20260921/Dataset-Intake-Contract.md` 交付的可行性。已查到的事实：殆知阁 `易藏/术数` 下有《遁甲演义》（含《烟波钓叟歌》开篇）、《奇门遁甲统宗》（值符 132 处 / 八门 37 / 九星 26）、《奇门遁甲秘笈大全》（值符 182 / 八门 47 / 九星 82）等 9 部；契约要求的 `SearchIndexPack`（向量索引）本线 M8 尚未产出（见 T05b）。 | 已发消息给【玄微】产品经理会话，内容含日期、书目、与本线冲突情况、契约里哪些字段本线暂不能给；冲突需用户排先后的，已转告用户 | 2026-09-22 跨会话消息；关联 T05b、T11。**进展 09-23**：答复草稿已写 `docs/replies/2026-09-23-xuan-qimen-corpus.md`（书目实查：《遁甲演义》含《烟波钓叟歌》全文，《奇门遁甲统宗》《奇门遁甲秘笈大全》讲值符八门九星）；A 档原文约 5 个工作日、B 档向量索引再加 1–2 周。**卡在两件用户决定**：①与 T02–T08 的先后；②原【玄微】产品经理会话已不在，答复发给谁 |
| T02 | 完成 | **把 run_all 里 5 条写死的 BLOCKED 改为真跑判定**：20.4、20.6、20.8、20.9、20.11 最后那句结论是写死的一行 `block_line`，理由（"未实现"等）可能已过时。做法同 M7 的 G2（ACT 27）。**先做这条：它决定后面 M8 各条的真实起点。**<br>**进展 09-23**：实查共 **7 处**写死——run_all 的 20.6、20.9、20.11 整条写死；20.4、20.8 调了 M8 验收但只要不失败就一律输出写死的 BLOCKED；M8 自己验收里 `mentions_mapping`、`knowledge_chain` 两条也无条件输出 BLOCKED（`pipeline/dataset_compiler/acceptance.py:638、660、692、728`）。 | 5 条都由实际运行结果决定；每条 BLOCKED 的理由都是实测到的具体缺口；有篡改探针证明不是写死 | 本会话 2026-09-23 核查 |
| T03 | 完成 | **修走后门（用户要求必须修）**：模块入口绕过 LedgerPort 直接读写 Ledger 内部。**实测 09-23 不止 M3**：M3 `corpus_structural` 30 处、M5 `automatic_validation` 15 处、M8 `dataset_compilation` 18 处，**共 63 处**（清单以 `python -m pipeline.contract_registry.acceptance` 的 `modules_port_clean` 为准）。全部改为只经端口。<br>**进展 09-23**：①账本端口新增 8 个只读查询（describe_revision、list_step_run_revisions、list_artifact_revisions、list_frozen_inputs、get_processing_run、list_step_runs、list_stage_packages、count_artifacts），`read_object` 挪进服务端与只读端共用的 LedgerReadMixin——SQL 留在账本层；②M5 15 处已清零（`3adf199`，主 Agent 改）；M8 18 处派 agy Gemini 3.8 Flash（worktree `learn_system-wt-t03-m8`，会话 t03m8），M3 30 处派 FreeBuff DeepSeek V4.1 Flash（主工作树，会话 t03m3），两路并行，文件不相交。<br>**M3 已验收（`a3e7908`）**：30 处清零、167 条全绿；step_offset 按 stage=m2 筛选，护栏用例在去掉筛选时报错（主 Agent 探针）。**T03 收尾待办**：①M5 清零时主 Agent 漏跑 contract_registry，`test_modules_port_clean_blocked_lists_three_dirty_modules` 与 `test_shell_exit_2` 自 `3adf199` 起为红，M8 收口后一并改；②删死代码 `corpus_compiler/acceptance.py:_get_step_data`（无调用方，且读不存在的列）；③`impl-08-orchestrator` 文档里写死的 20.10 期望文本同步。③顺带修正：`corpus_compiler/step_offset.py:217` 找不到 M2 运行时拿「该 EditionPart 最近一次任意阶段的运行」冒充 M2，改为按 stage=m2 筛选。 | 契约注册表 `modules_port_clean` PASS（M3、M5、M8 零处直接访问）；各包测试全绿 | run_all 20.10 实跑；用户 2026-09-23 第 4 点 |
| T03c | **完成（2026-09-24，主线 `25082a3` + 守护用例提交）**。111 处全部改为经 LedgerPort：M1 3、M2 5、M4 22（云端 Claude）、M7 28（agy，含裁决 (a)：`assembly/inputs.py:173` 改为 `describe_revision`→`get_step_run`，用户批准）、M6 53（FreeBuff 24 + cmd 29）。证据：五包扫描全 0；11 包 1490→1517 全绿 0 skip；检测器/登记表/调度器相对 `f4df613` 未动；守护用例 `test_t03c_packages_have_no_ledger_internals` 探针转红。详见 `docs/jules/T03c.report.md`「收尾验证」。遗留既有问题见 T16、T17。 | **新登记模块的走后门**。T03 只清了当时已登记的 M3/M5/M8 三个包；T04 一登记 M1、M7，扫描器就在 `pipeline/intake/`（`acceptance.py:114, 125` 等）和 `pipeline/assembly/`（28 处）命中直接读 Ledger 内部，`modules_port_clean` 退回 BLOCKED。M2、M4、M6 的包登记后很可能也有。**T03 说「全部清零」只对当时登记的模块成立。** 实测（`215d1e3`）5 个包共 111 处：intake 3、digitization 5、knowledge_extraction 22、assembly 28、review 53。照 T03 的做法清掉，不改扫描范围（那等于放宽）。 | M1、M2、M4、M6、M7 登记为生产模块后 `modules_port_clean` 仍 PASS | T04A、T04B 09-23 实测 |
| T03b | 待办 | **OCR / 模型 / 索引三个端口各自至少 2 个可替换 Adapter**（契约注册表 `other_ports_adapters`，实测 ocr=0、model=0、index=0）。与 T06 相连：模型端口的两个 Adapter 正好是 FreeBuff 与 OpenCode；索引端口与 T05b 相连。 | `other_ports_adapters` PASS；`run_all.sh 20.10` PASS | 契约注册表实跑；依赖 T06、T05b |
| T04 | 待办（**挡着它的 T03c 已于 09-24 完成**；云端已交还本地，见 `docs/handoff/LOCAL-RETURN.md`；等用户下令开工） | **交接**：`docs/handoff/CLOUD-HANDOFF.md`。T04A 半成品在分支 `wip/t04a-handoff`（`8332484`，红：orchestrator 1E+6F、contract_registry 6F），回报 `docs/handoff/t04a.report.md`、裁决 `docs/handoff/t04a-ruling1.md`；T04B 半成品在分支 `wip/t04b-handoff`（`87e889d`，只有 2 条红用例），回报 `docs/handoff/t04b.report.md`。两路都被 T03c 挡着。**完成判据第③条（真书账本复验）云端做不了，需用户本机。**<br>**M1→M8 连成一条线（用户 4 天前的要求）**。**实查 09-23**：登记表 `pipeline/contract_registry/registry.yaml` 里 M1、M2 是 `thin_import`（从 fixture 导入顶替，不是生产模块），M3/M5/M8 是生产模块，**M4、M6、M7 根本没登记**；调度器 `FIRST_SLICE_EDITION_STAGES=(m1,m2,m3,m5)`、`DEFERRED_STAGES=(m4,m6,m7)`；M8 的输入不接 M7。真书账本里 M1–M6 是手动逐段推进的（M4 人工事件 24、M6 26，M6 还有 1 次停在 awaiting_human），**M7、M8 从未在真书上跑过**。各阶段生产入口都已存在（run_m1…run_m8），主体是登记与接线。拆两路并行：**T04A** EditionRun M1→M6（FreeBuff）；**T04B** ReleaseRun M7→M8 并含 T05f（agy）；主 Agent 合并后做真书全线集成。**主 Agent 此前把"各模块过了自己的验收"说成"M1–M6 已完成"，是错的；本条完成前不许再说"已连通"。** **09-23 T04A 停手 4 条，已裁（`runs/prompts/t04a-ruling1.md`）**：M1/M2 模块自己登记 StagePackage（原先从不登记，Gate 永远过不去）；生产登记表只登记电子文本路线、运行输入显式声明 `route: text`、m3 换 `run_m3_text`；人工恢复走描述符 `resume_entry`，resume_token 不许落盘；20.1 宿主换 `qianyuan_ed01_text`、判据改 M1→M6 全线且只许收紧。 | ① 登记表 M1–M8 全部是生产模块（fixture 导入只留作测试宿主，不在生产线上）；② 调度器由 M1 推到 M8：遇到规格规定的人工节点（M4 提交、M6 审核、M7 裁决）以 awaiting_human 暂停，经人工接口处理后自动续跑，**除这些节点外不需要任何手动推进**；③ 真书《乾元秘旨》在账本副本上由调度器从 M1 跑到 M8，产出 knowledge_chain=compiled 的 PublicationPackage（人工节点用真书账本里已有的决定回放）；④ `run_all.sh 20.1` PASS；20.2 保持 PASS | 用户 2026-09-19 前后要求、2026-09-23 第 2 点；PLAN.md:93 |
| T04c | 待办 | **OCR 路线 M2 生产模块**。T04A 实查：登记表一个 stage 只能登记一个 Module，OCR 路线的 M2 目前只有 fixture 导入（`m2.fixture_import`），没有生产模块；T04 裁定生产线只登记电子文本路线，OCR 路线在调度器入口按 `route` 拒收。扫描本古籍要进生产线，必须先有这个模块。 | OCR 路线 M2 生产模块登记进登记表；`route: ocr` 的 EditionRun 由调度器跑通 M1→M6；mini_ed01 走调度器全线 | 主 Agent 09-23 裁决 T04A 时新增 |
| T05 | 待办 | **M8 全部问题逐条解决（用户这几天的主要要求）**。拆为下面 T05f、T05a–T05e（**先做 T05f**），全部完成才算 T05 完成。**主 Agent 此前几天做的是 M7（M8 的输入），没有跟用户对齐顺序，也没回头收 M8。** | T05f、T05a–T05e 全部完成；`m8-span-identity.sh` 全 PASS；run_all 20.6、20.9、20.11 PASS | 用户 2026-09-23 第 3 点 |
| T05f | 待办（并入 T04B） | **M8 核心：把三个已写好的构建函数接进 `run_m8`**。实查：`packs.build_knowledge_data_pack`、`packs.build_graph_projection_pack`、`packs.build_evidence_chain` **只有 `tests/test_packs.py` 在调，`run_m8`（`step.py:235`）一次都没调**——M8 只产出了 source_asset_pack、evidence_map_pack、release_manifest 三样。知识条目、图投影、证据链因此**从未被真实产出过**，外面写死的 BLOCKED 理由把这件事遮住了（与 M7 D 波「函数有、没接线」同形）。**排在 T05a–T05e 之前**，它们大多依赖本条。 | `run_m8` 以 M7 Snapshot 为输入，实际产出 KnowledgeDataPack、GraphProjectionPack 与证据链并封存进 Ledger；有一条真实形状输入走完全栈的用例（R15）；三个函数在非测试代码里都有调用点 | 主 Agent 09-23 实查；R15 |
| T05a | 待办 | M8：concept→span 的 mentions 映射（`m8-span-identity.sh` 唯一 BLOCKED 项）。 | `mentions_mapping` PASS | m8-span-identity.sh；需 M4 产出 concept mentions（薄接入先产） |
| T05b | 待办 | M8：SearchIndexPack（向量索引，D14-C），按 `Dataset-Intake-Contract.md` 给出 `embeddingProfile` 与 `spanIdMapping`。T01 奇门交付 B 档也要它。原文片段的索引不依赖 M4。 | SearchIndexPack 产出且过契约校验顺序 1–5 | D14-C；契约 §3.3 |
| T05c | 待办 | M8：KnowledgeEntry 逐项补全，`not_captured` 不被误判为不存在。 | `run_all.sh 20.6` PASS | 依赖 T02 |
| T05d | 待办 | M8：GraphProjectionPack，移动端数据与图投影同源、往返无损。 | `run_all.sh 20.9` PASS | 依赖 T02 |
| T05e | 待办 | M8：由 M7 的 identity_delta 生成跨 Release 的 IdentityMigrationMap，算注解锚点可迁移率。 | `run_all.sh 20.11` PASS | 依赖 T02；M7 已能产出 identity_delta |
| T06 | 待办 | **M4 接真模型**。**没有模型 API**（用户 2026-09-23），可用的只有：FreeBuff（DeepSeek V4.1 Flash、GLM 5.3 Flash）、OpenCode（MiMo V2.6 Flash、Muse Spark V1.3）、主 Agent 自己（Claude）。所以 Model Adapter 要包的是这些**命令行 / 会话工具**，不是 HTTP API。第一步：实测哪些能非交互调用（如 `opencode run -m …`；FreeBuff 是否有非交互模式），再定 A/B 抽取与 C 复核分别用谁（A/B 必须不同模型）。 | `m4-stage-gate.sh` 的 `cross_model_extraction` PASS；真书至少一个 EditionPart 由两个不同真模型独立抽取、第三个复核，过 M4 Gate；Adapter 可替换（20.10 不退步） | m4-stage-gate.sh；用户 2026-09-23 第 1 点 |
| T07 | 待办 | M3 实现 SemanticSpan（M4 现以 StructuralSpan 薄接入）。 | `m4-stage-gate.sh` 的 `semantic_span_input` PASS | m4-stage-gate.sh |
| T08 | 待办 | 术语分层：建立 `schemas/shared/homographs` 与七政术语表，实现 L1/L2/L3 自动判层。 | `m4-stage-gate.sh` 的 `term_layering_scan` PASS | m4-stage-gate.sh |
| T09 | 待办 | **核实 PLAN.md 里 13 条旧待办是否仍成立**（第 323–372 行，见 PLAN 原文）。 | 每条转成本表条目或标 `完成` / `不做` 并附证据；PLAN.md 同步 | PLAN.md:323–372 |
| T10 | 待办 | 20.4（全链双向追溯）、20.8（发布包含结构化知识）随 T04、T05、T06 完成后复验。 | `run_all.sh 20.4`、`20.8` PASS | 依赖 T04、T05、T06 |
| T11 | 待办 | **奇门首发材料**（与 T01 相连）：PLAN.md 里已有的奇门条目——《烟波钓叟歌》s13–s110 扩批模板（:356）、奇门试点材料选段（:359）、奇门分工位金标集与模型对比（:361）、据试点修订 Schema（:362）。按 T01 与用户商定的日期排进来。 | 按 T01 答复的交付范围产出，并过 M1–M8 相应 Gate | PLAN.md:356–362；依赖 T01 |
| T12 | 待办 | **全面盘点**（用户计划）：learn_system 生产 dataset 的架构、功能、代码。以本表为骨架，盘点中发现的新问题一律先入本表。 | 盘点报告落盘；新问题全部入表 | 用户 2026-09-23；建议在 T02、T09 之后开始，否则会读到过时结论 |
| T13 | 待用户决定 | **20.7 旧格局库怎么办**。事实：`pattern_knowledge_workbench/assets/ge_ju_database.sqlite` 496 条规则，出处书名填了 486 条、结构化条件 404 条，**原文 0 条、人工核实 0 条**，按规格没有原文不能进正式知识库，所以 FAIL 是按设计判的。选项：(a) 把 486 条的出处篇章（《十一曜定格》88、《星格贵贱总赋》52、《七政四时论》37…）按正规流程数字化、抽出带证据的知识再对回，旧库降为对照清单；(b) 改判据为"旧库只作对照"；(c) 维持 FAIL 直到回填。**主 Agent 建议 (a)，判据是否改由用户定。** | 用户选定；选 (a) 则拆成本表新条目 | run_all 20.7；规格 §20 第 7 条 |
| T14 | 待办 | **6 条用例在没有页图的机器上会红**。主 Agent 在干净副本（无页图、无真书账本）上实测：`orchestrator` 5 条（`test_blocked_line_exact_text_m4`、`test_fixture_yields_five_pass_one_blocked_exit_2`、`test_real_chain_detects_missing_upstream_lineage`、`test_real_chain_reaches_m5_and_m8`、`test_shell_exit_2_on_fixture`）与 `contract_registry` 1 条（`test_20_1_blocked_line_computed`），原因都是「派生页图缺失」。它们默认本机有页图目录，不像 `dataset_compiler` 那 36 条会按宿主缺失 skip。与 G2 修过的「写死本机有真书账本」同形。 | 这 6 条在有页图/无页图两种机器上都给出正确结论（按实际宿主计算期望，或缺页图时 skip 并写明原因） | 主 Agent 09-23 部署 Jules 时实测 |
| T15 | 待办 | **云端环境脚本缺两样东西，导致 2 条假红**。云端 Claude 09-24 在干净容器上实测：`tools/jules_setup.sh` 装完后，①没有 `en_US.UTF-8` locale，`openspec/acceptance/m5-evidence-gate.sh:9` 写死 `export LC_ALL=en_US.UTF-8`，stderr 的 setlocale 警告混进输出首行，`validation` 的 `test_shell_never_trusts_copy_verify` 红；②没有 `sqlite3` 命令行，run_all 20.7 由 FAIL 变 BLOCKED（「sqlite3 不可用」），`contract_registry` 的 `test_full_summary_unchanged` 红。手工 `localedef -i en_US -f UTF-8 en_US.UTF-8` 与 `apt-get install sqlite3` 后两条恢复，基线与 `docs/jules/T03c.md` 第五节一致。 | `jules_setup.sh` 在干净容器上补齐二者（或脚本不再写死 en_US），装完即得任务书基线 | 云端 Claude 09-24 跑 T03c 基线时发现 |
| T16 | 待办 | **review 包有 2 条偶发失败的用例**（cmd 09-24 实测，既有问题非本次引入）：`test_console_rework_line`、`test_close_with_pending_exit_2`，都是审核台命令行的子进程用例，改后全量 review 跑 9 次失败 1 次、单跑与基线难复现，疑似子进程/写锁计时。证据见 `docs/jules/T03c-m6rest.report.md`「验证 4」。 | 查明原因并修复，连跑 30 次全过 | cmd 09-24 |
| T17 | 待办 | **审核台 `cmd_queue` 遇 modify 决定必抛**（cmd 09-24 实测，既有缺陷）：用含 modify 的 `m6_decisions.yaml` 驱动 `queue`，退出码 2，`ReviewRefused: modify requires modified_revision_id`；在改动前的 `822670e` 上同样复现。T03c 要求行为不变，未修。候选：(a) cmd_queue 为 modify 补 `modified_revision_id`（从 reviewed_candidate 查）；(b) 明确 cmd_queue 不支持 modify 并给清楚的报错。 | 用户或主 Agent 裁定方案后修复，有用例钉住 | cmd 09-24，`docs/jules/T03c-m6rest.report.md`「待裁决 1」 |

## 二、待用户决定

| # | 状态 | 事项 | 主 Agent 建议 |
|---|---|---|---|
| U01 | 待用户决定 | Gitea 受保护分支 `codex/docs/knowledge-compilation` 比本地落后 306+ 个提交。全部内容已推到备份分支 `backup/knowledge-compilation-20260923`。是否合入、怎么合入？ | 在 Gitea 上从备份分支开合并请求，由你审后合入 |
| U02 | 待用户决定 | 废纸篓 `~/.Trash/learn_system-m7-probe-leftovers-20260923/`（3.6GB，本轮执行器的探针副本）确认后清空。 | 可以清空，其中没有独有内容 |
| U03 | 待用户决定 | 仓库里其他会话留下的未跟踪文件：`.claude/`、`.commandcode/`、nc-* 的 `DELIVERY_REPORT*.md`、`guwen-retrieval-deployment-and-lightweight-guide.md`，以及 worktree `.claude/worktrees/agent-ad7f6f7bb2ae5215e`。 | 交给对应会话认领；认领不了的由你决定删留 |
| U04 | 待用户决定 | 本会话的 Remote Control 仍开着（当初为跟另一台机器通话打开）。 | 用不上了，可在工具栏关掉 |
| U05 | 待用户决定 | T13（20.7 判据）——见上表。 | 选 (a) |

## 三、已定论、不做（留档，防止被当成遗漏）

| # | 事项 | 定论与理由 |
|---|---|---|
| X01 | M7 旧 Snapshot 缺 collation_units 须迁移 | 不做：真书账本里没有任何 M7 Snapshot，无实例可迁（CHARTER §32.2） |
| X02 | M7 返工时对勘关系反向、R07b 人工决定须重裁 | 接受为设计后果（CHARTER §29 Q8） |
| X03 | M7 Concept 合并不可达 | 维持：同名走别名已能表达，无数据需要（§21④） |
| X04 | M7 同 source 不同分册的扩展 | 维持拒收并写明理由（§21） |
| X05 | M7 `_id_allocation` 最大号被退役的两难 | 维持：真书无 Pattern 获批，触发时 model 拒收（§22.3） |
| X06 | M7 第三方引用退役号不自动改指 | 维持 fail-closed：改指规则规格未定义（§21④、§22.2） |

X03–X06 都是"遇到时报错停下、不会静默出错"的边界。若将来有真实数据需要，重新入第一节。

## 四、不归本线（注解社区 NC-*，归 C/S 会话）

PLAN.md 第 8、108–196 行的 NC-001～NC-026、Firebase 去留、上游书籍契约等共约 25 条，归 C/S 会话（G6 注解社区）追踪，本线不处理。
其中 **Firebase 去留（PLAN.md:109）是用户决定项**，已暂缓。

## 五、完成记录

（每完成一条，在这里追加一行：日期 / 编号 / 提交号 / 一句话证据）

- 2026-09-23 / T03 / `fd0ba6e` `3adf199` `a3e7908` `9928478` + 收尾提交 / 63 处走后门清零：账本端口补 8 个只读查询（主 Agent），M5 15 处（主 Agent）、M3 30 处（FreeBuff DeepSeek V4.1 Flash）、M8 18 处（agy Gemini 3.8 Flash，worktree 并行）；契约注册表 `modules_port_clean` PASS；step_offset 冒充 M2 的问题修掉（探针：去掉筛选即报错）；检测器灵敏度补用例；删死代码 `_get_step_data`；11 个包全绿。20.10 仍 BLOCKED，只因 T03b
- 2026-09-23 / T02 / `57e2a44` / 7 处写死判定全部改为读 M8 实际产出；探针：M8 报 graph_projection PASS/FAIL → 20.9 随之 PASS/FAIL；新理由实测出 M8 发布包只有 2 个子包、M8 输入不含 M7 Snapshot；11 个包全绿，全局 pass=3 fail=1 blocked=7
- 2026-09-23 / M7 全部（F～I 波）/ `64371c8` / `run_all.sh 20.5` PASS，`m7-assembler.sh` pass=17 fail=0 blocked=0，11 个包全绿（CHARTER §31–§32）
