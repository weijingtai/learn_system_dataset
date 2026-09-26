# T25：OCR 校对工具遗留 — README

状态：`讨论候选`（本文档本身是任务书，不是最终规范；`openspec/` 才是最终规范存放处）
对应 `TODO.md` 条目：T25（`TODO.md:58`）
来源：`docs/handoff/ASK-2026-09-26.reply.md` 第 2 节（"OCR 校对工具遗留"，`ASK-2026-09-26.reply.md:52-76`），
以及云端主 Agent 09-26 把该节要点搬进 `TODO.md` T25 一行（`TODO.md:58`）。

本任务**只写文档，不写代码**。文中给出的行号、命令、函数名均已在本次编写时逐一核实存在（核实方法与结果见第 3 节）。执行者按 `act/01.yaml` 逐步做，任何地方"对不上"就停手，不许自由发挥。

---

## 1. 目标

把 `TODO.md` T25 列出的 5 项遗留（R7 横排切分、`min_gap` 死参、`test_segment.py` 断言过宽、Colab 未实机、校对界面 8 条人工走查未勾）以及 `ASK-2026-09-26.reply.md` 第 2 节额外指出的 `export_corpus` 仍导旧格式问题，逐项做到：

- 有测试的项：先写红测试证明缺陷存在，再改到绿，测试永久留库（契约测试）。
- 只能人工做的项（Colab 实机、界面 8 条走查）：给出用户本人可以照做的清单和记录表，**不代做、不代勾**。
- 格式未定、下游模块未登记的项（`export_corpus` 接新 M1）：给出候选方案与推荐，写「待用户决定」，执行者到此停手，不擅自选定格式。

## 2. 背景 —— 逐项核实

### 2.1 R7：`segment_block` 横排分支用原始灰度、取错轴

**代码位置**：`ocr/src/gujiorc/ocr/segment.py:108-126`（横排分支，`else:` 起）。

```python
else:
    # 横排：水平投影切
    row_density = dark.mean(axis=0)                       # segment.py:110，这一步用的是 dark（墨迹掩码），是对的
    gaps = _find_gaps(row_density, min_gap, density_thresh)
    boxes = []
    for g0, g1 in gaps:
        sub = region[:, g0:g1]                             # segment.py:114 —— 用了 region（原始灰度），不是 dark（墨迹掩码）
        col_density = sub.mean(axis=0)                      # segment.py:115 —— 对 axis=0（行方向）求均值，结果长度 == g1-g0（这一段的宽度）
        row_nonzero = np.where(col_density > density_thresh)[0]  # segment.py:116 —— 这个数组的下标语义是"列内第几个像素列"，不是"行号"
        if len(row_nonzero) == 0:
            continue
        cy0, cy1 = row_nonzero[0], row_nonzero[-1] + 1       # segment.py:119 —— 把上面这个下标当成了 y 方向（行）范围
        boxes.append({
            "x": float(x0 + g0),
            "y": float(y0 + cy0),
            "w": float(g1 - g0),
            "h": float(cy1 - cy0),                            # segment.py:124 —— h 恒被 cy1-cy0 的取值范围限制在 [0, g1-g0] 之内
        })
```

**根因（两处叠加）**：

1. `region` 是这一整个文本块裁出来的**原始灰度**子图（值域 0–255，背景≈255），不是 `dark`（`_ink_mask` 算出来的布尔墨迹掩码）。用 `density_thresh=0.02` 去比较原始灰度均值几乎恒为真（255 的均值远大于 0.02），墨迹判定形同虚设。
2. `col_density = sub.mean(axis=0)` 对 `sub`（形状为 `(box高, g1-g0)`）按 `axis=0`（沿行方向，即纵向）求均值，结果是一个长度为 `g1-g0`（这一段的**宽度**）的一维数组，语义是"每一列的均值"，**不是"每一行的均值"**。随后把这个数组的非零区间 `(row_nonzero[0], row_nonzero[-1]+1)` 直接当作 `(cy0, cy1)`（y 方向，即行范围）使用，取值范围被这个数组的长度（`g1-g0`，等于该段宽度）天然限制住，与该段真实的墨迹高度无关。

**已用合成图像实测复现（本次核实，未改代码，脚本未入库、仅用于核实）**：

```
画布 400x200，字体 wqy-zenhei.ttc（Linux 可用，见 §3 环境说明），字号 40，
横排绘制「得孛敬」三字，起点 (20,80)，字距 60px；
传入 box = {x:10, y:10, w:300, h:150}（人为造一个远高于真实字高的框，
模拟 PaddleOCR 行检测框给得过于宽松的情形）

segment_block(gray, box, min_gap=2) 的实际输出（4 段）：
  {'x': 22.0, 'y': 10.0, 'w': 12.0, 'h': 12.0}
  {'x': 35.0, 'y': 10.0, 'w': 22.0, 'h': 22.0}
  {'x': 81.0, 'y': 10.0, 'w': 36.0, 'h': 36.0}
  {'x': 141.0, 'y': 10.0, 'w': 37.0, 'h': 37.0}
```

四段的 `h` 无一例外**恒等于同段的 `w`**，且与传入的 `box["h"]=150`、与真实文字墨迹高度（该字号下约 40px 上下）都无关——这正是 HANDOFF 所说"横排块的框高恒为垃圾值"（`ocr/docs/HANDOFF.md:152-153`）的可复现证据：`h` 不是测出来的，是被 `col_density` 数组长度（等于该段宽度）意外限制出来的一个和 `w` 恒等的数。

竖排主路径（`segment.py:95-107`）用的是 `dark.mean(axis=1)`（对，且轴向正确），不受影响，这与 `ocr/docs/HANDOFF.md:153`（"竖排主路径不受影响"）一致。

### 2.2 `_find_gaps` 的 `min_gap` 死参

**代码位置**：`ocr/src/gujiorc/ocr/segment.py:305-323`。

```python
def _find_gaps(density: np.ndarray, min_gap: int, thresh: float) -> list[tuple[int, int]]:
    """..."""
    below = density <= thresh   # 只用了 thresh
    content = ~below
    segments = []
    i = 0
    n = len(density)
    while i < n:
        if content[i]:
            j = i
            while j < n and content[j]:
                j += 1
            segments.append((i, j))
            i = j
        else:
            i += 1
    return segments
```

函数签名接收 `min_gap`（第 305 行），函数体从第 307 行到第 322 行任何地方都没有引用 `min_gap`。第 321-322 行的注释（"这里 min_gap 用于底部……但保留"）描述的是一个从未落地的设想，不是实际行为。

调用方 `segment_block`（`segment.py:98`、`segment.py:111`）把自己的 `min_gap` 参数原样转发给 `_find_gaps`，调用方以为这个参数在起作用，实际被静默忽略。这与 R7 是两个独立缺陷（R7 是轴/掩码错误，这里是死参数），但同在 `segment_block`→`_find_gaps` 这条调用链上，一并处理。

另有一个次要的、同类的死参数：`segment_block` 自己的 `pad: int = 2` 形参（`segment.py:70`）在函数体（`segment.py:85-126`）里也从未被引用。TDD 里一并加一条断言钉住（见 `TDD.md`），但不属于 TODO T25 原文列出的项，仅作为同批顺手修的死代码问题在 act 里注明来源，避免被当作擅自扩大范围。

### 2.3 `tests/test_segment.py` 断言过宽

**代码位置**：`ocr/tests/test_segment.py`。

- `test_segment_block_vertical`（`test_segment.py:36-51`），断言在第 49 行：
  ```python
  assert len(segs) >= 2, f"应切出多个字，得到 {len(segs)} → {segs}"
  ```
  只有下界、没有上界，也不检查几何形状是否合理。一个把整块切成 50 个碎段的错误实现同样能通过。

- `test_segment_page_chars`（`test_segment.py:54-74`），断言在第 72 行：
  ```python
  assert n >= 2, f"应切出多个单字，得到 {n}"
  ```
  同样只有下界。而 `segment_page_chars` 的设计不变量（`segment.py:338-341` 文档注释："框数恒等于字数"）本来就保证了 `n == len(text_chars)`——测试里 `line.text="得孛敬"`（3 字），所以 `n` 应该确定性地等于 `3`，`>= 2` 比设计承诺松了一档，且完全不会因 `_align_to_count` 失效而报警。

两条断言目前都"过宽到测不出该测的问题"，需要收紧为贴合实现设计不变量的精确断言（详见 `TDD.md`）。

### 2.4 Colab 从未实机跑过

**依据**：`ocr/docs/HANDOFF.md:85`（"§5.1 第 3 条"："Colab 实机未跑——只在本地用 OCR_ROOT 模拟过，未真正在 Google Colab 挂载 Drive 跑过"）；`ASK-2026-09-26.reply.md:62`复述同一事实。这是**只能由用户本人**在真实 Google Colab 环境里做的事（需要用户的 Google 账号、Drive 挂载、以及把 `ocr/colab/` 上传到 Drive），执行者拿不到这些条件，不得代跑、不得伪造"已验证"记录。清单见 `act/01.yaml` 第 6 步。

### 2.5 校对界面 8 条人工走查未勾

**依据**：`ocr/docs/PLAN_PROOFREAD_EDIT.md:307-317`（"手工验收清单"，对 `page_001` 第一列走一遍），8 条全部是 `- [ ]`：

```
- [ ] 橡皮筋能一次框中「三辰通載」四个框
- [ ] `M` 合并前两个框 → 变成一个 h=44 的框
- [ ] 选中末框 → 「等分 2 份」→ 两个 h≈66 的框
- [ ] 全选四框 → 「重灌」→ 三/辰/通/載 各归其位
- [ ] `Cmd+Z` 三次 → 完全回到原状
- [ ] 刷新页面后 `Cmd+Z` 仍可用（撤销栈落盘）
- [ ] 诊断面板本来报 4 行，修完第一列后剩 3 行
- [ ] 框数≠字数时点重灌 → 看到的是「请先用合并/拆分…」原文，不是「操作失败」
```

同一份文档 §8（`PLAN_PROOFREAD_EDIT.md:343-424`）记录的是"用 Chrome 无头截图 + CDP 黑盒交互"做的**自动化**验收（14/14、11/11），不是用户本人在浏览器里手动走一遍。`ASK-2026-09-26.reply.md:63`把这一点说得很直接："代码做完了，但用户没有亲手走查过"。这 8 条也是**只能用户本人**做的事，理由同 §2.4：这是产品验收，不是可由 Agent 代签的测试（`AGENTS.md` 未直接提及，但与 `TODO.md` T24 行"无任何 Agent 代签路径"同一条 P7 精神一致）。清单见 `act/01.yaml` 第 7 步。

### 2.6 `export_corpus` 仍导旧格式，需对接新 M1

**代码位置**：`ocr/src/gujiorc/core/export.py:136-173`（`export_corpus` 函数）。

`export_corpus` 产出的目录结构是：

```
{corpus_dir}/{technique_id}/{book}_ed{edition:02d}/
  ├─ source/transcript_v1.md
  └─ manifest.yaml       # export.py:160-171 拼出的旧格式：
                          #   source_id / work_title / edition_note / technique_id /
                          #   rights_status / files:[{path, role, sha256}]
```

对照现存的旧格式样板 `pipeline/corpus/qimen/yanbo_ed02/manifest.yaml`（5 个顶层键 + `files` 列表，`role` 取值如 `raw_ebook`/`transcript`），`export_corpus` 拼出的正是这个旧格式（`export.py:160-169` 逐字段对应）。

而新 M1（电子文本路线，`pipeline/intake/source.py:14-26` 的 `REQUIRED_KEYS`）要求的 `source_info.yaml` 是完全不同的 13 键结构：`source_id / work_title / edition_note / technique_id / rights_status / release_policy / edition_part{artifact_id,label,pages} / source_site / source_url / file_sha256 / pages / [repo_commit] / [yaml_metadata]`，且没有旧格式的 `files:[{path,role,sha256}]` 列表；真实样板见 `pipeline/corpus/_fixture/qianyuan_ed01_text/source_info.yaml:1-33`。`pipeline/intake/source.py:39-150`（`load_source`）会拒绝任何表外键（`SCH_002`），所以旧格式喂给新 M1 会被直接拒收，不是"缺字段"那么简单。

`openspec/legacy-storage-transition.md:25` 把 `pipeline/corpus/` 整体判定为 `ACTIVE_LEGACY`，决议"迁移"，未来目标是"M1/M2/M3 Source、Digitization、Corpus Artifact"；`legacy-storage-transition.md:51` 明确点名 `ocr/src/gujiorc/core/export.py` 是这条迁移的调用点之一。也就是说，`export_corpus` 现在导出的旧格式本身也在待迁移之列，不是新 M1 认可的终态。

**为什么本任务不能直接定下新格式**：新 M1 的电子文本路线（`pipeline/intake/source.py`）读的是"一份或多份已经是纯文本的源文件"（`read_source_files`，`source.py:153-235`），而 OCR 产出的是"逐页逐字带坐标框、生僻字标记、校订历史"的结构化数据（`ocr/src/gujiorc/core/models.py` 的 `PageResult`/`CharBox`），二者形状完全不同。OCR 路线要不要有自己的 M1/M2（`route: ocr`），这正是 `TODO.md` T04c（`TODO.md:29`）"待办"的内容——T04c 明确写着"登记表一个 stage 只能登记一个 Module……OCR 路线在调度器入口按 route 拒收"。T04c 没做完之前，"OCR 应该产出什么形状的 M1 输入"根本没有权威答案，本任务只能列候选、写清代价，不能替 T04c 做设计决定，也不能替用户选。

三个候选见第 4 节"非目标"及 `act/01.yaml` 第 5 步；执行者在该步止步，把候选摘要转给用户，等回复。

### 2.7 弧线排布识别（星盘图曲线字）——已有实验结论，明确不接入

**依据**：`ocr/docs/TASKS_ENG_GAPS.md:366-412`（任务 D，"星盘图曲线字切分实验（原型，允许失败）"）；`ocr/docs/HANDOFF.md:126-129`（"D：`experiments/curve_segment.py` + `experiments/CURVE_REPORT.md`……真实图可用，PaddleOCR 调用在 3.7.0 接口切换到 predict 后卡住，未拿框"）；`ASK-2026-09-26.reply.md:60`（"任务 D 做过实验……结论是『净效果为负，不接入』"）。

这条**不在本任务范围内**，只在第 4 节"非目标"里重申维持现状：版面登记继续用 `irregular_layout` 标注（`ocr/docs/HANDOFF.md:168-172` 的 `assess_layout()`/`register_anomaly()` 挂接，已实现），不重开曲线识别实验，不接入生产管线。

## 3. 基线核实（本次实测，未改代码）

按 `AGENTS.md` 的环境约定，`ocr/` 有自己的依赖（`paddleocr`/`opencv`/`opencc` 等，见 `ocr/pyproject.toml`），不是根 `.venv/`（Python 3.14，给 `pipeline/` 用）能跑的。本次在临时目录建了一个隔离的 Python 3.11 venv 只装 `ocr/tests/` 实际会 import 到的依赖（`numpy`、`Pillow`、`pytest`、`opencc-python-reimplemented`、`fastapi`、`uvicorn`、`httpx`），**没有装 `paddleocr`/`paddlepaddle`**（这两个包体积大且本任务不需要跑真实识别，`ocr/tests/` 里被跳过的 26 条正是依赖真实 PaddleOCR/图像素材的用例）。

```bash
# 建隔离环境（一次性，供核实用，不建议写进正式 CI 步骤）
python3 -m venv /tmp/ocr_baseline_venv
/tmp/ocr_baseline_venv/bin/pip install --quiet numpy Pillow pytest opencc-python-reimplemented fastapi uvicorn httpx

cd ocr && PYTHONPATH=src /tmp/ocr_baseline_venv/bin/python -m pytest tests/ -q
```

**实测结果（本次核实，2026-09-26，Linux 容器）**：

```
FAILED tests/test_segment.py::test_segment_block_vertical - OSError: cannot open resource
FAILED tests/test_segment.py::test_segment_page_chars - OSError: cannot open resource
2 failed, 134 passed, 26 skipped, 1 warning
```

**这 2 条失败不是 R7、不是断言过宽，是第三个环境问题**：`ocr/tests/test_segment.py:19` 硬编码字体路径 `"/System/Library/Fonts/STHeiti Medium.ttc"`（仅 macOS 有），在没有这个路径的机器（本容器、以及任何非 macOS 的执行者环境）上，`PIL.ImageFont.truetype()` 直接抛 `OSError: cannot open resource`，两条测试**从收集不到画布、根本没跑到 `segment_block` 就先炸了**。本容器里实际可用的中文字体是 `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`（`fc-list :lang=zh` 核实存在）。

`act/01.yaml` 第 2 步会先处理这个字体路径可移植性问题（否则新写的 R7/断言测试在非 macOS 执行者的机器上无法运行，会被误判为"测试环境坏了"而不是"R7 还没修"）。这不是 TODO T25 原文列出的项，但不先修就没法在本容器（或任何非 mac 的执行者环境）里让"先红后绿"闭环，属于让本任务本身可执行所必须的前置修复，act 里会注明来源与最小改动范围（只改测试文件里取字体路径的方式，不改 `segment.py`）。

本次核实用的合成图像验证脚本（R7 复现，§2.1 引用的四段输出）放在会话临时目录，**未入库**，`act/01.yaml` 会给出等价的构造参数，执行者按参数重新构造，不依赖本次的临时文件。

## 4. 范围与非目标

**范围（本任务要做完的）**：

1. `act/01.yaml` 第 2 步：字体路径可移植性前置修复（`ocr/tests/test_segment.py` 内，仅测试文件）。
2. `act/01.yaml` 第 3 步：R7——修 `segment_block` 横排分支（`segment.py:108-126`），补新用例。
3. `act/01.yaml` 第 4 步：`_find_gaps` 的 `min_gap` 死参（`segment.py:305`）与 `segment_block` 的 `pad` 死参（`segment.py:70`）。
4. `act/01.yaml` 第 4 步（同批）：收紧 `test_segment.py` 两条过宽断言（`test_segment.py:49`、`test_segment.py:72`）。
5. `act/01.yaml` 第 5 步：`export_corpus` 对接新 M1——列候选、写「待用户决定」，执行者到此停手。
6. `act/01.yaml` 第 6、7 步：Colab 实机走查、校对界面 8 条走查——只给用户本人用的清单与记录表，执行者不代做。

**非目标（本任务明确不做）**：

1. **弧线排布识别不重开**。维持 `irregular_layout` 登记（`ocr/docs/HANDOFF.md:168-172`），不新增曲线切分算法，不改 `experiments/curve_segment.py`。理由见 §2.7。
2. **OCR 路线 M2 生产模块不在本任务内**。这是 `TODO.md` T04c（`TODO.md:29`）的范围；本任务只在第 5 步给出接口约定的候选，不实现、不登记、不改 `pipeline/contract_registry/registry.yaml`。
3. **OCR 端口 Adapter 数（`other_ports_adapters`，`TODO.md` T03b，`TODO.md:27`）不在本任务内**。T03b 要求 OCR/模型/索引三个端口各自至少 2 个可替换 Adapter，这是端口抽象层面的工作，T25 只管 OCR 工具自身的代码质量遗留，不新增 Adapter。
4. **不改 `ocr/local/static/`（Web UI 前端 Vue 代码）本身**。第 7 步的界面走查是"用现有代码走一遍并记录结果"，不是"改前端代码"；若走查发现真的 bug，记录下来，另开新的 `TODO.md` 条目，不在本任务里顺手改。
5. **不产出 `ReleaseBundle`，不进 `openspec/`**。本任务的三份文档是任务书，不是最终规范；`export_corpus` 格式一旦由用户裁定，才可能需要新的 `openspec/` 条目，那是后续任务。

## 5. BDD 场景

```gherkin
Feature: R7 横排单字切分几何正确

  Scenario: 横排文本块切分出的每个字框，高度应反映真实墨迹高度，不应恒等于宽度
    Given 一张合成横排文字图像，字符间的真实墨迹高度与每字宽度不相等
    And 一个明显比真实文字带宽松的检测框（高度远大于单字真实高度）
    When 对该检测框调用 segment_block
    Then 返回的每个字框的 h 不应恒等于该字框的 w
    And 返回的每个字框的 h 应落在该字符真实墨迹高度的合理区间内

  Scenario: min_gap 参数实际影响 _find_gaps 的切分结果
    Given 一段一维投影密度数组，其中存在若干短暂低于阈值的窄缝
    When 分别用较小和较大的 min_gap 调用 segment_block 的横排/竖排分支
    Then 不同 min_gap 得到的分段结果应有差异（当窄缝宽度介于两个 min_gap 之间时）

  Scenario: segment_page_chars 的框数恒等于字数这一设计不变量被测试钉住
    Given 一行识别文本恰好 3 个字
    When 调用 segment_page_chars
    Then 返回的单字框数量应精确等于 3，不是"至少 2"

  Scenario: export_corpus 的产出格式与用途在文档中被诚实标注
    Given export_corpus 当前产出的是旧版 manifest.yaml 格式
    When 阅读该函数的文档字符串或相关任务文档
    Then 不应声称该产出已经打通新 M1；应指向"待用户决定"的候选方案

  Scenario: Colab 实机走查与校对界面 8 条人工走查只能由用户本人完成
    Given 一份记录表列出全部走查项
    When 执行者到达这两步
    Then 执行者应停手，把记录表交给用户，不自行勾选、不伪造"已验证"
```
