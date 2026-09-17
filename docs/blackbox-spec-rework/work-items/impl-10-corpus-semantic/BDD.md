# BDD：impl-10 M3 电子文本偏移锚点 + 语义层

## 1. 概述与场景背景

本工作包覆盖第一版电子文本（以《乾元秘旨》电子文本片段为验收宿主原型）的 M3 编译体系：
- 消费 M2 产出的四类产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`）；
- 产出带双向偏移锚点的 `corpus_spans`，片段 ID 格式为 `ss_<work>_ed<NN>_o<NNNNNNN>`；
- 在结构片段之上构建语义层，片段 ID 格式为 `sem_<work>_ed<NN>_o<NNNNNNN>`；
- 证据级别恒为 `offset_level`，发布级别签发 `INTERNAL_DEMO` / `DEV_SEARCH`；
- 原有 OCR 扫描页路线全部保留在附录并标记为 `DEFERRED（第二版 OCR）`。

---

## 2. 核心场景（第一版电子文本）

### 场景 1：偏移锚点与 DeterministicPatchSet 双向换算（L1 / act/00）

- **1.1 基础区间双向映射**
  - **Given** 原始文本 `raw_text` 与有序补丁集 `patches`；
  - **When** 调用 `map_raw_to_cleaned(patches, raw_start, raw_end)`；
  - **Then** 能够确定性计算出在清洗后文本中的对应区间 `(start_offset, end_offset)`；
  - **When** 调用 `map_cleaned_to_raw(patches, start_offset, end_offset)`；
  - **Then** 映射结果严格等于原始区间 `(raw_start, raw_end)`（正反向可逆）。

- **1.2 补丁增删变化下的边界精确性**
  - **Given** 补丁集合中包含替换（replacement）、插入（insertion）与删除（deletion）等不同动作；
  - **When** 针对跨补丁区间与补丁内部字符进行偏移映射；
  - **Then** 换算后的区间偏移严格考虑了各补丁的长度变化量（cumulative delta），切片字符与补丁预期逐字吻合。

- **1.3 锚点数据结构与哈希校验**
  - **Given** 原始与清洗文本的有效区间及引文 `quote`；
  - **When** 调用 `make_offset_anchor`；
  - **Then** 返回 7 键严格有序字典 `{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}`；
  - **And** `quote_sha256` 精确等于 `sha256(quote.encode('utf-8'))`。

- **1.4 异常区间拦截**
  - **Given** 传入倒置区间（`raw_start > raw_end`）、负数偏移或引文长度与区间差不符；
  - **Then** 抛出 `ValueError("SCH_002: ...")`，拒绝构造非法锚点。

---

### 场景 2：电子文本切分与片段 ID 跨清洗稳定性（L1 / act/01）

- **2.1 全文连续覆盖与切分**
  - **Given** 清洗后文本 `cleaned_text`；
  - **When** 调用 `segment_cleaned_text`；
  - **Then** 产出所有切分片段区间，首尾相接、无缺口、无重叠，片段拼接后 100% 还原 `cleaned_text`。

- **2.2 片段 ID 跨清洗修订的绝对稳定性（G7-RULINGS 第 78 条）**
  - **Given** 初始版本生成的 SourceSpan，ID 为 `ss_qianyuan_ed01_o0000128`（基于原始文本偏移 128）；
  - **When** 后续清洗规则调整，在偏移 0～100 之间增加了补丁，导致该片段在 `cleaned_text_revision` 中的起点从 128 漂移到 135；
  - **Then** 因为底层的 `raw_text` 保持冻结，其在 RawText 中的起点 `raw_start` 依然为 128；
  - **And** 重新编译后，该片段的 ID 依然稳定保持为 `ss_qianyuan_ed01_o0000128`，不随清洗修订漂移。

- **2.3 格式与前缀合规性**
  - **Given** 产出的所有 SourceSpan；
  - **Then** 片段 ID 严格匹配 `^ss_[a-z][a-z0-9]*_ed[0-9]{2}_o[0-9]{7}$`（`<work>` 禁止下划线，依第 102 条 Q1；形态唯一权威出处 `pipeline/ledger/ids.py`），绝不含未登记前缀（P8）；
  - **And** 每条 Span 的 `evidence_level` 严格为 `"offset_level"`。

---

### 场景 3：M3 电子文本输入解析与 StepRun 事务（L2 / act/02）

- **3.1 上游 M2 产物完整消费**
  - **Given** Ledger 中已封存且状态为 `succeeded` 的 M2 运行；
  - **When** 调用 `resolve_m3_text_inputs`；
  - **Then** 成功解析 `raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report` 四类产物。

- **3.2 上游未就绪或未成功阻断（P5）**
  - **Given** M2 StepRun 处于 `running` 或 `failed` 状态；
  - **When** 尝试启动 M3 编译；
  - **Then** 拒绝编译并抛出 `CompileRefused("P5: M2 阶段未成功完成")`。

- **3.3 清洗未结项阻断（§10.1）**
  - **Given** M2 `sanitization_report` 中 `deferred_count > 0`；
  - **When** 尝试启动 M3 编译；
  - **Then** 必须以 fail-closed 拦截，抛出 `CompileRefused("§10.1: 存在暂缓处理项 deferred")`，且 Ledger 无新增写入。

- **3.4 Checkpoint 与 Transformation 审计**
  - **Given** 正常的 M3 电子文本编译流程；
  - **When** 调用 `run_m3_text`；
  - **Then** 按批次有序写入 Checkpoint，封存 `corpus_spans` 制品；
  - **And** 记录 `compile_corpus` 的 Transformation，包含完整的输入与配置修订血缘。

---

### 场景 4：M3 电子文本结构 Gate 独立判定（L2 / act/03）

- **4.1 独立 Gate 判定放行**
  - **Given** 合法的 spans 文档与对应原始/清洗文本；
  - **When** 运行 `evaluate_text_coverage`；
  - **Then** 六项检查（`text_contiguous_coverage`、`text_strict_offset`、`raw_anchor_fidelity`、`identity_and_stability`、`evidence_level_honest`、`header_counts`）全部通过，`passed: true`。

- **4.2 文本篡改与哈希不符检出**
  - **Given** 人为篡改某片段的文本内容或引文哈希；
  - **When** 运行 `evaluate_text_coverage`；
  - **Then** `text_strict_offset` 检查如实判 FAIL，`passed: false`。

- **4.3 片段缺失或重叠检出**
  - **Given** 删去某一条片段或使相邻片段发生区间重叠；
  - **When** 运行 `evaluate_text_coverage`；
  - **Then** `text_contiguous_coverage` 检查如实判 FAIL。

---

### 场景 5：双模型切分提议与边界分歧判定（L3 / act/04）

- **5.1 窗口筛选规则**
  - **Given** 电子文本结构 spans 列表；
  - **When** 文本长度 `>= model_min_chars`（默认 12）；
  - **Then** 选为模型窗口，分配 `<work>_w%03d` 编号；小于阈值的片段作为单片段。

- **5.2 Proposer 请求体隔离与零网络（§12.2、P6）**
  - **Given** 为窗口构造请求；
  - **Then** 请求体只含本窗口文本，绝不包含其他窗口或另一 slot 内容；
  - **And** 整个回放流程在网络拦截下执行，网络连接尝试为 0；
  - **And** `LiveProposer` 无论是否配置环境变量均拒绝执行并抛出 `ModelCallDisabled`。

- **5.3 提议一致与分歧**
  - **Given** A、B 两个 Proposer 返回切分响应；
  - **When** 提议边界一致，Then 判定为 `agreed`；
  - **When** 提议边界不一致或任一非法，Then 判定为 `disputed`。

---

### 场景 6：语义层合成（`sem_` 偏移形态）与人工裁决恢复（L3 / act/05）

- **6.1 边界分歧进入人工队列**
  - **Given** 存在分歧窗口；
  - **When** StepRun 运行至边界判定后；
  - **Then** StepRun 状态进入 `awaiting_human`，封存 `boundary_review_queue`，返回 `resume_token`。

- **6.2 人工裁决与 Checkpoint 即时落盘（§17.1）**
  - **Given** 审核员提交人工裁决；
  - **When** 调用 `submit_boundary_decision`；
  - **Then** 写入 `human_event`（`decision_type: review_source_fidelity`）；
  - **And** 立即写入一个对应的 Checkpoint（`task_id: review:<window_id>`），绝不延后合并。

- **6.3 未结分歧阻断恢复**
  - **Given** 仍有分歧窗口未提交裁决；
  - **When** 调用 `resume_m3_text_full`；
  - **Then** 抛出 `DisputesUnresolved`，StepRun 维持 `awaiting_human`，`resume_token` 保持有效。

- **6.4 全部解决后封存 StagePackage**
  - **Given** 全部窗口已解决；
  - **When** 调用 `resume_m3_text_full`；
  - **Then** 产出带 `sem_<work>_ed<NN>_o<NNNNNNN>` 的 SemanticSpan；
  - **And** 组装并封存 m3 StagePackage，`gate_profile: "structural_and_semantic"`，`semantic: "passed"`，StepRun 转为 `succeeded`。

---

### 场景 7：独立语义 Gate 严格判定（L3 / act/06）

- **7.1 八项独立语义检查通过**
  - **Given** 恢复后的语义产物与原始响应、裁决事件；
  - **When** 运行 `evaluate_semantic_offset`；
  - **Then** 八项检查全部 ok，`semantic: "passed"`。

- **7.2 Gate 模块独立性（防同错同过）**
  - **Given** `semantic_gate.py` 源码；
  - **Then** 严禁 import 任何生成器实现模块（`offset_assemble`、`review`、`proposer` 等）。

---

### 场景 8：证据级别 offset_level 与 M5 校验兼容（L3, L4）

- **8.1 M5 G3 证据校验兼容**
  - **Given** `evidence_level == "offset_level"` 的电子文本片段；
  - **When** M5 G3 进行引文与偏移核对；
  - **Then** 严格复算引文哈希与切片偏移，验证与底层 `raw_text` 的换算链路；
  - **And** 判定合法通过，不校验字框 coordinates。

- **8.2 目标消费级别拦截**
  - **Given** `offset_level` 的 M3 包；
  - **Then** 允许下游用于签发 `INTERNAL_DEMO` 与 `DEV_SEARCH`；
  - **And** 若配置目标为 `PUBLIC_RELEASE`，M5 G3 严格拦截并拒绝通过。

---

### 场景 9：验收脚本与宿主缺失 BLOCKED 机制（L4 / act/07）

- **9.1 电子文本宿主缺失时如实 BLOCKED**
  - **Given** 未提供电子文本验收宿主目录；
  - **When** 执行 `openspec/acceptance/m3-coverage.sh`；
  - **Then** 打印包含 exact BLOCKED 文本的说明行，退出码为 2（BLOCKED），严禁伪造 exit 0。

- **9.2 宿主完整时验收通过**
  - **Given** 提供了有效的电子文本宿主目录；
  - **When** 执行验收检查；
  - **Then** 输出 `SUMMARY pass=9 fail=0 blocked=0`，退出码为 0。

- **9.3 全程零网络与 run_all.sh 不变**
  - **Given** 验收全程在 socket 拦截下运行；
  - **Then** 网络连接计数为 0；
  - **And** `git status` 确认 `openspec/acceptance/run_all.sh` 未发生任何改动。

---

## 附录：OCR 路线 BDD 场景（第二版 OCR）

> **以下内容为原 OCR / 页码路线草稿，全部标记为 `DEFERRED（第二版 OCR）`，不在第一版电子文本实现中启用。**

```text
原 OCR 路线场景（留第二版参考）：
- 0. 语义金标宿主 mini_ed01_semantic 校验与生成器重放
- 1. Proposer 与提议解析（基于 OCR 行文本）
- 2. 规则、字框对齐锚点、裁决合成 compile_semantic（基于 mini_ed01 字框对齐判定 glyphbox_level 与 offset_level 混合计数）
- 3. 独立语义 Gate（九项检查，覆盖页图与字框）
- 4. Ledger 集成到人工队列（run_m3_full）
- 5. 人工裁决、恢复与封存（基于页图与 OCR 行）
- 6. m3-coverage.sh 验收（基于 mini_ed01）
```
