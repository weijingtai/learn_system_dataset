"""ACT 01 单元测试：G1 来源与可重放性五项 Validator。

用例名与 act/01.yaml 的 tests 清单逐字一致；全部基于
``tests/helpers.py`` 的 ``fixture_context()``，对上下文副本施加篡改。
"""

import unittest

from pipeline.validation.g1_source import (
    validate_content_hashes,
    validate_frozen_bytes,
    validate_page_registry,
    validate_unresolved_chars,
)
from pipeline.validation.replay import validate_replay
from pipeline.validation.tests.helpers import fixture_context, offset_fixture_context


def _by_check(result, check):
    return [f for f in result["findings"] if f["check"] == check]


class G1FixtureCleanTest(unittest.TestCase):
    def test_fixture_context_g1_clean_except_four_unresolved_char_findings(self):
        ctx = fixture_context()
        self.assertEqual(validate_frozen_bytes(ctx)["findings"], [])
        self.assertEqual(validate_page_registry(ctx)["findings"], [])
        self.assertEqual(validate_content_hashes(ctx)["findings"], [])
        self.assertEqual(validate_replay(ctx)["findings"], [])

        result = validate_unresolved_chars(ctx)
        findings = result["findings"]
        self.assertEqual(len(findings), 4)
        unresolved = _by_check(result, "unresolved_glyph")
        unproofread = _by_check(result, "unproofread_glyphs")
        self.assertEqual(len(unresolved), 2)
        self.assertEqual(len(unproofread), 2)
        self.assertEqual(
            {f["subject"]["entity_id"] for f in unresolved},
            {"ss_sanche_ed01_p0001_s03", "ss_sanche_ed01_p0001_s04"},
        )
        for finding in unresolved:
            self.assertEqual(
                finding["severity"],
                {"INTERNAL_DEMO": "warning", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"},
            )
        for finding in unproofread:
            self.assertEqual(
                finding["severity"],
                {"INTERNAL_DEMO": "info", "DEV_SEARCH": "warning", "PUBLIC_RELEASE": "error"},
            )
        self.assertEqual(
            {f["subject"]["page"] for f in unproofread}, {"page_001", "page_003"}
        )


class G1FrozenBytesTest(unittest.TestCase):
    def test_frozen_byte_tamper_yields_src_003_hash_mismatch(self):
        ctx = fixture_context()
        rev = ctx["corpus_spans_revision_id"]
        ctx["raw"]["frozen"][rev]["actual_sha256"] = "0" * 64
        result = validate_frozen_bytes(ctx)
        findings = _by_check(result, "hash_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SRC_003")
        self.assertEqual(
            set(findings[0]["severity"].values()), {"error"}
        )

        missing = fixture_context()
        rev2 = missing["corpus_spans_revision_id"]
        missing["raw"]["frozen"][rev2]["actual_sha256"] = None
        missing["raw"]["frozen"][rev2]["doc"] = None
        missing_result = validate_frozen_bytes(missing)
        findings2 = _by_check(missing_result, "object_missing")
        self.assertEqual(len(findings2), 1)
        self.assertEqual(findings2[0]["code"], "SRC_001")


class G1PageRegistryTest(unittest.TestCase):
    def test_page_registry_detects_hash_mismatch_and_missing_pages(self):
        ctx = fixture_context()
        ctx["ocr_page_set"]["ocr_pages"][0]["sha256"] = "0" * 64
        findings = _by_check(validate_page_registry(ctx), "page_hash_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SRC_003")

        missing = fixture_context()
        missing["ocr_page_set"]["ocr_pages"] = [
            entry
            for entry in missing["ocr_page_set"]["ocr_pages"]
            if entry["page"] != "page_003"
        ]
        set_findings = _by_check(validate_page_registry(missing), "page_set_mismatch")
        self.assertTrue(set_findings)

        terminal = fixture_context()
        terminal["terminal_states"] = {"page_002": "manually_transcribed"}
        terminal_findings = _by_check(
            validate_page_registry(terminal), "terminal_state_mismatch"
        )
        self.assertTrue(terminal_findings)


class G1ContentHashesTest(unittest.TestCase):
    def test_content_hashes_catches_package_sha_mismatch(self):
        ctx = fixture_context()
        ctx["m3_package"]["manifest"]["content_sha256"] = "0" * 64
        findings = _by_check(validate_content_hashes(ctx), "content_sha256_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SRC_003")

        ctx2 = fixture_context()
        ctx2["corpus_package"]["spans_revision_id"] = "rev_" + "0" * 32
        findings2 = _by_check(validate_content_hashes(ctx2), "spans_revision_mismatch")
        self.assertEqual(len(findings2), 1)
        self.assertEqual(findings2[0]["code"], "REF_001")


class G1UnresolvedCharsTest(unittest.TestCase):
    def test_unresolved_chars_flags_pua_and_unrecognized_boxes(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["text"] = "\ue000三辰通載"
        pua = _by_check(validate_unresolved_chars(ctx), "forbidden_char_in_text")
        self.assertEqual(len(pua), 1)
        self.assertEqual(pua[0]["code"], "TXT_001")
        self.assertEqual(set(pua[0]["severity"].values()), {"error"})

        ctx2 = fixture_context()
        ctx2["spans_doc"]["spans"][1]["text"] = "（宋）\ufffd錢如璧撰\u25a1"
        box = _by_check(validate_unresolved_chars(ctx2), "forbidden_char_in_text")
        self.assertEqual(len(box), 1)


class G1ReplayTest(unittest.TestCase):
    def test_replay_succeeds_on_fixture(self):
        ctx = fixture_context()
        self.assertEqual(validate_replay(ctx)["findings"], [])

    def test_replay_fails_on_tool_version_mismatch(self):
        ctx = fixture_context()
        ctx["configuration"]["tool_version"] = "9.9.9"
        findings = _by_check(validate_replay(ctx), "replay_tool_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertIsNone(findings[0]["code"])
        self.assertEqual(set(findings[0]["severity"].values()), {"error"})

    def test_replay_fails_on_tampered_corpus_spans_bytes(self):
        ctx = fixture_context()
        rev = ctx["corpus_spans_revision_id"]
        ctx["raw"]["frozen"][rev]["actual_sha256"] = "0" * 64
        findings = _by_check(validate_replay(ctx), "replay_bytes_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SRC_003")


class G1OffsetLevelTest(unittest.TestCase):
    """R83（第 100 条 D5）：offset 档 G1 来源链复算（合成数据，不读 ocr_page）。"""

    def test_g1_offset_level_rejects_source_asset_sha_mismatch(self):
        clean = offset_fixture_context()
        self.assertEqual(validate_page_registry(clean)["findings"], [])

        ctx = offset_fixture_context()
        ctx["manifest"]["source_assets"][0]["normalized_sha256"] = "0" * 64
        findings = _by_check(validate_page_registry(ctx), "source_asset_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SRC_003")
        self.assertEqual(findings[0]["severity"], {
            "INTERNAL_DEMO": "error", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error",
        })

    def test_g1_offset_level_replay_recomputes_spans_bytes(self):
        ctx = offset_fixture_context()
        self.assertEqual(validate_replay(ctx)["findings"], [])
        self.assertTrue(validate_replay(ctx)["checked"]["replayed"])

        ctx["configuration"]["tool_version"] = "9.9.9"
        findings = _by_check(validate_replay(ctx), "replay_tool_mismatch")
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
