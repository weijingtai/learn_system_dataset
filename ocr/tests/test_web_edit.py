"""Web UI 编辑 API 端到端测试（不依赖 PaddleOCR，不碰生产数据）。

每个测试在 tmp_path 里造一份最小页数据，起 FastAPI TestClient 打真实 HTTP。
重点覆盖三件事：

1. **编辑即保存**：每个操作调完，磁盘上的 JSON 必须已经变了（不存在「未保存」态）。
2. **撤销跨请求可用**：撤销栈落盘，不依赖前端内存，刷新页面照样能 Cmd+Z。
3. **第 5 点的整条修复链**：合并 → 拆分 → 重灌，走 HTTP 打通。
"""
import json
import os
import sys

import pytest

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "local")))

from fastapi.testclient import TestClient  # noqa: E402

from gujiorc.core.models import CharBox, LineBox, PageResult  # noqa: E402


PAGE = "page_001"


def build_page() -> PageResult:
    """真实缺陷的最小复刻：page_001「三辰通載」列（见 test_edit.py 的说明）。"""
    chars = [
        CharBox(id=f"{PAGE}c0000", box={"x": 1061, "y": 263, "w": 88, "h": 24},
                char="三", orig_char="三", conf=1.0),
        CharBox(id=f"{PAGE}c0001", box={"x": 1061, "y": 298, "w": 88, "h": 9},
                char="辰", orig_char="辰", conf=1.0),
        CharBox(id=f"{PAGE}c0002", box={"x": 1061, "y": 328, "w": 88, "h": 58},
                char="通", orig_char="通", conf=1.0),
        CharBox(id=f"{PAGE}c0003", box={"x": 1061, "y": 399, "w": 88, "h": 131},
                char="載", orig_char="載", conf=1.0),
    ]
    line = LineBox(id=f"{PAGE}L0", box={"x": 1061, "y": 250, "w": 88, "h": 288},
                   text="三辰通載", conf=1.0)
    return PageResult(page=PAGE, image="p1.png", width=1203, height=1654,
                      chars=chars, lines=[line])


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    monkeypatch.delenv("OCR_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("OCR_SOURCE_DIR", raising=False)
    from gujiorc.core.storage import save_page_json
    from gujiorc.rare.detector import build_common_set, detect_rare_chars
    pr = build_page()
    # 跟生产管线一致：存页前先算生僻字标记。否则 is_rare 这类**派生**字段
    # 在初始文件里是 false，而任何编辑后接口都会重算成 true，
    # 「撤销回原状」的逐字节比对就会假红。
    detect_rare_chars(pr, build_common_set())
    save_page_json(pr)
    import app as web_app
    return TestClient(web_app.create_app(str(tmp_path))), tmp_path


def on_disk(root) -> dict:
    return json.loads((root / "data" / f"{PAGE}.json").read_text(encoding="utf-8"))


def chars_of(root) -> dict[str, dict]:
    return {c["id"]: c for c in on_disk(root)["chars"]}


def editable_snapshot(root) -> list[tuple]:
    """人工编辑真正该被撤销恢复的那部分状态（含顺序）。

    不能拿整段 JSON 字符串比：撤销时字框经 `parse_box` 走一遍 float()，
    磁盘上 `"h": 24` 会变成 `"h": 24.0`——值完全相等但字符串不同，
    逐字节比对会假红。`is_rare` 之类派生标记同理，由接口每次重算。
    """
    return [(c["id"], c["char"], c["orig_char"], c["status"],
             tuple(float(c["box"][k]) for k in ("x", "y", "w", "h")))
            for c in on_disk(root)["chars"]]


# ---------------- 编辑即保存 ----------------

def test_merge_writes_through(client):
    c, root = client
    r = c.post(f"/api/page/{PAGE}/edit/merge",
               json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"]})
    assert r.status_code == 200
    new_id = r.json()["id"]
    disk = chars_of(root)
    assert f"{PAGE}c0000" not in disk and f"{PAGE}c0001" not in disk
    assert disk[new_id]["box"]["y"] == 263
    assert disk[new_id]["box"]["h"] == 44          # 263..307
    assert disk[new_id]["orig_char"] == "三辰"      # 铁律：原始识别拼接保留
    assert disk[new_id]["extra"]["edit"]["op"] == "merge"


def test_split_writes_through(client):
    c, root = client
    r = c.post(f"/api/page/{PAGE}/edit/split", json={"id": f"{PAGE}c0003", "n": 2})
    assert r.status_code == 200
    ids = r.json()["ids"]
    disk = chars_of(root)
    assert len(ids) == 2 and all(i in disk for i in ids)
    assert f"{PAGE}c0003" not in disk
    # 两段严丝合缝盖住原框 399..530
    a, b = disk[ids[0]]["box"], disk[ids[1]]["box"]
    assert a["y"] == 399 and a["y"] + a["h"] == b["y"]
    assert b["y"] + b["h"] == 530
    # 拆出来的框如实标未识别，不复制源框的字
    assert [disk[i]["char"] for i in ids] == ["", ""]
    assert all(disk[i]["status"] == "unrecognized" for i in ids)


def test_delete_writes_through_and_logs_snapshot(client):
    c, root = client
    r = c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0001"]})
    assert r.status_code == 200
    assert f"{PAGE}c0001" not in chars_of(root)
    # 删掉的框必须还能从审计日志里查回来（铁律：不静默销毁）
    audit = (root / "logs" / "audit.jsonl").read_text(encoding="utf-8")
    assert "辰" in audit and "delete" in audit


def test_update_char_writes_through_keeping_orig(client):
    c, root = client
    r = c.post(f"/api/page/{PAGE}/edit/update",
               json={"id": f"{PAGE}c0001", "char": "一"})
    assert r.status_code == 200
    d = chars_of(root)[f"{PAGE}c0001"]
    assert d["char"] == "一" and d["orig_char"] == "辰"
    assert d["status"] == "corrected"


def test_create_writes_through(client):
    c, root = client
    r = c.post(f"/api/page/{PAGE}/edit/create",
               json={"box": {"x": 1061, "y": 540, "w": 88, "h": 20}, "char": "甲"})
    assert r.status_code == 200
    assert chars_of(root)[r.json()["id"]]["char"] == "甲"


def test_every_edit_returns_full_char_list(client):
    """前端整体替换即可，不必自己算增量。"""
    c, _ = client
    r = c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0001"]})
    assert len(r.json()["chars"]) == 3
    assert all("box" in ch and "char" in ch for ch in r.json()["chars"])


# ---------------- 撤销 / 重做 ----------------

def test_undo_restores_state_across_requests(client):
    """撤销栈落盘：刷新页面（新请求）照样能 Cmd+Z。"""
    c, root = client
    c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0001"]})
    assert c.get(f"/api/page/{PAGE}/edit/history").json()["undo"] == 1
    r = c.post(f"/api/page/{PAGE}/edit/undo")
    assert r.status_code == 200
    disk = chars_of(root)
    assert disk[f"{PAGE}c0001"]["char"] == "辰"
    assert disk[f"{PAGE}c0001"]["box"]["h"] == 9


def test_undo_then_redo(client):
    c, root = client
    c.post(f"/api/page/{PAGE}/edit/merge",
           json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"], "char": "二"})
    c.post(f"/api/page/{PAGE}/edit/undo")
    assert f"{PAGE}c0000" in chars_of(root)
    r = c.post(f"/api/page/{PAGE}/edit/redo")
    assert r.status_code == 200
    assert f"{PAGE}c0000" not in chars_of(root)


def test_undo_with_nothing_to_undo_returns_409_not_500(client):
    c, _ = client
    assert c.post(f"/api/page/{PAGE}/edit/undo").status_code == 409


def test_multi_step_undo_walks_back_one_step_at_a_time(client):
    c, root = client
    c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0001"]})
    c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0002"]})
    assert len(chars_of(root)) == 2
    c.post(f"/api/page/{PAGE}/edit/undo")
    assert len(chars_of(root)) == 3
    c.post(f"/api/page/{PAGE}/edit/undo")
    assert len(chars_of(root)) == 4


def test_reused_id_cannot_appear_after_delete_create_undo(client):
    """删尾框 → 新建 → 撤销：不得出现两个同 id 的框。"""
    c, root = client
    c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0003"]})
    new_id = c.post(f"/api/page/{PAGE}/edit/create",
                    json={"box": {"x": 0, "y": 0, "w": 9, "h": 9}}).json()["id"]
    assert new_id != f"{PAGE}c0003"
    c.post(f"/api/page/{PAGE}/edit/undo")     # 撤销新建
    c.post(f"/api/page/{PAGE}/edit/undo")     # 撤销删除
    ids = [ch["id"] for ch in on_disk(root)["chars"]]
    assert len(ids) == len(set(ids))


# ---------------- reflow 的诚实闸门 ----------------

def test_reflow_rejects_count_mismatch_with_actionable_message(client):
    """框数≠字数 → 400，且信息里要说清差多少、下一步该干什么。"""
    c, _ = client
    c.post(f"/api/page/{PAGE}/edit/create",
           json={"box": {"x": 1061, "y": 505, "w": 88, "h": 20}})
    ids = [f"{PAGE}c{i:04d}" for i in range(4)] + [f"{PAGE}c0004"]
    r = c.post(f"/api/page/{PAGE}/edit/reflow", json={"ids": ids})
    assert r.status_code == 400
    msg = r.json()["detail"]
    assert "5" in msg and "4" in msg
    assert "合并" in msg or "拆分" in msg      # 要告诉人怎么办


def test_reflow_does_not_touch_data_when_rejected(client):
    """闸门拦下时不得留下半个改动。"""
    c, root = client
    before = editable_snapshot(root)
    c.post(f"/api/page/{PAGE}/edit/reflow",
           json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"], "text": "三辰通載"})
    assert editable_snapshot(root) == before


def test_rejected_request_leaves_no_undo_entry(client):
    """被闸门拒绝的请求不得在撤销栈留「空一格」——
    否则用户按一次 Cmd+Z 毫无反应，再按一次才真正回退，撤销像坏了。"""
    c, _ = client
    r = c.post(f"/api/page/{PAGE}/edit/reflow",
               json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"], "text": "三辰通載"})
    assert r.status_code == 400
    assert c.get(f"/api/page/{PAGE}/edit/history").json() == {"undo": 0, "redo": 0}
    # 合法操作照常压栈
    c.post(f"/api/page/{PAGE}/edit/delete", json={"ids": [f"{PAGE}c0002"]})
    assert c.get(f"/api/page/{PAGE}/edit/history").json()["undo"] == 1


# ---------------- 第 5 点：整条修复链走 HTTP ----------------

def test_three_step_repair_of_the_sanche_column(client):
    """合并「三」的两段 → 拆开「通載」 → 按行文本重灌，四个字各归其位。"""
    c, root = client

    r1 = c.post(f"/api/page/{PAGE}/edit/merge",
                json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"]})
    assert r1.status_code == 200

    r2 = c.post(f"/api/page/{PAGE}/edit/split", json={"id": f"{PAGE}c0003", "n": 2})
    assert r2.status_code == 200

    ids = [ch["id"] for ch in sorted(on_disk(root)["chars"],
                                     key=lambda ch: ch["box"]["y"])]
    assert len(ids) == 4
    r3 = c.post(f"/api/page/{PAGE}/edit/reflow", json={"ids": ids})
    assert r3.status_code == 200
    assert r3.json()["text"] == "三辰通載"

    disk = chars_of(root)
    ordered = sorted(disk.values(), key=lambda ch: ch["box"]["y"])
    assert [ch["char"] for ch in ordered] == ["三", "辰", "通", "載"]
    # 修完诊断必须不再报警
    assert c.get(f"/api/page/{PAGE}/misaligned").json()["count"] == 0


def test_three_step_repair_is_fully_undoable(client):
    """三步都能一步步撤回原状——人工编辑不是单行道。"""
    c, root = client
    before = editable_snapshot(root)
    c.post(f"/api/page/{PAGE}/edit/merge",
           json={"ids": [f"{PAGE}c0000", f"{PAGE}c0001"]})
    c.post(f"/api/page/{PAGE}/edit/split", json={"id": f"{PAGE}c0003", "n": 2})
    ids = [ch["id"] for ch in on_disk(root)["chars"]]
    c.post(f"/api/page/{PAGE}/edit/reflow", json={"ids": ids})
    assert editable_snapshot(root) != before
    for _ in range(3):
        assert c.post(f"/api/page/{PAGE}/edit/undo").status_code == 200
    assert editable_snapshot(root) == before


# ---------------- 诊断接口 ----------------

def test_misaligned_endpoint_reports_the_defect(client):
    c, _ = client
    r = c.get(f"/api/page/{PAGE}/misaligned")
    assert r.status_code == 200
    assert r.json()["count"] == 1
    it = r.json()["items"][0]
    assert it["text"] == "三辰通載"
    assert {f["kind"] for f in it["flags"]} >= {"over", "drift"}
    assert any(b["shifted"] for b in it["boxes"])


def test_edit_on_missing_page_returns_404(client):
    c, _ = client
    assert c.post("/api/page/page_999/edit/delete",
                  json={"ids": ["x"]}).status_code == 404


def test_edit_with_unknown_box_id_returns_404(client):
    c, _ = client
    assert c.post(f"/api/page/{PAGE}/edit/delete",
                  json={"ids": ["nope"]}).status_code == 404


# ── 局部重识别 /ocr-crop ──────────────────────────────────────────────
# 引擎用 fake 顶替（不真跑 PaddleOCR 模型），只验端点的参数处理、
# 裁剪路径解析和阅读序拼接。识别质量本身归引擎管，不归端点管。

class _FakeOcr:
    """返回固定两字结果的假引擎：竖排「通」「載」，cx 相同 → 同列按 y 序。"""

    def ocr(self, img):
        return [{
            "rec_texts": ["通", "載"],
            "rec_polys": [
                [[10.0, 0.0], [30.0, 0.0], [30.0, 40.0], [10.0, 40.0]],
                [[10.0, 50.0], [30.0, 50.0], [30.0, 90.0], [10.0, 90.0]],
            ],
            "rec_scores": [0.9, 0.8],
        }]


@pytest.fixture
def page_with_image(client, monkeypatch):
    """在 books/ 里放一张真实小图，让裁剪真的走 PIL。"""
    c, root = client
    from gujiorc.core.paths import get_source_dir
    from PIL import Image
    img_path = get_source_dir() / "p1.png"
    Image.new("RGB", (1203, 1654), (255, 255, 255)).save(img_path)
    monkeypatch.setattr("gujiorc.ocr.engine.PaddleOcrEngine.get",
                        classmethod(lambda cls: _FakeOcr()))
    return c


def test_ocr_crop_by_ids_reads_boxes_and_orders_vertically(page_with_image):
    r = page_with_image.post(f"/api/page/{PAGE}/ocr-crop",
                             json={"ids": [f"{PAGE}c0002", f"{PAGE}c0003"]})
    assert r.status_code == 200
    out = r.json()
    # 两框 cx 相同聚成一列，列内从上到下 → 通在前載在后
    assert out["text"] == "通載"
    assert out["lines"][0]["text"] == "通"
    assert abs(out["score"] - 0.85) < 1e-6


def test_ocr_crop_by_explicit_box(page_with_image):
    r = page_with_image.post(f"/api/page/{PAGE}/ocr-crop",
                             json={"box": {"x": 1061, "y": 263, "w": 88, "h": 267}})
    assert r.status_code == 200 and r.json()["text"] == "通載"


def test_ocr_crop_requires_box_or_ids(page_with_image):
    assert page_with_image.post(f"/api/page/{PAGE}/ocr-crop", json={}).status_code == 400


def test_ocr_crop_on_missing_page_returns_404(page_with_image):
    assert page_with_image.post("/api/page/page_999/ocr-crop",
                                json={"ids": ["x"]}).status_code == 404


def test_ocr_crop_unknown_ids_returns_404(page_with_image):
    r = page_with_image.post(f"/api/page/{PAGE}/ocr-crop", json={"ids": ["nope"]})
    assert r.status_code == 404


def test_ocr_crop_engine_down_returns_503_with_hint(client, monkeypatch):
    c, root = client
    from gujiorc.core.paths import get_source_dir
    from PIL import Image
    Image.new("RGB", (100, 100), (255, 255, 255)).save(get_source_dir() / "p1.png")

    def _boom(cls):
        raise ImportError("paddleocr is not installed")
    monkeypatch.setattr("gujiorc.ocr.engine.PaddleOcrEngine.get", classmethod(_boom))
    r = c.post(f"/api/page/{PAGE}/ocr-crop",
               json={"box": {"x": 0, "y": 0, "w": 50, "h": 50}})
    assert r.status_code == 503 and "paddleocr" in r.json()["detail"]


# ── 标点不匹配诊断（punct_gap）────────────────────────────────────────
# 构造：行文本含标点 "通載。"（3字），但只有2个框（句号被并入前一个框）
# 诊断应报告 punct_gap 而非静默跳过

PAGE_PUNCT = "page_punct"


def build_punct_page() -> PageResult:
    chars = [
        CharBox(id=f"{PAGE_PUNCT}c0000", box={"x": 100, "y": 100, "w": 40, "h": 80},
                char="通", orig_char="通", conf=1.0),
        # 句号被并入「載」的框——框偏大（包含了句号的墨迹空间）
        CharBox(id=f"{PAGE_PUNCT}c0001", box={"x": 100, "y": 185, "w": 40, "h": 80},
                char="載", orig_char="載", conf=1.0),
    ]
    line = LineBox(id=f"{PAGE_PUNCT}L0",
                   box={"x": 100, "y": 100, "w": 40, "h": 165},
                   text="通載。", conf=1.0)
    return PageResult(page=PAGE_PUNCT, image="p1.png", width=400, height=600,
                      chars=chars, lines=[line])


@pytest.fixture
def punct_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    monkeypatch.delenv("OCR_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("OCR_SOURCE_DIR", raising=False)
    from gujiorc.core.storage import save_page_json
    from gujiorc.rare.detector import build_common_set, detect_rare_chars
    pr = build_punct_page()
    detect_rare_chars(pr, build_common_set())
    save_page_json(pr)
    import app as web_app
    return TestClient(web_app.create_app(str(tmp_path)))


def test_punct_gap_detected_when_period_missing(punct_client):
    c = punct_client
    r = c.get(f"/api/page/{PAGE_PUNCT}/misaligned")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    it = items[0]
    assert it["text"] == "通載。"
    # 应报告 punct_gap 信号
    assert any(f["kind"] == "punct_gap" for f in it["flags"])
    # 不应有 over/drift 信号（那是字错位，不是标点问题）
    assert not any(f["kind"] in ("over", "drift") for f in it["flags"])


def test_punct_gap_not_triggered_when_no_punctuation(client):
    """不含标点的行即使框数≠字数也不应报 punct_gap。"""
    c, _ = client
    # build_page() 的行 "三辰通載" 不含标点，4字4框，不应有 punct_gap
    r = c.get(f"/api/page/{PAGE}/misaligned")
    assert r.status_code == 200
    for it in r.json()["items"]:
        assert not any(f["kind"] == "punct_gap" for f in it["flags"])


def test_punct_gap_not_triggered_when_boxes_match(punct_client):
    """含标点但框数 == 字数时不应报 punct_gap。"""
    c = punct_client
    from gujiorc.core.storage import save_page_json
    from gujiorc.rare.detector import build_common_set, detect_rare_chars
    chars = [
        CharBox(id=f"{PAGE_PUNCT}c0000", box={"x": 100, "y": 100, "w": 40, "h": 40},
                char="通", orig_char="通", conf=1.0),
        CharBox(id=f"{PAGE_PUNCT}c0001", box={"x": 100, "y": 145, "w": 40, "h": 40},
                char="載", orig_char="載", conf=1.0),
        CharBox(id=f"{PAGE_PUNCT}c0002", box={"x": 100, "y": 190, "w": 40, "h": 15},
                char="。", orig_char="。", conf=0.9),
    ]
    line = LineBox(id=f"{PAGE_PUNCT}L0",
                   box={"x": 100, "y": 100, "w": 40, "h": 105},
                   text="通載。", conf=1.0)
    pr = PageResult(page=PAGE_PUNCT, image="p1.png", width=400, height=600,
                    chars=chars, lines=[line])
    detect_rare_chars(pr, build_common_set())
    save_page_json(pr)
    r = c.get(f"/api/page/{PAGE_PUNCT}/misaligned")
    assert r.status_code == 200
    assert r.json()["count"] == 0  # 无诊断问题
