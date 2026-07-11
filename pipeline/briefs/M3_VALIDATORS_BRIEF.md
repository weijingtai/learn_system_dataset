# M3 任务书：补齐校验器（依 PIPELINE_REVIEW_v1 §P0-3 优先级）

> 先读 pipeline/AGENT_GUIDE.md（含第 0 步）。按步骤 1–5 顺序执行，每步完成先跑该步验证再进下一步。
> 禁止修改 corpus/、units/、schemas/techniques/qimen/glossary_v0.yaml、现有任务的 output/。
> 所有新校验器风格与 validate.py 一致：只报错不改文件；PASS/FAIL＋错误码；退出码 0/1。

## 步骤 1：`validators/validate_glossary.py`

检查术语表（路径作参数）：concept_id 唯一且格式 `co_[a-z]+_\d{6}`；status 只允许 confirmed_v0/candidate/rejected/rejected_suggested；surface 非空；每个 seg_id 能在对应任务的 segments 里找到且 surface 是该段原文的子串（segments 文件路径作第二参数）；rejected 条目必须有 note。
错误码：GLO_001 编号、GLO_002 状态、GLO_003 surface 不在段中、GLO_004 缺 note。
**验证**：对现有 glossary_v0.yaml＋task_qimen_000003_concepts/input/segments.yaml 跑一遍应 PASS。

## 步骤 2：`validators/validate_assertion_task.py`

检查主张任务包（任务目录作参数）：
1. output/ 下同时存在 ≥2 个不同 --by 的归档（双路证明）与 review_compare.yaml、merged_final.yaml；
2. merged_final 中每条 status 为 cross_model_reviewed（单路 draft 里出现 cross_model_reviewed = FAIL，状态越权）；
3. 输入 segments 全覆盖：每个 seg 要么被 ≥1 条 assertion 的 evidence 引用，要么出现在 skipped_segments 且有 reason；
4. evidence 的 span 后缀必须落在输入 seg 范围内（防跨段越界引用）；
5. 若 input/ 有 editorial_notes.yaml，带括号段的 assertion 必须有 conditions 或该段在 skipped 中。
错误码：AST_001 缺双路件、AST_002 状态越权、AST_003 覆盖缺口、AST_004 越界引用、AST_005 括号段未处理。
**验证**：对 task_qimen_000004_assertions 跑一遍；如现有产物有不满足项（如 A 路未声明 skipped），输出 FAIL 是正确行为——原样汇报，不许为迁就旧产物放宽规则。

## 步骤 3：`validators/validate_rag_index.py`

检查 rag/index.sqlite：meta 必含 build_time/unit_count/skipped_units/source_release；五张表存在且 spans/assertions/evidence 非空；mentions 非空；三条端到端查询（locate 已知句命中、locate 乱码返回空、任取一个 mentions 的 concept_id 查询非空）；WARN：meta 缺 unit_hashes/script_sha256（转正式索引前必须补）。
错误码：RAG_001 表缺失、RAG_002 mentions 空、RAG_003 查询链路断、RAG_004（WARN）审计字段缺。
**验证**：对当前索引跑一遍，预期 PASS＋RAG_004 警告。

## 步骤 4：扩展 `check_segments.py`

新增：SEG_006（WARN）连续 ≥5 段 note 完全相同；SEG_007 段 text 含 `[()（）\[\]【】]` 时提示"该段含编者标记，确认 editorial_notes 已覆盖"（WARN）；--type D 时检查每段有 layer，layer=commentary 的段有 attached_to。
**验证**：对 task_qimen_000002_seg 重跑应 PASS＋若干 SEG_007 警告（s63/s109/s114 所在段）。

## 步骤 5：runner 自动生成 result.yaml 骨架

run_task.py 归档时若任务包 output/ 无 result.yaml，则生成骨架（task_id、result: completed、空的 uncertainties/lesson_candidates/needs_escalation: false），由执行 agent 补填。不覆盖已存在的 result.yaml。
**验证**：对 task_qimen_000001_seg 跑一次 mock，确认生成骨架且不破坏现有文件。

## 步骤 6：汇报

列出新增文件、每步验证命令与输出原文、发现的旧产物不合规项清单（只报告不修改），停止。
