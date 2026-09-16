# impl-10：M3 电子文本偏移锚点 + 语义层（§11、§11.1、G7-RULINGS §76–§81）

状态：`DRAFT`（起草 Agent 产出，待主 Agent 审查）

## 1. 目标与范围

第一版只做电子文本路线（G7-RULINGS §76 D1），不涉及 OCR 扫描与字框锚点：

1. **M3 电子文本编译（`pipeline/corpus_compiler/`）**：消费 M2 电子文本清洗产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`），生成带字符偏移锚点的 `corpus_spans`。
2. **证据级别**：`offset_level`，发布级别只做 `INTERNAL_DEMO` / `DEV_SEARCH`（§76）。`PUBLIC_RELEASE` 留第二版（OCR + 版本对勘升 `glyphbox_level`），不改规格 §11.1。
3. **片段 ID 形态**：无页码电子文本以字符偏移定位，片段 ID 格式为 `ss_<work>_ed<NN>_o<NNNNNNN>`（`o` 后为片段起点在冻结 `RawText` 中的字符偏移，7 位零填充，§78 D3）。因 RawText 物理冻结不可变，片段 ID 不随后续清洗修订（`cleaned_text_revision`）漂移。有页码来源保持现行 `_p<NNNN>_s<NN>` 形态不变（留第二版）。
4. **偏移锚点**：锚点结构为 `{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}`，经 `DeterministicPatchSet` 在原始文本与清洗文本之间实现确定性**双向换算**（§78 D3）。
5. **语义层（SemanticSpan）**：在电子文本结构片段之上建立语义层，标识前缀使用已登记的 `sem_`（§80 D5），偏移来源形态为 `sem_<work>_ed<NN>_o<NNNNNNN>`。默认规则切分（标点/换行），规则无法判定的长片段（>= 12 字符）作为模型窗口进行双模型边界提议。
6. **双模型独立提议与分歧裁决**：A、B 两个 Proposer 独立提议，一致即采纳；分歧进入 M3 边界分歧队列（`await_human`），由人工裁决写回 `human_event`（每条裁决落盘一个 Checkpoint，§17.1），恢复后由语义 Gate 校验并封存 m3 StagePackage。
7. **独立 Gate 判定**：同层全文覆盖 100%、无缺口、无重叠、严格 offset 比对等于文本、拼接等于清洗文本、未解决语义分歧为零（§11:521）。
8. **m3 StagePackage**：`gate_profile: "structural_and_semantic"`，`semantic: "passed"`，`disputes: {total, resolved_by_human, unresolved: 0}`，`evidence_level_counts: {offset_level: N, glyphbox_level: 0}`。
9. **不新增 ID 前缀**：严格遵守 P8，只用已登记的 `ss_`（含偏移形态）与 `sem_`（含偏移形态），不引入任何未登记前缀。
10. **零模型调用（P6）**：Proposer 采用 Adapter 接口，测试与验收只使用手写回放录制（`ReplayProposer`，标 `synthetic: true`），真实模型 Adapter 仅留默认禁用的桩（`LiveProposer`），生产代码零网络。
11. **不自建 fixture（P4）**：电子文本验收宿主属独占 ACT，由主 Agent 另行安排；本包只写对宿主的接口需求，不写 `pipeline/corpus/_fixture/**`。
12. **run_all.sh 不动**：本包验收脚本在宿主缺失时如实 exit 2（BLOCKED），不修改 `run_all.sh`，基线保持 `SUMMARY pass=2 fail=1 blocked=8`。

---

## 2. 上游契约（单一权威，第 85、86 条）

M3 电子文本编译直接消费 M2 产出的四类 artifacts：

> **单一权威声明（第 85、86 条）**：
> M2 产物形态的唯一权威定义在 `docs/blackbox-spec-rework/work-items/impl-09-intake/README.md` §4。
> 本包严格引用该处权威说明，**绝不复述第二份形态说明**，防止契约漂移。

上游产物引用清单：
1. **`raw_text`**：原始文本冻结，详见 `impl-09` README §4.1。片段 ID 偏移基于此冻结文本。
2. **`cleaned_text_revision`**：清洗后文本修订，详见 `impl-09` README §4.2。M3 切分与偏移定位的直接输入。
3. **`deterministic_patch_set`**：双向映射修补集，详见 `impl-09` README §4.3。每个 patch `{patch_id, raw_start, raw_end, cleaned_start, cleaned_end, action, basis}`。
4. **`sanitization_report`**：清洗发现报告，详见 `impl-09` README §4.4。包含 12 项 `kind` 闭集与 3 项 `terminal_state` 闭集（`processed` / `known_unresolvable` / `deferred`）。

**消费准入规则（P5、§10.1）**：
- M2 StepRun 必须处于 `succeeded` 状态，未成功的 M2 包一律拒绝（P5）。
- M2 `sanitization_report` 中 `deferred_count` 必须为 0；若存在 `deferred` 状态发现，M2 Gate 未通过，M3 必须拒绝编译（fail-closed，§10.1）。

---

## 3. 偏移锚点契约（G7-RULINGS 第 78 条）

### 3.1 锚点数据结构

电子文本片段的偏移锚点结构为：

```yaml
raw_text_revision_id: <rev_32hex>      # M2 冻结的原始文本修订 ID
raw_start: <int>                       # 在原始文本中的起点字符偏移 [0, len)
raw_end: <int>                         # 在原始文本中的终点字符偏移 (raw_start, len]
cleaned_text_revision_id: <rev_32hex>  # M2 清洗后文本修订 ID
start_offset: <int>                    # 在清洗后文本中的起点字符偏移 [0, len)
end_offset: <int>                      # 在清洗后文本中的终点字符偏移 (start_offset, len]
quote_sha256: <64-hex>                 # sha256(cleaned_text[start_offset:end_offset].encode('utf-8'))
```

### 3.2 坐标系与双向换算

1. **坐标系**：
   - `raw_start` / `raw_end`：以 Unicode 字符为单位，相对不可变 `raw_text` 从 0 起算，左闭右开 `[start, end)`。
   - `start_offset` / `end_offset`：以 Unicode 字符为单位，相对 `cleaned_text_revision` 完整文本从 0 起算，左闭右开 `[start, end)`。
2. **双向换算算法**：
   - 经 `DeterministicPatchSet` 中的有序 patches 列表进行区间映射：
     - `map_raw_to_cleaned(patches, raw_start, raw_end) -> (start_offset, end_offset)`
     - `map_cleaned_to_raw(patches, start_offset, end_offset) -> (raw_start, raw_end)`
   - 当区间未发生 patch 变更时，偏移量按累计 delta 平移；当区间内包含 patch 时，按 patch 的 `(raw_start, raw_end) ↔ (cleaned_start, cleaned_end)` 精确对齐。
3. **引文哈希验证**：
   - `quote = cleaned_text[start_offset:end_offset]`
   - `quote_sha256 = hashlib.sha256(quote.encode('utf-8')).hexdigest()`
   - 必须满足 `len(quote) == end_offset - start_offset > 0`。

### 3.3 片段 ID 形态与稳定性机制（第 78 条）

- **片段 ID 格式**：`ss_<work>_ed<NN>_o<NNNNNNN>`
  - `<work>`：作品 slug（如 `qianyuan`）。
  - `ed<NN>`：版本编号（如 `ed01`）。
  - `o<NNNNNNN>`：小写字母 `o` 后接片段起点在**冻结 RawText 中的字符偏移**（`raw_start`），7 位定长补零（例如 `o0000000`、`o0000128`）。
- **稳定性机制**：
  - M1 入库后原始文件字节即冻结为 `raw_text`，物理不可变；
  - 无论后续清洗规则如何升级、清洗修订（`cleaned_text_revision`）如何迭代，片段在冻结 RawText 中的起点位置 `raw_start` 严格固定；
  - 因此，`ss_<work>_ed<NN>_o<NNNNNNN>` 具备跨清洗修订的绝对稳定性，下游 M4/M5/M6/M7/M8 引用的片段标识不会因文本清洗而漂移。
- **有页码来源**：保持 `ss_<work>_ed<NN>_p<NNNN>_s<NN>` 格式不变（保留在第二版 OCR 路线）。

---

## 4. 语义层契约（G7-RULINGS 第 80 条）

### 4.1 标识前缀与两形态

`sem_` 前缀已在 `openspec/id-prefix-registry.md` §3.6 登记确认，属于语义锚（SemanticSpan）：
1. **偏移来源（第一版）**：`sem_<work>_ed<NN>_o<NNNNNNN>`
   - `o<NNNNNNN>` 为该语义片段起点在冻结 RawText 中的字符偏移（7 位零填充）。
   - 示例：`sem_qianyuan_ed01_o0000128`。
2. **页码来源（第二版 OCR）**：`sem_<work>_ed<NN>_p<NNNN>_s<NNN>`
   - 示例：`sem_sanche_ed01_p0001_s001`。
3. **纪律**：`sem_` 已经登记，严禁擅自发明任何新前缀（P8）。

### 4.2 SemanticSpan 数据结构

```yaml
semantic_span_id: sem_<work>_ed<NN>_o<NNNNNNN>
sequence: <int>                        # 全文顺序号，从 1 连续递增
start_offset: <int>                    # 清洗文本起点偏移
end_offset: <int>                      # 清洗文本终点偏移
text: <str>                            # 片段原文切片
quote_sha256: <64-hex>                 # sha256(text.encode('utf-8'))
boundary_origin: rule | cross_model_agreed | human_decided
window_id: <str | null>                # 窗口 ID（如 qianyuan_w001），规则单片为 null
structural_refs:
  - span_id: ss_<work>_ed<NN>_o<NNNNNNN>
    start: <int>                       # 相对所引结构 Span 文本的局部起点
    end: <int>                         # 相对所引结构 Span 文本的局部终点
evidence_level: offset_level
source_anchor:
  raw_text_revision_id: <rev_32hex>
  raw_start: <int>
  raw_end: <int>
  cleaned_text_revision_id: <rev_32hex>
  start_offset: <int>
  end_offset: <int>
  quote_sha256: <64-hex>
```

### 4.3 边界切分与人工分歧裁决流程

1. **规则优先**：电子文本默认按句读/换行切分为结构 Span；长度 `< model_min_chars`（默认 12）的片段直接作为单语义片段（`boundary_origin: rule`）。
2. **模型窗口**：长度 `>= model_min_chars` 的片段进入模型窗口，生成窗口 ID（`<work>_w%03d`）。
3. **双模型独立提议**：A、B 两个 Proposer 独立提议，仅接收当前窗口文本，输出 `{"segments": [{"start_offset", "end_offset", "reason"}]}`。
4. **比较与分歧判定**：
   - 若 A 与 B 切分边界完全相同 → 采纳为 `cross_model_agreed`；
   - 若 A 与 B 边界不一致或任一提议非法 → 判定为 `disputed`，进入 M3 边界分歧队列。
5. **进入人工队列**：StepRun 状态迁移为 `awaiting_human`，封存 `boundary_review_queue` 修订，返回 `resume_token`。
6. **人工裁决与即时落盘**：
   - 审核员通过 M3 review 接口提交裁决（选择 A、选择 B 或自定义切分），写入 `human_event`（`schema: m3_boundary_decision/1`，`decision_type: review_source_fidelity`）。
   - 每条人工裁决被接受后立即落盘一个 Checkpoint（§17.1）。
7. **恢复与封存**：所有分歧窗口解决后（未决分歧数 == 0），调用 `resume`，StepRun 恢复运行，语义 Gate 全检通过后生成 m3 StagePackage 并封存。

---

## 5. 与 M5 证据校验的接口

在第一版 `evidence_level: offset_level` 下，M5 Automatic Validation（`pipeline/validation/`，门禁 G3）的校验接口规范如下：

1. **引文哈希校验**：
   - M5 逐条读取 EvidenceLink 引用的 SourceSpan / SemanticSpan。
   - 断言 `evidence_link.quote_sha256 == sha256(evidence_link.quote.encode('utf-8'))`。
   - 断言 `span.quote_sha256 == evidence_link.quote_sha256`。
2. **文本切片与偏移校验**：
   - M5 依据锚点 `(start_offset, end_offset)` 直接切片 `cleaned_text_revision`，断言切片与 `evidence_link.quote` 逐字相同。
   - 沿 `DeterministicPatchSet` 校验 `(raw_start, raw_end)` 与底层 `raw_text` 原始文本一致，哈希链路完整。
3. **免除字框断言**：
   - 在 `offset_level` 下，锚点无字框数据，`glyphs: []`。M5 G3 判定 `evidence_level == "offset_level"` 为合法，不得因缺少字框报 FAIL。
4. **消费级别拦截**：
   - `offset_level` 允许签发 `INTERNAL_DEMO` 与 `DEV_SEARCH` 消费级别；
   - `PUBLIC_RELEASE` 会被 M5 G3 严格拦截（要求 `glyphbox_level`，留第二版 OCR）。

---

## 6. 对电子文本验收宿主的接口需求

> **硬约束（P4）**：本包不得自建 fixture、不得写入 `pipeline/corpus/_fixture/**`。
> 电子文本验收宿主（取《乾元秘旨》片段）属独占 fixture ACT，由主 Agent 另行安排。

本包对验收宿主的接口需求规格如下：

### 6.1 所需宿主文件清单

| 文件名 | 说明 |
|---|---|
| `乾元秘旨_期望_cleaned.txt` | M2 清洗后的文本文件，UTF-8 编码，包含前两节完整文本（约 2000–5000 字符） |
| `乾元秘旨_期望_deterministic_patch_set.yaml` | M2 双向修补集，包含清洗过程中产生的所有 patches |
| `乾元秘旨_期望_m2_stage_package.yaml` | M2 StagePackage，用于作为 M3 的冻结上游输入 |
| `乾元秘旨_期望_recordings.yaml` | 手写回放模型提议录制，标注 `synthetic: true` 与 `template_id: m3_boundary_v1` |
| `乾元秘旨_期望_human_decisions.yaml` | 手写人工裁决事件样例，标注 `synthetic: true` |
| `乾元秘旨_期望_corpus_spans.yaml` | M3 结构层期望产物（含偏移锚点） |
| `乾元秘旨_期望_semantic_spans.yaml` | M3 语义层期望产物（含 `sem_` 偏移锚点） |
| `乾元秘旨_期望_m3_stage_package.yaml` | M3 阶段包期望产物，`gate_profile: structural_and_semantic` |

### 6.2 必备键集与哈希规范

1. **`corpus_spans.yaml`**：
   - 顶层键：`work, source_id, edition_part_artifact_id, evidence_level, content_status, span_count, spans`
   - 每条 Span 键：`span_id, sequence, start_offset, end_offset, text, quote_sha256, evidence_level, source_anchor`
   - `source_anchor` 键：`raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256`
2. **`semantic_spans.yaml`**：
   - 顶层键：`work, source_id, edition_part_artifact_id, raw_spans_sha256, gate_profile, segmentation_profile, content_status, span_count, window_count, dispute_count, evidence_level_counts, spans`
   - 每条 Span 键：`semantic_span_id, sequence, start_offset, end_offset, text, quote_sha256, boundary_origin, window_id, structural_refs, evidence_level, source_anchor`
3. **哈希与计数约束**：
   - 宿主文本经 SHA-256 钉住，不得发生隐式漂移。
   - `dispute_count >= 1`，确保真实覆盖「比较 → 分歧 → await_human → 裁决 → resume」完整链路。
   - `unresolved_disputes == 0`，确保恢复后 Gate 能如实通过。

---

## 7. 用户待办

| 待办事项 | 说明 | 阻断项 |
|---|---|---|
| 电子文本验收宿主制作 | 取《乾元秘旨》片段制作，标注 `synthetic_fixture: true`（独占 ACT，P4） | M3 验收脚本 exit 0 |
| 签发决定表模板填写 | 主 Agent 生成签发模板后，由用户以专家身份填写并署名导入（第 80 条，P7） | M6 真实签发与下游放行 |

---

## 8. 待裁决

无。

---

## 附录：OCR 路线（第二版 OCR）

> **以下内容为原 OCR / 页码路线草稿，全部标记为 `DEFERRED（第二版 OCR）`，不在第一版电子文本实现中启用。**

### DEFERRED（第二版 OCR）：原 M3 语义层设计草稿

```text
原草稿依据与设计点（留第二版参考）：
1. 依据 mini_ed01 图像扫描页与 OCR JSON（lines/chars 字框）
2. 结构层由 impl-02 产出 StructuralSpan + glyphbox 锚点
3. SemanticSpan 使用页码形态 sem_<work>_ed<NN>_p<NNNN>_s<NNN>
4. 证据级别为 glyphbox_level（逐字 glyphs 切片）与 offset_level 混合
5. 依赖 pipeline/corpus/_fixture/mini_ed01_semantic/ 录制宿主
6. 原待裁决 D1–D14：
   - D1: 标识前缀（主 Agent 第 80 条已裁决采纳 sem_，支持页码与偏移双形态）
   - D2: 模型 Adapter（采纳 A，纯回放 + 禁用桩）
   - D3: gate_profile 取值 structural_and_semantic
   - D4: StepRun 拓扑（单 StepRun 覆盖完整生命周期）
   - D5: 回放录制身份（Adapter 后端）
   - D6: 裁决类型 review_source_fidelity
   - D7: 金标位置
   - D8: 复用结构层私有助手
   - D9: m3-coverage.sh 改造
   - D10: 完整性检查范围
   - D11: 字框不对齐行如实判定
   - D12: 窗口选择阈值
   - D13: 复核模型 C
   - D14: artifact_type 登记
```
