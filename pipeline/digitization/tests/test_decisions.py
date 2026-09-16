"""M2 决定表单元测试（synthetic_fixture: true）。"""

import copy
import unittest

from pipeline.digitization.cleaner import Finding
from pipeline.digitization.decisions import (
    check_decisions_coverage,
    load_decisions,
)
from pipeline.digitization.errors import DigitizationRefused


class TestDecisions(unittest.TestCase):
    """M2 终态决定表加载与覆盖度检查测试集。"""

    def _valid_decisions_dict(self):
        return {
            "schema_version": "1.0.0",
            "edition_part_artifact_id": "art_000000000000000000000000000000e1",
            "entries": [
                {
                    "page": "page_001",
                    "finding_id": "missing@10-15",
                    "terminal_state": "processed",
                    "reason": "人工核对底本补齐",
                    "decided_by": "校勘员张三",
                    "note": "参考古籍版本",
                }
            ],
        }

    def test_load_decisions_valid(self):
        """synthetic_fixture: true，合法输入 → 返回值键序固定。"""
        raw = self._valid_decisions_dict()
        res = load_decisions(raw)
        self.assertEqual(res["schema_version"], "1.0.0")
        self.assertEqual(res["edition_part_artifact_id"], raw["edition_part_artifact_id"])
        self.assertEqual(len(res["entries"]), 1)
        self.assertEqual(list(res.keys()), ["schema_version", "edition_part_artifact_id", "entries"])

    def test_load_decisions_missing_key_SCH_001(self):
        """synthetic_fixture: true，缺必填键报 SCH_001。"""
        # 缺少顶层必填键
        raw = self._valid_decisions_dict()
        del raw["edition_part_artifact_id"]
        with self.assertRaises(DigitizationRefused) as ctx:
            load_decisions(raw)
        self.assertEqual(ctx.exception.code, "SCH_001")

        # entry 缺少必填键
        raw2 = self._valid_decisions_dict()
        del raw2["entries"][0]["decided_by"]
        with self.assertRaises(DigitizationRefused) as ctx:
            load_decisions(raw2)
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_load_decisions_bad_terminal_state_SCH_002(self):
        """synthetic_fixture: true，非法 terminal_state 报 SCH_002。"""
        raw = self._valid_decisions_dict()
        raw["entries"][0]["terminal_state"] = "unknown_state"
        with self.assertRaises(DigitizationRefused) as ctx:
            load_decisions(raw)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_load_decisions_empty_reason_SCH_001(self):
        """synthetic_fixture: true，reason 为空串报 SCH_001。"""
        raw = self._valid_decisions_dict()
        raw["entries"][0]["reason"] = "   "
        with self.assertRaises(DigitizationRefused) as ctx:
            load_decisions(raw)
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_load_decisions_bad_schema_version_SCH_002(self):
        """synthetic_fixture: true，非法 schema_version 报 SCH_002。"""
        raw = self._valid_decisions_dict()
        raw["schema_version"] = "2.0.0"
        with self.assertRaises(DigitizationRefused) as ctx:
            load_decisions(raw)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_check_decisions_coverage_all_decided(self):
        """synthetic_fixture: true，所有 deferred 均有决定 → 返回空列表。"""
        decisions = self._valid_decisions_dict()
        findings = [
            Finding(
                finding_id="missing@10-15",
                kind="missing",
                raw_start=10,
                raw_end=15,
                raw_excerpt="[缺字]",
                context="...",
                action="flagged",
                patch_id=None,
                basis="basis",
                terminal_state="deferred",
            )
        ]
        missing = check_decisions_coverage(decisions, findings)
        self.assertEqual(missing, [])

    def test_check_decisions_coverage_missing_deferred(self):
        """synthetic_fixture: true，deferred 缺少决定 → 返回缺失 finding_id。"""
        decisions = self._valid_decisions_dict()
        findings = [
            Finding(
                finding_id="missing@10-15",
                kind="missing",
                raw_start=10,
                raw_end=15,
                raw_excerpt="[缺字]",
                context="...",
                action="flagged",
                patch_id=None,
                basis="basis",
                terminal_state="deferred",
            ),
            Finding(
                finding_id="missing@20-25",
                kind="missing",
                raw_start=20,
                raw_end=25,
                raw_excerpt="[缺字2]",
                context="...",
                action="flagged",
                patch_id=None,
                basis="basis",
                terminal_state="deferred",
            ),
        ]
        missing = check_decisions_coverage(decisions, findings)
        self.assertEqual(missing, ["missing@20-25"])

    def test_check_decisions_coverage_non_deferred_not_required(self):
        """synthetic_fixture: true，非 deferred finding 不需要决定。"""
        decisions = {
            "schema_version": "1.0.0",
            "edition_part_artifact_id": "art_000000000000000000000000000000e1",
            "entries": [],
        }
        findings = [
            Finding(
                finding_id="control_char@0-1",
                kind="control_char",
                raw_start=0,
                raw_end=1,
                raw_excerpt="\u200b",
                context="...",
                action="patched",
                patch_id="patch_001",
                basis="basis",
                terminal_state="processed",
            )
        ]
        missing = check_decisions_coverage(decisions, findings)
        self.assertEqual(missing, [])

    def test_decisions_modification_does_not_affect_input(self):
        """synthetic_fixture: true，load_decisions 返回深拷贝，修改不影响入参。"""
        raw = self._valid_decisions_dict()
        raw_copy = copy.deepcopy(raw)
        res = load_decisions(raw)
        res["entries"][0]["reason"] = "被外部篡改"
        self.assertEqual(raw, raw_copy)


if __name__ == "__main__":
    unittest.main()
