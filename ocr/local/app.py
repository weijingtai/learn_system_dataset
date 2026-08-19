"""gujiorc 本地 Web UI（M3，最小可用版）。

FastAPI 服务，浏览器访问本地查看古籍 OCR 复原结果。
功能：
- 列出页面 JSON
- 复原显示：底图 + 全部字框 + 字/生僻字高亮
- 查询某字跳转到出现位置

用法：
    cd ocr
    pip install fastapi uvicorn
    OCR_ROOT=xxx python local/app.py        # 或设环境变量
    浏览器打开 http://localhost:8000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 让 gujiorc 可导入
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

    # 静态资源（前端页面）
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return static_dir.joinpath("index.html").read_text(encoding="utf-8")

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
        # 返回底图文件
        from fastapi.responses import FileResponse
        pr = load_page_json(page)
        if pr is None or not pr.image:
            raise HTTPException(404, "无底图")
        img_path = Path(pr.image)
        if not img_path.exists():
            # 尝试在 books/ 下找
            cand = struct["books"] / Path(pr.image).name
            if cand.exists():
                img_path = cand
            else:
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
    async def fix_char(page: str, req: dict):
        """Web 端改正字：保留 orig_char + 记录 mapping。req: {char_id, new_char}"""
        from gujiorc.core.storage import load_page_json, save_page_json
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        cid = req.get("char_id"); new_char = req.get("new_char")
        if not cid or new_char is None:
            raise HTTPException(400, "需要 char_id 和 new_char")
        ch = next((x for x in pr.chars if x.id == cid), None)
        if ch is None:
            raise HTTPException(404, f"字框 {cid} 不存在")
        ch.set_char(new_char, mapping_source="manual")
        save_page_json(pr)
        return {"ok": True, "id": cid, "orig": ch.orig_char, "char": ch.char,
                "mapping": ch.mapping}

    @app.post("/api/page/{page}/segment-new")
    async def add_char(page: str, req: dict):
        """手动补标：新增一个未识别字框。req: {box:{x,y,w,h}, char?}"""
        from gujiorc.core.storage import load_page_json, save_page_json
        from gujiorc.core.models import CharBox
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, f"页面 {page} 不存在")
        box = req.get("box")
        if not box or not all(k in box for k in ("x", "y", "w", "h")):
            raise HTTPException(400, "需要 box:{x,y,w,h}")
        # 生成新 id
        seq = len(pr.chars)
        new_id = f"{page}c{seq:04d}"
        new_char = req.get("char", "")
        pr.chars.append(CharBox(
            id=new_id, box={k: float(box[k]) for k in ("x","y","w","h")},
            char=new_char, orig_char=new_char, source="manual",
            status="pending",
        ))
        save_page_json(pr)
        return {"ok": True, "id": new_id}

    @app.get("/api/page/{page}/char/{char_id}/rotate")
    def rotate_preview(page: str, char_id: str, angle: float = 0):
        """生成某字框旋转调正后的预览图（PNG）。angle 为正则逆时针。"""
        from fastapi.responses import FileResponse
        import tempfile
        from PIL import Image
        from gujiorc.core.storage import load_page_json
        pr = load_page_json(page)
        if pr is None:
            raise HTTPException(404, "页面不存在")
        ch = next((x for x in pr.chars if x.id == char_id), None)
        if ch is None:
            raise HTTPException(404, "字框不存在")
        # 加载底图
        img_path = Path(pr.image)
        if not img_path.exists():
            cand = struct["books"] / Path(pr.image).name
            img_path = cand if cand.exists() else None
        if not img_path:
            raise HTTPException(404, "底图不存在")
        img = Image.open(img_path).convert("RGB")
        b = ch.box
        x0, y0 = int(b["x"]), int(b["y"])
        x1, y1 = int(b["x"]+b["w"]), int(b["y"]+b["h"])
        x0, y0 = max(0,x0), max(0,y0)
        x1, y1 = min(img.width,x1), min(img.height,y1)
        crop = img.crop((x0, y0, x1, y1))
        # 放大 + 旋转调正
        crop = crop.resize((int(crop.width*4), int(crop.height*4)), Image.LANCZOS)
        if angle:
            crop = crop.rotate(-angle, expand=True, fillcolor=(255,255,255))
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        crop.save(tmp.name)
        return FileResponse(tmp.name, media_type="image/png")

    return app


if __name__ == "__main__":
    import uvicorn
    root = os.environ.get("OCR_ROOT")
    app = create_app(root)
    uvicorn.run(app, host="127.0.0.1", port=8000)