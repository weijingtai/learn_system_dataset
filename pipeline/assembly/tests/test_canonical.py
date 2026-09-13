"""M7 规范化与提案键单元测试（spec §15, §8.1）。"""

import re
import unittest

from pipeline.assembly.canonical import (
    PROPOSAL_KINDS,
    RELATION_KINDS,
    canonical_json,
    content_sha256,
    make_key,
    nfc_key,
    sha256_hex,
    work_key,
)
from pipeline.ledger.errors import InvalidIdentifier, SchemaViolation
from pipeline.ledger.ids import kind_of


class TestCanonical(unittest.TestCase):
    def test_canonical_json_key_order_independent(self):
        obj1 = {"b": 1, "a": {"z": 10, "y": 20}}
        obj2 = {"a": {"y": 20, "z": 10}, "b": 1}
        self.assertEqual(canonical_json(obj1), canonical_json(obj2))

    def test_canonical_json_trailing_newline_and_utf8(self):
        obj = {"text": "七政四余", "number": 42}
        result = canonical_json(obj)
        self.assertTrue(result.endswith(b"\n"))
        self.assertEqual(result.decode("utf-8")[-1], "\n")
        # 确保无 ascii 转义（如 \u4e03）
        self.assertIn("七政四余".encode("utf-8"), result)

    def test_nfc_key_normalizes_and_strips(self):
        # e + combining acute accent -> single code point é in NFC
        composed = "e\u0301"
        self.assertEqual(nfc_key(f"  {composed}  "), "é")
        self.assertEqual(nfc_key("  七政四余  "), "七政四余")
        with self.assertRaises(SchemaViolation) as ctx:
            nfc_key(123)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_make_key_format(self):
        key = make_key("merge", ("pattern", "src_qizheng_ed01", "pat_qizheng_000001"))
        self.assertTrue(re.match(r"^merge:[0-9a-f]{32}$", key), f"Key format mismatch: {key}")

    def test_make_key_never_matches_registered_prefix(self):
        # 全部 kind 各一次，确保 pipeline.ledger.ids.kind_of 返回 None
        for kind in PROPOSAL_KINDS + RELATION_KINDS:
            key = make_key(kind, ("subject_kind", "subject_id_123"))
            self.assertIsNone(kind_of(key), f"Key {key} unexpectedly matches registered prefix")

    def test_make_key_rejects_unknown_kind(self):
        with self.assertRaises(SchemaViolation) as ctx:
            make_key("unknown_kind", ("a", "b"))
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_work_key_from_source_id(self):
        self.assertEqual(work_key("src_qizheng_ed01"), "qizheng")
        self.assertEqual(work_key("src_sanche_ed02"), "sanche")

    def test_work_key_rejects_bad_source_id(self):
        for bad_id in ["invalid_src", "src_qizheng", "src__ed01", "src_123_ed01"]:
            with self.assertRaises(InvalidIdentifier) as ctx:
                work_key(bad_id)
            self.assertEqual(ctx.exception.code, "ID_001")


if __name__ == "__main__":
    unittest.main()
