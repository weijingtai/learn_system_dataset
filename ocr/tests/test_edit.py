"""字框编辑操作契约测试（不依赖 PaddleOCR）。

覆盖 `gujiorc.core.edit` 的七个操作与一个诊断：
merge / split / delete / update / create / reflow / undo-redo / diagnose_page。

这批测试的立场：**编辑操作必须守项目数据铁律**——原始 OCR 识别永不销毁。
merge/split 会产生新框、删掉源框，所以每条这类测试都会顺带断言
「源框的完整快照留在 extra.edit.orig_snapshot 里」，否则原始识别就丢了。

另一条被反复断言的是 reflow 的诚实闸门：框数 ≠ 行文本字数时必须**拒绝**，
不许多出来的框凭空造字、也不许把多出来的字悄悄丢掉（铁律：不得伪造字符）。
"""
import os
import sys

import pytest

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import (  # noqa: E402
    CharBox, LineBox, PageResult, STATUS_CORRECTED, STATUS_UNRECOGNIZED,
)
from gujiorc.core import edit  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    """每个测试一个独立 OCR_ROOT，撤销栈落盘互不干扰。"""
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    monkeypatch.delenv("OCR_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("OCR_SOURCE_DIR", raising=False)
    yield tmp_path


def cb(seq: int, y: float, h: float, char: str, x: float = 100, w: float = 40,
       conf: float = 1.0) -> CharBox:
    return CharBox(id=f"page_001c{seq:04d}", box={"x": x, "y": y, "w": w, "h": h},
                   char=char, orig_char=char, conf=conf, extra={"band": 0})


def sanche_page() -> PageResult:
    """复刻真实缺陷：page_001「三辰通載」列的框字错位。

    行文本 '三辰通載'（4 字，conf 1.00，**本身是对的**），行框 y=250 h=288，
    即每字应占 72px。但投影把「三」切成两段（上两横 / 第三横）、又把「通載」
    并成一段，两个错误刚好抵消 → 段数 4 == 字数 4，逃过了「段数==字数」契约，
    实际每个框从第 2 个起都装着下一个字的识别结果。
    """
    chars = [
        cb(0, 263, 24, "三", x=1061, w=88),   # 框内实为 三 的上两横
        cb(1, 298, 9, "辰", x=1061, w=88),    # 框内实为 三 的第三横
        cb(2, 328, 58, "通", x=1061, w=88),   # 框内实为 辰
        cb(3, 399, 131, "載", x=1061, w=88),  # 框内实为 通 + 載 两个字
    ]
    line = LineBox(id="page_001L0", box={"x": 1061, "y": 250, "w": 88, "h": 288},
                   text="三辰通載", conf=1.0)
    return PageResult(page="page_001", image="p1.png", width=1203, height=1654,
                      chars=chars, lines=[line])


def clean_page() -> PageResult:
    """一列 4 字，框与字严格对应、间距均匀（诊断不该报警）。"""
    chars = [cb(i, 250 + 72 * i + 10, 52, ch, x=1061, w=88)
             for i, ch in enumerate("三辰通載")]
    line = LineBox(id="page_001L0", box={"x": 1061, "y": 250, "w": 88, "h": 288},
                   text="三辰通載", conf=1.0)
    return PageResult(page="page_001", image="p1.png", width=1203, height=1654,
                      chars=chars, lines=[line])


# ---------------- merge：一个字被切成两个框 ----------------

def test_merge_geometry_is_union_of_sources():
    """合并「三」的两段：新框须包住 263..307 的全部墨迹。"""
    pr = sanche_page()
    new = edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])
    assert new.box["y"] == 263
    assert new.box["y"] + new.box["h"] == 307      # 298 + 9
    assert new.box["x"] == 1061 and new.box["w"] == 88


def test_merge_removes_sources_and_leaves_one_box():
    pr = sanche_page()
    new = edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])
    ids = [c.id for c in pr.chars]
    assert "page_001c0000" not in ids and "page_001c0001" not in ids
    assert new.id in ids
    assert len(pr.chars) == 3


def test_merge_keeps_full_snapshot_of_sources():
    """数据铁律：源框被删掉了，它们的原始识别必须完整留在新框里。"""
    pr = sanche_page()
    new = edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])
    snap = new.extra["edit"]["orig_snapshot"]
    assert [s["id"] for s in snap] == ["page_001c0000", "page_001c0001"]
    assert [s["orig_char"] for s in snap] == ["三", "辰"]
    # 快照必须含坐标，才能真正回退
    assert snap[0]["box"]["h"] == 24 and snap[1]["box"]["h"] == 9
    assert new.extra["edit"]["op"] == "merge"


def test_merge_default_char_is_concatenation_not_invention():
    """不给字时只做拼接，绝不猜。拼接结果如实写进 orig_char。"""
    pr = sanche_page()
    new = edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])
    assert new.orig_char == "三辰"
    assert new.char == "三辰"
    assert new.mapping is None       # 没有人工改字，不该编造 mapping


def test_merge_with_explicit_char_records_mapping():
    """用户说这两个框其实是一个「二」：char 改、orig_char 留拼接原样。"""
    pr = sanche_page()
    new = edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"], char="二")
    assert new.char == "二"
    assert new.orig_char == "三辰"            # 原始识别不被覆盖
    assert new.mapping["from"] == "三辰"
    assert new.mapping["target"] == "二"
    assert new.mapping["source"] == "manual:merge"
    assert new.status == STATUS_CORRECTED


def test_merge_new_box_takes_reading_order_slot_of_first_source():
    """新框须插在源框原来的位置，否则整页阅读序错乱。"""
    pr = sanche_page()
    edit.merge_boxes(pr, ["page_001c0001", "page_001c0002"])
    # 原顺序 c0000,c0001,c0002,c0003 → 合并 1+2 后新框应在下标 1
    assert pr.chars[0].id == "page_001c0000"
    assert pr.chars[1].extra["edit"]["op"] == "merge"
    assert pr.chars[2].id == "page_001c0003"


def test_merge_requires_two_or_more():
    pr = sanche_page()
    with pytest.raises(ValueError):
        edit.merge_boxes(pr, ["page_001c0000"])


def test_merge_unknown_id_raises_not_silently_skips():
    pr = sanche_page()
    with pytest.raises(KeyError):
        edit.merge_boxes(pr, ["page_001c0000", "page_001c9999"])


# ---------------- split：两个字被并成一个框 ----------------

def test_split_at_coordinate_produces_two_boxes():
    """把「通載」框在 y=466 切开。"""
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", at=[466])
    assert len(parts) == 2
    assert parts[0].box["y"] == 399 and parts[0].box["h"] == 67    # 399..466
    assert parts[1].box["y"] == 466 and parts[1].box["h"] == 64    # 466..530


def test_split_pieces_cover_source_extent_exactly():
    """切出来的段首尾必须严丝合缝盖住原框，不得漏一像素墨迹。"""
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", at=[440, 480])
    assert len(parts) == 3
    assert parts[0].box["y"] == 399
    assert parts[-1].box["y"] + parts[-1].box["h"] == 399 + 131
    for a, b in zip(parts, parts[1:]):
        assert a.box["y"] + a.box["h"] == b.box["y"]


def test_split_into_n_equal_parts():
    """跨两个字位的框，等分 2 份是最常用的快捷操作。"""
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", n=2)
    assert len(parts) == 2
    assert parts[0].box["h"] == pytest.approx(65.5)
    assert parts[1].box["y"] == pytest.approx(464.5)


def test_split_keeps_full_snapshot_of_source():
    """数据铁律：源框被拆没了，它的原始识别必须留在每个碎片里。"""
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", n=2)
    for p in parts:
        e = p.extra["edit"]
        assert e["op"] == "split"
        assert e["from"] == "page_001c0003"
        assert e["orig_snapshot"]["orig_char"] == "載"
        assert e["orig_snapshot"]["box"]["h"] == 131


def test_split_without_chars_marks_unrecognized_not_fabricated():
    """拆开后没人给字 → 如实标未识别，绝不把源框的字复制给两半。"""
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", n=2)
    assert [p.char for p in parts] == ["", ""]
    assert all(p.status == STATUS_UNRECOGNIZED for p in parts)


def test_split_with_chars_assigns_in_order():
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", n=2, chars=["通", "載"])
    assert [p.char for p in parts] == ["通", "載"]
    assert [p.orig_char for p in parts] == ["通", "載"]


def test_split_at_outside_box_raises():
    pr = sanche_page()
    with pytest.raises(ValueError):
        edit.split_box(pr, "page_001c0003", at=[999])


def test_split_n_must_be_at_least_two():
    pr = sanche_page()
    with pytest.raises(ValueError):
        edit.split_box(pr, "page_001c0003", n=1)


def test_split_horizontal_box_cuts_on_x():
    """横排框（w>h）须按 x 切，不能按 y。"""
    pr = sanche_page()
    pr.chars.append(CharBox(id="page_001c0009", box={"x": 10, "y": 20, "w": 100, "h": 30},
                            char="甲乙", orig_char="甲乙"))
    parts = edit.split_box(pr, "page_001c0009", n=2)
    assert parts[0].box["w"] == 50 and parts[1].box["x"] == 60
    assert parts[0].box["h"] == 30 and parts[1].box["h"] == 30


# ---------------- delete / update / create ----------------

def test_delete_removes_only_named_boxes():
    pr = sanche_page()
    edit.delete_boxes(pr, ["page_001c0001"])
    assert [c.id for c in pr.chars] == [
        "page_001c0000", "page_001c0002", "page_001c0003"]


def test_delete_unknown_id_raises():
    pr = sanche_page()
    with pytest.raises(KeyError):
        edit.delete_boxes(pr, ["page_001c9999"])


def test_update_box_geometry_only():
    pr = sanche_page()
    edit.update_box(pr, "page_001c0000", box={"x": 1061, "y": 250, "w": 88, "h": 60})
    c = next(c for c in pr.chars if c.id == "page_001c0000")
    assert c.box["h"] == 60
    assert c.char == "三" and c.orig_char == "三"


def test_update_char_never_overwrites_orig_char():
    """数据铁律的核心断言。"""
    pr = sanche_page()
    edit.update_box(pr, "page_001c0001", char="一")
    c = next(c for c in pr.chars if c.id == "page_001c0001")
    assert c.char == "一"
    assert c.orig_char == "辰"          # 原始识别永不覆盖
    assert c.mapping["from"] == "辰" and c.mapping["target"] == "一"
    assert c.status == STATUS_CORRECTED


def test_create_box_gets_unique_id_after_deletions():
    """删掉尾框再新建，不得撞已用过的号（用 len(chars) 生号就会撞）。"""
    pr = sanche_page()
    edit.delete_boxes(pr, ["page_001c0003"])
    new = edit.create_box(pr, {"x": 0, "y": 0, "w": 10, "h": 10})
    assert new.id != "page_001c0003"
    assert len({c.id for c in pr.chars}) == len(pr.chars)


def test_create_box_inserted_in_reading_order():
    """新框按阅读序（竖排：x 由右至左，列内 y 由上至下）落位。"""
    pr = sanche_page()
    edit.create_box(pr, {"x": 1061, "y": 320, "w": 88, "h": 6})
    ys = [c.box["y"] for c in pr.chars if c.box["x"] == 1061]
    assert ys == sorted(ys)


# ---------------- reflow：第 5 点的关键操作 ----------------

def test_reflow_reassigns_line_text_in_reading_order():
    """几何修好后，一键让文字顺移归位——这就是「三辰通載」的解法。"""
    pr = sanche_page()
    edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])   # 三 的两段并回来
    tail = next(c for c in pr.chars if c.box["h"] == 131)
    edit.split_box(pr, tail.id, n=2)                            # 通載 切开
    ids = [c.id for c in pr.chars]
    assert len(ids) == 4
    edit.reflow(pr, ids)
    assert [c.char for c in pr.chars] == ["三", "辰", "通", "載"]


def test_reflow_refuses_when_more_boxes_than_chars():
    """4 字 5 框 → 必须拒绝。多出来的框不许凭空造字。"""
    pr = sanche_page()
    edit.create_box(pr, {"x": 1061, "y": 540, "w": 88, "h": 20})
    with pytest.raises(ValueError) as e:
        edit.reflow(pr, [c.id for c in pr.chars])
    assert "5" in str(e.value) and "4" in str(e.value)


def test_reflow_refuses_when_fewer_boxes_than_chars():
    """4 字 3 框 → 必须拒绝。不许把第 4 个字悄悄丢掉。"""
    pr = sanche_page()
    edit.delete_boxes(pr, ["page_001c0003"])
    with pytest.raises(ValueError):
        edit.reflow(pr, [c.id for c in pr.chars])


def test_reflow_uses_owning_line_text_when_not_given():
    pr = sanche_page()
    edit.reflow(pr, [c.id for c in pr.chars])
    assert "".join(c.char for c in pr.chars) == "三辰通載"


def test_reflow_accepts_explicit_text():
    pr = sanche_page()
    edit.reflow(pr, [c.id for c in pr.chars], text="甲乙丙丁")
    assert [c.char for c in pr.chars] == ["甲", "乙", "丙", "丁"]


def test_reflow_never_overwrites_orig_char():
    """数据铁律：重灌只改 char，orig_char 保留原来那个错位的识别。"""
    pr = sanche_page()
    edit.reflow(pr, [c.id for c in pr.chars], text="甲乙丙丁")
    assert [c.orig_char for c in pr.chars] == ["三", "辰", "通", "載"]
    assert all(c.mapping and c.mapping["source"] == "manual:reflow" for c in pr.chars)


def test_reflow_unchanged_char_is_not_marked_corrected():
    """重灌后字没变的框不该被标成「已改正」，否则改动统计全是噪声。"""
    pr = sanche_page()
    edit.reflow(pr, [c.id for c in pr.chars], text="三乙丙丁")
    assert pr.chars[0].char == "三"                    # 本来就是「三」，没动
    assert pr.chars[0].status != STATUS_CORRECTED
    assert pr.chars[0].mapping is None
    assert pr.chars[1].status == STATUS_CORRECTED      # 辰 → 乙，动了


def test_reflow_alone_cannot_fix_misalignment_geometry_must_come_first():
    """立此存照：单靠重灌修不了「三辰通載」——必须先修几何。

    这一列的框数已经是 4、行文本也是 4 字，重灌只会把 三辰通載 原样按顺序
    再灌一遍，结果与错位前**一模一样**。因为错的不是文字、是段边界：
    「三」被切成两段、「通載」并成一段，两个错误互相抵消。
    所以正确的修法顺序是 合并 → 拆分 → 重灌，缺一不可。
    """
    pr = sanche_page()
    before = [(c.id, c.char, dict(c.box)) for c in pr.chars]
    edit.reflow(pr, [c.id for c in pr.chars])
    after = [(c.id, c.char, dict(c.box)) for c in pr.chars]
    assert before == after
    # 而诊断依然把它报为疑似错位——说明重灌不是这一类问题的解
    assert edit.diagnose_page(pr) != []


def test_reflow_no_line_and_no_text_raises():
    pr = sanche_page()
    pr.lines = []
    with pytest.raises(ValueError):
        edit.reflow(pr, [c.id for c in pr.chars])


# ---------------- undo / redo ----------------

def test_undo_restores_previous_chars():
    pr = sanche_page()
    edit.push_history(pr)
    edit.delete_boxes(pr, ["page_001c0001"])
    restored = edit.undo(pr)
    assert [c.id for c in restored.chars] == [
        "page_001c0000", "page_001c0001", "page_001c0002", "page_001c0003"]


def test_undo_restores_geometry_and_char_exactly():
    pr = sanche_page()
    edit.push_history(pr)
    edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"], char="二")
    restored = edit.undo(pr)
    c = next(c for c in restored.chars if c.id == "page_001c0001")
    assert c.char == "辰" and c.box["h"] == 9 and c.mapping is None


def test_redo_after_undo():
    pr = sanche_page()
    edit.push_history(pr)
    edit.delete_boxes(pr, ["page_001c0001"])
    pr = edit.undo(pr)
    pr = edit.redo(pr)
    assert "page_001c0001" not in [c.id for c in pr.chars]


def test_undo_on_empty_history_raises():
    pr = sanche_page()
    with pytest.raises(IndexError):
        edit.undo(pr)


def test_redo_cleared_by_new_edit():
    """撤销后又做了新编辑，旧的 redo 分支必须作废（否则会重放到错的状态）。"""
    pr = sanche_page()
    edit.push_history(pr)
    edit.delete_boxes(pr, ["page_001c0001"])
    pr = edit.undo(pr)
    edit.push_history(pr)
    edit.delete_boxes(pr, ["page_001c0002"])
    with pytest.raises(IndexError):
        edit.redo(pr)


def test_history_is_bounded():
    pr = sanche_page()
    for i in range(edit.HISTORY_LIMIT + 10):
        edit.push_history(pr)
    assert edit.history_depth(pr.page)["undo"] == edit.HISTORY_LIMIT


def test_history_is_per_page():
    pr = sanche_page()
    edit.push_history(pr)
    other = sanche_page()
    other.page = "page_002"
    assert edit.history_depth("page_002")["undo"] == 0
    assert edit.history_depth("page_001")["undo"] == 1


# ---------------- diagnose_page：把第 5 点这类行自动找出来 ----------------

def test_diagnose_flags_the_sanche_misalignment():
    """真实缺陷必须被报出来，且指出是哪几个框有问题。"""
    pr = sanche_page()
    issues = edit.diagnose_page(pr)
    assert len(issues) == 1
    it = issues[0]
    assert it["line_id"] == "page_001L0"
    assert it["text"] == "三辰通載"
    assert it["pitch"] == pytest.approx(72.0)
    kinds = {f["kind"] for f in it["flags"]}
    assert "over" in kinds       # 載 框 h=131 跨了两个字位
    assert "thin" in kinds       # 辰 框 h=9 只是一条横
    assert "drift" in kinds      # 框心整体偏离应有字位


def test_diagnose_reports_expected_vs_actual_per_box():
    """诊断要能直接告诉人「这个框该装第几个字」，不然还是要肉眼数。"""
    pr = sanche_page()
    it = edit.diagnose_page(pr)[0]
    rows = {r["id"]: r for r in it["boxes"]}
    assert rows["page_001c0002"]["char"] == "通"
    assert rows["page_001c0002"]["slot"] == 2          # 它占的是第 2 个字位
    assert rows["page_001c0002"]["index"] == 3         # 却拿到了第 3 个字
    assert rows["page_001c0002"]["shifted"] is True
    assert rows["page_001c0003"]["spans"] >= 2         # 它跨了 ≥2 个字位


def test_diagnose_expect_char_comes_from_geometry_not_position():
    """`expect_char` 必须由「框落在哪个字位」算出，否则它恒等于现有 char。

    切分层本来就是按位置配字的，所以拿 text[i] 当「应为」等于用错误答案
    当标准答案，这一列永远看不出问题。必须用 text[框实际所在字位]。
    """
    pr = sanche_page()
    rows = {r["id"]: r for r in edit.diagnose_page(pr)[0]["boxes"]}
    # c0002 的框落在第 2 字位，几何上那里该是「辰」，但它拿的是「通」
    assert rows["page_001c0002"]["expect_char"] == "辰"
    assert rows["page_001c0002"]["char"] == "通"
    assert any(r["expect_char"] != r["char"] for r in rows.values())


def test_diagnose_does_not_flag_a_clean_line():
    assert edit.diagnose_page(clean_page()) == []


def test_diagnose_skips_line_when_box_count_differs_from_text():
    """框数≠字数是另一类问题（已由切分层保证不发生），诊断不该在这里误报。"""
    pr = sanche_page()
    edit.delete_boxes(pr, ["page_001c0003"])
    assert edit.diagnose_page(pr) == []


def test_diagnose_ignores_single_char_lines():
    pr = sanche_page()
    pr.lines[0].text = "三"
    pr.chars = pr.chars[:1]
    assert edit.diagnose_page(pr) == []


# ---------------- 未识别框的诚实性（存盘往返不得伪造原始识别）----------------

def test_empty_orig_char_survives_roundtrip_not_backfilled_from_char():
    """拆出来的框如实标「未识别」，人工填字后**不得**把人工填的字冒充成 OCR 原始识别。

    `CharBox.from_dict` 有一条向后兼容兜底（旧数据无 orig_char → 用 char 顶上）。
    它必须只对「字段缺失」生效，不能对「字段存在但故意为空」生效——否则
    split 出的空框一旦被 reflow/改字填上，存盘再读就变成「OCR 原本就认得这个字」，
    审计链上再也分不清哪个字是机器认的、哪个是人填的。
    """
    from gujiorc.core.models import CharBox
    c = CharBox(id="page_001c0035", box={"x": 0, "y": 0, "w": 10, "h": 10})
    c.set_char("通", mapping_source="manual:reflow")
    assert c.orig_char == ""                       # 内存里就该是空
    back = CharBox.from_dict(c.to_dict())
    assert back.orig_char == "", "存盘往返把人工填的字冒充成了原始识别"
    assert back.char == "通"
    assert back.mapping["from"] == ""              # 原本什么都没认出来


def test_legacy_dict_without_orig_char_still_backfills():
    """向后兼容不能丢：真正的旧数据（根本没有 orig_char 这个键）仍要用 char 兜底。"""
    from gujiorc.core.models import CharBox
    legacy = {"id": "page_001c0000", "box": {"x": 0, "y": 0, "w": 10, "h": 10}, "char": "三"}
    assert CharBox.from_dict(legacy).orig_char == "三"


def test_split_then_reflow_keeps_orig_char_empty_through_storage(tmp_path):
    """整条链路（拆分 → 重灌 → 存盘 → 读回）都不得伪造 orig_char。"""
    from gujiorc.core.storage import load_page_json, save_page_json
    pr = sanche_page()
    parts = edit.split_box(pr, "page_001c0003", n=2)
    assert [p.orig_char for p in parts] == ["", ""]
    edit.merge_boxes(pr, ["page_001c0000", "page_001c0001"])
    edit.reflow(pr, [c.id for c in pr.chars])
    save_page_json(pr)
    got = {c.id: c for c in load_page_json("page_001").chars}
    for p in parts:
        assert got[p.id].char in ("通", "載")
        assert got[p.id].orig_char == "", f"{p.id} 的原始识别被人工填的字覆盖了"
