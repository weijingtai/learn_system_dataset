# TDD：T25 OCR 校对工具遗留

环境：`ocr/` 有自己的一套依赖，不是仓库根 `.venv/`（那个是给 `pipeline/` 用的 Python 3.14）。
执行者按 `act/01.yaml` 第 1 步建好本任务专用的隔离测试环境后，本文里的 `$PT` 统一代表：

```
PT="<你在 act 第 1 步建好的 venv>/bin/python"
```

跑法统一为（仓库根，即本 worktree 根目录）：

```bash
cd ocr && PYTHONPATH=src $PT -m pytest tests/ -q
cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment.py -v
cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment_alignment.py -v   # 回归护栏，见下
```

**开工基线**（act 第 1 步做完后，任何一条改动前先跑一遍，记录数字）：

```bash
cd ocr && PYTHONPATH=src $PT -m pytest tests/ -q
# 本次核实（2026-09-26，README §3 已记）：2 failed, 134 passed, 26 skipped
# 这 2 条失败是字体路径问题（macOS 专用路径），不是 R7、不是断言过宽——
# act 第 2 步先修字体解析，这 2 条基线失败应变为 0 failed（而不是被跳过）
```

---

## 0. 前置：字体路径可移植性（不算 TODO T25 原文条目，是让后面测试能跑的必要前提）

**背景**：`ocr/tests/test_segment.py:19` 硬编码 `"/System/Library/Fonts/STHeiti Medium.ttc"`（仅 macOS）。本次核实在 Linux 容器上跑通了这条路径不存在，`test_segment_block_vertical`、`test_segment_page_chars` 两条现有测试直接 `OSError`（见 README §3）。不先修，本文档下面新增的所有测试在非 macOS 的执行者机器上也会以同样方式假红。

### 用例：`test_cjk_font_resolves_on_this_machine`（新增，`ocr/tests/test_segment.py`）

- **准备**：无（纯粹调用一个新写的 `_resolve_cjk_font()` 辅助函数）。
- **动作**：调用 `_resolve_cjk_font()`。
- **断言**：返回值是一个存在的文件路径字符串；若两个已知候选（见下）都不存在，该函数必须 `pytest.skip(...)`，而不是返回 `None` 或抛未处理异常。
- **预期先红原因**：`_resolve_cjk_font()` 函数目前不存在（`ImportError`/`AttributeError`）。
- **实现要求**（写给执行者，非本文档判定范围之外）：

  ```python
  import pytest

  _CJK_FONT_CANDIDATES = (
      "/System/Library/Fonts/STHeiti Medium.ttc",              # macOS
      "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",           # Linux（本次核实在容器内存在）
  )

  def _resolve_cjk_font() -> str:
      for p in _CJK_FONT_CANDIDATES:
          if os.path.isfile(p):
              return p
      pytest.skip("未找到可用中文字体（尝试过: %r），跳过依赖字体渲染的测试" % (_CJK_FONT_CANDIDATES,))
  ```

  `make_vertical_text_image()`（已存在，`test_segment.py:15-28`）与下面新增的 `make_horizontal_text_image()` 都改为用 `_resolve_cjk_font()` 取字体路径，不再硬编码。

- **篡改探针**：把两个候选路径都改成不存在的路径 → 该用例必须变成 `skipped`（不是 `failed`，不是静默通过）；改回一个真实存在的路径 → 恢复正常跑。

**验证**：`cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment.py -v` 全绿，且 `test_segment_block_vertical`、`test_segment_page_chars` 不再是 `OSError`。

---

## 1. R7：`segment_block` 横排分支

对应代码：`ocr/src/gujiorc/ocr/segment.py:108-126`。

### 1.1 新增测试文件位置

写进 `ocr/tests/test_segment.py`（不新建文件，横排测试与竖排测试放一起，方便对照）。需要在文件顶部新增 import：

```python
from gujiorc.ocr.segment import _ink_mask  # noqa: E402   # 用于测试里独立算真值，不是被测代码本身
```

### 1.2 用例：`test_segment_block_horizontal_uses_ink_mask_and_correct_axis`

- **准备**：
  1. 新增 `make_horizontal_text_image(width=400, height=200, font_size=40, chars="得孛敬", x0=20, y0=80, step=None)` 辅助函数（仿照已有 `make_vertical_text_image` 的写法，用 `_resolve_cjk_font()` 取字体，横向逐字绘制，`step` 缺省为 `font_size+20`）。**三个字都要真的画出来**（不像竖排 helper 跳过"得"那样跳过任何字——本用例故意要三字都存在墨迹,便于和"真值"逐段核对）。
  2. 调用一次得到 `gray`。
  3. 构造 `box = {"x": 10, "y": 10, "w": 300, "h": 150}`——**故意让 box 的高度（150）远大于三个字真实的墨迹带高度**（字号 40 的墨迹带通常在 30~60px 量级）。这是复现 R7 的关键：只有 box 高度与"真实高度"明显不同、且与某个分段的宽度也明显不同时，"h 恒等于 w"这个症状才无法被巧合掩盖（本次核实用完全相同的参数复现过，见 README §2.1）。
- **动作**：`segs = segment_block(gray, box, min_gap=2)`。
- **断言**：
  1. `len(segs) == 3`（三个字，横排分支不经过 `_align_to_count`，全 3 段之间空白足够宽，不会被误判为一段）。
  2. 对每个 `s in segs`：`s["h"] != s["w"]`——这是 R7 的可复现症状（h 恒等于 w），修复后不应再必然相等。
  3. 独立算一遍"真值"（不调用被测函数，只用已确认正确的 `_ink_mask`）：在 `box` 范围内取 `region = gray[10:160, 10:310]`、`dark = _ink_mask(region)`；对每个 `s`，取 `g0 = int(s["x"]) - 10, g1 = g0 + int(s["w"])`，`sub_dark = dark[:, g0:g1]`，`rows = np.where(sub_dark.any(axis=1))[0]`，`true_h = rows[-1] - rows[0] + 1`；断言 `abs(s["h"] - true_h) <= 3`。
- **预期先红原因**：现状 `segment.py:114-119` 用 `region`（原始灰度）而非 `dark`（墨迹掩码）判定，且 `col_density = sub.mean(axis=0)` 的结果长度恒等于该段宽度 `g1-g0`，导致 `cy1-cy0`（进而 `h`）被这个长度天然限制住，`h` 恒等于 `w`——断言 2 和断言 3 都会失败（断言 3 失败是因为 `h` 与真实墨迹行高偏差远超过 3px：本次核实实测偏差达十几到上百像素，见 README §2.1 的复现数据）。
- **篡改探针**：
  1. 把修复后的横排分支临时改回 `sub = region[:, g0:g1]`（原始灰度）→ 断言 2 必须转红。
  2. 把修复后 `col_density`/`row_nonzero` 的轴向改回沿用错误变量（制造 h 与 w 再度恒等）→ 断言 2 必须转红。
  3. 故意把断言 3 的容差从 `<=3` 改成 `<=1000`（放宽到形同虚设）→ 提醒执行者这类"放宽断言让测试通过"是 `AGENTS.md`/`TODO.md` 第七条明令禁止的，act 里会重复这条铁律。

### 1.3 竖排回归护栏（不新增用例，只是要求）

竖排分支（`segment.py:95-107`）本次未改，act 里要求修完 R7 后必须重跑：

```bash
cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment.py::test_segment_block_vertical tests/test_segment.py::test_segment_page_chars -v
```

两条都应保持通过（且已在 §0 修好字体路径的前提下不再是 `OSError`），证明横排分支的改动没有牵动竖排分支（`is_vertical(box)` 分支互斥，代码上不共享横排那段逻辑，但仍需实跑确认）。

---

## 2. `_find_gaps` 的 `min_gap` 死参

对应代码：`ocr/src/gujiorc/ocr/segment.py:305-323`（`_find_gaps` 函数体从未引用 `min_gap`）。

### 2.1 设计取舍（写给执行者，避免误解为"随便接上就行"）

`min_gap` 按字面意思应表示"两段内容之间，空白宽度小于这个值就不算真正的间隙（应合并成一段）"。**但不能**把它实现成"内容段本身短于 min_gap 就当噪声丢弃/并入相邻段"——那正是 `ocr/docs/HANDOFF.md:155-160`（§11 第 1 条）记录并已修掉的 `_merge_thin_segments` 那个回归（把「二」「一」这类窄笔画字误并进邻字，靠"字数已知"的 `_align_to_count` 来处理才是现在的设计）。**`min_gap` 只准用来判定"空白间隙"是否够宽算真间隙，不准用来判定"内容段"是否够宽算真内容。**

### 2.2 用例：`test_find_gaps_min_gap_merges_only_narrow_blank_runs`

- **文件**：`ocr/tests/test_segment.py`（新增，需要 `from gujiorc.ocr.segment import _find_gaps  # noqa: E402`）。
- **准备**：直接构造一维密度数组，不经过图像：
  ```python
  density = np.array([1.0] * 10 + [0.0] * 5 + [1.0] * 10)
  ```
  语义：两段内容（各 10 个采样点）中间夹了一段 5 个采样点宽的空白。
- **动作**：分别用 `min_gap=3`（小于空白宽度 5）和 `min_gap=8`（大于空白宽度 5）调用 `_find_gaps(density, min_gap=…, thresh=0.02)`。
- **断言**：
  1. `min_gap=3` 时：`len(segs) == 2`（空白宽度 5 ≥ min_gap 3，仍算真间隙，保持切开）。
  2. `min_gap=8` 时：`len(segs) == 1`（空白宽度 5 < min_gap 8，不算真间隙，应合并成一段），且合并后那一段的 `(start, end) == (0, 25)`。
- **预期先红原因**：现状函数体（`segment.py:307-320`）完全不引用 `min_gap`，两次调用结果逐字节相同（都是 `[(0,10),(15,25)]`），断言 2 必然失败。
- **篡改探针**：
  1. 把修复后的实现改回忽略 `min_gap`（等价于删掉合并逻辑）→ 断言 2 转红。
  2. 把合并逻辑误写成按"内容段宽度"而非"空白宽度"判定 → 用 `density = np.array([1.0]*2 + [0.0]*1 + [1.0]*10)`（内容段宽 2 很窄，空白只有 1）配 `min_gap=5` 试探：正确实现应因为空白宽度 1 < min_gap 5 而合并成一段（`[(0,13)]`）；如果误实现成"内容段宽度 < min_gap 就丢弃该短段"，则会得到 `[(3,13)]`（丢了前两个采样点），这条探针能把两种实现分开。act 里要求执行者把这条探针也跑一遍，附结果进回报。

### 2.3 必须重跑的既有回归护栏（不是新用例，是硬性要求）

```bash
cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment_alignment.py -v
```

这个文件此前已存在（README §2.2 引用过它的一条用例名 `test_thin_stroke_not_merged_into_previous_char`）。**这一条必须继续通过**，一旦变红，说明 `min_gap` 的修法不小心重新引入了 HANDOFF §11.1 记录过的那个回归，act 里的处理是**停手报告**，不是想办法让它也变绿（那基本等于又发明一套新的启发式，超出本任务范围）。

---

## 3. `tests/test_segment.py` 断言收紧

### 3.1 `test_segment_block_vertical`（现状 `test_segment.py:49`）

现状：
```python
assert len(segs) >= 2, f"应切出多个字，得到 {len(segs)} → {segs}"
```

**改为**：
```python
assert 2 <= len(segs) <= 4, f"2个真实字符应切出 2~4 段（含笔画细分），得到 {len(segs)} → {segs}"
```

- **理由**：`make_vertical_text_image(chars="得孛敬")` 实际只画了 2 个字（"得"被 `test_segment.py:24-25` 的 `if ch == "得": continue` 跳过，字符串里另外 2 字"孛""敬"才真的落墨）。原断言只有下界，一个把整块切成 50 段的错误实现也能通过。改成双边界后，本次核实用 `wqy-zenhei.ttc` 实测得到 `len(segs) == 2`（两个字各自形成一个连续墨迹段，未被内部笔画间隙拆开），上界 4 留出字体差异的余量但堵死"随便切出一堆碎段"这类错误。
- **预期先红原因**：这一步本身不会让当前实现变红（当前实现在字体修好后应该仍是 2 段），它是"收紧"不是"修 bug"；红/绿的验证方式是**篡改探针**（见下），不是"改前红改后绿"。
- **篡改探针**：把 `segment_block` 临时改成对横排/竖排都返回 10 个等分段（模拟一个严重错误的实现）→ 断言必须转红（原来的 `>=2` 不会转红，这正是要收紧的理由）。

### 3.2 `test_segment_page_chars`（现状 `test_segment.py:72`）

现状：
```python
assert n >= 2, f"应切出多个单字，得到 {n}"
```

**改为**：
```python
assert n == 3, f"line.text 恰好 3 字，_align_to_count 应保证框数恒等于字数，得到 {n}"
```

- **理由**：`segment_page_chars` 的设计不变量（`segment.py:338-341` 文档注释）保证"框数恒等于字数"，`line.text="得孛敬"` 是 3 字，`n` 应确定性地等于 3，与字体、真实画了几个字无关（第三个字"得"没有墨迹，也会被 `_align_to_count` 等分出一个框，只是该框大概率落在 `unrecognized`/空白区域——这是设计好的行为，不是 bug）。本次核实已实测 `n == 3`（见 README/本文件开头的 `_resolve_cjk_font` 说明所依赖的探针脚本，两种字体路径下均如此，因为这个不变量与像素无关，只与"字数"这个整数有关）。
- **预期先红原因**：同上，属于收紧而非修 bug，不预期让当前实现变红。
- **篡改探针**：把 `_align_to_count` 的调用临时去掉（`segment_page_chars` 直接用原始 `seg_boxes` 而不做数量对齐）→ `n` 会退化为投影出的原始段数（很可能不等于 3）→ 新断言必须转红，旧的 `>= 2` 断言在这种退化情形下很可能仍然通过（因为原始段数通常也 ≥2），这正是"旧断言测不出这个退化"的证据，建议执行者在回报里贴这组对比。

---

## 4. `export_corpus` —— 已裁决（用户 2026-09-26，候选 A）：标注为 audit-only，生产接入交给 T04c

`README.md` §2.6 已记录裁决过程与三个候选。**候选 A 生效**：不改 `manifest.yaml` 的字段结构本身（仍是旧格式），只做两件事：①在代码里加一个明确的机器可读标注，②用测试把"现状 + 标注 + 交接说明"三件事同时钉住。这不再是"到此止步"，是要做完的实现。

### 4.1 实现要求（写给执行者）

1. `ocr/src/gujiorc/core/export.py` 顶层（`export_corpus` 函数定义之前，建议紧邻 `# ---------------- pipeline corpus 导出（manifest.yaml） ----------------` 这行注释之后，即 `export.py:112` 附近）新增一个模块级常量：

   ```python
   # T25 候选 A（用户 2026-09-26 裁决）：export_corpus 保留旧格式，仅供人工核对/审计留档；
   # 不对接新 M1（pipeline/intake/source.py 的 source_info.yaml）。
   # OCR 路线的生产接入见 TODO.md T04c——那里要设计的 OCR 专属 M1/M2 模块直接消费
   # 页面 JSON/audit.jsonl，不经过本函数或 manifest.yaml。
   EXPORT_CORPUS_FORMAT = "legacy_audit_only"
   ```

2. `export_corpus` 的 docstring（`export.py:148`，现状仅一行"导出为 pipeline corpus 目录 + manifest.yaml（PLANS §6.1）。"）追加一段：

   ```python
   def export_corpus(
       ...
   ) -> dict[str, Path]:
       """导出为 pipeline corpus 目录 + manifest.yaml（PLANS §6.1）。

       用途限定（用户 2026-09-26 裁决 T25 候选 A，见 EXPORT_CORPUS_FORMAT）：
       本函数产出旧格式，仅供人工核对/审计留档，不是新 M1 的生产输入。
       OCR 路线的生产接入见 TODO.md T04c。
       """
   ```

   **不改**函数体、不改 `manifest` 拼出的字段（`export.py:160-171` 逐字不动）。

### 4.2 用例：`test_export_corpus_is_marked_legacy_audit_only_and_points_to_t04c`（新增，`ocr/tests/test_export_corpus.py`）

- **准备**：最小 `PageResult`（1 页 1 字，仿既有 `test_export_corpus.py` 里的 `make_page`，见该文件已存在，无需新建）。
- **动作**：①`from gujiorc.core import export as export_mod`；②调用 `export_corpus(pages, tmp_dir, book="t25probe", work_title="T", technique_id="qizheng")`，读回 `manifest.yaml`。
- **断言**（四条，同一条用例里都要有）：
  1. `export_mod.EXPORT_CORPUS_FORMAT == "legacy_audit_only"`（常量存在且取值正确）。
  2. `"T04c" in export_mod.export_corpus.__doc__`（docstring 指向交接点，字符串精确匹配 `"T04c"`，不匹配别的措辞，避免今后有人改了措辞却没意识到这条测试在钉什么）。
  3. manifest 内容仍包含旧格式的标志字段 `files:`（列表，含 `role: "transcript"`）——沿用原有的"现状钉子"断言，防止有人顺手把格式也改了。
  4. manifest 内容**不**包含新 M1 `source_info.yaml` 要求的必填键（`pipeline/intake/source.py:14-26` 的 `REQUIRED_KEYS`，例如 `release_policy`、`edition_part`、`source_site` 均不出现在 manifest 文本里）——候选 A 明确不实现候选 B/C，这条防止有人在这一步顺手实现了候选 B。
- **预期先红原因**：断言 1、2 现状必然失败（`EXPORT_CORPUS_FORMAT` 不存在 → `AttributeError`；docstring 不含 `"T04c"`）；断言 3、4 现状应当已经是真（旧格式、无新必填键），先跑一遍确认这两条本来就是绿的，只有 1、2 会红。
- **篡改探针**：
  1. 把 `EXPORT_CORPUS_FORMAT` 的值改成别的字符串（如 `"legacy"`）→ 断言 1 转红。
  2. 把 docstring 里的 `"T04c"` 删掉或换成别的措辞 → 断言 2 转红。
  3. 反证断言 4：临时把断言反过来写成"manifest 应包含新 M1 必填键"→ 必须转红（证明现状确实不是新格式，不是测试写错）。

---

## 5. 只有用户能做的两项 —— 不在本节写测试

Colab 实机跑通、校对界面 8 条人工走查（`ocr/docs/PLAN_PROOFREAD_EDIT.md:309-316`）没有自动化测试形式；这两项的"验证方法"是 `act/01.yaml` 第 6、7 步给出的人工记录表，不是这里的 pytest 用例。

---

## 6. 汇总：本次改动后必须全绿的命令

```bash
cd ocr && PYTHONPATH=src $PT -m pytest tests/ -q
# 期望：0 failed；原有 26 skipped 不应增加（除非确认是 §0 字体解析导致的新 skip，
#       且必须是"两个候选字体都找不到"这一种原因，不是别的原因）
cd ocr && PYTHONPATH=src $PT -m pytest tests/test_segment.py tests/test_segment_alignment.py -v
# 期望：全部 passed，逐条核对用例名与本文件列出的一致
```
