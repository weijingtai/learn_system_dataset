# OCRProfile 参数化设计

状态：已确认设计；尚未实现
日期：2026-09-08

## 1. 决议

Learn System 继续使用仓库 `ocr/` 中已经验证的中国传统竖排古籍 OCR 工具及其 FastAPI + Vue 校订界面。当前不替换识别引擎，不引入 Kraken，不重写 OCR 算法，也不新增调参 UI。

不同书籍、Edition、字体、纸张和版式不能共用一组固定参数。M2 必须支持版本化 `OCRProfile`：先用代表页调参并由人工抽样验收，达标后冻结该 Profile，再批量处理对应 Edition 或 EditionPart。

## 2. 当前实现基线

现有主路径已经能够调整：

- `gap`：区块和单字切分间距；
- `conf`：低置信标记阈值；
- `bleed_thresh`：背面透印抑制阈值；
- 是否启用单字切分；
- 人工改字、补框、合并、拆分、重排、撤销和重做。

当前尚未形成完整参数化：

- `config.yaml` 加载器没有接入主要 `run` 路径；
- PaddleOCR 初始化选项、列聚合参数、墨迹二值化、漏框修复和异常版面阈值仍有硬编码；
- 一次运行没有保存完整参数快照及其哈希；
- 没有 Profile 校准集、人工真值和实际正确率报告；
- 参数变化后无法可靠判断哪些 OCR 结果应重跑。

## 3. 最小数据模型

`OCRProfile` 归属于一个 Edition，默认覆盖其全部 EditionPart。只有同一 Edition 内确有显著不同版式时，才允许 EditionPart 引用覆盖 Profile。

每个逻辑 Profile 使用稳定的 `ocr_profile_id`；每次修改生成新的、不可复用的 `ocr_profile_revision_id`。已经开始的 StepRun 永远引用冻结 Revision，不读取后来修改的配置。

```text
OCRProfileRevision
├── identity: profile_id / revision_id / edition_id / optional edition_part_id
├── engine: name / package_version / model / language / orientation options
├── rendering: dpi / scale / color mode
├── preprocessing: bleed threshold / denoise and crop switches
├── layout: reading direction / block gap / column gap
├── segmentation: min gap / density / ink contrast / repair thresholds
├── confidence: low-confidence and anomaly thresholds
├── calibration: sample set / metrics / acceptance thresholds
└── provenance: creator / timestamp / parent revision / canonical hash
```

首版使用 YAML，并用 JSON Schema 校验；不建立专用数据库编辑器。

## 4. 校准与批量运行

```text
新 Edition
→ 选择 5–10 张代表页
→ 生成候选 OCRProfileRevision
→ 运行现有 OCR
→ 在现有 FastAPI + Vue 中人工核对
→ 生成 CalibrationReport
→ 达标后冻结 Profile
→ 批量识别 EditionPart
→ 人工只处理低置信、异常页和抽检页
→ 封存 DigitizationPackage
```

代表页应尽量覆盖正文密页、淡印或透印页、目录或小字页，以及该 Edition 中实际存在的表格、图形或特殊版面。不存在的版面类型不需要人为制造。

验收以人工真值计算的实际字符正确率、漏字率、错框率和异常页召回为准。OCR 引擎自己的平均置信度只能用于排序人工复核队列，不能替代实际正确率。

正常正文页默认以字符正确率不低于 95% 为批量运行下限，97% 为优选目标；异常版面单独进入人工终态，不用正文平均值掩盖。最终 M2 Gate 仍要求人工校订后的文本和证据位置满足发布级验收标准。

## 5. 运行与追溯

每次 OCR StepRun 必须保存：

- `ocr_profile_revision_id` 和 Profile 文件哈希；
- 引擎、依赖和模型版本；
- 输入页图哈希；
- 原始 OCR JSON、字框和置信度；
- 预处理、切分和异常检测报告；
- 人工校订 Revision 与审计事件；
- CalibrationReport 或批准该 Profile 的人工决定。

Profile 修改后创建新 Revision 和新 StepRun。旧结果不得覆盖；只有受该 Profile 影响且被重新运行的页面产生新 Artifact Revision。

## 6. 最少代码边界

首版只增加三项薄能力：

1. `--profile <yaml>`：把 Profile 参数映射到现有 OCR 调用；
2. 启动前 JSON Schema 校验，配置无效时停止，不静默退回默认值；
3. 输出完整参数快照、哈希和 CalibrationReport。

明确不做：自动寻参、模型权重训练、第二 OCR 引擎、在线参数中心、新调参界面、逐页任意配置。只有实际新书样本证明现有参数项不足时，才把对应硬编码提升为 Profile 字段。

## 7. 接入黑箱的位置

`OCRProfile` 是 Contract Registry 管理的 M2 配置 Artifact。Local Orchestrator 只负责把冻结 Revision 交给现有 OCR 命令并记录结果；FastAPI + Vue 继续负责校订，不承担工作流编排。

M2 输出接口保持 `DigitizationPackage`，所以以后即使更换识别引擎，也只需实现相同 Profile 输入和 PageResult 输出，不影响 M3–M8。
