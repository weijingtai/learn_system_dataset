"""gujiorc.core.edit — 字框编辑操作（Web UI 人工校对的后端）。

七个操作 + 一个诊断，全部是纯函数（只吃 `PageResult`、不碰 HTTP），便于测试：

    merge_boxes   一个字被切成多个框 → 并回一个（如「二」被切成两个「一」）
    split_box     多个字被并进一个框 → 切开（如「八二」的下横被并进「八」）
    delete_boxes  删框
    update_box    改框几何 / 改框内字
    create_box    补标一个框
    reflow        按行文本重灌文字到框（几何修好后让文字顺移归位）
    undo / redo   基于整页 chars 快照的撤销栈（落盘，跨进程可用）
    diagnose_page 找出「框数==字数但框↔字错位」的行

数据铁律（`models.CharBox` 的类文档）：**原始 OCR 识别永不覆盖销毁**。
merge/split 会删掉源框，所以它们把源框的**完整快照**写进新框的
`extra.edit.orig_snapshot`；改字一律走 `set_char()`，只改 `char` + `mapping`。

为什么需要 `reflow`：PaddleOCR 给的是整行文本，段边界是沿投影另算的。
当「一个字被切成两段」和「两个字并成一段」在同一行内同时发生时，
段数与字数刚好相等，切分层的「段数==字数」契约察觉不到，但从错位处起
每个框都装着下一个字的识别结果。此时行文本本身是对的，只有几何错了——
所以正确的修法是「先修几何，再让文字按阅读序重灌」，而不是逐框改字。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .models import (
    CharBox, PageResult, STATUS_CORRECTED, STATUS_PENDING, STATUS_UNRECOGNIZED,
)
from .paths import ensure_struct

# 撤销栈上限。每格是一页 chars 的快照（数百字 ≈ 100KB 量级），50 格足够一轮人工校对。
HISTORY_LIMIT = 50

# ── diagnose_page 的三个信号阈值 ──────────────────────────────────────
# pitch = 行长 / 字数，即「每字应占多少像素」。
# 一个框比一个字位还大 1.6 倍 → 它多半跨了两个字位（「通載」并成一框）。
OVER_PITCH = 1.6
# 一个框不到字位的 1/4 → 它多半只是一条笔画（「三」的单横被当成一个字）。
THIN_PITCH = 0.25
# 框心偏离它「应该在」的字位中心超过 0.6 个字位 → 该框装的不是它位置上的那个字。
# 这一项才是真正抓错位的：over/thin 只说明框的尺寸怪，drift 说明字被移了位。
DRIFT_PITCH = 0.6


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── id 生成 ────────────────────────────────────────────────────────────

def _seed_seq(pr: PageResult) -> None:
    """把 id 水位线抬到「不低于现有框的最大序号 + 1」。

    每个会改动 chars 的操作入口都要先叫一次，尤其是 `delete_boxes`：
    删掉尾框**之后**再算水位就看不到它了，新建框会重新发出刚删掉的号，
    撤销把旧框恢复回来即出现重号。
    """
    prefix = f"{pr.page}c"
    seq = int(pr.extra.get("next_seq", 0))
    for c in pr.chars:
        if c.id.startswith(prefix):
            tail = c.id[len(prefix):]
            if tail.isdigit():
                seq = max(seq, int(tail) + 1)
    pr.extra["next_seq"] = seq


def _next_id(pr: PageResult) -> str:
    """发一个新框 id，取页级单调水位线 `extra.next_seq`，只增不回退。

    水位线存在 `pr.extra` 里，而撤销快照只存 `chars`（见 `push_history`），
    所以撤销不会把它拨回去——恢复出来的旧框与后来新建的框永不重号。
    """
    _seed_seq(pr)
    prefix = f"{pr.page}c"
    seq = int(pr.extra["next_seq"])
    existing = {c.id for c in pr.chars}
    while f"{prefix}{seq:04d}" in existing:
        seq += 1
    pr.extra["next_seq"] = seq + 1
    return f"{prefix}{seq:04d}"


def _pick(pr: PageResult, ids: Iterable[str]) -> list[tuple[int, CharBox]]:
    """按给定 id 取框，返回 [(下标, 框)]，保持页内原顺序。id 不存在则报错。"""
    index = {c.id: i for i, c in enumerate(pr.chars)}
    out = []
    for cid in ids:
        if cid not in index:
            raise KeyError(f"字框 {cid} 不存在于 {pr.page}")
        out.append((index[cid], pr.chars[index[cid]]))
    out.sort(key=lambda t: t[0])
    return out


def _is_vertical(box: dict) -> bool:
    return float(box["h"]) >= float(box["w"])


# ── merge ─────────────────────────────────────────────────────────────

def merge_boxes(pr: PageResult, ids: list[str], char: Optional[str] = None) -> CharBox:
    """把多个框合并成一个（几何取并集）。用于「一个字被切成了多个框」。

    `char=None` 时新框的字是各源框字的**拼接**（不猜、不重识别）；
    给了 `char` 则视为人工改正，`orig_char` 仍保留拼接结果，改动记进 `mapping`。
    源框的完整快照写进 `extra.edit.orig_snapshot`（数据铁律：原始识别不销毁）。
    """
    if len(ids) < 2:
        raise ValueError(f"合并至少需要 2 个框，收到 {len(ids)} 个")
    _seed_seq(pr)      # 必须在删源框之前，否则新框会重用源框的号
    picked = _pick(pr, ids)
    slot = picked[0][0]
    srcs = [c for _, c in picked]

    x0 = min(c.box["x"] for c in srcs)
    y0 = min(c.box["y"] for c in srcs)
    x1 = max(c.box["x"] + c.box["w"] for c in srcs)
    y1 = max(c.box["y"] + c.box["h"] for c in srcs)

    joined = "".join(c.orig_char or c.char for c in srcs)
    new = CharBox(
        id=_next_id(pr),
        box={"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
        char=joined,
        orig_char=joined,
        conf=min((c.conf for c in srcs), default=0.0),
        source="manual",
        status=STATUS_PENDING if joined else STATUS_UNRECOGNIZED,
        parent=srcs[0].parent,
        extra={
            **{k: v for k, v in (srcs[0].extra or {}).items() if k != "edit"},
            "edit": {
                "op": "merge",
                "from": [c.id for c in srcs],
                "orig_snapshot": [c.to_dict() for c in srcs],
                "ts": _now(),
            },
        },
    )
    if char is not None and char != joined:
        new.set_char(char, mapping_source="manual:merge")

    for i, _ in reversed(picked):
        del pr.chars[i]
    pr.chars.insert(slot, new)
    return new


# ── split ─────────────────────────────────────────────────────────────

def split_box(pr: PageResult, cid: str, *, at: Optional[list[float]] = None,
              n: int = 0, chars: Optional[list[str]] = None) -> list[CharBox]:
    """把一个框切成多个。用于「多个字被并进了一个框」。

    切向由框自身决定：竖排框（h>=w）按 y 切，横排框按 x 切。
    `at` 给绝对坐标切线（可多条）；`n` 给等分份数。二者择一。
    `chars` 按顺序给各段的字；不给则如实标 `unrecognized`——**绝不把源框的字
    复制给每一段**，那是伪造。
    """
    _seed_seq(pr)      # 必须在删源框之前，否则第一个碎片会重用源框的号
    picked = _pick(pr, [cid])
    slot, src = picked[0]
    vertical = _is_vertical(src.box)
    pos, size = ("y", "h") if vertical else ("x", "w")
    lo = float(src.box[pos])
    hi = lo + float(src.box[size])

    if at:
        cuts = sorted(float(a) for a in at)
        for a in cuts:
            if not lo < a < hi:
                raise ValueError(f"切线 {a} 不在框 {cid} 的 [{lo}, {hi}] 范围内")
    elif n:
        if n < 2:
            raise ValueError(f"等分份数须 >= 2，收到 {n}")
        step = (hi - lo) / n
        cuts = [lo + step * (i + 1) for i in range(n - 1)]
    else:
        raise ValueError("需要 at（切线坐标）或 n（等分份数）之一")

    bounds = [lo, *cuts, hi]
    snapshot = src.to_dict()
    parts: list[CharBox] = []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        ch = (chars[i] if chars and i < len(chars) else "")
        box = dict(src.box)
        box[pos] = a
        box[size] = b - a
        parts.append(CharBox(
            id="",   # 占位，源框删掉后统一发号（水位线已在函数开头抬过）
            box=box, char=ch, orig_char=ch,
            conf=src.conf if ch else 0.0,
            source="manual",
            status=STATUS_CORRECTED if ch else STATUS_UNRECOGNIZED,
            parent=src.parent,
            extra={
                **{k: v for k, v in (src.extra or {}).items() if k != "edit"},
                "edit": {"op": "split", "from": cid,
                         "orig_snapshot": snapshot, "ts": _now()},
            },
        ))

    del pr.chars[slot]
    for i, p in enumerate(parts):
        p.id = _next_id(pr)
        pr.chars.insert(slot + i, p)
    return parts


# ── delete / update / create ──────────────────────────────────────────

def delete_boxes(pr: PageResult, ids: list[str]) -> list[dict]:
    """删框，返回被删框的完整快照（调用方可写审计日志）。"""
    _seed_seq(pr)      # 必须在删之前，否则被删的号会被重新发出去
    picked = _pick(pr, ids)
    removed = [c.to_dict() for _, c in picked]
    for i, _ in reversed(picked):
        del pr.chars[i]
    return removed


def update_box(pr: PageResult, cid: str, *, box: Optional[dict] = None,
               char: Optional[str] = None) -> CharBox:
    """改一个框的几何和/或字。改字走 `set_char`，`orig_char` 永不覆盖。"""
    _, c = _pick(pr, [cid])[0]
    if box is not None:
        c.box = {k: float(box[k]) for k in ("x", "y", "w", "h")}
    if char is not None and char != c.char:
        c.set_char(char, mapping_source="manual")
    return c


def create_box(pr: PageResult, box: dict, char: str = "") -> CharBox:
    """补标一个框，按阅读序（竖排：x 由右至左、列内 y 由上至下）插入。"""
    new = CharBox(
        id=_next_id(pr),
        box={k: float(box[k]) for k in ("x", "y", "w", "h")},
        char=char, orig_char=char, conf=0.0, source="manual",
        status=STATUS_CORRECTED if char else STATUS_UNRECOGNIZED,
    )
    # 落位：找同列（x 接近）里第一个 y 比它大的框，插在其前；找不到就追加。
    slot = len(pr.chars)
    for i, c in enumerate(pr.chars):
        same_col = abs(c.box["x"] - new.box["x"]) < max(new.box["w"], 1) * 0.8
        if same_col and c.box["y"] > new.box["y"]:
            slot = i
            break
    pr.chars.insert(slot, new)
    return new


# ── reflow ────────────────────────────────────────────────────────────

def _line_of(pr: PageResult, boxes: list[CharBox]):
    """找这批框所属的行：按「框心落在行内」的命中数投票，取命中最多的行。

    不要求行**完整包住**这批框的外接矩形——那样一个稍微出界的框（比如用户
    多选进来一个补标框）就会让 reflow 报「找不到行」，把真正该报的
    「框数≠字数」错误挡在后面。投票法只要多数框在行内就能定位，
    数量校验交给 `reflow` 自己的诚实闸门。
    """
    if not boxes or not pr.lines:
        return None
    best, best_hits = None, 0
    for ln in pr.lines:
        lb = ln.box
        hits = sum(
            1 for c in boxes
            if lb["x"] - 2 <= c.box["x"] + c.box["w"] / 2 <= lb["x"] + lb["w"] + 2
            and lb["y"] - 2 <= c.box["y"] + c.box["h"] / 2 <= lb["y"] + lb["h"] + 2
        )
        # 同命中数时取面积小的行（列嵌套时更精确）
        if hits > best_hits or (hits == best_hits and hits > 0 and best is not None
                                and lb["w"] * lb["h"] < best.box["w"] * best.box["h"]):
            best, best_hits = ln, hits
    return best if best_hits else None


def reading_order(boxes: list[CharBox], vertical: Optional[bool] = None) -> list[CharBox]:
    """按阅读序排：竖排为列内 y 由上至下；横排为 x 由左至右。"""
    if vertical is None:
        vertical = all(_is_vertical(c.box) for c in boxes) or len(boxes) < 2
    key = (lambda c: (round(-c.box["x"] / 8), c.box["y"])) if vertical \
        else (lambda c: (round(c.box["y"] / 8), c.box["x"]))
    return sorted(boxes, key=key)


def reflow(pr: PageResult, ids: list[str], text: Optional[str] = None) -> list[CharBox]:
    """把 `text` 按阅读序重灌到这批框上。这是「框对了字错位」的正解。

    诚实闸门：框数必须**恰好等于** text 字数，否则拒绝。多一个框就会凭空造字，
    少一个框就会悄悄丢字，两者都违反铁律（不得伪造字符 / 不静默丢弃）。
    `text=None` 时取这批框所属行的识别文本（那是对的，错的只是几何）。
    """
    boxes = [c for _, c in _pick(pr, ids)]
    if text is None:
        line = _line_of(pr, boxes)
        if line is None or not line.text:
            raise ValueError("这批框找不到所属行（或行文本为空），请显式给出 text")
        text = line.text
    if len(boxes) != len(text):
        raise ValueError(
            f"框数与字数不符：{len(boxes)} 个框 vs {len(text)} 个字（{text!r}）。"
            f"请先用合并/拆分把几何修到框数=字数，再重灌。"
        )
    ordered = reading_order(boxes)
    for c, ch in zip(ordered, text):
        if c.char != ch:
            c.set_char(ch, mapping_source="manual:reflow")
    return ordered


# ── undo / redo ───────────────────────────────────────────────────────

def _hist_path(page: str):
    d = ensure_struct()["logs"] / "edit_history"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{page}.json"


def _load_hist(page: str) -> dict[str, list]:
    p = _hist_path(page)
    if not p.exists():
        return {"undo": [], "redo": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"undo": d.get("undo", []), "redo": d.get("redo", [])}
    except (OSError, json.JSONDecodeError):
        return {"undo": [], "redo": []}


def _save_hist(page: str, hist: dict[str, list]):
    p = _hist_path(page)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def push_history(pr: PageResult):
    """在改动**之前**调用，把当前 chars 压入撤销栈，并作废 redo 分支。

    作废 redo 是必须的：撤销后又做了别的编辑，原来的重做目标已经不在这条
    历史线上了，重放会得到一个从未存在过的状态。
    """
    hist = _load_hist(pr.page)
    hist["undo"].append([c.to_dict() for c in pr.chars])
    if len(hist["undo"]) > HISTORY_LIMIT:
        hist["undo"] = hist["undo"][-HISTORY_LIMIT:]
    hist["redo"] = []
    _save_hist(pr.page, hist)


def undo(pr: PageResult) -> PageResult:
    """回到上一个快照。当前状态压入 redo 栈。就地改 `pr` 并返回它。"""
    hist = _load_hist(pr.page)
    if not hist["undo"]:
        raise IndexError(f"{pr.page} 没有可撤销的编辑")
    hist["redo"].append([c.to_dict() for c in pr.chars])
    snap = hist["undo"].pop()
    pr.chars = [CharBox.from_dict(d) for d in snap]
    _save_hist(pr.page, hist)
    return pr


def redo(pr: PageResult) -> PageResult:
    hist = _load_hist(pr.page)
    if not hist["redo"]:
        raise IndexError(f"{pr.page} 没有可重做的编辑")
    hist["undo"].append([c.to_dict() for c in pr.chars])
    snap = hist["redo"].pop()
    pr.chars = [CharBox.from_dict(d) for d in snap]
    _save_hist(pr.page, hist)
    return pr


def history_depth(page: str) -> dict[str, int]:
    h = _load_hist(page)
    return {"undo": len(h["undo"]), "redo": len(h["redo"])}


# ── diagnose_page ─────────────────────────────────────────────────────

def diagnose_page(pr: PageResult) -> list[dict[str, Any]]:
    """找出「框数==字数但框↔字错位」的行。

    只看几何：把行长按字数等分成若干「字位」，逐框比对它的尺寸和位置。
    三个信号（阈值见模块顶部常量）：
      over  框比一个字位大得多 → 一个框跨了多个字（如「通載」并成一框）
      thin  框比一个字位小得多 → 一个框只装了一条笔画（如「三」的单横）
      drift 框心偏离它应在的字位 → 从这里起文字被整体移了位

    只报告、不改数据。框数≠字数的行跳过（那是另一类问题，由切分层的
    「段数==字数」契约保证不发生），单字行跳过。
    """
    issues: list[dict[str, Any]] = []
    for line in pr.lines:
        text = line.text or ""
        n = len(text)
        if n < 2:
            continue
        lb = line.box
        vertical = _is_vertical(lb)
        pos, size = ("y", "h") if vertical else ("x", "w")
        inside = [
            c for c in pr.chars
            if c.box["x"] >= lb["x"] - 2
            and c.box["x"] + c.box["w"] <= lb["x"] + lb["w"] + 2
            and c.box["y"] >= lb["y"] - 2
            and c.box["y"] + c.box["h"] <= lb["y"] + lb["h"] + 2
        ]
        if len(inside) != n:
            continue
        ordered = reading_order(inside, vertical)
        pitch = float(lb[size]) / n
        if pitch <= 0:
            continue

        flags: list[dict[str, Any]] = []
        rows: list[dict[str, Any]] = []
        for i, c in enumerate(ordered):
            ext = float(c.box[size])
            center = float(c.box[pos]) + ext / 2
            slot_center = float(lb[pos]) + pitch * (i + 0.5)
            drift = (center - slot_center) / pitch
            spans = max(1, round(ext / pitch))
            # 该框实际落在第几个字位（1-based，便于人读）
            actual_slot = int((center - float(lb[pos])) // pitch) + 1
            actual_slot = max(1, min(n, actual_slot))
            rows.append({
                "id": c.id, "char": c.char, "orig_char": c.orig_char,
                # 按几何该装的字 = 它实际所在字位上的那个字。
                # 不能写 text[i]（它恒等于该框现有的 char，因为切分层就是按位置
                # 配字的），那样这一列永远看不出错，等于没诊断。
                "expect_char": text[actual_slot - 1],
                "index": i + 1, "slot": actual_slot,
                "shifted": actual_slot != i + 1,
                "size": round(ext, 1), "spans": spans, "drift": round(drift, 2),
            })
            if ext > OVER_PITCH * pitch:
                flags.append({"kind": "over", "id": c.id,
                              "note": f"框长 {ext:.0f} 约为字位 {pitch:.0f} 的 {ext/pitch:.1f} 倍"})
            if ext < THIN_PITCH * pitch:
                flags.append({"kind": "thin", "id": c.id,
                              "note": f"框长 {ext:.0f} 不足字位 {pitch:.0f} 的 1/4"})
            if abs(drift) > DRIFT_PITCH:
                flags.append({"kind": "drift", "id": c.id,
                              "note": f"框心偏离第 {i+1} 字位 {drift:+.1f} 个字位"})

        # thin 单独出现常是「一」「二」这类字本身就矮，不算错位；
        # 要有 over（跨字）或 drift（移位）才判定为疑似。
        if any(f["kind"] in ("over", "drift") for f in flags):
            issues.append({
                "line_id": line.id, "text": text, "box": dict(lb),
                "pitch": round(pitch, 1), "vertical": vertical,
                "flags": flags, "boxes": rows,
            })
    return issues
