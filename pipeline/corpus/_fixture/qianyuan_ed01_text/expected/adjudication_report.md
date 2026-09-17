# 《乾元秘旨》M2 清洗结果仲裁报告

本报告由**仲裁员**产出：对比"独立金标"（不读不运行 pipeline 代码的人工通读结果）与"流水线 M2"（`pipeline.digitization.cleaner.clean_text` 实际运行结果）的逐条差异，给出有证据的裁决建议。**本报告只给建议，不做最终裁决，也未修改任何文件**（原文、金标、`pipeline/**` 代码全程只读）。

## 0. 原文哈希核对

```
命令: shasum -a 256 qianyuan_ed01_text.md
实际输出: 3f7170cd504e496096bc933ab5ed8805d68fa98625c91c5c09a9e3a61fcecdbb
要求值:   3f7170cd504e496096bc933ab5ed8805d68fa98625c91c5c09a9e3a61fcecdbb
结果: 一致
```

同时核实字符数：`len(text) == 17735`，与任务描述、金标报告一致。

## 1. M2 实际运行方式

在 `/Users/jingtaiwei/Git/Public/learn_system` 下，用 `.venv/bin/python`、`PYTHONPATH=.` 直接调用：

```python
from pipeline.digitization.cleaner import clean_text
from pipeline.digitization.patcher import build_patches
from pipeline.digitization.reporter import build_sanitization_report

text = open("pipeline/corpus/_fixture/qianyuan_ed01_text/qianyuan_ed01_text.md", encoding="utf-8").read()
result = clean_text(text)   # findings, cleaned_text
patches = build_patches(text, result.cleaned_text, result.findings)
report = build_sanitization_report(result.findings, patches)
```

运行前核实：`pipeline/intake/source.py` 中 `yaml_metadata` 是**提交时的独立字段**，不是从文件内容里解析剥离出来的——冻结进 `raw_text` 的仍是原始文件的**全部字节（含 YAML 头）**。也就是说，本次直接对全文（含头）调用 `clean_text` 与真实 M1→M2 流水线会喂给 M2 的 `raw_text` 是同一份内容，不存在"因为跳过了 M1 所以少了预处理"的偏差。

M2 实测逐类计数（脚本落盘于 `scripts/run_m2.py`，输出见 `m2_findings.json`）：

```
duplicate: 12
escape_residue: 76
private_use_area: 39
replacement_char: 4
watermark: 2
合计: 133
```

与任务描述给出的表格完全一致；`report['summary']` 字段也逐一核对一致。M2 自身对 133 条 finding 做了 `text[raw_start:raw_end] == raw_excerpt` 自检，**133 条全部通过**（脚本输出："M2 自检: 共 133 条，通过 133 条，失败 0 条"）。

## 2. 逐类分歧：对位结果与逐条判断

### 2.1 `escape_residue`（金标 24 条 / M2 76 条）

**对位方法**：把 M2 的 76 条单字符级 finding（每条覆盖 2 字符，即 `\X` 转义对）与金标 23 条合并区间（不含 YAML 头那条）分别展开成"被覆盖字符偏移集合"，逐集合比对。

**结果**：两个集合**完全相同**（均为 152 个字符偏移，`set` 相等为 `True`）。即：76 个单字符 finding 精确等于 23 个合并区间在字符层面拆开后的样子——**M2 与金标看到的是完全相同的 76 个转义符、完全相同的位置**，唯一区别是登记粒度：M2 每个转义符单独一条，金标把相邻转义符合并成连续区间。

判为 **E（口径分歧）**，不选边，建议见 §4。

**额外差异**：金标多出 1 条（offset 0–478，YAML 头未与正文分离）。核实 `cleaner.py` 的 `escape_residue` 正则 `r"\\[\-\[\]\*\_\\]"` 只处理 Markdown 转义符，**完全没有**"检测文件是否以 YAML front matter 开头且未与正文分离"这条逻辑分支。而 README §5 第5项'转换残留'明确把"YAML 头与正文分离"列为该检查项的三个子项之一（另两个是 Markdown 转义、HTML/脚本）。判为 **B（M2 漏报）**：不是解释空间问题，是代码里确实没有这条规则。

### 2.2 `watermark`（金标 1 条 uncertain / M2 2 条）

**对位方法**：按 offset 直接比对。

| 来源 | offset | 内容 |
|---|---|---|
| 金标（uncertain） | 392–429 | `2025-09-15 转换自「殆知阁」GitHub 仓库中的 txt 版本` |
| M2 | 124–255 | `https://github.com/daizhige-org/daizhigev20/blob/...乾元秘旨.md`（github_repo_url 字段值） |
| M2 | 270–370 | `https://daizhige.org/.../乾元秘旨.html`（daizhige_url 字段值） |

**三处 offset 互不重叠，零交集**——两边根本不是在争论"同一处该不该算水印"，而是**各自标了完全不同的位置**。这本身就是一个值得主 Agent 关注的信号：金标独立通读时把注意力放在"维护者声明"这句中文话上；M2 的正则是无差别 `https?://\S+` 匹配，扫中的是 YAML 头里另外两个结构化字段（`github_repo_url`、`daizhige_url`）的值。

- **M2 两条（m2_only）**：判为 **A（M2 误报）**。这两个 URL 是文件自带的结构化溯源字段（键名即 `github_repo_url`/`daizhige_url`），语义上对应 M1 契约 §2.1 的 `source_url`/`source_site` 字段，是应当保留的出处引用，不是第三方塞进正文的广告/推广链接。watermark 的"链接"子类正则对全文（含 YAML 头）无差别扫描，命中即 `action=patched`（会从 cleaned_text 整段剥离），会导致可核验的来源引用丢失。
- **金标一条（golden_only）**：判为 **F（无法判定）**。缺的不是底本，是一个规格范围问题：README §2.3 说 YAML 头"原样保存...不做解析转换"，这句话到底是"YAML 头整体不受 M2 正文类检查约束"还是"只约束 M1 对 yaml_metadata 字段本身的处理方式"，本报告无法从 README/RULINGS 独立判定。**但有一个值得注意的不一致**：M2 自己已经在同一个 YAML 头内对另外两个字段做了 watermark 扫描并命中，说明 M2 的**实际行为**已经默认"YAML 头在扫描范围内"——如果以 M2 自己的实际行为为准，这条就该改判 B（M2 漏报，正则字面模式没覆盖这句中文维护者声明）。

### 2.3 `duplicate`（金标 0 条 / M2 12 条）

**对位方法**：12 条 M2 finding 逐条核对，全部落在金标判定的 `textualized_diagram` 区块（offset 2250–2458，第23–24行星曜排布图）内部，且与 `escape_residue` 命中的 `\-\-\-\-` 转义连字符序列**完全重合**。

```
2254-2262, 2263-2275, 2276-2284, 2286-2294, 2298-2306, 2308-2316,
2320-2328, 2330-2338, 2339-2351, 2352-2360, 2401-2409, 2423-2431
```

逐条切出原文确认：全部是 `\-\-\-\-`/`\-\-\-\-\-\-` 这类由反斜杠+连字符构成的星图栏位分隔符，**没有一条是中文文献内容的重复**。核实触发规则是 `cleaner.py` 里 duplicate 检测的"附加触发：连续紧邻重复短语（≥4字符）"正则 `r"([^\s，。！？、]{4,})\1+"`——这个负向字符类只排除了几个中文标点，没有排除 ASCII 反斜杠/连字符，于是把"反斜杠+连字符"2字符单元的连续重复也当成了"重复短语"命中。

金标报告 §2.8 明确说明：**跑过同一条正则、看到了同样的命中**，但基于"标点符号构成，非文献内容重复"主动排除，不计入 duplicate。

12 条全部判为 **A（M2 误报）**：这不是"术数古籍里合法重复的口诀/星名/格式化条目"这种语义级重复，是纯粹的排版分隔符号被正则误当作"内容重复"，且已经被 escape_residue、textualized_diagram 两个规则各自正确登记过一次——三重计数同一段标点符号，语义上也用词不当（"重复内容"应指文献内容重复，不是分隔符号重复）。

**特别说明**：本次逐条核实未发现任何 M2 duplicate finding 属于"合法的口诀复述/星名重复被误标"这种任务描述里预设的典型场景——12 条全部是同一种模式（星图分隔符），根源单一，不是十二个独立的误判。

### 2.4 `textualized_diagram`（金标 1 条 / M2 0 条）

金标唯一候选：offset 2250–2458，第23–24行"元星天道立极之图/元星仰观天文之图"星图排布，紧接第25行原文明确说明"右将元星天道立极之图、元星仰观天文之图，依元星一书开载"，可确认是插图的文本化排布。

核实 M2 的检测正则 `diagram_box_pattern`：要求**整行**只由框线/ASCII图形字符组成（`^[ \t]*[框线字符集]{3,}[ \t]*$`，或以框线字符开头结尾），此外还有【图表】显式标记与 Markdown 表格竖线两个分支。本区块每行是"中文星曜名 + 转义连字符"交替出现（如 `计\-\-\-\-日\-\-\-\-\-\-月...`），**整行不是纯分隔符**，三个分支正则都不匹配，M2 零命中。

对照 README §5 第10项边界说明原文："连续2行以上、每行≥3个此类字符的制表符/框线字符区块（...ASCII框线 +-| ...）"——本区块 2 行、每行远超 3 个转义连字符，**按规格文字描述应在检测范围内**，不属于"自由手绘式字符画、单行图形或分散的标点线条"这一明确排除的例外。判为 **B（M2 漏报）**：代码实现（要求整行都是分隔符）比规格文字描述（每行≥3个此类字符即可，未要求整行）更严格，是实现漏洞而非规格边界之外。

### 2.5 `variant_mixed`（金标 1 条 uncertain / M2 0 条）

金标候选：offset 14282–14283，"於"（全文唯一 1 处，与其余 71 处"于"不一致）。

核实 `pipeline/digitization/data/variant_pairs.yaml`（122 对繁简字表）：**表内没有"於/于"这一对**（对 `tc`/`sc` 字段逐一搜索均为空）。更进一步核实检测算法本身：`if has_tc and has_sc:` 要求表里某个繁体字与其对应简体字都要**实际出现在文本里**才会触发扫描；逐一核对表内全部 122 个繁体候选字，**没有一个出现在本文件中**（`tc_present` 为空集合）。也就是说，即便表里补上"於/于"，只要这份 122 对的表覆盖不到文中实际出现的繁体字，`variant_mixed` 对本文档就是**结构性恒为 0**，与文档内容本身无关。

判为 **B（M2 漏报）**，且是两层叠加的漏报：(1) 数据表缺"於/于"这一常见文言虚词对；(2) 算法"命中首个字符即 `break`，全文只登记 1 条"的设计，即便补表后也无法反映"混杂了几处"，与其余 11 类"逐处登记"的一般原则不一致（详见附录代码位置）。

金标本身标了 `uncertain`（"於"是文言合法写法还是转换残留无法排除），这一点本报告同样无法独立判定，留给主 Agent；但"M2 现有规则结构性检测不到"这一点是可以从代码确证的事实，不受 uncertain 影响。

## 3. 计数一致的七类：抽查结论

对 `replacement_char`、`private_use_area`、`encoding_issue`、`control_char`、`header_footer`、`missing`、`suspected_error` 逐类做了 `sorted[(raw_start, raw_end)]` 集合比对：

| kind | 结论 |
|---|---|
| `replacement_char` | 两边 4 条位置**逐一相同**：(2520,2521)/(11349,11350)/(13033,13034)/(14287,14288)，excerpt 均为半角 `?` |
| `private_use_area` | 两边 39 条位置**逐一相同**，涉及 U+E03D(24)/U+E052(12)/U+E049(3) 三个码位 |
| `encoding_issue` | 两边均 0 条，判定一致 |
| `control_char` | 两边均 0 条，判定一致；但两边都独立观察到全文 134 处全角空格（U+3000，段首缩进）均未登记为发现——这是隐藏的一致判断，未反映在计数表里，若验收口径改为"全角空格规范化并记录"，两边会**同时**系统性少报，值得主 Agent 留意 |
| `header_footer` | 两边均 0 条，判定一致 |
| `missing` | 两边均 0 条，判定一致，理由相同（全文无目录小节，`missing_determinable=false`） |
| `suspected_error` | 两边均 0 条，判定一致，理由相同（零网络无法调阅底本核证，宁可少报） |

**结论：七个"计数一致"的类别，位置也真的一致**，不存在"数目凑巧相同但标的位置不同"的情况。

## 4. 总建议

| kind | 建议 |
|---|---|
| `duplicate` | **改 M2**：把"附加触发：连续紧邻重复短语（≥4字符）"正则的重复单元收窄为"至少含一个非 ASCII 标点/非转义字符"，或直接排除已被 `escape_residue`/`textualized_diagram` 命中的区间，避免星图分隔符被三重计数。12 条 M2 发现全部判误报，金标 0 条成立。 |
| `escape_residue` | **定计数口径**（不选边）：字符级覆盖完全一致，建议主 Agent 在 README §81 明确 finding 是"逐字符"还是"合并区间"粒度，两种粒度应可从同一份 `deterministic_patch_set` 无损互推。**另改 M2**：补上"YAML 头与正文分离"这条独立检查分支（README §5 第5项三个子项之一，目前完全缺失）。 |
| `watermark` | **先裁决范围，再改代码**：主 Agent 需要先回答"YAML 头结构化字段是否属于 M2 正文类检测范围"。若裁定"在范围内"（与 M2 现有实际行为一致）——则应**改 M2**：(a) 排除 `github_repo_url`/`daizhige_url` 这类已被识别为溯源字段的 URL（当前 2 条误报），(b) 补充"转换自「XX」...版本"这类中文声明句式的正则（当前漏报金标那 1 条）。若裁定"不在范围内"——则应**改 M2**把 watermark 扫描范围限定在 YAML 头结束标记之后的正文部分，3 条分歧会同时消失。 |
| `textualized_diagram` | **改 M2**：`diagram_box_pattern` 要求整行都是分隔符字符过严，应放宽为"一行内此类分隔字符达到密度/数量阈值即可"，不要求整行纯分隔符，使其能覆盖"星曜名目+转义连字符交替排布"这类规格文字已经描述过的图表形式。 |
| `variant_mixed` | **改 M2**：(a) `variant_pairs.yaml` 补充"於/于"等高频文言虚词繁简对；(b) 检测算法"命中首个字符即停"的设计应改为逐处登记，与其余 11 类保持一致的登记粒度。金标该条本身标了 `uncertain`，"於"这一具体个案是否计入，仍需主 Agent 对该字是否属于文言合法写法做出裁决。 |

## 5. 自检：逐条验证 `text[raw_start:raw_end] == excerpt`

脚本 `scripts/build_adjudication.py` 在生成 `adjudication.yaml` 的**同一次运行**里，对每一条 dispute 现场从原文用 `text[raw_start:raw_end]` 切出 excerpt（不是手抄），生成后再逐条回验：

```
共 19 条，通过 19 条，失败 0 条
verdict 分布: {'E': 1, 'B': 3, 'F': 1, 'A': 14}
```

（另：M2 自身 133 条 finding 的自检见 §1，"共 133 条，通过 133 条，失败 0 条"；金标自身 70 条 finding 的自检见金标报告 §3，"共 70 条，通过 70 条，失败 0 条"——三份数据各自独立自检全部通过。）

## 未做清单

1. **PUA 字形未解析**：39 处私用区码位本报告同样未做 GlyphWiki/Jigmo 查证（零网络限制，与金标处境相同），只确认了两边位置一致，未对码位本身对错做任何判断。
2. **`duplicate` 12 条的根因判定局限于本次核实到的一种模式**（星图分隔符被正则误当重复），未穷举 M2 duplicate 检测逻辑在其他假设性输入下是否还有别的误报模式——本文档只提供了这一种真实样本。
3. **`watermark` 的范围裁决未替主 Agent 拍板**：本报告指出了"M2 实际行为已默认 YAML 头在扫描范围内"这一不一致信号，但没有替主 Agent 决定 README §2.3 的最终解释，这是任务要求刻意留白的部分（F 类不得强行给结论）。
4. **`variant_mixed` 的"於"字本身是否为文言合法写法**：本报告只确认了"M2 现有规则结构性检测不到"这一代码事实，未对"於"字个案的文献学正误做出判断（与金标处境相同，缺底本/校勘依据）。
5. **`escape_residue` 的合并规则未提出具体算法**：建议里说"应统一登记粒度口径"，但没有给出"何为相邻""跨行是否合并"的具体规则草案，这部分留给主 Agent 或后续 ACT 设计。
6. **未检查 `deterministic_patch_set`（`build_patches` 产出）与 `sanitization_report`（`build_sanitization_report` 产出）本身的正确性**：只用它们跑通了一遍 M2 全流程并确认 `report['summary']` 与直接统计 `findings` 一致，未对 patch 的 `raw_start/raw_end/cleaned_start/cleaned_end` 双向映射做逐条校验（任务未要求，超出仲裁范围）。
7. **未对 M2 133 条与金标 70 条之外、可能存在的"两边都没标但确实有问题"的位置做地毯式复核**（例如全文是否还有其他类型的水印用语、其他重复段落等）——本报告的核实范围严格限定在"两边分歧的位置"与"两边计数一致类别的位置抽查"，没有对全文做超出两份清单之外的独立通读。
