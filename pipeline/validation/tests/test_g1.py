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
from pipeline.validation.tests.helpers import (
    OFFSET_PUA_FINDING,
    fixture_context,
    offset_fixture_context,
    offset_pua_fixture_context,
)


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

    def test_g1_glyphbox_pua_still_error(self):
        """OCR 档护栏（第 103 条 D1）：即使清洗报告里有对得上的记录，仍判三级 error。

        为让本护栏对「glyphbox 档也走对账」这一改动**敏感**，这里刻意把对账所需
        字段补齐（``cleaned_text``／``patches`` 与一条完全对得上的
        ``known_unresolvable`` 记录）：若 OCR 档误用对账口径，就会产出
        ``known_unresolvable_char_disclosed``。
        """
        ctx = fixture_context()
        span = ctx["spans_doc"]["spans"][0]
        span["text"] = "\ue03d三辰通載"
        start = span["start_offset"]
        ctx["cleaned_text"] = "占" * (len(span["text"]) + start)
        ctx["patches"] = []
        ctx["sanitization_report"] = {
            "findings": [
                {
                    "finding_id": "private_use_area@%d-%d" % (start, start + 1),
                    "kind": "private_use_area",
                    "raw_start": start,
                    "raw_end": start + 1,
                    "terminal_state": "known_unresolvable",
                }
            ]
        }
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "known_unresolvable_char_disclosed"), [])
        findings = _by_check(result, "forbidden_char_in_text")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "TXT_001")
        self.assertEqual(set(findings[0]["severity"].values()), {"error"})


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


class G1OffsetKeptCharDisclosureTest(unittest.TestCase):
    """R83b（第 103 条 D1）：offset 档禁止字符与 sanitization_report 对账。"""

    def test_g1_offset_pua_with_known_unresolvable_finding_is_disclosed_warning(self):
        ctx = offset_pua_fixture_context()
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "forbidden_char_in_text"), [])
        self.assertEqual(result["checked"]["forbidden_chars"], 1)
        self.assertEqual(result["checked"]["disclosed"], 1)

        findings = _by_check(result, "known_unresolvable_char_disclosed")
        self.assertEqual(len(findings), 1)
        self.assertIsNone(findings[0]["code"])
        self.assertEqual(
            findings[0]["severity"],
            {"INTERNAL_DEMO": "warning", "DEV_SEARCH": "warning", "PUBLIC_RELEASE": "error"},
        )
        self.assertIn(OFFSET_PUA_FINDING["finding_id"], findings[0]["detail"])
        self.assertEqual(findings[0]["validator_id"], "g1_unresolved_chars")
        self.assertEqual(findings[0]["gate"], "G1")

    def test_g1_offset_pua_without_finding_is_error(self):
        ctx = offset_pua_fixture_context()
        ctx["sanitization_report"]["findings"] = []
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "known_unresolvable_char_disclosed"), [])
        findings = _by_check(result, "forbidden_char_in_text")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "TXT_001")
        self.assertEqual(set(findings[0]["severity"].values()), {"error"})

    def test_g1_offset_pua_with_wrong_terminal_state_is_error(self):
        ctx = offset_pua_fixture_context()
        ctx["sanitization_report"]["findings"][0]["terminal_state"] = "processed"
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "known_unresolvable_char_disclosed"), [])
        self.assertEqual(len(_by_check(result, "forbidden_char_in_text")), 1)

    def test_g1_offset_pua_with_mismatched_kind_is_error(self):
        ctx = offset_pua_fixture_context()
        ctx["sanitization_report"]["findings"][0]["kind"] = "escape_residue"
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "known_unresolvable_char_disclosed"), [])
        self.assertEqual(len(_by_check(result, "forbidden_char_in_text")), 1)

    def test_g1_offset_pua_matched_by_two_findings_is_error(self):
        ctx = offset_pua_fixture_context()
        duplicate = dict(OFFSET_PUA_FINDING)
        duplicate["finding_id"] = "private_use_area@6-7#dup"
        ctx["sanitization_report"]["findings"].append(duplicate)
        result = validate_unresolved_chars(ctx)
        self.assertEqual(_by_check(result, "known_unresolvable_char_disclosed"), [])
        self.assertEqual(len(_by_check(result, "forbidden_char_in_text")), 1)

    def test_g1_offset_pua_public_release_is_error(self):
        ctx = offset_pua_fixture_context()
        findings = _by_check(
            validate_unresolved_chars(ctx), "known_unresolvable_char_disclosed"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"]["PUBLIC_RELEASE"], "error")
        self.assertEqual(findings[0]["severity"]["INTERNAL_DEMO"], "warning")

    def test_g1_offset_disclosure_names_match_m2_contract(self):
        """kind / 终态名与 M2 契约常量逐字一致（第 85、103 条 D2）。"""
        from pipeline.digitization import FINDING_KINDS, TERMINAL_STATES

        from pipeline.validation import g1_source as g1

        for kind in ("private_use_area", "replacement_char", "control_char"):
            self.assertIn(kind, FINDING_KINDS)
        self.assertIn(g1._KNOWN_UNRESOLVABLE, TERMINAL_STATES)
        self.assertEqual(g1._kind_for_forbidden_char("\ue03d"), "private_use_area")
        self.assertEqual(g1._kind_for_forbidden_char("\ufffd"), "replacement_char")
        self.assertEqual(g1._kind_for_forbidden_char("\x0c"), "control_char")
        self.assertIsNone(g1._kind_for_forbidden_char("\u25a1"))
        self.assertIsNone(g1._kind_for_forbidden_char("\u3013"))


if __name__ == "__main__":
    unittest.main()
