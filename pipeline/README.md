# pipeline：典籍整理流水线

用最简单的话说明这个目录是什么。

## 目录结构

```
pipeline/
├── corpus/      原始典籍（转录文本＋来源登记），只加不改
├── units/       整理出来的知识单元（一个文件夹 = 一个单元）
├── schemas/     数据格式说明（SCHEMA.md，写给人和 AI 看）
├── validators/  校验程序（validate.py，自动判对错）
├── examples/    样例（positive = 正确示范；negative = 故意写错的，用来测试校验程序）
├── task-templates/  以后交给 AI 模型的任务包模板（M2 填充）
├── escalations/ 升级人工的问题（格式见 HANDBOOK 第 2.3 节）
├── rag/         检索系统（按 RAG_GUIDE.md 构建，可随时删除重建）
└── gold/        金标集（人工核对过的标准答案，M2 之后逐步积累）
```

## 四本手册的分工

- `AGENT_GUIDE.md`：六条铁律＋工作循环＋修错查表——**所有 AI agent 必读的入门**；
- `HANDBOOK.md`：各工位详细规程、通过/不通过样例、文本类型判定、大部头书籍分批策略、容错分级、升级人工格式——**AI 干活时对照的完整规范**；
- `RAG_GUIDE.md`：检索系统的构建规格——**M-RAG1（L1+L2）已上线**，`python3 rag/query.py locate "..."` 可用；L3 与 EvidenceBundle 未开工。运行任何脚本前先装依赖：`pip install -r requirements.txt`，自检 `python3 -c "import yaml, opencc"`；
- `OPERATOR_MANUAL.md`：**写给人的**管理手册——一本典籍从找书到成品的十步、未知问题四步法、可信书源清单、档案系统（registry/）用法。
- `TASKGEN_HANDOFF.md`：**任务包生成器平台化（P0–P3）的交接文档**——要动 `tools/lib/taskgen.py` 或三个下游 gen 工具、或新增技法时必读；含架构、回归门禁用法、已知坑。
- `DATASET_ACCEPTANCE_STANDARD.md`：**整本书到发布数据集的验收草案**——定义全书覆盖、证据锚点、内容分层、确定性盘面匹配、专家签发和发布门禁；单个 unit PASS 不代表数据集可投入 APP。

## 怎么用（现在只有一个命令）

```
python3 validators/validate.py units/ku_qimen_000001    # 校验一个单元
python3 validators/validate.py --all                     # 校验所有单元
```

结果只有两种：`PASS`（全对）或列出每一条错误（错误码＋位置＋原因）。

## 核心规矩（校验程序强制执行）

1. 每条主张必须指回原文的具体位置，指不回 = 报错；
2. 引用的原文必须和转录文件逐字一致，差一个字 = 报错；
3. 编号、字段、状态词必须符合格式，错 = 报错；
4. 校验程序只报错，从不悄悄修改内容。
