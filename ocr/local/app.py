"""gujiorc 本地 Web UI（M3，最小可用版）。

FastAPI 服务，浏览器访问本地查看古籍 OCR 复原结果。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def create_app(ocr_root: str | None = None) -> FastAPI:
    if ocr_root:
        os.environ["OCR_ROOT"] = ocr_root

    from gujiorc.core.paths import ensure_struct
    from gujiorc.core.storage import load_page_json

    struct = ensure_struct()
    data_dir = struct["data"]

    app = FastAPI(title="gujiorc 古籍 OCR 工作台")

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(static_dir.joinpath("index.html").read_text(encoding="utf-8"))

    @app.get("/api/pages")
    def list_pages():
        pages = sorted(p.stem for p in data_dir.glob("page_*.json") if not p.stem.endswith(".marked"))
        return {"pages": pages, "root": str(struct["root"])}

    @app.get("/api/page/{page}")
    def get_page(page: str):
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        return pr.to_dict()

    @app.get("/api/image/{page}")
    def get_image(page: str):
        from fastapi.responses import FileResponse
        pr = load_page_json(page)
        if pr is None or not pr.image:
            raise HTTPException(404, "无底图")
        img_path = Path(pr.image)
        if not img_path.exists():
            cand = struct["books"] / Path(pr.image).name
            img_path = cand if cand.exists() else None
        if not img_path:
            raise HTTPException(404, f"底图不存在: {pr.image}")
        return FileResponse(str(img_path))

    @app.get("/api/dict/{char}")
    def get_dict(char: str):
        from gujiorc.rare.dictionary import query_rare
        return query_rare(char)

    @app.get("/api/search")
    def search_char(char: str):
        from gujiorc.index.fulltext import CharIndex
        idx = CharIndex()
        try:
            rows = idx.query_char(char)
        finally:
            idx.close()
        return {"char": char, "hits": rows}

    @app.post("/api/page/{page}/fix")
    def fix_char(page: str, req: dict):
        from gujiorc.core.audit import log_event
        from gujiorc.core.storage import load_page_json, save_page_json
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        cid = req.get("char_id")
        new_char = req.get("new_char")
        if not cid or new_char is None:
            raise HTTPException(400, "需要 char_id 和 new_char")
        ch = next((x for x in pr.chars if x.id == cid), None)
        if ch is None:
            raise HTTPException(404, f"字框 {cid} 不存在")
        ch.set_char(new_char, mapping_source="manual")
        save_page_json(pr)
        log_event("fix", actor="web", page=page, char_id=cid,
                  **{"from": ch.orig_char, "to": new_char, "source": "manual"})
        return {"ok": True, "id": cid, "orig": ch.orig_char, "char": ch.char,
                "mapping": ch.mapping}

    @app.post("/api/page/{page}/segment-new")
    def add_char(page: str, req: dict):
        from gujiorc.core.audit import log_event
        from gujiorc.core.storage import load_page_json, save_page_json
        from gujiorc.core.models import CharBox
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        box = req.get("box")
        if not box or not all(k in box for k in ("x", "y", "w", "h")):
            raise HTTPException(400, "需要 box:{x,y,w,h}")
        seq = len(pr.chars)
        new_id = f"{page}c{seq:04d}"
        new_char = req.get("char", "")
        pr.chars.append(CharBox(
            id=new_id, box={k: float(box[k]) for k in ("x", "y", "w", "h")},
            char=new_char, orig_char=new_char, source="manual",
            status="pending",
        ))
        save_page_json(pr)
        log_event("segment_new", actor="web", page=page, char_id=new_id,
                  box={k: float(box[k]) for k in ("x", "y", "w", "h")})
        return {"ok": True, "id": new_id}

    @app.get("/api/anomalies")
    def list_anomalies(page: str = "", last: int = 0):
        from gujiorc.core.anomaly import list_anomalies as _list
        items = _list(page=page or None, last=last or 0)
        return {"items": items, "count": len(items)}

    # ── 人工校对编辑（core/edit.py 的 HTTP 外壳）─────────────────────
    #
    # 统一约定，前端只需处理一种返回：
    #   1. 改动前先抓快照（snapshot_chars），操作**成功后**才落撤销栈
    #      （push_snapshot）——被拒绝的请求不留「空一格」的撤销
    #   2. 改完立刻落盘（save_page_json）——编辑即保存，没有「未保存」状态
    #   3. 返回**整页 chars** + 撤销栈深度，前端整体替换即可，不必自己算增量
    #   4. 写审计日志，改了什么永久可查
    # 校验失败（ValueError/KeyError）一律转 4xx 并把原因原样带给用户，
    # 不静默吞掉——尤其是 reflow 的「框数≠字数」闸门。

    def _edit_ctx(page: str):
        from gujiorc.core.storage import load_page_json
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        return pr

    def _edit_done(pr, action: str, **log_fields):
        from gujiorc.core.audit import log_event
        from gujiorc.core.edit import history_depth
        from gujiorc.core.storage import save_page_json
        from gujiorc.rare.detector import build_common_set, detect_rare_chars
        # 改完重算生僻字标记，否则新框在前端永远不着色
        detect_rare_chars(pr, build_common_set())
        save_page_json(pr)
        log_event(action, actor="web", page=pr.page, **log_fields)
        return {"ok": True, "chars": [c.to_dict() for c in pr.chars],
                "history": history_depth(pr.page)}

    @app.post("/api/page/{page}/edit/merge")
    def edit_merge(page: str, req: dict):
        from gujiorc.core.edit import merge_boxes, push_snapshot, snapshot_chars
        pr = _edit_ctx(page)
        ids = req.get("ids") or []
        snap = snapshot_chars(pr)
        try:
            new = merge_boxes(pr, ids, char=req.get("char"))
        except KeyError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))
        push_snapshot(page, snap)
        out = _edit_done(pr, "merge", char_id=new.id, merged_from=ids, to=new.char)
        out["id"] = new.id
        return out

    @app.post("/api/page/{page}/edit/split")
    def edit_split(page: str, req: dict):
        from gujiorc.core.edit import push_snapshot, snapshot_chars, split_box
        pr = _edit_ctx(page)
        cid = req.get("id")
        if not cid:
            raise HTTPException(400, "需要 id")
        snap = snapshot_chars(pr)
        try:
            parts = split_box(pr, cid, at=req.get("at"), n=int(req.get("n") or 0),
                              chars=req.get("chars"))
        except KeyError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))
        push_snapshot(page, snap)
        out = _edit_done(pr, "split", char_id=cid,
                         into=[p.id for p in parts], at=req.get("at") or [],
                         n=int(req.get("n") or 0))
        out["ids"] = [p.id for p in parts]
        return out

    @app.post("/api/page/{page}/edit/delete")
    def edit_delete(page: str, req: dict):
        from gujiorc.core.edit import delete_boxes, push_snapshot, snapshot_chars
        pr = _edit_ctx(page)
        ids = req.get("ids") or []
        if not ids:
            raise HTTPException(400, "需要 ids")
        snap = snapshot_chars(pr)
        try:
            removed = delete_boxes(pr, ids)
        except KeyError as e:
            raise HTTPException(404, str(e))
        # 被删框的完整快照进审计日志，删掉的原始识别仍可查回
        push_snapshot(page, snap)
        return _edit_done(pr, "delete", removed=removed)

    @app.post("/api/page/{page}/edit/update")
    def edit_update(page: str, req: dict):
        from gujiorc.core.edit import push_snapshot, snapshot_chars, update_box
        pr = _edit_ctx(page)
        cid = req.get("id")
        if not cid:
            raise HTTPException(400, "需要 id")
        snap = snapshot_chars(pr)
        try:
            c = update_box(pr, cid, box=req.get("box"), char=req.get("char"))
        except KeyError as e:
            raise HTTPException(404, str(e))
        push_snapshot(page, snap)
        return _edit_done(pr, "update", char_id=cid,
                          **{"from": c.orig_char, "to": c.char})

    @app.post("/api/page/{page}/edit/create")
    def edit_create(page: str, req: dict):
        from gujiorc.core.edit import create_box, push_snapshot, snapshot_chars
        pr = _edit_ctx(page)
        box = req.get("box")
        if not box or not all(k in box for k in ("x", "y", "w", "h")):
            raise HTTPException(400, "需要 box:{x,y,w,h}")
        snap = snapshot_chars(pr)
        new = create_box(pr, box, char=req.get("char", ""))
        push_snapshot(page, snap)
        out = _edit_done(pr, "segment_new", char_id=new.id, box=new.box)
        out["id"] = new.id
        return out

    @app.post("/api/page/{page}/edit/reflow")
    def edit_reflow(page: str, req: dict):
        """按行文本把文字重灌到这批框上（几何修好后让文字顺移归位）。"""
        from gujiorc.core.edit import push_snapshot, reflow, snapshot_chars
        pr = _edit_ctx(page)
        ids = req.get("ids") or []
        if not ids:
            raise HTTPException(400, "需要 ids")
        snap = snapshot_chars(pr)
        try:
            ordered = reflow(pr, ids, text=req.get("text"))
        except KeyError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            # 「框数≠字数」的闸门信息要原样给用户看，它自带下一步该怎么做
            raise HTTPException(400, str(e))
        push_snapshot(page, snap)
        out = _edit_done(pr, "reflow", to="".join(c.char for c in ordered),
                         ids=[c.id for c in ordered])
        out["text"] = "".join(c.char for c in ordered)
        return out

    @app.post("/api/page/{page}/edit/undo")
    def edit_undo(page: str):
        from gujiorc.core.edit import undo
        pr = _edit_ctx(page)
        try:
            undo(pr)
        except IndexError as e:
            raise HTTPException(409, str(e))
        return _edit_done(pr, "undo")

    @app.post("/api/page/{page}/edit/redo")
    def edit_redo(page: str):
        from gujiorc.core.edit import redo
        pr = _edit_ctx(page)
        try:
            redo(pr)
        except IndexError as e:
            raise HTTPException(409, str(e))
        return _edit_done(pr, "redo")

    @app.get("/api/page/{page}/edit/history")
    def edit_history(page: str):
        from gujiorc.core.edit import history_depth
        return history_depth(page)

    @app.get("/api/page/{page}/misaligned")
    def misaligned(page: str):
        """疑似「框数==字数但框↔字错位」的行。只诊断，不改数据。"""
        from gujiorc.core.edit import diagnose_page
        pr = _edit_ctx(page)
        items = diagnose_page(pr)
        return {"items": items, "count": len(items)}

    @app.get("/api/page/{page}/char/{char_id}/rotate")
    def rotate_preview(page: str, char_id: str, angle: float = 0):
        from gujiorc.core.audit import log_event
        from gujiorc.core.storage import load_page_json
        from fastapi.responses import FileResponse
        import tempfile
        from PIL import Image
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, "页面不存在")
        ch = next((x for x in pr.chars if x.id == char_id), None)
        if ch is None:
            raise HTTPException(404, "字框不存在")
        img_path = Path(pr.image)
        if not img_path.exists():
            cand = struct["books"] / Path(pr.image).name
            img_path = cand if cand.exists() else None
        if not img_path:
            raise HTTPException(404, "底图不存在")
        img = Image.open(img_path).convert("RGB")
        b = ch.box
        x0, y0 = int(b["x"]), int(b["y"])
        x1, y1 = int(b["x"] + b["w"]), int(b["y"] + b["h"])
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img.width, x1), min(img.height, y1)
        crop = img.crop((x0, y0, x1, y1))
        crop = crop.resize((int(crop.width * 4), int(crop.height * 4)), Image.LANCZOS)
        if angle:
            crop = crop.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        crop.save(tmp.name)
        log_event("rotate", actor="web", page=page, char_id=char_id, angle=angle)
        return FileResponse(tmp.name, media_type="image/png")

    return app


if __name__ == "__main__":
    import uvicorn
    root = os.environ.get("OCR_ROOT")
    # 端口可配：并排比对两套数据（如生产结果 vs 实验结果）需要同时起两个实例
    port = int(os.environ.get("OCR_WEB_PORT", "8000"))
    app = create_app(root)
    uvicorn.run(app, host="127.0.0.1", port=port)
