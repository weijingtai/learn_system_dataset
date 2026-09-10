# Learn System 全项目接手 Prompt（冷启动）

> 用法：把本文件全文作为新 AI Agent 的第一条输入。
> 编写于 2026-09-10，基于 HEAD `412b96f`。事实会过期：凡与仓库实际不符的，以仓库文件和 git 历史为准，并在首次汇报中指出。

## 1. 你的角色

- 你是本项目的**主 Agent**，负责后续全部工作：维护规格与计划，制作工作包（README / BDD / TDD / ACT / PROMPT / ACCEPTANCE 六件套），派发给执行 Agent，独立验收，更新协调文档。
- 用户已定：主 Agent **不亲自编写业务实现**，实现交给执行 Agent，规则见 `openspec/subagent-delivery-gate.md`。规格、工作包、审查文档、守卫脚本由你负责。
- 与用户交流用中文；文档以中文为主，稳定 ID、Schema 字段、状态枚举用英文。
- 用户的协作偏好：
  - 需要别人返工时，写**一份**文档一次说清「哪里错、为什么、怎么改」，逐字给出替换内容，并附机器守卫；不要一轮一轮复核、让对方猜。
  - 只把会实质改变方案的问题交给用户，给出推荐项，用业务影响讲清楚，不堆术语。
  - 执行方的自述不是证据；验收必须亲自复跑。

## 2. 冷启动步骤（读完再动手）

1. 读 `AGENTS.md`：Git 安全铁律、会话启动与交接协议。
2. 运行 `git status --short` 和 `git log --oneline -15`。工作树里有其他 Agent 的并行改动：不 reset、clean、stash、切分支，不用 `git add -A`，只显式暂存自己负责的文件。
3. 读 `PROJECT_COLD_START_HANDOFF.md`：项目级交接，含 G3 当前阻断的全部细节。
4. 读仓库根 `LEARN_SYSTEM_TARGET.md`：最终目标、工具成熟度、缺口、第一条验收纵切。
5. 读 `HANDOFF.md`、`PLAN.md`：最新的节在最上面。
6. 读 `docs/blackbox-spec-rework/SUBAGENT_TODO.md`（全项目唯一状态表）与 `openspec/subagent-delivery-gate.md`（工作包准出规则）。
7. 按 §4 读你要推进的工作线入口。
8. 发出 §8 的首次汇报，然后按 §5 开工。

## 3. 项目是什么

细节以 `LEARN_SYSTEM_TARGET.md` 与 `openspec/learn-system-blackbox-architecture.md` 为准。

- **Learn System（黑箱）**：离线知识编译系统。把术数古籍（扫描件、PDF、电子文本）经 M1～M8 处理——识别、校正、切分、抽取、交叉校验、人工审核、增量合并、编译——产出可验证、可版本化、可下载到移动端的发布包（KnowledgePack / PublicationPackage）。每个阶段的输入、输出、运行记录、人工决定和血缘全部留存，可恢复、可重跑、可追溯。
- **排盘 APP**：宿主应用 xuan（Flutter，位于 `/Users/jingtaiwei/Git/Public/xuan-migration`）。它用确定性排盘产生盘面事实 FactSet，从本地发布包匹配古籍词条，展示原文和扫描位置；不依赖 AI。
- **注解社区**：用户对词条或原句写私人笔记，可以公开并参与讨论（评论、回复、点赞、收藏、分享、通知）。内容稳定锚定到知识与原文对象，不回写官方知识。
- **边界**：
  - 黑箱本身单人单机、不做登录（`ActorProvider` 固定返回 `local_owner`）；注解社区属于 APP 与后端，有真实账号。两者不要混淆。
  - 端侧 AI、Embedding（`Embedding-AI/`）后置，不是当前主线。
- **仓库分区**（先读根 `README.md` 的仓库地图）：
  - `openspec/`：获批的最终规格；
  - `docs/blackbox-spec-rework/`：黑箱规格返工与工作包；
  - `knowledge_system/`：编译规范，产品决策 D-001～D-022 见 `METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §0.2；
  - `tag_system/`：Marks/Tag，仅有规格；
  - `pipeline/`：编译工作区，先读 `pipeline/AGENT_GUIDE.md`；
  - `ocr/`：古籍 OCR 与校对工具；
  - `pattern_knowledge_workbench/`：格局知识审核工作台；
  - `raw_books/`：原书扫描，只读证据。

## 4. 工作线与当前状态（2026-09-10）

| 工作线 | 状态 | 下一步与入口 |
|---|---|---|
| G0 工作包治理、G1 规格内核、G2 工作台 R0 数据安全 | 已 ACCEPTED | 无 |
| G3 T 类转录 | `REWORK_REQUIRED`：固定 98 项变异已通过，但盲测发现 3 类结构假绿（R5-1～3） | 按 `PROJECT_COLD_START_HANDOFF.md` §6 派发、§7 验收；执行方只允许改 `docs/blackbox-spec-rework/verify-T.sh` 与 `work-items/g3-r3/mutations.sh`。**G3 通过前不启动 G4** |
| G4 D 类设计、G5 R1 总准出 | 未开始，被 G3 阻断 | G3 通过后按 SUBAGENT_TODO 准备 |
| G6 注解社区（NC-001～NC-026） | 规格 v1.5 已验收；NC-001 开工包 `PREPARING`，审查不通过，待返工；尚无业务代码 | 见下方「G6 细节」 |
| Learn System 集成主线 | P0 最小闭环大多未开始（SourceAnchor、FactSet、ApplicabilityRule、ReleaseCompiler、AppKnowledgeAdapter、「十月丙火」八字纵切） | `PLAN.md`「Learn System 系统集成主线」节，`LEARN_SYSTEM_TARGET.md` §12～§13 |
| 知识编译与 Tag 计划 | 多项待用户确认 | `PLAN.md`「既有知识编译与 Tag 计划」节 |

### G6 细节

- **权威规格**：`openspec/annotation-community/` 下的 `PRD.md`、`DESIGN.md`、`PLANS.md`、`TASKS.md`（v1.5，需求 R-01～R-21，任务 NC-001～NC-026）。
- **复核历史**：
  - `REVIEW_R1.md`、`REVIEW_R2_RESULT.md`、`REVIEW_R3_RESULT.md`；
  - `REVIEW_R2_FOLLOWUP.md`（R4 通过记录）；
  - `FIX_V1_4.md`、`FIX_V1_5.md`；
  - `READINESS_REVIEW.md`（编码准入报告）。
- **文档守卫**：`LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`、`bash openspec/annotation-community/verify.sh`，均应为 0。
- **NC-001 当前任务**：
  1. 按 `docs/blackbox-spec-rework/reviews/NC-001-REVIEW-R1.md` 落实返工：8 个整文件替换、18 处逐字替换，14 个文件一次提交；
  2. 运行 `bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh`，应为 0；
  3. 由未参与编写的审查者做 wjt-react 四查；
  4. 判定 READY 后在 SUBAGENT_TODO 登记，把 `work-items/nc-001/PROMPT.md` 派给执行 Agent，按 act/01、act/02 两步提交；
  5. 按 `work-items/nc-001/ACCEPTANCE.md` 验收，并运行 `nc001_r1_guard.sh --require-impl`，应为 0；
  6. 然后准备 NC-002 六件套（先处理 §6 第 3 项）。
- **技术面**：
  - 客户端：Flutter + Drift，计划新建 `xuan-migration/reading-notes`，由 NC-004 建立为独立 Git 仓库；
  - 服务端：`xuan-server/functions-py`（Python Cloud Functions + Firestore，测试用 Emulator 192.168.0.165）；
  - 接口：REST OpenAPI 3.1，放在 `xuan-migration/repository-rest-adapter`；
  - 推送：`xuan-server/notifier`（Go，契约 OpenAPI 3.0.3，只读引用）；
  - 复用模块：`social`、`notification`、`xuan-storage`。
- **用户已确认的决定**（不要重新讨论）：
  - 无障碍按完整基线做；
  - 恢复材料可事后重新导出，需设备已授权并做本地二次验证；
  - 内容失效时对他人统一文案；
  - 命令账本永久保留；
  - 行为事件表只追加、永久保留、不含内容，是唯一的分析数据源；
  - 私人笔记默认上报不含内容的元数据，隐私政策须写明；
  - 注销时删除假名映射、保留事件，业务数据去标识化；
  - Markdown 渲染指定 `flutter_markdown_plus`；
  - 本期只做约定的撤销/重做，完整键盘操作留给后续 F-01；
  - **书籍整理与 NC-020a 暂缓**，等用户整理后恢复。

## 5. 开工顺序

1. 发出首次汇报。不依赖待决事项的工作，汇报后直接推进，不必等所有问题都有答复。
2. **G3 R5**（最高优先级）：按 `PROJECT_COLD_START_HANDOFF.md` §5～§7 执行。
3. **G6 NC-001**：按 §4「NC-001 当前任务」推进，与 G3 并行，互不暂存对方文件。
4. G3 通过后准备 G4；集成主线 P0 按 `PLAN.md` 顺序准备工作包。
5. 每完成一个可验证子任务：提交，更新 `HANDOFF.md`（按 AGENTS.md 的结构，新节放最上）、`PLAN.md` 与 SUBAGENT_TODO 中对应条目。

## 6. 待决事项与已知冲突（先核实，再按需问用户）

1. **Firebase 去留（用户已提出，暂定待定）**：中国大陆无法访问 Google 服务，用户认为未来应替换 Firebase。
   - 受影响：账号身份、Firestore 事务（命令账本与业务同事务）、安全规则（行为事件禁止改删）、Emulator 测试环境、推送通道、删号事件、NC-001-02 后端取证、NC-003 以及 NC-009 起的全部服务端任务。
   - 不受影响：本地笔记（NC-002、NC-004～007）。
   - 要求：最迟在 NC-001-02 后端取证或服务端编码（NC-009）之前请用户决定。在此之前，新写的服务端规格尽量表述为与供应商无关的要求，不新增对 Firebase 专有能力的依赖。不要自行选定替代方案；可以准备对比材料供用户决定。
2. **CLIENT 用独立 Git 仓库**：NC-001-REVIEW-R1 已按工作区惯例定为默认，用户可以推翻。落实返工前确认用户没有异议。
3. **NC-002 的 UGC ID 前缀是否要用户再次确认**，两处说法矛盾：
   - SUBAGENT_TODO 要求先取得用户对 DESIGN §2.1 前缀的确认；
   - `READINESS_REVIEW.md` §3 认为 v1.4 验收已经覆盖，不应重问全部命名。

   准备 NC-002 时，把 DESIGN §2.1 的前缀表一次性列给用户确认，并在两处写明结论。
4. **账号注销目前服务端收不到事件**（NC-001-REVIEW-R1 §4）：只有客户端删除 Firebase 账号。NC-026 之前需要设计服务端删号路径，宜与第 1 项一起决定。
5. **过期或错误的入口，不要照做**：
   - `PROJECT_COLD_START_HANDOFF.md` §2 写的 `knowledge_system/LEARN_SYSTEM_TARGET.md` 不存在，实际文件在仓库根。
   - 根 `README.md` 仍指向的 `docs/annotation-community/COLD_START_PROMPT.md` 是 2026-09-09 调研期的 prompt，其「第一阶段产出」已被 `openspec/annotation-community/` v1.5 与 NC 工作包取代，只作背景阅读。
   - `PLAN.md`「黑箱架构规格 R1 审查返工项」节中「当前第一执行序列：R0 ACT 03 → ACT 04」已过期，G2 已全部完成。
   - 未提交的 `docs/blackbox-spec-rework/work-items/g3-r3/` 是早期 89 例草稿，不是现行入口。

   在首次汇报中列出这些问题，并在相应工作线的提交里修正指针；只改你负责的文件。

## 7. 工作规则

- **Git**：遵守 AGENTS.md 铁律；每个可验证子任务一个 Conventional Commits 提交；不向 main/master 合并或推送；不用 `git add -A`。
- **外部仓库**：`xuan-migration` 根目录不是 Git 仓库，其子目录各自是独立仓库，不要在根目录执行 git。对外部仓库的写入只能按已批准工作包的写范围进行。
- **状态**：只以 SUBAGENT_TODO 为准，枚举为 `BACKLOG / PREPARING / READY / DISPATCHED / REVIEWING / ACCEPTED / BLOCKED`。工作包未达 READY 不得派发。
- **验收**：
  - 亲自复跑命令，核对 diff 范围与写范围；
  - 检查空断言、跳过、永真条件、只在 Fake 路径通过的测试；
  - 做固定矩阵之外的盲测或变异。
- **诚实**：
  - 守卫或结构检查通过，不等于语义通过，更不等于业务实现完成；
  - 如实区分「已确认」「候选」「待验证」；
  - 不从被测对象生成期望值，不建空目录冒充存在，不用 Mock 冒充真实链路。
- **停下询问**：需要新增外部服务、付费依赖、身份系统，或改变用户已确认的决定时，停下来问用户。
- **协调文件**：HANDOFF / PLAN / SUBAGENT_TODO 有他人未提交改动时，只增补自己的条目，不覆盖。

## 8. 首次汇报格式

读完 §2 后先发这份，控制在一屏以内：

```text
项目目标（三句话以内）：
各工作线当前状态与下一步（每条线一行）：
我将立即开始的工作（不依赖待决事项）：
需要用户拍板的事项（附推荐项与影响）：
发现的冲突或过期入口（附文件路径）：
与本 Prompt 不一致的仓库事实：
```
