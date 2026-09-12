"""ACT impl-04/00：规范化 JSON 与修订号剥离纯函数的测试。

只使用标准库；不读 fixture、不访问 Ledger。
"""

import unittest

from pipeline.dataset_compiler.canonical import (
    canonical_bytes,
    normalized_sha256,
    sha256_hex,
    strip_revision_ids,
)
from pipeline.ledger.errors import SchemaViolation


class CanonicalBytesTests(unittest.TestCase):
    """canonical_bytes / sha256_hex 的基本契约。"""

    def test_canonical_bytes_sorted_compact_utf8(self):
        data = canonical_bytes({"b": 1, "a": "甲"})
        self.assertEqual(data, '{"a":"甲","b":1}'.encode("utf-8"))

    def test_canonical_rejects_nan(self):
        with self.assertRaises(ValueError):
            canonical_bytes({"x": float("nan")})

    def test_sha256_hex_requires_bytes_SCH_001(self):
        with self.assertRaises(SchemaViolation) as ctx:
            sha256_hex("abc")
        self.assertEqual(ctx.exception.code, "SCH_001")


class StripRevisionIdsTests(unittest.TestCase):
    """strip_revision_ids 的递归与纯函数性质。"""

    def test_strip_revision_ids_recursive(self):
        source = {
            "artifact_revision_id": "rev_" + "0" * 32,
            "keep": 1,
            "nested": {
                "ocr_page_artifact_revision_id": "rev_" + "1" * 32,
                "keep2": [
                    {
                        "source_asset_artifact_revision_id": "rev_" + "2" * 32,
                        "k": 3,
                    }
                ],
            },
        }
        out = strip_revision_ids(source)
        self.assertNotIn("artifact_revision_id", out)
        self.assertNotIn("ocr_page_artifact_revision_id", out["nested"])
        self.assertNotIn(
            "source_asset_artifact_revision_id", out["nested"]["keep2"][0]
        )
        self.assertEqual(out["keep"], 1)
        self.assertEqual(out["nested"]["keep2"][0]["k"], 3)
        # 入参未被修改
        self.assertIn("artifact_revision_id", source)
        self.assertIn("ocr_page_artifact_revision_id", source["nested"])

    def test_normalized_sha256_ignores_revision_ids(self):
        base = {
            "x": 1,
            "artifact_revision_id": "rev_" + "a" * 32,
            "nested": {"ocr_page_artifact_revision_id": "rev_" + "b" * 32, "y": 2},
        }
        only_ids_changed = {
            "x": 1,
            "artifact_revision_id": "rev_" + "c" * 32,
            "nested": {"ocr_page_artifact_revision_id": "rev_" + "d" * 32, "y": 2},
        }
        other_changed = {
            "x": 2,
            "artifact_revision_id": "rev_" + "a" * 32,
            "nested": {"ocr_page_artifact_revision_id": "rev_" + "b" * 32, "y": 2},
        }
        self.assertEqual(normalized_sha256(base), normalized_sha256(only_ids_changed))
        self.assertNotEqual(normalized_sha256(base), normalized_sha256(other_changed))


if __name__ == "__main__":
    unittest.main()
