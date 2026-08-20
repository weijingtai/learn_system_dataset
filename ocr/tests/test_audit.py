"""gujiorc.core.audit 测试。"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gujiorc.core.audit import log_event, read_events  # noqa: E402


def test_append_and_read(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    p1 = log_event("fix", actor="cli", page="page_001", char_id="c0", **{"from": "旧", "to": "新"})
    log_event("fix", actor="cli", page="page_002", char_id="c1", **{"from": "A", "to": "B"})
    log_event("rotate", actor="web", page="page_001", char_id="c2", angle=10)
    assert p1.exists()
    events = read_events()
    assert len(events) == 3
    assert events[0]["action"] == "fix"
    assert events[0]["page"] == "page_001"
    assert events[2]["action"] == "rotate"


def test_filter_page(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    log_event("fix", actor="cli", page="page_001", char_id="c0", **{"from": "旧", "to": "新"})
    log_event("fix", actor="cli", page="page_002", char_id="c1", **{"from": "A", "to": "B"})
    hits = read_events(page="page_001")
    assert len(hits) == 1
    assert hits[0]["page"] == "page_001"


def test_invalid_action_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    try:
        log_event("hack", actor="cli", page="page_001")
    except ValueError:
        pass
    else:
        raise AssertionError("expect ValueError")


def test_read_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    assert read_events() == []