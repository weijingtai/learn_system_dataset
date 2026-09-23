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
| T02 | 待办 | **把 run_all 里 5 条写死的 BLOCKED 改为真跑判定**：20.4、20.6、20.8、20.9、20.11 最后那句结论是写死的一行 `block_line`，理由（"未实现"等）可能已过时。做法同 M7 的 G2（ACT 27）。**先做这条：它决定后面 M8 各条的真实起点。** | 5 条都由实际运行结果决定；每条 BLOCKED 的理由都是实测到的具体缺口；有篡改探针证明不是写死 | 本会话 2026-09-23 核查 |
| T03 | 待办 | **修 M3 走后门（用户要求必须修）**：M3 `corpus_structural` 入口绕过 LedgerPort 直接读写 Ledger 内部（`pipeline/corpus_compiler/step.py:431, 446, 534` 等，以 run_all 20.10 实报为准）。改为只经端口。 | `run_all.sh 20.10` 不再报 M3 直接访问 Ledger；corpus_compiler 与 contract_registry 测试全绿 | run_all 20.10 实跑；用户 2026-09-23 第 4 点 |
| T04 | 待办 | **M1→M8 连成一条线（用户 4 天前的要求）**：调度器现在只串了 M1–M3、M5；M4、M6、M7、M8 都要登记为生产 Module 并串进去。M4 先用现有薄接入跑通整条线，真模型由 T06 替换，不互相等。**主 Agent 此前把"各模块过了自己的验收"说成"M1–M6 已完成"，是错的；本条完成前不许再说"已连通"。** | ① 用 mini_ed01 由调度器从 M1 一路跑到 M8，全程无手动介入，产出 PublicationPackage；② 真书《乾元秘旨》同样一条线跑通；③ `run_all.sh 20.1` PASS；④ 中途任一阶段失败能从最近 Checkpoint 恢复（20.2 保持 PASS） | 用户 2026-09-19 前后要求、2026-09-23 第 2 点；PLAN.md:93 |
| T05 | 待办 | **M8 全部问题逐条解决（用户这几天的主要要求）**。拆为下面 T05a–T05e，全部完成才算 T05 完成。**主 Agent 此前几天做的是 M7（M8 的输入），没有跟用户对齐顺序，也没回头收 M8。** | T05a–T05e 全部完成；`m8-span-identity.sh` 全 PASS；run_all 20.6、20.9、20.11 PASS | 用户 2026-09-23 第 3 点 |
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

- 2026-09-23 / M7 全部（F～I 波）/ `64371c8` / `run_all.sh 20.5` PASS，`m7-assembler.sh` pass=17 fail=0 blocked=0，11 个包全绿（CHARTER §31–§32）
