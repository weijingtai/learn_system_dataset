# TASKS：OCR 工程缺口补齐 — 执行任务书（交给 AI agent 照做）

> 日期：2026-08-19
> 作者是规划 agent；**执行者是另一个 AI agent**。
> 上游依据：`ocr/docs/HANDOFF.md` §5.2 工程缺口、§6 实现方向；`ocr/docs/PLANS.md` §6 pipeline 衔接。
> 状态：待执行。按 A → B → C → D 顺序做；D 是实验任务，允许失败。
> 每个任务独立提交一次 git。做完一个任务再做下一个，禁止跳着做。

---

## 0. 全局规则（每个任务开工前重读一遍）

1. **工作目录**：只允许在 `ocr/` 内改文件。禁止改 `pipeline/`、`tag_system/`、`knowledge_system/` 下的任何文件（只读参考可以）。
2. **禁止碰的文件**：`ocr/local/static/`（index.html、vendor/）和 `ocr/scripts/fetch_frontend.py` —— 这是未提交、未验收的 Web UI Vue 改版，属于另一条线，**绝对不要改、不要提交它们**。
3. **环境**（每条命令都先执行）：
   ```bash
   cd /Users/jingtaiwei/Git/Public/xuan-migration/learn_system/ocr
   source .venv/bin/activate
   # 跑 Python 时永远带 PYTHONPATH=src
   ```
4. **测试基线**：开工前先跑 `PYTHONPATH=src pytest tests/ -q`，必须 37 个全过才开始；每完成一个任务再跑一遍，全过才能提交。禁止跳过或删除既有测试。
5. **git 提交纪律**：
   - 只 `git add <明确列出的文件路径>`，**禁止 `git add .` / `git add -A`**（工作区有别人的未提交改动，见规则 2）。
   - 提交信息用 Conventional Commits（每个任务下方给了现成的消息，直接用）。
   - 禁止 push、禁止合并到 main、禁止 rebase / reset --hard / stash。
   - 提交前跑 `git diff --check`（检查空白错误）。
6. **不确定就停**：如果实际代码和本任务书描述对不上（比如行号偏移、函数名不同），停下来，把差异写进 `ocr/docs/HANDOFF.md` 的"进行到一半的事"，不要自由发挥。

---

## 任务 A：Unihan 离线库下载脚本

难度：★（最简单，先做这个）。目标：一条命令把 Unihan 数据下到本地，让 `dict` 命令能查出所有汉字的读音/部首/笔画/释义。

### A.1 开工前必读（顺序读）

1. `ocr/src/gujiorc/rare/dictionary.py` —— 重点看 `Unihan` 类的 `_load()` 和 `_load_txt()`。**结论：解析代码已经写好了**，它会自动找 `data/unihan/` 目录下的 `Unihan*.txt` 文件解析，字段是 `kMandarin`（读音）、`kDefinition`（释义）、`kRSUnicode`（部首）、`kTotalStrokes`（笔画）。**本任务不需要改 dictionary.py**。
2. `ocr/src/gujiorc/core/paths.py` —— `get_root()`：数据根目录由环境变量 `OCR_ROOT` 决定，未设置则是 `ocr/data_work/`。
3. `ocr/scripts/fetch_frontend.py` —— 参考它的下载写法（urllib + UA 头 + 已存在则跳过）。

### A.2 新建文件 `ocr/scripts/fetch_unihan.py`

完整行为规格：

1. 下载 URL：`https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip`（约 7MB 的 zip）。
2. 目标目录：`Path(os.environ.get("OCR_ROOT", "")) or <ocr 项目根>/data_work` 下的 `data/unihan/`。直接 `from gujiorc.core.paths import get_root`，目标 = `Path(get_root()) / "data" / "unihan"`（运行时需 `PYTHONPATH=src`）。
3. 用 `urllib.request` 下载（带 `User-Agent: Mozilla/5.0` 头，超时 120s），存到临时文件，用 `zipfile.ZipFile` 解压**全部** `Unihan_*.txt` 到目标目录。
4. 幂等：目标目录已有 `Unihan_Readings.txt` 就打印"已存在，跳过"直接退出；`--force` 参数可强制重下。
5. 结束打印每个解压文件的字节数。核心两个文件必须存在：`Unihan_Readings.txt`（含 kMandarin/kDefinition）、`Unihan_RadicalStrokeCounts.txt`（含 kRSUnicode/kTotalStrokes），缺了就报错退出码 1。
6. 打印一句提示：这些数据文件**不要提交 git**（体积大；data_work/ 已在 .gitignore）。

骨架（照这个写，补全即可）：

```python
# 下载 Unihan 离线库（生僻字读音/部首/笔画/释义数据）到 data/unihan/
# 执行: PYTHONPATH=src python scripts/fetch_unihan.py [--force]
import os, sys, urllib.request, zipfile, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from gujiorc.core.paths import get_root  # noqa: E402

URL = "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip"
REQUIRED = ["Unihan_Readings.txt", "Unihan_RadicalStrokeCounts.txt"]

def main() -> int:
    force = "--force" in sys.argv
    dest = Path(get_root()) / "data" / "unihan"
    dest.mkdir(parents=True, exist_ok=True)
    # TODO: 1) 若 not force 且 REQUIRED 文件都在 → 打印跳过并 return 0
    # TODO: 2) urllib 下载 zip 到 tempfile（Request 带 UA，timeout=120）
    # TODO: 3) zipfile 解压全部 Unihan_*.txt 到 dest
    # TODO: 4) 校验 REQUIRED 都存在，打印每个文件大小；缺 → return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### A.3 验收（逐条复制执行，全过才算完成）

```bash
cd /Users/jingtaiwei/Git/Public/xuan-migration/learn_system/ocr && source .venv/bin/activate
PYTHONPATH=src python scripts/fetch_unihan.py
# 期望：下载成功，列出 Unihan_*.txt 文件大小

# 验证 1：查一个【不在内置术数字典】的字，读音必须来自 Unihan
PYTHONPATH=src python scripts/ocr_workbench.py dict 夔
# 期望：输出包含 reading: kuí（夔不在内置字典，能查到=Unihan 生效）

# 验证 2：内置字典仍然优先（孛 的释义应含"月孛"字样）
PYTHONPATH=src python scripts/ocr_workbench.py dict 孛

# 验证 3：原有测试不受影响
PYTHONPATH=src pytest tests/ -q   # 37 passed
```

### A.4 提交

```bash
git add scripts/fetch_unihan.py
git diff --cached --check && git commit -m "feat(ocr): Unihan离线库下载脚本-补齐生僻字读音/部首数据源(工程缺口3)"
```

### A.5 禁止

- 不改 `dictionary.py`（解析已支持，别重复造）。
- 不把 Unihan 数据文件加进 git。

---

## 任务 B：导出 manifest.yaml（打通 pipeline 衔接）★核心

难度：★★★。目标：`export` 命令新增 `--corpus-out` 模式，直接产出 pipeline 规定的目录结构和 manifest.yaml，让 OCR 成果能被知识编译管线消费。

### B.1 开工前必读（顺序读）

1. `pipeline/corpus/qimen/yanbo_ed02/manifest.yaml` —— **格式样板，逐字段抄**。
2. `pipeline/validators/validate.py` 第 93–112 行 —— 校验规则：`SRC_001`=files 里登记的文件必须存在；`SRC_003`=登记的 sha256 必须和文件实际哈希一致。我们的 manifest 必须过这两条。
3. `ocr/src/gujiorc/core/export.py` 全文 —— 已有 `gen_transcript_md()`（生成 transcript 正文），本任务复用它。
4. `ocr/scripts/ocr_workbench.py` 的 `cmd_export`（约 263 行起）—— 挂新参数的地方。
5. `ocr/docs/PLANS.md` §6.1 —— 衔接规范，重点第 4 条：有未识别字时必须在 edition_note 里注明"该底本存在 N 个未识别字形待人工补录"，不得伪造字符。

### B.2 改 `ocr/src/gujiorc/core/export.py`：新增两个函数

在文件末尾追加（骨架照抄，补全 TODO）：

```python
# ---------------- pipeline corpus 导出（manifest.yaml） ----------------

def sha256_file(path: Path) -> str:
    """计算文件 sha256 十六进制。分块读，不一次载入。"""
    import hashlib
    # TODO: 以 rb 模式按 1MB 块循环 update，返回 hexdigest()

def count_unknown(pages: list[PageResult]) -> int:
    """统计导出后会变成 □ 的字框数（char 为空）。"""
    # TODO: sum(1 for p in pages for c in p.chars if not c.char)

def export_corpus(
    pages: list[PageResult],
    corpus_dir: str | Path,
    *,
    book: str,                      # 书目 ID，如 "qtwx"（拼音/英文，做目录名）
    work_title: str,                # 书名原文，如 "新刻琴堂五星"
    technique_id: str,              # 技法 ID，如 "qimen"（须与 pipeline/corpus/ 下已有目录名一致风格）
    edition: int = 1,               # 版次，进目录名 _ed01
    edition_note: str = "",
    rights_status: str = "public_domain",
    groups_resolve=None,            # 与 export_common 同款的分组映射函数
) -> dict[str, Path]:
    """导出为 pipeline/corpus 结构 + manifest.yaml（PLANS §6.1）。

    目录: {corpus_dir}/{technique_id}/{book}_ed{edition:02d}/
      ├─ source/transcript_v1.md
      └─ manifest.yaml
    返回 {"manifest": Path, "transcript": Path, "unknown": int}
    """
    # TODO 按编号实现：
    # 1. book_dir = Path(corpus_dir) / technique_id / f"{book}_ed{edition:02d}"
    #    (book_dir / "source").mkdir(parents=True, exist_ok=True)
    # 2. transcript 路径 = book_dir/"source"/"transcript_v1.md"
    #    内容 = gen_transcript_md(pages, groups_resolve)   # 复用现有函数
    # 3. n = count_unknown(pages)
    #    若 n > 0：note 追加 "；该底本存在 {n} 个未识别字形待人工补录（导出为 □ 占位）"
    #    （原文已有"未识别"字样则不重复追加）
    # 4. manifest.yaml 内容必须严格是下面模板的样子（值一律双引号，防 YAML 转义问题）：
    #
    #    source_id: "src_{book}_ed{edition:02d}"
    #    work_title: "{work_title}"
    #    edition_note: "{note}"
    #    technique_id: "{technique_id}"
    #    rights_status: "{rights_status}"
    #    files:
    #      - path: "source/transcript_v1.md"
    #        role: "transcript"
    #        sha256: "{sha256_file(transcript路径)}"
    # 5. 写盘（utf-8），返回 {"manifest": ..., "transcript": ..., "unknown": n}
```

**注意**：不要用 yaml 库生成（避免键序/转义不可控），直接 f-string 拼模板。双引号值是合法 YAML。

### B.3 改 `ocr/scripts/ocr_workbench.py` 的 export 子命令

1. 在 `p_export = sub.add_parser("export", ...)` 处新增参数（照现有 add_argument 风格）：
   - `--corpus-out`（目录路径；给了才走 corpus 模式）
   - `--work-title`（必填当 corpus 模式；书名原文）
   - `--technique-id`（corpus 模式必填）
   - `--edition`（int，默认 1）
   - `--edition-note`（默认 ""）
   - `--rights-status`（默认 "public_domain"）
2. `cmd_export` 里：`args.corpus_out` 非空时调 `export_corpus(...)`，打印三个返回值和"未知字 N 个已按 □ 导出"；同时保留原 `export_common` 逻辑不动（两种模式并存）。
3. corpus 模式缺 `--work-title` 或 `--technique-id` 时打印错误并 `return 1`（不要静默用默认值）。

### B.4 新建测试 `ocr/tests/test_export_corpus.py`

仿照 `tests/test_export.py` 的写法（sys.path.insert + make_page 工厂），至少覆盖：

```python
def test_export_corpus_writes_manifest_and_transcript():
    # tmp 目录导出后断言：
    # 1. manifest.yaml 与 source/transcript_v1.md 都存在
    # 2. manifest 里 source_id == "src_test_ed01"
    # 3. manifest 里的 sha256 与重新计算的文件哈希一致（import hashlib 自算比对）
    # 4. manifest 里出现 path: "source/transcript_v1.md" 和 role: "transcript"

def test_manifest_notes_unknown_count():
    # 页里含 char="" 的字框 → manifest 文本含 "未识别字形待人工补录"

def test_manifest_no_note_when_all_recognized():
    # 全部有字 → edition_note 不含 "未识别字形"
```

### B.5 验收

```bash
cd /Users/jingtaiwei/Git/Public/xuan-migration/learn_system/ocr && source .venv/bin/activate
PYTHONPATH=src pytest tests/ -q          # 37+新增 全过
PYTHONPATH=src pytest tests/test_export_corpus.py -v

# 真数据联验（若 data_work/ 里有页面数据）：
OCR_ROOT=data_work PYTHONPATH=src python scripts/ocr_workbench.py export --book qtwx \
  --corpus-out /tmp/corpus_test --work-title "新刻琴堂五星" --technique-id wuxing
# 然后人工比对 /tmp/corpus_test/wuxing/qtwx_ed01/manifest.yaml
# 与 pipeline/corpus/qimen/yanbo_ed02/manifest.yaml 字段一一对应
```

### B.6 提交

```bash
git add src/gujiorc/core/export.py scripts/ocr_workbench.py tests/test_export_corpus.py
git diff --cached --check && git commit -m "feat(ocr): 导出manifest.yaml+corpus目录结构(M6/§6.1)-打通pipeline衔接(工程缺口1)"
```

### B.7 禁止

- 禁止改 `pipeline/` 下任何文件（validate.py 只读参考）。
- 禁止在 manifest 里写死 sha256 或省略哈希。
- 禁止对文本做简繁转换（transcript 保持原字形，已有铁律）。

---

## 任务 C：全局审计日志 audit.jsonl

难度：★★。目标：所有改字/分组/补标/旋转操作追加写入 `logs/audit.jsonl`（跨页可追溯），并提供 `audit` 查询命令。现状：只有字级 `orig_char`+`mapping`，没有全局操作流水。

### C.1 开工前必读

1. `ocr/src/gujiorc/core/models.py` 的 `CharBox.set_char` —— 看懂 mapping 结构 `{target, from, source, ts}`。
2. `ocr/src/gujiorc/core/paths.py` 的 `ensure_struct()` —— `logs/` 目录已自动创建，直接用。
3. `ocr/scripts/ocr_workbench.py` 的 `cmd_fix`（约 200 行）和 `cmd_groups`（约 327 行）—— 挂日志的 CLI 侧位置。
4. `ocr/local/app.py` 三个写操作路由：93 行 `POST /api/page/{page}/fix`、111 行 `POST /api/page/{page}/segment-new`、134 行 `GET /api/page/{page}/char/{char_id}/rotate`。

### C.2 新建 `ocr/src/gujiorc/core/audit.py`

```python
"""gujiorc.core.audit — 全局审计日志（append-only，跨页可追溯）。

每行一个 JSON 事件，写 {OCR_ROOT}/logs/audit.jsonl。
铁律：只追加、永不修改/删除已有行。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .paths import get_root, ensure_struct

# 允许的 action 枚举（写死，防乱写）
ACTIONS = {"fix", "segment_new", "rotate", "verify",
           "group_create", "group_add", "group_define", "group_remove", "export"}

def log_event(action: str, *, actor: str, page: str = "",
              char_id: str = "", **fields) -> Path:
    """追加一条审计事件，返回 audit.jsonl 路径。

    actor: "cli" | "web" | "colab"
    fields: 任意附加键值（from/to/source/note 等，值必须是可 json 序列化的简单类型）
    action 不在 ACTIONS 里 → raise ValueError
    """
    # TODO: 1) 校验 action ∈ ACTIONS
    #       2) event = {"ts": datetime.now().isoformat(timespec="seconds"),
    #                   "actor": actor, "action": action,
    #                   "page": page, "char_id": char_id, **fields}
    #       3) path = ensure_struct()["logs"] / "audit.jsonl"
    #          with open(path, "a", encoding="utf-8") 单次 write 一整行 json.dumps(..., ensure_ascii=False) + "\n"

def read_events(*, page: str | None = None, action: str | None = None,
                last: int = 0) -> list[dict]:
    """读审计事件。page/action 过滤；last=N 只返回最近 N 条（保持时间正序）。
    文件不存在返回 []。坏行（非 JSON）跳过，不抛异常。"""
```

### C.3 挂接 6 个写点（每个都是两行：import + 调用）

| 位置 | action | 附带字段 |
|---|---|---|
| `cmd_fix` 改字成功后 | `fix` | `from=旧字, to=新字, source="manual"`, actor=`"cli"` |
| `cmd_groups` create | `group_create` | `group_id, name` |
| `cmd_groups` add/remove | `group_add` / `group_remove` | `group_id, samples=[...]` |
| `cmd_groups` define | `group_define` | `group_id, char=定义字` |
| app.py fix 路由成功后 | `fix` | 同 CLI，actor=`"web"` |
| app.py segment-new 成功后 | `segment_new` | `char_id=新框ID, box` |
| app.py rotate 成功后 | `rotate` | `char_id, angle`（注意它现在是 GET 路由，**不要改路由方法**，只加日志） |

写法示例（cmd_fix 内，成功分支末尾）：

```python
from gujiorc.core.audit import log_event
log_event("fix", actor="cli", page=page_id, char_id=char_id,
          **{"from": old_char, "to": new_char, "source": "manual"})
```

（注意 `from` 是 Python 关键字，必须用 `**{"from": ...}` 传。）

### C.4 新增 CLI 子命令 `audit`

`scripts/ocr_workbench.py` 里仿照 `query` 命令添加：

```
PYTHONPATH=src python scripts/ocr_workbench.py audit [--page page_003] [--action fix] [--last 20]
```

输出：每行一条 `ts  actor  action  page  char_id  摘要`，无事件打印"暂无审计记录"。

### C.5 新建测试 `ocr/tests/test_audit.py`

```python
# 用 os.environ["OCR_ROOT"] = tmp 目录（monkeypatch fixture）隔离
def test_append_and_read():          # 写 3 条读回 3 条；每条有 ts/actor/action
def test_filter_page():              # 只看某页 → 只剩对应条数
def test_invalid_action_raises():    # log_event("hack", ...) → ValueError
def test_read_missing_file():        # 文件不存在 → []
```

注意：测试里改 `OCR_ROOT` 要用 pytest 的 `monkeypatch.setenv`，并在测试后保证不影响其他用例（`paths.get_root()` 每次现读环境变量，没问题）。

### C.6 验收

```bash
cd /Users/jingtaiwei/Git/Public/xuan-migration/learn_system/ocr && source .venv/bin/activate
PYTHONPATH=src pytest tests/ -q                       # 全过
# 手工验证（对 data_work 真数据，若存在）：
OCR_ROOT=data_work PYTHONPATH=src python scripts/ocr_workbench.py fix page_003 all 凡 --from-char 凢
OCR_ROOT=data_work PYTHONPATH=src python scripts/ocr_workbench.py audit --last 5
# 期望：能看到刚才那条 fix 记录
```

### C.7 提交

```bash
git add src/gujiorc/core/audit.py scripts/ocr_workbench.py local/app.py tests/test_audit.py
git diff --cached --check && git commit -m "feat(ocr): 全局审计日志audit.jsonl-CLI/Web全写点挂接(工程缺口2)"
```

### C.8 禁止

- 审计文件只追加；不做轮转、不做清理、不做"修复"功能。
- 不把审计事件写进每页 JSON（页面数据结构不变）。
- 不改 app.py 的路由方法（GET 保持 GET）。

---

## 任务 D：星盘图曲线字切分实验（原型，允许失败）

难度：★★★★（研究性）。性质：**spike**——产出实验报告和原型脚本，**不改生产管线**（不碰 `src/gujiorc/ocr/segment.py`、`pipeline.py`）。

### D.1 背景（为什么要做、方向是什么）

星盘图（图画式版面）的字沿圆弧排布、每个字的朝向随半径方向变化。PaddleOCR 的检测（det）通常**仍能框住单个字**，失败在识别（rec）——它假设字是正立的。已留下的设计方向（PLANS §1 方向检测、§7 风险对策、HANDOFF §6 中期 3）归纳为一条：**沿圆弧几何重定向 + 逐字旋转到正立后重识别，置信度择优**。

### D.2 产出物

1. `ocr/experiments/curve_segment.py` —— 原型脚本（独立可跑，可 import gujiorc 但不修改它）
2. `ocr/experiments/CURVE_REPORT.md` —— 实验报告

### D.3 算法步骤（写进原型，按编号实现）

```
输入: 一张星盘图 + PaddleOCR det 结果（框列表）
1. 圆心估计:
   a. cv2.HoughCircles 找候选圆心（星盘有同心环，取票数最高的中心）
   b. 用 det 框中心点集做最小二乘圆拟合（numpy 解线性方程组即可）refine 圆心
2. 分环: 每个框中心到圆心的距离 → 一维聚类（按距离排序找间隙，或 KMeans）→ 环号 ring
3. 每字定向: 字的预期朝向 = 圆心指向该字的半径方向
   星盘字"头朝外"或"头朝圆心"两种都有 → 两个假设都要试
4. 重识别: 按框 crop（外扩 4px）→ PIL Image.rotate(角度, expand=True, fillcolor=白)
   → PaddleOCR rec 单字识别 → 记录 (角度假设, 识别字, conf)
5. 择优: 原始识别 vs 两种旋转假设，取 conf 最高者；输出对比表
6. 阅读序: 按 (ring, 极角θ) 排序输出，而不是 (x, y)
```

### D.4 验收（实验验收，不设识别率指标）

1. 脚本能对一张测试图完整跑完并打印对比表（原识别 vs 旋转重识别：字/置信度）。
2. `CURVE_REPORT.md` 写清：测试图来源、圆心估计效果、两种头向假设哪种对、置信度提升的字数/总数、失败案例分析、**是否值得接入生产管线的结论与建议参数**。
3. **前置依赖**：需要一张真实星盘图（问用户要，或 `data_work/books/` 下找）。拿不到真图就：用 PIL 自己合成一张"文字沿圆弧排布"的测试图（100×100 画布摆 8 个字绕圈），完成自测，并在报告开头注明"未实测真图，结论待真图验证"。

### D.5 提交

```bash
git add experiments/curve_segment.py experiments/CURVE_REPORT.md
git diff --cached --check && git commit -m "exp(ocr): 星盘曲线字弧线切分原型实验-圆拟合+旋转重识别(方向验证)"
```

### D.6 禁止

- 不改 `src/gujiorc/` 下任何生产文件（这是实验，验证方向后才决定接入）。
- 不伪造识别结果——识别不出的字如实留空，报告里说明（铁律：不得伪造字符）。

---

## 附录：完成后的收尾（最后一个任务做完时执行）

1. `PYTHONPATH=src pytest tests/ -q` 全过。
2. 更新 `ocr/docs/HANDOFF.md`：按文件顶部的交接模板重写"刚完成/进行到一半/下一步"，把本文件状态改为"已完成"。
3. 提交：`git add ocr/docs/HANDOFF.md ocr/docs/TASKS_ENG_GAPS.md && git commit -m "docs(ocr): 工程缺口任务书收尾-HANDOFF更新"`。
