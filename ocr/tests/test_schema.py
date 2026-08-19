"""gujiorc.core.schema 校验测试（M7_）。"""
import json
import os
import sys
import tempfile

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.schema import (  # noqa: E402
    validate_page_dict, validate_page_file, check_json_loadability, ValidationError,
)


def make_valid_page():
    return {
        "page": "page_001",
        "book": "book1",
        "image": "img.png",
        "width": 100,
        "height": 200,
        "chars": [
            {"id": "page_001c0000", "box": {"x": 1, "y": 2, "w": 10, "h": 12}, "char": "貴"},
            {"id": "page_001c0001", "box": {"x": 15, "y": 2, "w": 10, "h": 12}, "char": "人",
             "status": "corrected", "mapping": {"from": "凢", "target": "凡", "source": "manual"}},
        ],
    }


def test_valid_page_no_errors():
    assert validate_page_dict(make_valid_page()) == []


def test_missing_required_field():
    d = make_valid_page()
    del d["width"]
    errs = validate_page_dict(d)
    assert any("缺必填字段" in e and "width" in e for e in errs)


def test_bad_box_negative():
    d = make_valid_page()
    d["chars"][0]["box"]["x"] = -5
    errs = validate_page_dict(d)
    assert any("box.x 不能为负" in e for e in errs)


def test_bad_status_enum():
    d = make_valid_page()
    d["chars"][0]["status"] = "INVALID_STATUS"
    errs = validate_page_dict(d, page="page_001")
    assert any("非法 status" in e for e in errs)


def test_duplicate_ids():
    d = make_valid_page()
    d["chars"][1]["id"] = d["chars"][0]["id"]
    errs = validate_page_dict(d)
    assert any("重复字框 id" in e for e in errs)


def test_mapping_requires_from():
    d = make_valid_page()
    d["chars"][1]["mapping"] = {"target": "凡"}
    errs = validate_page_dict(d)
    assert any("mapping 缺字段" in e for e in errs)


def test_file_validation_and_loadability():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "page_001.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(make_valid_page(), f, ensure_ascii=False)
        assert validate_page_file(p) == []
        data = check_json_loadability(p)
        assert data["page"] == "page_001"

        # 损坏文件
        bad = os.path.join(tmp, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        assert validate_page_file(bad)  # 非空错误


def test_bad_file_raises():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "broken.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"page": "x"}, f)
        try:
            check_json_loadability(p)
            assert False, "应抛 ValidationError"
        except ValidationError:
            pass