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
