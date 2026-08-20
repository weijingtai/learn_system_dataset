"""gujiorc.core.export corpus 导出测试（PLANS §6.1）。"""
import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gujiorc.core.models import PageResult, CharBox  # noqa: E402
from gujiorc.core.export import export_corpus  # noqa: E402


def make_page(page="page_001"):
    chars = [
        CharBox(id=f"{page}c0", box={"x": 0, "y": 0, "w": 1, "h": 1}, char="貴", orig_char="貴"),
        CharBox(id=f"{page}c1", box={"x": 1, "y": 0, "w": 1, "h": 1}, char="人", orig_char="人"),
        CharBox(id=f"{page}c2", box={"x": 2, "y": 0, "w": 1, "h": 1}, char="", orig_char="凢"),
    ]
    return PageResult(page=page, image="i.png", width=10, height=10, chars=chars)


def test_export_corpus_writes_manifest_and_transcript():
    with tempfile.TemporaryDirectory() as tmp:
        out = export_corpus(
            [make_page()],
            tmp,
            book="test",
            work_title="新刻琴堂五星",
            technique_id="wuxing",
            edition=1,
            rights_status="public_domain",
        )
        assert out["manifest"].exists()
        assert out["transcript"].exists()
        text = out["manifest"].read_text(encoding="utf-8")
        assert 'source_id: "src_test_ed01"' in text
        assert 'path: "source/transcript_v1.md"' in text
        assert 'role: "transcript"' in text
        assert 'technique_id: "wuxing"' in text
        assert 'rights_status: "public_domain"' in text
        assert 'work_title: "新刻琴堂五星"' in text
        actual = hashlib.sha256(out["transcript"].read_bytes()).hexdigest()
        assert f'sha256: "{actual}"' in text


def test_manifest_notes_unknown_count():
    with tempfile.TemporaryDirectory() as tmp:
        out = export_corpus(
            [make_page()],
            tmp,
            book="test",
            work_title="新刻琴堂五星",
            technique_id="wuxing",
        )
        text = out["manifest"].read_text(encoding="utf-8")
        assert "未识别字形待人工补录" in text


def test_manifest_no_note_when_all_recognized():
    page = PageResult(page="page_001", image="i.png", width=10, height=10, chars=[
        CharBox(id="c0", box={"x": 0, "y": 0, "w": 1, "h": 1}, char="貴", orig_char="貴"),
        CharBox(id="c1", box={"x": 1, "y": 0, "w": 1, "h": 1}, char="人", orig_char="人"),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        out = export_corpus(
            [page], tmp, book="test", work_title="test", technique_id="qimen"
        )
        text = out["manifest"].read_text(encoding="utf-8")
        assert "未识别字形" not in text