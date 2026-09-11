# mini_ed01 fixture（D-15 统一验收宿主）

本目录是《三辰通载》第一册前三页（`page_001`、`page_002`、`page_003`）的**最小可跑验收宿主**。
它存在的唯一目的是让黑箱架构的 Module Interface、StagePackage 信封、字框级 SourceAnchor
与阶段 Gate 能在几十 KB 的规模上被确定性、可重复地验收，而不是靠人工观察。

- 来源：`ocr/data_work/data/page_001..003.json`（OCR 页面 JSON，原样拷贝）
  与 `ocr/data_work/logs/anomalies.jsonl`。
- 身份：`source_id=src_sanche_ed01`；`technique_id=qizheng`；`EditionPart` 标签「卷一·前三页」。
- 工作：`三辰通載三十卷`（影宋鈔本）。

## 1. 内容不作知识来源

本 fixture 的内容是 **机器转录（`content_status: machine_extracted`）**，未经人工校对，
仅作结构验收宿主：它用于证明「原文片段 → 字框锚点 → 阶段包信封 → 期望包哈希」这条链是
可校验的，**不得**作为知识来源、证据来源或发布输入引用。`page_002` 是无文字页，
终态登记为 `known_unrecognizable`（§10.1 允许 M2 Gate 放行）。

## 2. 页图不进 Git（硬约束）

三张页图（`ocr/data_work/sanche_pages/page_001..003.png`）**不在本目录，也不在 Git 中**。
它们是被 `.gitignore` 忽略的本机派生素材（见 `openspec/legacy-storage-transition.md` §6），
任何克隆者都可能没有。本 fixture 只做两件事：

1. 在 `manifest.yaml` 的 `source_assets` 中登记每页的 `path_ref`、`sha256`、`width`、`height`
   （`object_store: local`、`in_git: false`）；
2. 在 `spans.yaml` 的每条 span 中以 `source_anchor.image_sha256` 引用该页哈希。

本目录内**不得**出现任何 `png` / `jpg` / `jpeg` / `pdf` 文件（`verify.sh` V8 会检查）。
缺素材时不得创建空文件、替代图片或伪造哈希。

## 3. 自校验

```bash
bash pipeline/corpus/_fixture/mini_ed01/verify.sh
```

- 本机有素材：8 项检查全部 `PASS`，末行 `FIXTURE OK`，退出码 0。
- `.venv` 缺失：打印 `BLOCKED_ENV .venv missing`，退出码 3。

检查项（每条打印 `PASS <name>` 或 `FAIL <name> <原因>`）：

| 检查 | 内容 |
|---|---|
| `manifest_sha256` | `manifest.yaml` 的 `files[]` 每项 sha256 == 实际文件 |
| `ids` | manifest / spans / expected 中所有 ID 匹配已登记前缀格式（§8.1） |
| `coverage` | `page_001` / `page_003` 的 spans offset 严格切出 `text`、依序覆盖整块；`page_002` 无 span 且终态为 `known_unrecognizable` |
| `anchors` | 每条 span 的 `line_id` / `bbox` / 字框锚点（`char_index`、`glyph_id`、`char`、`box`）与页面 JSON 逐项一致，`image_sha256` 与 manifest 资产一致 |
| `expected_schema` | `expected/m1..m3.stage_package.yaml` 通过 `stage_package.schema.json`（D-02） |
| `expected_hash` | 三个期望包的 `content_sha256` 按 §22 规则重算相等，`counts` 与实际相等 |
| `assets` | `source_assets` 每项若在素材根目录存在则 sha256 与尺寸相等 |
| `no_images` | 本目录内无图像文件 |

退出码：任一 `FAIL` → 1；无 `FAIL` 但有阻塞 → 3；否则 0。

### 在缺图的机器上

```bash
FIXTURE_ASSET_ROOT=/nonexistent bash pipeline/corpus/_fixture/mini_ed01/verify.sh; echo $?
```

预期：非图像检查照常执行，缺的三页各打印一行
`BLOCKED_SOURCE_ASSET_MISSING ocr/data_work/sanche_pages/page_00N.png`，退出码 3。
这是**预期行为**，不是失败：素材是环境问题，不是 fixture 内容问题。

## 4. 可重放

删除本目录内除 `tools/` 与 `README.md` 之外的所有生成物后，可用确定性生成器重建：

```bash
.venv/bin/python pipeline/corpus/_fixture/mini_ed01/tools/build_fixture.py \
  --out /tmp/mini_ed01_rebuild
diff -r --exclude=tools --exclude=README.md /tmp/mini_ed01_rebuild \
  pipeline/corpus/_fixture/mini_ed01   # 期望无输出
```

生成器只用 Python 标准库 + `yaml`，不写时间戳、不写绝对路径、不写随机值；
输入缺失时打印 `BLOCKED_SOURCE_ASSET_MISSING <路径>` 并退出 3，且不创建任何文件。
`verify.sh` 也由该生成器产出，因此重放校验同时证明「自校验脚本与生成器模板一致」。

## 5. 目录结构

```text
mini_ed01/
├── README.md                          本文件（人工维护，不参与重放比对）
├── manifest.yaml                      来源清单：作品、版次、权利、页素材登记、文件哈希
├── pages/page_00{1,2,3}.json          OCR 页面 JSON（与 ocr/data_work/data 逐字节相同）
├── source/transcript_v1.md            机器转录（一行 OCR = 一节内的一行）
├── anomalies.yaml                     page_002 的异常终态与原始证据
├── spans.yaml                         43 条字框级 span，5 个 batch
├── expected/m{1,2,3}.stage_package.yaml  期望的 m1–m3 阶段包（含 lineage 串联）
├── tools/build_fixture.py             确定性生成器（重放入口）
└── verify.sh                          自校验脚本（V1–V8）
```

## 6. 口径说明（两处已登记的实现裁定）

1. **span 的 offset 语义**：`start_offset` / `end_offset` 相对该页在 transcript 中的文本块
   （块 = 该页各行以 `\n` 连接）。offset 区间**严格切出该行 `text`**（`block[start:end] == text`），
   行与行之间的唯一间隔是该页文本块内的一个 `\n`；首个 span 从 0 起，尾部 cover 到块尾。
   这样「严格 offset」可与双层 Span、SourceAnchor 直接对接。
2. **`manifest.files` 的范围**：ACT `act/r2-02.yaml` 要求 `files` 同时覆盖 `expected/*.yaml`，
   同时要求 `expected/m1` 的 `manifest.content_sha256` 等于 `sha256(manifest.yaml)`。
   二者构成哈希环（`manifest.yaml` 字节取决于 `expected/m1` 的 sha256，而 `expected/m1` 字节
   又取决于 `manifest.yaml` 的字节），无不动点解。本 fixture 保留 `content_sha256` 规则，
   把 `files` 限定为 6 个非 expected 文件；`expected/m1..m3` 由 V5（Schema）与 V6
   （content_sha256 + counts 重算）全量钉死，任一字节篡改即 FAIL。
