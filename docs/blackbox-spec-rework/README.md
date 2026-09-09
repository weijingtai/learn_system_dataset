# 黑箱架构规格 R1 返工 — 执行入口

> 审查对象：`openspec/learn-system-blackbox-architecture.md`（状态 `REVIEW_FAILED_R1`）
> 审查结论来源：2026-09-08 四角色独立交叉审查（架构 / 验收 / 用户体验 / 规划）
> 返工项母本：`PLAN.md` 的「黑箱架构规格 R1 审查返工项」一节（R0 / RA–RG，40 条）
> 本目录是**转译产物**：把那 40 条翻译成执行者可以直接照做的指令，目标是**一次做对，不再迭代**。

## 先读这个：为什么返工量看起来大，实际不大

40 条里有相当一部分的答案**已经写在既有已定稿文档里**，执行者只需按坐标搬运，不需要设计。
转译时逐条核对过照抄源，把它们分成了三类：

| 类别 | 条数 | 执行者要求 | 文件 |
|---|---|---|---|
| **ACT**（代码实现） | 4 | 便宜模型即可（ACT 04 除外） | `act/01.yaml` … `act/04.yaml` |
| **T 类**（转录搬运） | 13 | 中等模型，**不做设计决策** | `T-transcribe.md` |
| **D 类**（设计判断） | 19 | **必须较强模型** | `D-design.md` |

T 类的答案分别来自：
- `pipeline/schemas/core/SCHEMA.md` §5 §6 — 七个内容状态、九个错误码、五种 ID 格式
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §3 §4 — 三级消费级别、G1–G7 硬门禁、字框级证据要求
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二 §三 — 术语三层模型与三步判层（连 ID 规则都给全了）
- `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §3.2 §3.3 — 八类专家审核、争议不得藏深层
- `tag_system/TAG_SYSTEM_DESIGN.md` 222/224/225/307/438 — Tag 区五个字段与概念字典规模

**规则：照抄源与规格冲突时以照抄源为准**，并在规格里标注「沿用 / 取代」关系，不要静默二选一。

## 已经定了的，不要再问

| 事项 | 结论 | 定于 |
|---|---|---|
| 首纵切术数与素材 | 七政《三辰通载三十卷》影宋鈔本；`SourceAsset` = `ocr/data_work/sanche_pages/page_001..010.png` | 2026-09-08 用户裁定 |
| 证据等级 | `glyphbox_level`（字框级） | 同上，连带确定 |
| M6 工具 | 复用现有七政工作台原型，不新建 | 同上，连带确定 |
| 496 条空 rule | 不作为纵切输入，知识从原文重新抽取 | 同上，连带确定 |
| PLAN.md 处置 | **只增补不重写**，未勾选项零删除 | 审查结论，见 D-16 |
| 门禁命名 | 全规格只允许出现 G1–G7，不得新造门禁名 | `DATASET_ACCEPTANCE_STANDARD.md` §4 |

## 已拍板的 7 项（2026-09-08）

| # | 问题 | 决议 | 后续状态 |
|---|---|---|---|
| 1 | Ledger 进程模型 | 单机本地进程；统一客户端；单写入者 + WAL | 已写回规格，待实现 |
| 2 | Pattern、Concept、KnowledgeEntry | Pattern 是 Concept 的可规则识别子类；KnowledgeEntry 是发布聚合视图 | 已写回规格，待补齐 R1 全部契约 |
| 3 | `EditionPart` | 优先按卷；无卷时用连续页区间 | 已写回规格，待实现 |
| 4 | M3/M4 人工队列 | 复用并提升现有工作台为跨阶段 Review Console | 已写回规格，待实现 |
| 5 | 既有存储 | 校订事实和 corpus 迁移；派生索引重跑；旧 units/工作台库冻结 | 详见 `openspec/legacy-storage-transition.md` |
| 6 | 版权边界 | 原件放本地 Object Store；APP具备打开能力；是否随包下发由 ReleasePolicy 决定 | 已写回规格，待实现 |
| 7 | 工作台 AI 聊天 | 从 Review Console 剥离；未来只经 M4 Model Adapter 接入 | ACT 04 已解除拍板阻塞，待执行 |

## 转译者异议的裁定

**异议 1 — 已裁定。**
原文写「`grep -c '192.168' pubspec.yaml` 返回 0」。经核对：`enumeration` 全仓 `*.dart` 引用数为 **0**（可直接删，已转译为 ACT 03）；
但 `ai_core` 有 **8 处 import**，分布在 `lib/providers/ai_chat_controller.dart`（6 处）、
`lib/pages/chat_page.dart`、`lib/pages/rule_list_page.dart`，直接删会导致工作台编译不过。
用户已于 2026-09-08 选择「剥离 AI 聊天」。因此原验收标准可达，ACT 04 在 ACT 03 完成后可执行；
未来模型能力只通过 M4 Model Adapter 和已留痕 CandidatePackage 接入。

**异议 2 — 已纳入。**
转译时核对 `.gitignore` 才发现：仓库明令「版权源书不进公开仓」，`*.pdf` 与 `raw_books/**/*.pdf` 均被忽略，
而首纵切源 PDF 实测 **247M**。这与 `§9`／`§16`／`§20.8`／`LEARN_SYSTEM_TARGET.md:140` 四处冲突。
已作为 RG 组补入 PLAN.md，并按用户批准的三层存储与 ReleasePolicy 方案写入正式规格。

## 怎么验

```bash
bash docs/blackbox-spec-rework/verify-T.sh      # T 类逐条 PASS/FAIL，退出码 = FAIL 数
```

**当前基线：19 FAIL / 1 PASS**（唯一的 PASS 是「无章节被误标为最终规范」）。
这个数字就是进度条——每完成一条 T 类返工，FAIL 应减一。
D 类的进度在同一脚本末尾以提示行显示（不计入退出码，因为它们需人工确认质量）。

`§20` 完成标准的判据脚本 `openspec/acceptance/run_all.sh` 属于 D-18 的产出，**现在还不存在**，
建出来之后它会成为整份规格的总验收入口。

## 执行顺序

见 `D-design.md` 末尾「执行顺序」一节，已按依赖排好四轮。
规格内核先严格执行 `D-01 → D-03 → D-02`。ACT 01/02/03、T-11、D-16 与该序列无共享写路径时可并行。
