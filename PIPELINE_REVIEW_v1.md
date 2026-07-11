# PIPELINE_REVIEW_v1

更新时间：2026-07-11
评审范围：`pipeline/AGENT_GUIDE.md`、`pipeline/HANDBOOK.md`、`pipeline/RAG_GUIDE.md`、`pipeline/OPERATOR_MANUAL.md`、`pipeline/validators/`、`pipeline/lessons/LESSONS.md`、`task_qimen_000002_seg`、`task_qimen_000003_concepts`、`task_qimen_000004_assertions`、`ku_qimen_000002`、`rag/` L1+L2 产物、`METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.1.1.md` 与 `v1.2.md`。

限制：只评审并写报告；未修改 `pipeline/` 下任何现有文件。

## 总结结论

`pipeline/` 已经跑通一次真实小书生命周期，且最核心假设被验证：逐字证据、双路盲提取、人工抽查和 L1/L2 索引能实际抓住错误并形成可追溯知识单元。最有价值的实测成果是 `review_compare.yaml` 抓到 s10 “三元”被误读为“三候”的模型知识渗入，这证明双路比对不是形式主义。

当前主要风险不在“能不能跑”，而在“能不能扩批且可复现”。P0 缺口是：手册状态落后于现实、运行环境未锁定、审计链的权利/人工签发/索引构建记录尚未闭合、validators 还没有覆盖实测暴露的高频结构性错误。若直接扩到 s13-s110，最先撞到的会是状态升级、跳段覆盖、括号注文层、术语闭集边界和成本/返工账本缺失。

## P0：扩批前必须处理

### 1. 手册与现实产物状态不一致

发现：

- `RAG_GUIDE.md` 第 7 章仍写“当前状态：本手册为规格，尚未开工”，但现实已经有 `rag/build_index.py`、`rag/query.py`、`index.sqlite`，并完成 locate/concept/assertion 三链路实测。
- `README.md` 也仍写 RAG “M2 之后启动”，没有反映 M-RAG1 已经完成首轮。
- `OPERATOR_MANUAL.md` 第 8-9 步把“编译词条＋重建检索”放在完整流程后段，但本次实践跳过了词条聚合，直接从 validated units 和 glossary 构建 L1/L2。
- `HANDBOOK.md` 仍说 agent 不直接写 `LESSONS.md`，但本次经验已经由人工/复核方固化进 `pipeline/lessons/LESSONS.md`；规则本身合理，但需要写明“由验收方收录后生效”的现实流程。

影响：后续 agent 会按过时状态判断，以为 RAG 尚未实现，或以为必须等词条聚合后才能建 L1/L2。

建议：

- 回写手册状态：标记 M-RAG1 已有首版实现，L3 与 EvidenceBundle/check_answer 仍未开工。
- 在 `RAG_GUIDE.md` 增补“当前实现偏差与验收记录”小节，列出 mentions 空表事故及修复后的 concept 链路验收。
- 在 `OPERATOR_MANUAL.md` 明确阶段 0 允许“units -> L1/L2 索引”的轻量路径，词条聚合可后置。

### 2. 运行环境未锁定，校验与 RAG 重建不可复现

发现：

- 本机裸 `python3` 跑 `validators/validate.py`、`validators/check_segments.py`、`rag/query.py` 均因缺少 `yaml` 模块失败。
- 仓库没有 `requirements.txt`、`pyproject.toml` 或等价依赖声明。
- `rag/build_index.py` 还依赖 `opencc`，手册说 opencc 不可用则 blocked，但没有安装检查脚本或环境说明。

影响：当前 `index.sqlite` 可读且 meta 显示 `unit_count=2`、`skipped_units=[]`，但另一个 agent 接手时未必能重建同一索引。扩批后这会变成交付阻断。

建议：

- 新增项目级依赖声明：至少 `PyYAML`、`opencc`，并记录推荐 Python 版本。
- 新增 `pipeline/requirements.txt` 或根目录 `pyproject.toml`。
- 手册中的命令改为先执行环境检查，例如 `python3 -c "import yaml, opencc"`。
- `run_task.py`、validators、RAG 脚本共享同一依赖说明。

### 3. validators 未覆盖实测出现的结构性错误

当前 validators 已覆盖：

- `validate.py`：必填字段、枚举、ID 格式、重复 ID、source manifest、文件哈希、引文逐字包含、unit span 引用、assertion evidence 存在。
- `check_segments.py`：切分覆盖、A 类半联、seg_id 连续、text/note 空、B 类超长警告。

实测出现但未程序检查：

- 主张提取遗漏 `skipped_segments`：A 路在 s03-s05 未声明跳过，只有比对报告人工指出。
- 主张状态越权：单路输出应只能 `machine_extracted`，`cross_model_reviewed` 应只能由比对/签发流程产生；当前 `validate.py` 只检查枚举合法，不检查状态来源。
- 双路比对件缺失：`review_compare.yaml` 是防污染核心证据，但没有 validator 要求 `cross_model_reviewed` 单元必须能追溯到双路 draft 与 compare。
- 输入覆盖：工位 5 只处理 s01-s12 是有意小样本；扩批时需要检查每个输入 segment 要么产出 assertion，要么在 `skipped_segments` 中声明原因。
- 术语 surface 与 segment 原文逐字匹配：`review_claude.yaml` 说做过程序校验，但 `validators/` 中没有对应脚本。
- 术语补录/剔除审计：太白、荧惑补录和“干”剔除建议没有统一机器检查。
- `note` 批量复制：LESSONS 记录“note 必须段段不同”，但 `check_segments.py` 只查非空，不查重复/低信息 note。
- 括号/夹注层处理：LESSONS 要求先扫 `[()（）\[\]【】]`，本次产生 `editorial_notes.yaml`，但没有检查 task input 是否携带/读取该文件。
- RAG mentions 空表：已经修复实现，但没有独立验收脚本断言 `concept` 查询链路非空。
- source rights 质量：`rights_status: public_domain` 能过，但没有要求来源 URL、下载日期、RightsGrant、权利证据文件。
- 索引版本完整性：RAG meta 有 build_time/unit_count/skipped/source_release，但没有 unit 清单哈希。

建议优先级：

1. `validate_assertion_task.py`：检查双路 draft、`review_compare.yaml`、`merged_final.yaml`、`skipped_segments`、状态升级路径。
2. `validate_glossary.py`：检查 concept_id 唯一、surface 在对应 segment 中出现、seg_id 存在、status 枚举、补录/剔除记录。
3. `validate_rag_index.py`：检查 meta、表计数、三条端到端 query、mentions 非空、unit 清单哈希。
4. 扩展 `check_segments.py`：检查重复 note、括号标记提示、类型 D 必填 layer/attached_to/commentator。
5. 扩展 `validate.py`：把 `cross_model_reviewed` 与 review provenance 绑定；未绑定则报错或 warning。

### 4. 审计链仍有断点

已闭合的链路：

- `raw_books/qimendunjia/yanbodiaosou.md` 进入 `pipeline/corpus/qimen/yanbo_ed02/raw/yanbodiaosou.md`，manifest 记录 raw/transcript sha256。
- 任务运行目录记录了 `prompt.txt`、`run.yaml`、输入文件哈希、prompt 哈希、response 哈希。
- `review_compare.yaml` 记录双路分歧、裁决依据和胜出方。
- `ku_qimen_000002` 记录 unit/provenance/assertions/review，人工抽查 5/13 通过。
- RAG `index.sqlite` meta 记录 build_time、unit_count、skipped_units、source_release。

断点：

- raw_books 到 corpus 缺少来源 URL、下载日期、采集人、原始权利依据；`rights_status: public_domain` 缺少 RightsGrant 证明。
- ed02 manifest 明确“用户提供的简体通行电子本，无影像底本，文字未核对”，但后续 `status`/展示层没有把“未核影像”作为用户可见来源风险。
- `editorial_notes.yaml` 来自 ESC 裁决，但 manifest/task/run 没有把该 ESC 决议作为正式依赖登记。
- 人工抽查签发只写“抽查 5/13 全部通过”，缺少抽中的 assertion_id、检查项、操作者签名或时间戳粒度。
- `review_compare.yaml` 是手工汇总件，没有输出哈希或被 `ku_qimen_000002/review.yaml` 以哈希引用。
- `glossary_v0.yaml` 141 条人工签发，文件顶部有签发说明，但缺少完整 review 清单、签发人、输入候选哈希与最终 diff。
- `index.sqlite` 没有记录构建命令、脚本哈希、依赖版本、被索引 unit 列表哈希；`rag/` 下存在多个 `.fuse_hidden...` 文件，说明构建/删除过程留了不应发布的临时文件。

建议：

- 建立 `audit_manifest.yaml` 或在现有 manifest/review 中增加 `depends_on` 数组，记录每个派生产物依赖的文件 sha256。
- 人工 review 统一记录抽样明细：`sampled_assertions`、`checks`、`result`、`reviewer`、`reviewed_at`。
- RAG meta 增加 `unit_hashes`、`script_sha256`、`dependency_versions`、`build_command`。
- rights 从枚举升级为 RightsGrant 最小结构，至少包含权利主体、来源 URL、采集时间、许可范围、证据路径。

## P1：s13-s110 扩批会先撞到的问题

### 1. 类型 A 长歌扩批的段落上下文问题

s01-s12 相对独立，s13 以后进入直符、值使、三奇六仪、三遁、格局、八门九星等密集术语段。许多主张跨相邻联互证，例如 s13-s16、s21-s24、s66-s75。若仍按“每联独立”硬提，会增加条件丢失和跨段补知识。

建议：工位 5 的任务包保留当前 batch 的全文 segments，并明确“证据可以引用相邻段作 condition，但 proposition 必须以当前段为主”；validator 检查跨段引用是否在 task input 范围内。

### 2. 括号与注文层会在 s63、s109、s114 放大

本次已通过 `editorial_notes.yaml` 裁定 `(开门六乙合六己...)` 为 commentary，`(逢)` 为校补字。扩批时如果工位 5 未强制读取 editorial_notes，会把注文当正文主张，属于严重语义污染。

建议：每个 assertion task input 必须包含 `editorial_notes.yaml` 快照；validator 检查带括号 span 的 assertion 是否包含 layer/condition 或跳过原因。

### 3. 术语闭集边界会变成主要返工源

术语表已经 141 条，但当前 RAG mentions 只会收已进入 unit spans 的术语；扩批后会出现：

- 单字天干地支大量误命中。
- “九宫”在“一九宫”中的子串误命中，LESSONS 已记录 v0 可接受但需边界判断。
- star/door/god/pattern 分类会影响后续 APP 展示和查询。

建议：扩批前先把 `validate_glossary.py` 和词边界策略做出来；至少对闭集术语按最长匹配和类别白名单检查。

### 4. 状态与编号治理会先混乱

当前 `task_qimen_000004_assertions` 使用 `as_qimen_000100-000149`。扩 s13-s110 时如果每批手工分配，很容易 assertion/proposition ID 冲突，且 `cross_model_reviewed` 会被人工合并文件直接写入。

建议：建立 `id_registry.yaml` 或批次账本，分配 assertion/proposition/source_span 号段；状态升级由合并器或 validator gate 统一处理。

### 5. 成本账本没有回填

v1.1.1 §9.8 要求阶段 0 回填 tokens、返工率、人工分钟、成本。当前 run.yaml 没有 token/cost 字段，人工 review 也没有耗时。扩批后无法判断 H3/单位经济。

建议：run.yaml 增加 token、费用、耗时；review.yaml 增加人工分钟；每批生成 `batch_metrics.yaml`。

## P1：类型 C/D 大部头会先撞到的问题

### 类型 C：《穷通宝鉴》类条目书

最先风险：

- outline/batches 还没有真实产物；`batches.yaml` 仍停留在手册模板层。
- 条目边界不是诗歌联句，`check_segments.py --type C` 目前没有任何 C 类特有检查。
- 表格/条目结构需要可还原字段，当前 segments 只有 `seg_id/text/note`。
- 条目路径如“十干/月令/调候/用神”需要进入 source_span 或 unit metadata，否则 RAG 只能找句子，不能按结构定位。

建议：

- 先做 3 个条目小样本，不直接整卷。
- 为 C 类 segments 增加 `entry_title`、`path`、`row_col` 或 `structure_note`。
- 写 `check_segments.py --type C`：检查条目标题、路径、原表行列保真、无跨条目拼接。

### 类型 D：注疏混排

最先风险：

- 现有 `validate.py` 不认识 layer/commentator/attached_to。
- `RAG_GUIDE` 和 unit schema 没有明确正文主张与注家主张的查询/展示分层。
- 若注家观点进入正文 assertion，后续 APP 会把“某注家解释”展示成“原书说法”。

建议：

- 先把 `SourceSpan.layer` 纳入 schema。
- assertion 增加 `speaker/source_layer/commentator` 或等价字段。
- RAG 查询结果必须显示层级，EvidenceBundle 不得吞掉 commentator。

## P1：与 v1.1.1 / v1.2 的偏差清单

### 应回写进文档的实践简化

- 完整十工位在阶段 0 被实际压缩为：来源建档/转录登记、语义切分、术语候选+人工签发、主张双路提取+比对、知识单元、L1/L2 RAG。白话释义、规则候选、词条聚合、ReleaseBundle 尚未进入首轮。
- RAG L1/L2 可以在词条聚合前从 units/glossary 编译，用作技术验证和审计工具。
- `review_compare.yaml` 成为主张工位的关键审计物，应从“人工汇总习惯”升级为标准交付物。
- LESSONS 机制已证明有效，应在 v1.1.1 §7/§8 中明确“lesson_candidates -> 复核方筛选 -> LESSONS.md”的治理闭环。
- 阶段 0 OpenSpec 不必等阶段 2；这与 v1.2 §15 一致，应覆盖 pipeline 的最小规格、依赖和 validator gate。

### 应纠正实践以贴回设计的偏差

- v1.1.1 要求 SourcePackage 记录来源、权利、版本、页码；ed02 只有简体电子本与 sha256，缺 RightsGrant、URL、影像核对和页码映射。
- v1.1.1 §7.1 要求保存模型名称、模型版本、任务模板版本、时间、输入哈希和输出哈希；当前 `model_id` 只是 `opencode`/`claude`，缺真实模型版本与 endpoint 记录。
- v1.1.1 §9.8 成本模型未回填；run/review 没有 token、耗时、返工率。
- v1.2 §10.5/§13/§14 要求 RightsGrant 覆盖率 100% 作为外部实验门槛；当前 `rights_status: public_domain` 太粗。
- v1.2 §3.1 区分“文本忠实度”和“现实有效性”；当前 status `cross_model_reviewed` 容易被误读为“术理正确”，需要展示标签拆分。
- v1.2 §10.6 主张级 fail-closed AI 放行要求 100% SourceSpan 覆盖；当前 schema 有 evidence，但没有程序检查“所有生成回答或对外解释必须只用 bundle 内 span”。

### 可接受但需标注的偏离

- ed02 使用“用户提供简体通行电子本，无影像底本”作为试点底本：可接受于内部 pipeline 验证，但不得进入对外 ReleaseBundle 或用户实验。
- 当前 RAG `source_release: dev`：适合开发索引，不应被 APP 消费。
- 术语子串误命中 v0 可接受：只要 RAG/APP 展示前标明是开发索引，并在扩批前升级边界检查。

## P2：四本手册逐项修订建议

### AGENT_GUIDE

- 保留六条铁律。
- 更新示例：现在 ed02 是简体电子本，不要继续只用繁体差异作为唯一例子；同时加入“简体底本也一字不改”。
- 加入“任务包若有 editorial_notes.yaml 必读；缺失但原文有括号标记则 blocked/ESC”。
- 错误码表补 SEG、GLO、RAG、AUDIT 类新码。

### HANDBOOK

- 第 2 章 result.yaml 与现实输出不一致：本次主要产物没有统一 result.yaml，需决定补齐还是调整规范。
- 第 3/5 章的类型 C/D 规则需要对应 validator 字段，否则只是人工纪律。
- 第 6 章复核 agent 规则应把 `review_compare.yaml` 标准化。
- 第 8 章版本说明“以校验程序实际行为为准”要小心：校验程序覆盖不足时不能让实践绕过手册，应改为“确定性字段以校验器为准，语义字段以手册+复核为准”。

### RAG_GUIDE

- 更新当前状态：M-RAG1 首版已实现；L3、EvidenceBundle、check_answer 未实现。
- 增加 `build_index.py` 的实际数据来源说明：mentions 来自 glossary seg_ids 映射到已索引 spans。
- 增加“开发索引不可发布”的门槛：source_release 不能是 dev、unit list hash 必须存在、RightsGrant 必须完整。
- `concept` 子命令现在返回术语相关 span，不直接返回 assertions；手册写“术语 -> 相关主张＋证据”与实现不完全一致。要么改实现，要么改手册。

### OPERATOR_MANUAL

- 第 2 步找底本要补“用户上传/手工提供文本”的权利与核验分支。
- 第 7 步抽查签发需要标准抽查单格式。
- 第 8-9 步需区分“开发 RAG 验证”和“发布检索库”。
- 第 10 步归档收尾应加入更新 `lessons`、`registry/works/<book>.yaml`、`batch_metrics.yaml` 和 rights/audit 清单。

## 建议落地顺序

1. 先补依赖与复现：`requirements`、环境检查、RAG/validator smoke test。
2. 再补 validators：assertion task、glossary、RAG index、segment note/layer。
3. 回写四本手册的当前状态与实测偏差。
4. 为 s13-s110 建 `batches.yaml`、id_range、batch_metrics 和 review template，只放 2-3 批。
5. 类型 C/D 不直接扩整本；先做一个 C 条目样本和一个 D 注疏样本，验证 schema 与 validator 后再开大书。

## 复验记录

- 读取 `index.sqlite`：存在 `spans/assertions/evidence/mentions/meta/spans_fts` 等表。
- `meta`：`build_time=2026-07-11T07:04:05.665120+00:00`，`unit_count=2`，`skipped_units=[]`，`source_release=dev`。
- 表计数：`spans=11`，`assertions=14`，`evidence=15`，`mentions=13`。
- SQLite 直接查询 “二至还乡” 命中 `ss_yanbo_ed01_p0001_s02` 与 `ss_yanbo_ed02_p0001_s01`。
- 使用当前裸 `python3` 运行 validators/RAG 脚本失败：`ModuleNotFoundError: No module named 'yaml'`。因此本报告未声称当前环境可重建索引，只确认现有 SQLite 产物可读。
