# impl-09：M1 电子文本入库 + M2 电子文本清洗（§9、§10、G7-RULINGS §76–§83）

状态：`DRAFT`（起草 Agent 产出，待主 Agent 审查）

## 1. 目标与范围

第一版只做电子文本路线（G7-RULINGS §76 D1），不涉及 OCR 扫描：

1. **M1（`pipeline/intake/`）**：从任意来源站点读入电子文本原始文件（md/txt/epub 等），登记 Work/Edition/SourceAsset，记录来源说明与权利状态（§77 D2），冻结为 `source_manifest`。不做清洗、不做 OCR、不做知识判断（§9）。
2. **M2（`pipeline/digitization/`）**：对 M1 入库的电子文本执行 §4.4 十三项清洗，产出四类 artifacts——`raw_text`（原始文本冻结）、`cleaned_text_revision`（清洗修订）、`deterministic_patch_set`（双向映射）、`sanitization_report`（发现记录，§81）。清洗结果经人工确认后 M2 Gate 放行。
3. **证据级别**：`offset_level`，发布级别只做 `INTERNAL_DEMO` / `DEV_SEARCH`（§76）。
4. **来源无关**：M1 按来源无关设计——来源站点、原始 URL、仓库提交号为字段，同书多来源各自登记 SourceAsset/Edition（§77 D2）。
5. **片段 ID**：无页码文本以字符偏移定位，片段 ID 格式 `ss_<work>_ed<NN>_o<NNNNNNN>`（§78 D3）；语义层用 `sem_` 前缀（§80 D5）。
6. **不新增 ID 前缀**：片段 ID 用已登记的 `ss_`/`sem_` 两种形态；`finding_id` 不引入新前缀，采用 `<kind>@<raw_start>-<raw_end>` 复合键格式（P8 合规）。
7. **P7**：任何需要人工确认的清洗决定（补字、改形近误字、判定缺失章节）都必须由用户决定表产出，本包只定义决定表格式与导入路径，不得伪造人工决定。
8. **零模型调用**（P6）：不调用任何 LLM/云服务；清洗为确定性规则。
9. **run_all.sh 不动**：本包只新建 `m1-intake.sh`、`m2-sanitization.sh` 两份验收脚本；接进 `run_all.sh` 属另一个独占 ACT（P4），由主 Agent 安排。本包验收脚本在宿主缺失时 exit 2（BLOCKED）。
10. **synthetic_fixture 标记**：本包所有测试用的合成文本样例与合成决定表均标 `synthetic_fixture: true`，验收判定不得把它们当作真实签发或真实书源（第 52、53 条、P7）。

**OCR 路线**（第二版）：

> 原 OCR 路线（真实页图 + 既有 OCR JSON 登记）内容保留在本文件，全部标记为 `DEFERRED（第二版 OCR）`，不在本版实现。

## 2. 上游来源契约（来源无关，§77 D2）

### 2.1 来源登记

M1 电子文本入库按来源无关设计。每份来源登记以下信息：

| 字段 | 含义 | 必填 |
|---|---|---|
| `source_id` | 来源唯一标识 | 是 |
| `work_title` | 书名 | 是 |
| `edition_note` | 版本说明 | 是 |
| `technique_id` | 技术形态 ID | 是 |
| `rights_status` | 权利状态声明 | 是 |
| `release_policy` | 发布策略（full_scan / derived_page_images_only / reference_and_hash_only） | 是 |
| `edition_part` | 分册信息（artifact_id, label, pages） | 是 |
| `source_site` | 来源站点域名（如 `daizhige.org`、`ctext.org`） | 是 |
| `source_url` | 原始 URL | 是 |
| `file_sha256` | 原始文件（磁盘下载物）SHA-256 | 是 |
| `pages` | 页/文件列表（非空，无重复） | 是 |
| `repo_commit` | 仓库提交号（如适用） | 否（缺省 None） |
| `yaml_metadata` | 文件头 YAML 元数据原样保存（如有） | 否（缺省 None） |

缺必填键 → `SCH_001`；出现表外键 → `SCH_002`。`repo_commit`/`yaml_metadata` 缺省为 None，不得因缺失而拒。

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
    sha256: <64-hex>            # 磁盘原始文件字节的 SHA-256 → 追踪链闭合到下载物
    normalized_sha256: <64-hex> # 归一化 UTF-8 后字节的 SHA-256 → 追踪链闭合到冻结 RawText
    original_encoding: <utf-8-sig | utf-8 | gb18030>   # 实际探测到的原编码
    size: <文件字节长度>
    width: null           # 电子文本无图像尺寸
    height: null
    object_store: local
    in_git: false
    yaml_metadata: <原样保存，如有>
    source_site: <来源站点>
    source_url: <原始 URL>
    repo_commit: <提交号，如有，无则 null>
files: []
conversion:
  tool: pipeline.intake
  tool_version: "0.1.0"
  inputs: [<path_ref>...]
  note: "M1 电子文本入库；不做清洗（§9）"
content_status: "machine_extracted"
```

`source_assets[]` 键序逐字：`page, path_ref, sha256, normalized_sha256, original_encoding, size, width, height, object_store, in_git, yaml_metadata, source_site, source_url, repo_commit`（14 个）。`sha256` 为**磁盘原始文件字节**的哈希（与 M1 输入 `source_info.file_sha256` 同源），`normalized_sha256` 为 UTF-8 归一化后、即冻结进 `raw_text` 的字节哈希——两个哈希各自闭合追踪链的一端（第 94 条 D4）；`original_encoding` 由 `read_source_files` 探测写入。`width`/`height` 对电子文本为 null（无图像尺寸）；`size` = 归一化后字节长度；`repo_commit` 无则 null。顶层不含 `source_sites`——来源以 `source_assets[]` 逐份登记为权威（§77 来源无关），顶层不冗余。

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
finding_id: "<kind>@<raw_start>-<raw_end>"（无新前缀，P8 合规；同一 kind 同一区间唯一）
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

> **数据驱动与检测边界说明（裁决第 91、92 条）**：
> 1. **`missing` 检测边界**：对照文内目录（如「目錄」「卷目」等节）核对各章节在正文中是否出现，缺失者登记为已知缺口并恒设 `deferred`；文内无目录时（无从判定）不产出 `missing` finding，此属已知边界而非缺陷。正文中若有显式「【缺】」类标记亦作为附加触发识别。
> 2. **`duplicate` 检测边界与段落阈值**：全文去重比对以单行/段落为粒度，设定段落长度 $\ge 8$ 字符进行频次统计；低于 8 字符的短句因在古籍中易与常见排版重合（如反复出现的“初九”“九二”等爻题）不参与全文段落比对，仅在连续紧邻出现（$\ge 4$ 字符紧邻重复）时触发附加登记。
> 3. **`textualized_diagram` 检测边界与字符集**：识别显式【图表】/【图式】/〔图〕标记、Markdown 表格分隔线，以及连续 2 行以上、每行 $\ge 3$ 个字符的制表符/框线字符区块（覆盖 Unicode 单双制表符 `─│┌┐└┘├┤┬┴┼═║╔╗`、ASCII 框线 `+-|` 以及破折连线 `—―` 等）；自由手绘式字符画、单行图形或分散的标点线条属已知未覆盖范围。
> 4. **数据驱动查证表**：`variant_mixed`（繁简字表 $\ge 100$ 对，无自映射）与 `suspected_error`（形近误字表，撤销纯数量下限，实行内容自洽质量判据：严禁 `wrong == correct` 自映射、严禁空 `basis`，每条必须具备确切校勘记或权威工具书依据）采用 `pipeline/digitization/data/` 下的数据文件驱动，查证表非穷尽、可后续按版本校勘审定增补。

## 6. 追踪链

```
片段（ss_/sem_ ID）
  → 清洗文本偏移（cleaned_text_revision 中的位置）
    → DeterministicPatchSet 映射（patch_id）
      → 原始文本偏移（raw_text 中的位置）
        → SourceAsset SHA-256
```

`source_assets[]` 同时登记两个哈希，各自闭合追踪链的一端（第 94 条 D4）：

```
最终产物 ──normalized_sha256──→ 冻结 RawText ──patch 映射──→ raw 偏移 ──sha256──→ 磁盘下载物
```

即：`sha256` 是磁盘上那个文件的字节哈希（与 `source_info.file_sha256` 同源），`normalized_sha256` 是归一化 UTF-8 后、即冻结进 `raw_text` 的字节哈希。带 BOM 或 GB18030 来源两者不等——原实现只记归一化哈希，链条回不到「我当初下载的就是这个文件」。

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
- 本包只定义对验收宿主的接口需求，具体清单如下：

**需要的文件与用途**：

| 文件名 | 用途 |
|---|---|
| `乾元秘旨_电子文本片段.txt`（或 `.md`） | M1 入库的原始电子文本样例；UTF-8 无 BOM；取自《乾元秘旨》前两节（"太极图说"至"河图洛书"区间） |
| `乾元秘旨_期望_cleaned.txt` | M2 清洗后期望产出的 `cleaned_text_revision` 内容，用于比对 |
| `乾元秘旨_期望_sanitization_report.yaml` | M2 清洗后期望产出的 `sanitization_report`，包含 finding 列表与 summary |
| `乾元秘旨_期望_m1_stage_package.yaml` | M1 StagePackage（source_manifest），用于 acceptance 检查键序 |
| `乾元秘旨_期望_m2_stage_package.yaml` | M2 StagePackage（sanitization_report + patches），用于 acceptance 检查 |

**每份文件的必备键**：

| 文件 | 必备键 |
|---|---|
| M1 StagePackage | `source_manifest`（键序见 §3：source_id, work_title, ..., content_status），`raw_text`（revision_id, size） |
| M2 StagePackage | `sanitization_report`（findings[], summary, deferred_count），`deterministic_patch_set`（patches[]） |
| sanitization_report | `findings[].finding_id`, `findings[].kind`, `findings[].raw_start`, `findings[].raw_end`, `findings[].raw_excerpt`, `findings[].context`, `findings[].action`, `findings[].patch_id`, `findings[].basis`, `findings[].terminal_state`, `summary`（各 kind 计数），`deferred_count` |

**需要固定的哈希**：

| 字段 | 哈希方式 |
|---|---|
| `source_asset.file_sha256` | 对原始 `.txt`/`.md` 文件全文取 SHA-256；宿主产出后写死 |
| `sanitization_report` 的 sha256 | 对 report YAML 序列化后取 SHA-256；宿主产出后写死 |

**《乾元秘旨》取样规格**：

- 取前两节（"太极图说"与"河图洛书"），约 2000–5000 字符
- 原始文本须包含以下已知问题（确保清洗有实际效果）：
  - `?` 替换字符 ≥ 4 处
  - PUA 码位 ≥ 39 个
  - 零宽控制字符 ≥ 2 处
  - Markdown 转义残留（`\-`、`\[`）≥ 1 处
  - 繁简混杂 ≥ 1 处
- 清洗后期望发现条数：约 46 条（与上游 fixture 对齐；具体以 `grep -c 'kind:'` 实数为准）
- `deferred_count` = 0（第一版不含需人工决定的发现）

### 7.3 对 Ledger

- M1 通过 `put_artifact` 写入 `source_manifest`、`raw_text`、`source_asset`
- M2 通过 `put_artifact` 写入 `cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`
- 事务序列遵循 §17 Checkpoint 落盘粒度

## 8. 用户待办

| 待办 | 内容 | 阻断 |
|---|---|---|
| 电子文本验收宿主 | 主 Agent 另行安排（P4），取《乾元秘旨》片段；产出后须标 `synthetic_fixture: true` | M2 Gate 真实验证 |
| 人工终态决定表 | 用户亲笔写（§77 D5），第一版首批取《乾元秘旨》前若干节；验收判定不得把合成决定表当作真实签发 | M2 真实验证 |
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
