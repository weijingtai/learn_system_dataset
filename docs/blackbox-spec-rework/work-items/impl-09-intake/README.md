# impl-09：M1 电子文本入库 + M2 电子文本清洗（§9、§10、G7-RULINGS §76–§83）

状态：`DRAFT`（起草 Agent 产出，待主 Agent 审查）

## 1. 目标与范围

第一版只做电子文本路线（G7-RULINGS §76 D1），不涉及 OCR 扫描：

1. **M1（`pipeline/intake/`）**：从任意来源站点读入电子文本原始文件（md/txt/epub 等），登记 Work/Edition/SourceAsset，记录来源说明与权利状态（§77 D2），冻结为 `source_manifest`。不做清洗、不做 OCR、不做知识判断（§9）。
2. **M2（`pipeline/digitization/`）**：对 M1 入库的电子文本执行 §4.4 十三项清洗，产出四类 artifacts——`raw_text`（原始文本冻结）、`cleaned_text_revision`（清洗修订）、`deterministic_patch_set`（双向映射）、`sanitization_report`（发现记录，§81）。清洗结果经人工确认后 M2 Gate 放行。
3. **证据级别**：`offset_level`，发布级别只做 `INTERNAL_DEMO` / `DEV_SEARCH`（§76）。
4. **来源无关**：M1 按来源无关设计——来源站点、原始 URL、仓库提交号为字段，同书多来源各自登记 SourceAsset/Edition（§77 D2）。
5. **片段 ID**：无页码文本以字符偏移定位，片段 ID 格式 `ss_<work>_ed<NN>_o<NNNNNNN>`（§78 D3）；语义层用 `sem_` 前缀（§80 D5）。
6. **不新增 ID 前缀**：片段 ID 用已登记的 `ss_`/`sem_` 两种形态；`finding_id` 等新前缀须写「## 待裁决」。
7. **P7**：任何需要人工确认的清洗决定（补字、改形近误字、判定缺失章节）都必须由用户决定表产出，本包只定义决定表格式与导入路径，不得伪造人工决定。
8. **零模型调用**（P6）：不调用任何 LLM/云服务；清洗为确定性规则。

**OCR 路线**（第二版）：

> 原 OCR 路线（真实页图 + 既有 OCR JSON 登记）内容保留在本文件，全部标记为 `DEFERRED（第二版 OCR）`，不在本版实现。

## 2. 上游来源契约（来源无关，§77 D2）

### 2.1 来源登记

M1 电子文本入库按来源无关设计。每份来源登记以下信息：

| 字段 | 含义 | 必填 |
|---|---|---|
| `source_site` | 来源站点域名（如 `daizhige.org`、`ctext.org`） | 是 |
| `source_url` | 原始 URL | 是 |
| `repo_commit` | 仓库提交号（如适用） | 否 |
| `file_sha256` | 原始文件 SHA-256 | 是 |
| `yaml_metadata` | 文件头 YAML 元数据原样保存（如有） | 否 |

同书多来源各自登记为独立 SourceAsset/Edition，不写死单一来源站点。

### 2.2 权利状态

权利状态如实登记（§77 D2）：

- `rights_status`：如实填写站方声明（如「站方声明免费下载、未附许可证」）
- `release_policy`：取值 `full_scan` / `derived_page_images_only` / `reference_and_hash_only`（§16:717–721）
- 公开发布前须逐源复核授权

### 2.3 YAML 元数据原样保存

原始文件头部 YAML（如有）原样保存进 `source_manifest` 的 `source_assets[].yaml_metadata` 字段，不做解析、不做转换。

## 3. M1 产出契约

M1 输出 `source_manifest`，顶层键序与 fixture `manifest.yaml` 一致：

```yaml
source_id: <from submission>
work_title: <from submission>
edition_note: <from submission>
technique_id: <from submission>
rights_status: <from submission>
release_policy: <from submission>
edition_part:
  artifact_id: <from submission>
  label: <from submission>
  pages: [page_001, ...]  # 电子文本按文件列表
source_assets:
  - page: <filename_stem>
    path_ref: <relative_path>
    sha256: <64-hex>
    width: null           # 电子文本无图像尺寸
    height: null
    object_store: local
    in_git: false
    yaml_metadata: <原样保存，如有>
    source_site: <来源站点>
    source_url: <原始 URL>
    repo_commit: <提交号，如有>
files: []
conversion:
  tool: pipeline.intake
  tool_version: "0.1.0"
  inputs: [<path_ref>...]
  note: "M1 电子文本入库；不做清洗（§9）"
content_status: "machine_extracted"
```

`source_assets[].width/height` 对电子文本为 null（无图像尺寸）。`source_manifest` 内容结构为代码草案（P3），正式化随 impl-08 Contract Registry。

## 4. M2 产出契约（§10:478，§81）

M2 电子文本清洗产出四类 artifacts：

### 4.1 `raw_text`（原始文本冻结）

- 原始文件字节经编码统一后冻结为 `raw_text` 修订
- 冻结后不可变；片段 ID `ss_<work>_ed<NN>_o<NNNNNNN>` 的偏移基准

### 4.2 `cleaned_text_revision`（清洗修订）

- 清洗后的文本修订，以 `prev_revision_id` 指向 `raw_text`
- 包含清洗后的完整文本与元数据

### 4.3 `deterministic_patch_set`（确定性修补集）

- 记录原始文本与清洗文本之间的双向映射
- 每个 patch：`{patch_id, raw_start, raw_end, cleaned_start, cleaned_end, action, basis}`
- 证据链：片段 → 清洗文本偏移 → patch 映射 → 原始文本偏移 → SourceAsset SHA-256

### 4.4 `sanitization_report`（清洗报告）

发现条目最小键集（§81）：

```yaml
finding_id: <唯一 ID>
kind: <闭集，见下>
raw_start: <字符偏移>
raw_end: <字符偏移>
raw_excerpt: <原始文本片段>
context: <上下文说明>
action: kept | patched | flagged
patch_id: <关联 patch_id，如有>
basis: <底本/CTP/GlyphWiki 等依据>
terminal_state: processed | known_unresolvable | deferred
```

**`kind` 闭集**（§81）：`replacement_char`（替换字符）、`private_use_area`（私用区字符）、`escape_residue`（转义残留）、`watermark`（水印广告）、`header_footer`（页眉页脚）、`duplicate`（重复内容）、`missing`（缺失内容）、`textualized_diagram`（文本化图表）、`variant_mixed`（繁简混杂）、`suspected_error`（疑似形近误字）、`control_char`（控制字符）、`encoding_issue`（编码问题）。

**`terminal_state` 闭集**（§10.1）：`processed`（已处理）、`known_unresolvable`（已知不可解决，须附理由与证据）、`deferred`（暂缓处理）。

**`deferred` 阻断 M2 Gate**：任何发现的 `terminal_state` 为 `deferred` 时，M2 Gate 不通过，禁止进入 M3。

## 5. 清洗必做清单（§4.4 十三项，逐条落为可判定检查）

| # | 清洗项 | 检查规则 | 发现 kind | 终态 |
|---|---|---|---|---|
| 1 | 编码统一 UTF-8 | 检测 BOM 与编码声明；记录原编码 | `encoding_issue` | processed |
| 2 | 乱码与替换字符 | `?`、`□`、U+FFFD 逐处登记位置与上下文；不得猜字替换 | `replacement_char` | processed/known_unresolvable |
| 3 | 生僻字与 PUA | 区分 CJK 扩展区字与真正 PUA 码位；对照 GlyphWiki/Jigmo 查证；无法映射的保留原码并登记 | `private_use_area` | processed/known_unresolvable |
| 4 | 控制字符 | 零宽字符、异常空白检测；全角空格按版式规则保留或规范化并记录 | `control_char` | processed |
| 5 | 转换残留 | Markdown 转义（`\-`、`\[`）、HTML/脚本、YAML 头与正文分离 | `escape_residue` | processed |
| 6 | 水印广告 | 非文献内容检测（页脚、维护者声明、链接） | `watermark` | processed |
| 7 | 页眉页脚 | 重复标题行检测 | `header_footer` | processed |
| 8 | 重复内容 | 全文去重比对，登记位置，不静默删除 | `duplicate` | processed/deferred |
| 9 | 缺失内容 | 对照目录/CTP 核对完整性，缺失登记为已知缺口 | `missing` | deferred |
| 10 | 异常字段与结构 | 节标题识别、正文/注文/夹注格式、文本化图表区块登记 | `textualized_diagram` | processed |
| 11 | 繁简混杂 | 记录原貌，不强制转换；规范化只进派生层并可逆 | `variant_mixed` | processed |
| 12 | 形近误字 | 只登记疑点，改字须有底本依据并走 patch，不得由模型直接改 | `suspected_error` | deferred |
| 13 | 扫描本差异 | 第一版不改正，留第二版对勘 | — | —（不生成发现） |

## 6. 追踪链

```
片段（ss_/sem_ ID）
  → 清洗文本偏移（cleaned_text_revision 中的位置）
    → DeterministicPatchSet 映射（patch_id）
      → 原始文本偏移（raw_text 中的位置）
        → SourceAsset SHA-256（M1 入库时冻结）
```

每个 `sanitization_report` 发现都带 `raw_start/raw_end`（原始偏移）和关联 `patch_id`，可沿 patch 映射追溯到清洗后文本的对应位置。片段 ID `ss_<work>_ed<NN>_o<NNNNNNN>` 的偏移基准为冻结的 `raw_text`，不随清洗修订漂移（§78 D3）。

## 7. 接口需求

### 7.1 对 M3（偏移锚点，impl-10）

- M3 消费 `cleaned_text_revision` 生成偏移锚点
- 片段 ID 用 `ss_` 偏移形态 `ss_<work>_ed<NN>_o<NNNNNNN>`（§78）
- 语义层用 `sem_` 前缀（§80 D5）
- M3 零改动本包不涉及

### 7.2 对电子文本验收宿主

- 电子文本验收宿主（取《乾元秘旨》片段）属**独占 fixture ACT**，由主 Agent 另行安排（P4）
- 本包**不得自建 fixture、不得写 `pipeline/corpus/_fixture/**`**
- 本包只定义对验收宿主的接口需求：需要哪些文件、键、哈希

### 7.3 对 Ledger

- M1 通过 `put_artifact` 写入 `source_manifest`、`raw_text`、`source_asset`
- M2 通过 `put_artifact` 写入 `cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`
- 事务序列遵循 §17 Checkpoint 落盘粒度

## 8. 用户待办

| 待办 | 内容 | 阻断 |
|---|---|---|
| 电子文本验收宿主 | 主 Agent 另行安排（P4），取《乾元秘旨》片段 | M2 Gate 真实验证 |
| 人工终态决定表 | 用户亲笔写（§77 D5），第一版首批取《乾元秘旨》前若干节 | M2 真实验证 |
| PUA 映射表 | 对照 GlyphWiki/Jigmo 查证后建立映射表（§79 D4） | 清洗实现 |

## 9. 待裁决

无。

---

## 附录：OCR 路线（第二版 OCR）

> 以下内容为原 OCR 路线草稿，全部 `DEFERRED（第二版 OCR）`，不在本版实现。

### DEFERRED（第二版 OCR）：M1 Source Intake + M2 Digitization & Correction 真实最薄接入

原 OCR 路线目标：把目前只由 `pipeline/ledger/fixture_ingest.py` 从 fixture 常量模拟灌入的 m1、m2 两个阶段，换成读取真实素材的最薄 Module：

- M1（`pipeline/source_intake/`）：从真实页图目录读入字节，计算 SHA-256 与 PNG 尺寸
- M2（`pipeline/digitization/`）：登记已有 OCR 结果，异常页人工终态
- 来源不可区分：M3 零改动
- 真实前十页跑通：page_001..010 走通 M1→M2→M3

`DEFERRED（第二版 OCR）` 原因：第一版改为电子文本路线，OCR 路线留待第二版证据升级时实现。

### DEFERRED（第二版 OCR）：目录规划

```text
pipeline/source_intake/
  __init__.py        M1_TOOL / M1_TOOL_VERSION / 任务名常量
  errors.py          IntakeRefused、SourceAssetMissing
  serialize.py       dump_manifest_yaml
  submission.py      load_submission
  assets.py          png_size、read_assets、unlisted_assets
  manifest.py        build_source_manifest、manifest_bytes
  step.py            run_m1
  __main__.py        python -m pipeline.source_intake
  acceptance.py      m1-replay 判定
  tests/             helpers.py test_manifest.py test_step.py test_acceptance.py
pipeline/digitization/
  __init__.py        M2_TOOL / 版本 / GATE_PROFILE / 终态常量
  errors.py          DigitizationRefused、OcrWorkMissing
  ocr_work.py        read_ocr_work、snapshot_matches
  decisions.py       load_decisions
  plan.py            required_terminal_pages、excluded_page_bytes、plan_digitization
  gate.py            evaluate_m2_gate
  inputs.py          resolve_m2_inputs
  step.py            run_m2
  __main__.py        python -m pipeline.digitization
  acceptance.py      m2-export-integrity 判定
  tests/             helpers.py test_plan.py test_gate.py test_step.py test_step_failures.py test_parity.py test_acceptance.py
```

### DEFERRED（第二版 OCR）：完成判据

```bash
export LC_ALL=en_US.UTF-8; PY=.venv/bin/python
$PY -m unittest discover -s pipeline/source_intake/tests -t . 2>&1 | tail -1   # OK
$PY -m unittest discover -s pipeline/digitization/tests -t . 2>&1 | tail -1    # OK
bash openspec/acceptance/m1-replay.sh; echo exit=$?
bash openspec/acceptance/m2-export-integrity.sh; echo exit=$?
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo exit=$?
bash openspec/acceptance/run_all.sh | tail -1
```
