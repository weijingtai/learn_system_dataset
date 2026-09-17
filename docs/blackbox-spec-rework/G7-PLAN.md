# G7 黑箱剩余工作分波计划（Dataset 会话）

更新时间：2026-09-15
执行方式：tmux + `cmd --yolo`，模型 `deepseek/deepseek-v4.1-flash`（用户 2026-09-12 指令；W1 期间用 agy，额度不稳后切换，监控用 `tmux-watch.sh --agent cmd`），**同时最多 2～3 路**；主 Agent 只写裁决、只读报告文件与待裁决表，验收用脚本在 `git archive` 干净树上跑。裁决见 `G7-RULINGS.md`。

## 0. 现状

- 已验收：impl-01 Artifact Ledger；impl-02 M3 结构层（J3 `c5f744c`、ACT 06 `eee3c35`）；impl-00 act/10 INTERFACES §4 闭集登记（`ea90ca8`）；impl-03 M5 首切片（K2 `6e21038`、CLI 返工 `8367893`）。impl-04 M8 首切片 K1/K2/ACT 07 已验收，ACT 08（`950b77b`，run_all 20.4/20.8）验收中。`m3-coverage.sh`、`m5-evidence-gate.sh`、`m8-span-identity.sh` 均 exit 2；`run_all.sh` `pass=2 fail=1 blocked=8`。
- 草稿：impl-05～10 仍为 `DRAFT`（impl-08 已定稿 `cd6c7a6` 待四查），按 `G7-RULINGS.md` 裁剪后逐包定稿、四查、实现。
- 首纵切口径（用户决定，G7-RULINGS 第 43 条）：交付 mini_ed01 上 Ledger → M3 → M5 → M8 可跑通证据链；§20.3/20.4/20.8 可判，§20.1/§20.9 如实 BLOCKED（M4/M6 未接入、GraphProjectionPack 未编译），不改规格 §22.3 正文。

## 1. 并行规则

1. 每路 agy 只写自己的目录；提交用 `git commit -m … -- <路径…>`，只提交自己的路径；遇 `index.lock` 等待重试，不删锁。
2. 高风险共享面（`openspec/schemas/`、`pipeline/corpus/_fixture/`、`openspec/acceptance/run_all.sh`、`pipeline/ledger/`）同一时刻只允许一路写。
3. 执行方不写台账（SUBAGENT_TODO/HANDOFF/PLAN/ACCEPTANCE），报告写 `~/tmux-agents/runs/<会话>.report.md`，有疑问写「待裁决」后停手。
4. 监控 `tmux-watch.sh --interval 60 --idle-need 3 --stall 1800`；被唤醒先读报告文件。
5. agy 额度耗尽：换 agy 内另一模型续接一次；仍不可用则暂停并告知用户，不改派批量子 Agent。
6. 注解社区线（C/S 会话）也在本工作树用 agy，派发前 `tmux ls` 计入并行数。

## 2. 分波

| 波次 | 并行路数 | 内容 | 写范围 | 出口 |
|---|---|---|---|---|
| W0 | 主 Agent | 回归门禁补录、提交 impl-02 验收记录；草稿原样提交为 DRAFT 快照 | 台账、草稿目录 | 提交 |
| W1 | 2 | **A** 补全 impl-00 接口总表与 impl-03（M5）草稿；**B** 对账审查 impl-04～10 草稿与 impl-00 的接口一致性，汇总全部待裁决项 | A：`impl-00-interfaces/`、`impl-03-validation/`；B：`reviews/G7-DRAFTS-REVIEW-R1.md` | 主 Agent 一次性裁决，写 `G7-RULINGS.md` |
| W2 | 2 | **C** 执行 impl-00 契约 ACT（新 Schema、fixture m4/m5/m8 期望产物、verify 扩展）；**D** 按裁决定稿 impl-03、impl-04 为 READY 并做 wjt-react 四查 | C：schemas + fixture（独占）；D：两个工作包目录 | 主 Agent 验收 C；D 判 READY |
| W3 | 2 | **E** impl-03 M5 实现（`ACCEPTED`）；**F** impl-04 M8 实现（K1–K3 验收收尾）。原 **G** impl-05 按用户决定（G7-RULINGS 第 43 条）移出首纵切 | `pipeline/validation/`、`pipeline/dataset_compiler/` 各自独占 | 首纵切关键路径 Ledger→M3→M5→M8 跑通；`m5-evidence-gate.sh`、`m8-span-identity.sh` exit 2；§20.1/§20.9 如实 BLOCKED |
| W4 | ≤3 | **I** impl-08 Orchestrator + Contract Registry（`ACCEPTED`，K4 `f79eafd`）；**G** impl-05 M4 最薄接入（K1–K3 `ACCEPTED`，K4 验收脚本进行中）；impl-00 前置 act/12、act/05（`ACCEPTED`） | 各自宿主目录；`run_all.sh` 单写者 | §20.1、§20.10 已计算化判定（仍 BLOCKED） |
| W5 | ≤3 | **H** impl-06 M6 最薄接入（定稿中，先于 P：M8 知识链需要 M6 正式知识）；**P** impl-04 跟进批：知识链前三段与 GraphProjectionPack 接 M6 正式知识（H 定稿后起草）；**J** impl-09 M1/M2 真实接入（前置：用户撰写真实前十页人工终态决定表，P7）；**K** impl-10 M3 语义层（前置：用户确认 SemanticSpan 前缀，P8） | 各自宿主目录 | §20.1、§20.4、§20.8、§20.9 转判；`m3-coverage.sh` exit 0 |
| W6 | 1 | **L** impl-07 M7 增量汇编（首纵切外） | `pipeline/assembly/` | §20.5 |

每一波全部验收后才开下一波；某路返工只占用该路名额。

## 3. 每波主 Agent 动作（控制 token）

1. 写一份提示词文件（`~/tmux-agents/runs/prompts/<会话>.txt`），启动 agy，挂监控。
2. 被唤醒：读报告文件 → 需要裁决的只读待裁决段 → 回复或验收。
3. 验收：`git archive` 干净树 + 预写脚本，输出只取 `tail`/SUMMARY 行；结论写 ACCEPTANCE，台账随验收一并提交。

## 4. 文本源优先路线（殆知阁 TXT）与第二版必做清单

登记时间：2026-09-15（用户提出；**唯一登记处**，第二版 OCR 与文本清洗事项一律记在本节，不另开清单）。决定项 §4.6 待用户确认前不派发实现。

### 4.1 背景与调研结论

- 来源：殆知阁 `https://daizhige.org/`，数据仓库 `https://github.com/daizhige-org/daizhigev20`（默认分支 `data`，约 7.7GB，2026-09-12 更新）。收录范围几乎覆盖所需书目，但为电子文本，非扫描 PDF。
- 许可：仓库根目录**无 LICENSE**，README 无使用/再发布/商用条款 → 权利状态不明。
- 样本《乾元秘旨》（`易藏/术数/乾元秘旨.md`，[清]舒继英，外链 `ctp:wb457118`）：
  - 形态：原 txt 已转为 Markdown，文件头 YAML（title 简/繁、author、category、lastmod、github_repo_url、daizhige_url、additional_info、external_links），正文 158 行、17,735 字符。
  - 结构：**无页码**、无 Markdown 标题；节标题是独立短行（如「月」「五星四余」）；段落以全角空格缩进。
  - 质量：替换字符 `?` 4 处（如「无远弗?」）；私用区（PUA）字符 39 个（依赖仓库 `FONTS.md` 所述字体）；Markdown 转义残留（`\-`、`\[`）；以连字符拼出的文本化图表（「元星天道立极之图」等）；形近误字（「次日岁星天」应为「次曰」一类）；繁简混杂。
- 规格依据：§3/§9 允许 TXT/EPUB 作为 SourceAsset、电子转录本为独立 Edition；§10 M2 覆盖电子文本清洗；§11.1 `offset_level` 只可用于 `INTERNAL_DEMO`、`DEV_SEARCH`，`PUBLIC_RELEASE` 必须 `glyphbox_level`（TARGET:140「纯文本引用只能算开发级证据」）。

### 4.2 两期路线

- **第一版（文本源优先）**：以殆知阁电子文本为 Edition，走 M1→M8 全链，证据级别 `offset_level`，发布级别 `INTERNAL_DEMO` / `DEV_SEARCH`，不做实图 OCR。
- **第二版（证据升级）**：同书扫描本做 OCR，M7 版本对勘把电子文本与扫描本逐字对齐，证据升级到 `glyphbox_level` 后才可 `PUBLIC_RELEASE`。

### 4.3 第一版：各阶段到 100% 要做的事

| 阶段 | 要做的事 |
|---|---|
| M1 | 新增电子文本入库：登记 Work/Edition（电子转录本）/SourceAsset（md/txt 原文件 SHA-256、仓库提交号、原始 URL、YAML 元数据原样保存）、来源说明与权利准入决定（`rights_status` 如实登记，见 §4.6 D2）。 |
| M2 | 电子文本清洗（清单见 §4.4），产出 `RawText`、`CleanedTextRevision`、`DeterministicPatchSet`、`SanitizationReport`（§10:478），不得静默删除；清洗结果经人工确认后 M2 Gate 放行。 |
| M3 | 支持 `offset_level` 片段：无页码文本按「节 + 段 + 字符偏移」定位（ID 格式见 §4.6 D3）；补语义层（SemanticSpan，前缀待确认）；新增电子文本验收宿主（不改已验收 `mini_ed01`）。 |
| M4 | 核对 `offset_level` 输入可用；真实 `expert_verified` 签发（用户签发表）。 |
| M5 | G3 按 offset + quote hash 核对；补候选级校验（现为 `scope=corpus_only`）。 |
| M6 | 接 M7（真实输出驱动 `run_m7`，`upstream_m6_real`/`snapshot_projection` 转判）；真实签发；旧审核工作台数据迁入。 |
| M7 | 消费真实 M6 输出；第一版单一电子文本 Edition 汇编。 |
| M8 | 知识链前三段 + GraphProjectionPack；按 `INTERNAL_DEMO` 出包。 |
| 全局 | `run_all.sh` 11 项全部 PASS；各阶段验收脚本无 BLOCKED（依赖用户待办的项除外须如实标注）。 |

### 4.4 电子文本清洗必做清单（M2，第一版即做，逐项进 SanitizationReport）

1. 编码：统一 UTF-8，识别并记录原编码与 BOM。
2. 乱码与替换字符：`?`、`□`、`U+FFFD` 等逐处登记位置与上下文，不得猜字替换；可对照 CTP 或其他底本补字，补字作为 patch 记录来源。
3. 生僻字与私用区（PUA）字符：先区分「CJK 扩展区字（只需字体显示）」与「真正的私用区码位」；殆知阁 `FONTS.md` 只说明网页用 GlyphWiki 的 Jigmo/花園明朝字体显示，未给映射表——私用区码位须对照 GlyphWiki/Jigmo 查证后建立映射表（PUA → 标准 Unicode 或 IDS 描述），无法映射的保留原码并登记，不得猜字替换。
4. 控制字符、零宽字符、异常空白（全角空格缩进按版式规则保留或规范化并记录）。
5. 转换残留：Markdown 转义（`\-`、`\[`）、HTML/脚本、YAML 头与正文分离（元数据入 M1，不进正文）。
6. 水印、广告、站点说明、非文献内容（页脚、维护者声明、链接）。
7. 页眉页脚与重复标题行。
8. 重复章节 / 重复段落（全文去重比对，登记位置，不静默删除）。
9. 缺失章节（对照目录、CTP 外链或其他底本核对完整性，缺失登记为已知缺口）。
10. 异常字段与结构：节标题识别（独立短行）、正文/注文/夹注格式、文本化图表（以连字符拼出的图，登记为图表区块，不进语义切片或单独标注）。
11. 繁简混杂与异体字：记录原貌，不强制转换；规范化只进派生层并可逆。
12. 形近误字（如「日/曰」）：只登记疑点，改字须有底本依据并走 patch，不得由模型直接改。
13. 与扫描本/其他版本的差异不在第一版改正，留第二版对勘（§4.5）。

### 4.5 第二版必做清单（不得遗漏）

1. 扫描本获取与 M1 登记（原始扫描、拆页、图像哈希）。
2. OCR：版本化 `OCRProfile`，代表页校准、人工验收并冻结 Revision；保留 OCR 原始 JSON、字框、置信度、校订 Revision、质量报告与审计日志（§10）。
3. 异常页三终态（`manually_transcribed` / `known_unrecognizable` / `deferred`）与 M2 Gate 放行规则；**前十页人工终态决定表**（用户待办）。
4. 扫描本同样执行 §4.4 中适用的清洗与异常检查（乱码、重复/缺失、异常字段等）。
5. M7 版本对勘：电子文本 ↔ 扫描本逐字对齐（Alignment / VariantReading / Addition / Omission），异文进审核。
6. 证据升级：片段从 `offset_level` 升到 `glyphbox_level`（页、图像哈希、字框四点坐标），M8 片段身份延续。
7. M7 多 Edition 增量汇编、身份迁移、返工替换。
8. 公开发布：权利确认与 `ReleasePolicy`，`PUBLIC_RELEASE` 验收。
9. 旧 OCR 校对工具（FastAPI + Vue）与旧工作台数据迁入。
10. `sem_` 页码形态序号位数：第 80 条与 impl-00 act/14 为 3 位、`openspec/id-prefix-registry.md` §3.6 为 2 位——启用页码形态前裁定并改登记表（第 102 条 Q2）。

### 4.6 用户决定（2026-09-15 已定，G7-RULINGS 第 76–80 条）

- D1（第 76 条）：第一版只做 `INTERNAL_DEMO` / `DEV_SEARCH`，`offset_level`。
- D2（第 77 条）：殆知阁声明免费下载、未附许可证，如实登记并附我方校准记录；书源不限殆知阁，M1 电子文本入库按来源无关设计。
- D3（第 78 条）：无页码文本以字符偏移定位；片段 ID `ss_<work>_ed<NN>_o<NNNNNNN>`（原始文本起点偏移，7 位）。
- D4（第 79 条）：无法映射的字保留原码位，记录可显示该字的字体与 GlyphWiki 字形名，发布物附字体说明。
- D5（第 80 条）：SemanticSpan 前缀 `sem_`（页码/偏移两种形态）；`expert_verified` 由用户填写主 Agent 生成的签发决定表模板，经 M6 console 导入，Agent 不代填；前十页人工终态决定表移至第二版。

### 4.7 电子文本问题的可追踪模型（第 81 条）

- 与 OCR 同等可追踪：§4.4 每一项清洗发现都是 `SanitizationReport` 中一条带原始文本偏移的记录（`finding_id, kind, raw_start, raw_end, raw_excerpt, context, action, patch_id, basis, terminal_state`），终态沿用 OCR 异常页口径，`deferred` 阻断 M2 Gate。
- 证据链：片段 → 清洗文本偏移 → `DeterministicPatchSet` 映射 → 原始文本偏移 → SourceAsset SHA-256。
- 以《乾元秘旨》为例应产生的记录：`?` 替换字符 4 条、私用区字符 39 条、Markdown 转义残留若干条、文本化图表区块若干条、疑似形近误字（「次日/次曰」等）、繁简混杂——每条都有偏移、上下文、处理动作与依据。
- 现状兼容性：规格支持；M5（`g3_evidence.py`）、M7（`assembly/model.py`）、M8（`dataset_compiler/levels.py`）已接受 `offset_level`；**缺口在上游**——INTERFACES §4 未登记四类清洗产物，M1 无电子文本入库，M2 无文本清洗实现，M3 只生成字框锚点，无电子文本验收宿主。
- 补齐顺序：impl-00 闭集登记（四类产物 + 片段 ID 新形态 + `sem_` 前缀）→ M1 电子文本入库 → M2 文本清洗 → M3 偏移锚点与语义层 → 电子文本验收宿主（取《乾元秘旨》片段，不改 `mini_ed01`）。

### 4.8 markitdown 评估（第 82 条）

- 不进证据链（无位置映射、非高保真、图片 OCR 走大模型违反 P6）。
- 可选用途：后续 EPUB/DOCX/HTML 等电子格式的格式适配器，输出冻结为 `RawText` 并登记工具与版本；殆知阁 md/txt 不需要。
- 引入依赖须另立 ACT 并经用户同意，禁用全部 LLM/云服务选项。

## 5. W7 执行链路（tmux + OpenCode，2026-09-15 用户指令）

### 5.1 执行器与纪律

- 执行器：tmux 手动托管 opencode。首选 `opencode-go/deepseek-v4.1-flash`（**只用 V4.1 Flash**，禁用 `deepseek-v4-flash`，遇限流先报告用户、不自行降级）；但 2026-09-15 实测该模型报「requires explicit opt in（最新版仅中国区托管）」，需用户在 opencode.ai 工作区开通，故本轮按用户决定改用 `opencode/mimo-v2.5-free`（免费档，每 24 小时重置），开通后再切回 V4.1 Flash。`tmux-agent.sh` 暂不支持 opencode，启动与投递按 `~/tmux-agents/README.md` §2 手动括号粘贴；续接用 `-s <会话ID>`，不用 `-c`。
- 同时最多 2 路；监控用主 Agent 的 `oc-watch.sh`（回报文件停手标记 / 屏幕停滞 / 限流字样 / 会话消失 / 超时即退出唤醒）。
- 每步：起草六件套 → 审查（异厂商或主 Agent 自审小 ACT）→ 分组实现并停下 → 主 Agent 在 `git archive` 干净树独立验收（含矩阵外端到端与篡改）。
- 回报必须写全证据（hash、Red、Green、verify 原文），只写标题视为未完成；遇契约冲突停手写「## 待裁决」。

### 5.2 步骤

| 步 | 内容 | 前置 | 出口 |
|---|---|---|---|
| 7.0 | M6→M7 真实上游接线：`run_m7` 消费真实 M6 `close_review` 产出，M7 `upstream_m6_real`、M6 `snapshot_projection` 转判；更新过时 BLOCKED 文案；顺带小清理（M7 `acceptance.py` no_model_calls 静默跳过、`model.py` 尾随空白、M6 acceptance 比对 `first_review.decisions/checkpoints`） | impl-06、impl-07 G0 已 ACCEPTED | `m7-assembler.sh` BLOCKED 6→5、`m6-data-fields.sh` BLOCKED 3→2，其余不变 |
| 7.1 | impl-00 新 ACT：INTERFACES §4 登记电子文本四类产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`，命名以规格 §10 为准）；登记片段 ID 偏移形态（第 78 条）与 `sem_` 前缀（第 80 条）；`check_interfaces.py` 新增对应检查 | 第 76–82 条 | `check_interfaces.py` 末行 `fail=0` |
| 7.2 | impl-09 改范围为「M1+M2 电子文本」：来源无关入库（第 77 条）+ 文本清洗（§4.4 清单，第 81 条可追踪模型，四类产物）+ 电子文本验收宿主（《乾元秘旨》片段，不改 `mini_ed01`） | 7.1 | 新增 M1/M2 验收脚本 exit 0/2 如实；清洗发现逐条带偏移可追溯 |
| 7.3 | impl-10 M3：偏移锚点（第 78 条）+ 语义层（`sem_`，第 80 条） | 7.2 | `m3-coverage.sh` 在电子文本宿主上 exit 0 |
| 7.4 | 签发决定表模板（第 80 条，主 Agent 生成）→ 用户填写 → M4/M6 真实签发导入 | 7.3 | 用户完成填写；真实签发判定转判 |
| 7.5 | impl-04 跟进：M8 知识链前三段 + GraphProjectionPack，按 `INTERNAL_DEMO` 出包 | 7.0、7.3 | M8 BLOCKED 转判；`run_all.sh` 相应项转判 |

顺序：7.0 与 7.1 并行 → 7.2 → 7.3 → 7.4 与 7.5。第二版（OCR、对勘、证据升级、公开发布）见 §4.5，不在 W7。

### 5.3 W7 跟进清理（发现即记，随相应波次做）

- M6 测试桩 `pipeline/review/testing/` 的合成 candidate_set 为手写 YAML，已漂移于真实 M4 输出契约（第 84 条：缺 `counts.concept_mentions`、`school_views[].claim_refs`/`changes_current_judgment`，被 M7 `validate_candidate_set` 拒）。g0-06 只做最小补字段；长期应改由真实 `run_m4` 产出，随 impl-09 或 impl-04 跟进批一并整改。
- M7 `acceptance.py` 的 `no_model_calls` 曾静默跳过不可解析文件（g0-06 修）；M6 acceptance 未比对金标 `first_review.decisions`/`checkpoints`（act/12 修）。

## 6. W8 真书走到 M8（2026-09-16，第 100 条）

执行器：tmux + opencode `opencode/union-alpha`（免费档），同时最多 2 路；M4 b 路抽取也用它，a 路用 Claude 子 Agent。监控 `~/tmux-agents/bin/oc-watch.sh`。

| 步 | 内容 | 包 | 前置 | 出口 |
|---|---|---|---|---|
| 8.0 | J3f（`duplicate` 独立护栏，第 99 条）→ J4b（M1/M2 验收脚本改为对宿主原文实跑并与独立金标比对；期望文件由金标生成；宿主目录入库） | impl-09 | — | `m1-intake.sh`/`m2-sanitization.sh` 在真书宿主 exit 0；金标缺失 → exit 2 |
| 8.1 | `ledger/ids.py` 登记偏移与 `sem_` 形态（D3）；电子文本 M3 补 `corpus_package`/`coverage_report`/m3 阶段包（D2） | impl-01、impl-10 返工（可并行，文件不相交） | 8.0 | M4 `resolve_m3_outputs` 在真书临时 Ledger 上通过 |
| 8.2 | 节选定 + 两路抽取提交件（D4）；M4 去 `page` 硬依赖；真书 M4 跑通 | impl-05 返工 + 宿主 `qianyuan_ed01_text/m4/` | 8.1 | M4 `succeeded`，候选 ≤ 40，分歧进队列 |
| 8.3 | M5 offset 档 G1/G2/G3（D5） | impl-03 返工 | 8.1（可与 8.2 并行） | 真书 M5 `validation_package` 如实 |
| 8.4 | M6 适配 + 审核决定表模板（D6）→ **用户填表** → 导入 | impl-06 返工 | 8.2、8.3 | M6 `reviewed_edition` 产出（依赖用户） |
| 8.5 | M7 ID/证据级别放开（D7），真书 Snapshot | impl-07 返工 | 8.4 | M7 Snapshot 产出 |
| 8.6 | M8 读 Snapshot、知识链前三段、`reference_and_hash_only`、GraphProjectionPack（先定格式，D8） | impl-04 返工 + impl-00 登记 | 8.5（格式草案可提前） | 真书 `INTERNAL_DEMO` 发布包 |
| 8.7 | 各验收脚本电子文本路线（D9）；orchestrator 登记 m4/m6、m3 文本入口；`run_all.sh` 按判定输出（独占 ACT） | impl-08、各包 | 8.6 | `run_all.sh` 相应项转判 |

用户待办（W8，第 104 条）：8.2 M4 分歧裁决表亲填（每组选 a/b/both/neither）；8.4 M6 审核决定表亲填。真书链 Ledger：`var/ledgers/qianyuan_w8/`。

W8 跟进（发现即记）：
- 结构层与语义层 m3 阶段包共存规则（第 102 条 Q5）——任何下游消费 `sem_` 之前裁定。
- `pipeline/corpus_compiler/gate.py:23` 页码形态 parts 正则收归 `ids.py`（8.1 报备，字符集未分叉，低优先）。
