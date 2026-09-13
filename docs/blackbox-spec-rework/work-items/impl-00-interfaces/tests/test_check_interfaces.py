# -*- coding: utf-8 -*-
"""impl-00/10 `check_interfaces.py` 的用例。

先于 INTERFACES.md 修改编写：此时 §4 缺 6 个新类型且残留 `gate_report`，
`test_required_type_missing_fails`、`test_forbidden_type_present_fails` 等应为 Red。
"""
from __future__ import annotations

import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

W = Path(__file__).resolve().parents[1]
if str(W) not in sys.path:
    sys.path.insert(0, str(W))

import check_interfaces as ci  # noqa: E402

REPO_DOC = W / "INTERFACES.md"
SUMMARY_RE = re.compile(r"^I00-IF SUMMARY pass=\d+ fail=\d+$")


def statuses(results):
    """[(编号, 状态, 原因)] → {编号: 状态}。"""
    return {num: status for num, status, _ in results}


class CheckInterfacesTest(unittest.TestCase):
    def setUp(self):
        self.text = REPO_DOC.read_text(encoding="utf-8")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _copy(self, text: str) -> Path:
        path = self.tmp / "INTERFACES.md"
        path.write_text(text, encoding="utf-8")
        return path

    def _drop_lines(self, text: str, needle: str) -> str:
        kept = [line for line in text.splitlines() if needle not in line]
        return "\n".join(kept) + "\n"

    def _mutate_status_cell(self, text: str, needle: str, status: str) -> str:
        out = []
        for line in text.splitlines():
            if line.lstrip().startswith("|") and needle in line:
                cells = line.split("|")
                cells[-2] = " %s " % status
                line = "|".join(cells)
            out.append(line)
        return "\n".join(out) + "\n"

    def test_if01_passes_on_repo_copy(self):
        self.assertEqual(statuses(ci.run_checks(REPO_DOC))["IF01"], "PASS")

    def test_required_type_missing_fails(self):
        res = statuses(ci.run_checks(self._copy(self._drop_lines(self.text, "`gate_results`"))))
        self.assertEqual(res["IF02"], "FAIL")

    def test_duplicate_type_fails(self):
        out = []
        for line in self.text.splitlines():
            out.append(line)
            if line.lstrip().startswith("|") and "`source_asset_pack`" in line:
                out.append(line)
        res = statuses(ci.run_checks(self._copy("\n".join(out) + "\n")))
        self.assertEqual(res["IF10"], "FAIL")

    def test_required_type_marked_deferred_fails(self):
        text = self._mutate_status_cell(self.text, "`release_manifest`", "纵切后")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF11"], "FAIL")

    def test_ruling_marker_missing_fails(self):
        res = statuses(ci.run_checks(self._copy(self.text.replace("corpus_only", "corpus-scope"))))
        self.assertEqual(res["IF13"], "FAIL")

    def test_forbidden_type_present_fails(self):
        marker = "\n## 5."
        row = "\n| M5 | `gate_report` | 任务级 | — | 纵切后 |\n"
        text = self.text.replace(marker, row + marker, 1)
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF18"], "FAIL")

    def test_m4_required_types_present(self):
        res = statuses(ci.run_checks(REPO_DOC))
        for num in ("IF19", "IF20", "IF21", "IF22", "IF23"):
            self.assertEqual(res[num], "PASS")

    def test_m4_type_missing_fails(self):
        res = statuses(
            ci.run_checks(self._copy(self._drop_lines(self.text, "`candidate_submission`")))
        )
        self.assertEqual(res["IF19"], "FAIL")

    def test_m4_type_marked_deferred_fails(self):
        text = self._mutate_status_cell(self.text, "`candidate_lane_set`", "纵切后")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF11"], "FAIL")

    def test_m4_duplicate_type_fails(self):
        out = []
        for line in self.text.splitlines():
            out.append(line)
            if line.lstrip().startswith("|") and "`dispute_queue`" in line:
                out.append(line)
        res = statuses(ci.run_checks(self._copy("\n".join(out) + "\n")))
        self.assertEqual(res["IF10"], "FAIL")

    def test_legacy_m4_name_present_fails(self):
        marker = "\n## 5."
        row = "\n| M4 | `candidate_batch` | 任务级 | — | 纵切后 |\n"
        text = self.text.replace(marker, row + marker, 1)
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF24"], "FAIL")

    def test_m6_required_types_present(self):
        res = statuses(ci.run_checks(REPO_DOC))
        for num in ("IF25", "IF26", "IF27", "IF28"):
            self.assertEqual(res[num], "PASS")

    def test_m6_type_missing_fails(self):
        res = statuses(ci.run_checks(self._copy(self._drop_lines(self.text, "`review_queue`"))))
        self.assertEqual(res["IF25"], "FAIL")

    def test_m6_type_marked_deferred_fails(self):
        text = self._mutate_status_cell(self.text, "`reviewed_edition`", "纵切后")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF11"], "FAIL")

    def test_m6_duplicate_type_fails(self):
        out = []
        for line in self.text.splitlines():
            out.append(line)
            if line.lstrip().startswith("|") and "`rework_impact_report`" in line:
                out.append(line)
        res = statuses(ci.run_checks(self._copy("\n".join(out) + "\n")))
        self.assertEqual(res["IF10"], "FAIL")

    def test_correction_request_type_present_fails(self):
        marker = "\n## 5."
        row = "\n| M6 | `correction_request` | 退回 | — | 纵切后 |\n"
        text = self.text.replace(marker, row + marker, 1)
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF29"], "FAIL")

    def test_missing_file_exit_3(self):
        rc = ci.main(["--file", str(self.tmp / "nope.md")])
        self.assertEqual(rc, 3)

    def test_summary_line_format(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ci.main(["--file", str(REPO_DOC)])
        last = buf.getvalue().strip().splitlines()[-1]
        self.assertTrue(SUMMARY_RE.match(last), last)
        self.assertIn("fail=0", last)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
