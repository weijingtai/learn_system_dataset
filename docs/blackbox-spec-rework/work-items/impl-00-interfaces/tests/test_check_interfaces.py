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
REPO = W.parents[3]
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

    def test_m2_et_required_types_present(self):
        res = statuses(ci.run_checks(REPO_DOC))
        for num in ("IF30", "IF31", "IF32", "IF33"):
            self.assertEqual(res[num], "PASS")

    def test_m2_et_type_missing_fails(self):
        res = statuses(
            ci.run_checks(self._copy(self._drop_lines(self.text, "`raw_text`")))
        )
        self.assertEqual(res["IF30"], "FAIL")

    def test_m2_et_type_marked_deferred_fails(self):
        text = self._mutate_status_cell(self.text, "`cleaned_text_revision`", "纵切后")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF11"], "FAIL")

    def test_m2_et_duplicate_type_fails(self):
        out = []
        for line in self.text.splitlines():
            out.append(line)
            if line.lstrip().startswith("|") and "`sanitization_report`" in line:
                out.append(line)
        res = statuses(ci.run_checks(self._copy("\n".join(out) + "\n")))
        self.assertEqual(res["IF10"], "FAIL")

    def test_sanitization_report_keyset_missing_fails(self):
        # 删去 finding_id 说明行
        text = self.text.replace("finding_id", "NO_FINDING_ID")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF34"], "FAIL")

    def test_ss_offset_form_missing_fails(self):
        # 副本的 registry 缺 o<NNNNNNN>
        registry_path = W.parent.parent.parent.parent / "openspec" / "id-prefix-registry.md"
        if registry_path.is_file():
            registry_text = registry_path.read_text(encoding="utf-8")
            modified_registry = registry_text.replace("o<NNNNNNN>", "NO_OFFSET")
            # 写入临时文件
            tmp_registry = self.tmp / "id-prefix-registry.md"
            tmp_registry.write_text(modified_registry, encoding="utf-8")
            res = statuses(ci.run_checks(REPO_DOC, tmp_registry))
            self.assertEqual(res["IF35"], "FAIL")

    def test_sem_prefix_missing_fails(self):
        # 副本的 registry 缺 sem_
        registry_path = W.parent.parent.parent.parent / "openspec" / "id-prefix-registry.md"
        if registry_path.is_file():
            registry_text = registry_path.read_text(encoding="utf-8")
            modified_registry = registry_text.replace("sem_", "NO_SEM_")
            # 写入临时文件
            tmp_registry = self.tmp / "id-prefix-registry.md"
            tmp_registry.write_text(modified_registry, encoding="utf-8")
            res = statuses(ci.run_checks(REPO_DOC, tmp_registry))
            self.assertEqual(res["IF36"], "FAIL")

    def test_missing_file_exit_3(self):
        rc = ci.main(["--file", str(self.tmp / "nope.md")])
        self.assertEqual(rc, 3)

    def test_m8_w8_required_type_present(self):
        res = statuses(ci.run_checks(REPO_DOC))
        self.assertEqual(res["IF40"], "PASS")

    def test_entry_id_allocation_missing_fails(self):
        res = statuses(
            ci.run_checks(self._copy(self._drop_lines(self.text, "`entry_id_allocation`")))
        )
        self.assertEqual(res["IF40"], "FAIL")

    def test_entry_id_allocation_marked_deferred_fails(self):
        text = self._mutate_status_cell(self.text, "`entry_id_allocation`", "纵切后")
        res = statuses(ci.run_checks(self._copy(text)))
        self.assertEqual(res["IF11"], "FAIL")

    def test_entry_id_allocation_duplicate_type_fails(self):
        out = []
        for line in self.text.splitlines():
            out.append(line)
            if line.lstrip().startswith("|") and "`entry_id_allocation`" in line:
                out.append(line)
        res = statuses(ci.run_checks(self._copy("\n".join(out) + "\n")))
        self.assertEqual(res["IF10"], "FAIL")

    def test_if41_graph_projection_edge_no_id_passes(self):
        res = statuses(ci.run_checks(REPO_DOC))
        self.assertEqual(res["IF41"], "PASS")

    def test_graph_projection_pack_with_edge_id_fails(self):
        tampered = self.text.replace(
            "{source, relation, target",
            "{edge_id, source, relation, target",
        )
        res = statuses(ci.run_checks(self._copy(tampered)))
        self.assertEqual(res["IF41"], "FAIL")

    def test_graph_projection_pack_with_e_prefix_fails(self):
        tampered = self.text.replace(
            '"relation": "belongs_to_concept"',
            '"edge_id": "e_018f9e740001", "relation": "belongs_to_concept"',
        )
        res = statuses(ci.run_checks(self._copy(tampered)))
        self.assertEqual(res["IF41"], "FAIL")

    def test_if42_graph_projection_node_id_passes(self):
        res = statuses(ci.run_checks(REPO_DOC))
        self.assertEqual(res["IF42"], "PASS")

    def test_graph_projection_pack_with_forbidden_prefix_fails(self):
        tampered = self.text.replace(
            '"node_id": "as_example_000001"',
            '"node_id": "c_example_000001"',
        )
        res = statuses(ci.run_checks(self._copy(tampered)))
        self.assertEqual(res["IF42"], "FAIL")

    def test_if43_evidence_map_7_keys_passes(self):
        res = statuses(ci.run_checks(REPO_DOC))
        self.assertEqual(res["IF43"], "PASS")

    def test_evidence_map_pack_with_8_keys_fails(self):
        tampered = self.text.replace(
            "必须恰含 7 个键",
            "每条 chain 包含 8 个键",
        )
        res = statuses(ci.run_checks(self._copy(tampered)))
        self.assertEqual(res["IF43"], "FAIL")

    def test_if44_m8_checks_passes_with_xfail_on_repo(self):
        raw_res = ci.run_checks(REPO_DOC)
        res = statuses(raw_res)
        self.assertEqual(res["IF44"], "PASS")
        reasons = {num: r for num, _, r in raw_res}
        self.assertTrue(reasons["IF44"].startswith("XFAIL: gate.py 待实现新增"), reasons["IF44"])

    def test_if44_m8_checks_missing_fails(self):
        tampered = self.text.replace("`chain_closure`", "`NO_CHAIN_CLOSURE`")
        res = statuses(ci.run_checks(self._copy(tampered)))
        self.assertEqual(res["IF44"], "FAIL")

    def test_if44_gate_file_missing_fails(self):
        fake_gate = self.tmp / "nonexistent_gate.py"
        res = statuses(ci.run_checks(REPO_DOC, gate_path=fake_gate))
        self.assertEqual(res["IF44"], "FAIL")

    def test_summary_line_format(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ci.main(["--file", str(REPO_DOC)])
        last = buf.getvalue().strip().splitlines()[-1]
        self.assertTrue(SUMMARY_RE.match(last), last)
        self.assertIn("fail=0", last)
        self.assertEqual(rc, 0)


class M2ClosedSetTest(unittest.TestCase):
    """第 103 条 D2（R83c）：kind / terminal_state 枚举的唯一权威在 impl-09 README 与代码常量。"""

    def setUp(self):
        self.text = REPO_DOC.read_text(encoding="utf-8")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.constants = (REPO / "pipeline" / "digitization" / "__init__.py").read_text(
            encoding="utf-8"
        )
        self.readme = W.parent / "impl-09-intake" / "README.md"

    def _copy(self, text: str) -> Path:
        path = self.tmp / "INTERFACES.md"
        path.write_text(text, encoding="utf-8")
        return path

    def _add_enum_clause(self, clause: str) -> Path:
        """把一条 ``∈ `{...}` `` 枚举子句插到 sanitization_report 行（键集之后）。"""
        anchor = "`kind` 与 `terminal_state` 的枚举"
        self.assertIn(anchor, self.text)
        patched = self.text.replace(anchor, clause + "；" + anchor, 1)
        return self._copy(patched)

    def test_if37_if38_pass_when_enums_not_restated(self):
        res = statuses(ci.run_checks(REPO_DOC))
        self.assertEqual(res["IF37"], "PASS")
        self.assertEqual(res["IF38"], "PASS")
        self.assertEqual(res["IF39"], "PASS")

    def test_restored_stale_kind_enum_fails(self):
        stale = "`kind` ∈ `{hook_variant, fallback_variant, orthographic_variant, truncated_source, numeral_mismatch}`"
        res = statuses(ci.run_checks(self._add_enum_clause(stale)))
        self.assertEqual(res["IF37"], "FAIL")
        self.assertEqual(res["IF38"], "PASS")

    def test_restored_stale_terminal_state_enum_fails(self):
        stale = "`terminal_state` ∈ `{patch_applied, superseded, deferred, terminal}`"
        res = statuses(ci.run_checks(self._add_enum_clause(stale)))
        self.assertEqual(res["IF38"], "FAIL")
        self.assertEqual(res["IF37"], "PASS")

    def test_kind_enum_matching_code_constants_passes(self):
        kinds = ci.code_tuple(self.constants, "FINDING_KINDS")
        clause = "`kind` ∈ `{%s}`" % ", ".join("`%s`" % kind for kind in kinds)
        res = statuses(ci.run_checks(self._add_enum_clause(clause)))
        self.assertEqual(res["IF37"], "PASS")

    def test_code_constants_drift_from_impl09_readme_fails(self):
        modified = self.readme.read_text(encoding="utf-8").replace(
            "`control_char`（控制字符）、", ""
        )
        readme_copy = self.tmp / "README.md"
        readme_copy.write_text(modified, encoding="utf-8")
        res = statuses(ci.run_checks(REPO_DOC, impl09_readme_path=readme_copy))
        self.assertEqual(res["IF39"], "FAIL")

    def test_missing_code_constants_fail(self):
        constants_copy = self.tmp / "digitization_init.py"
        constants_copy.write_text("# 空文件\n", encoding="utf-8")
        res = statuses(ci.run_checks(REPO_DOC, m2_constants_path=constants_copy))
        self.assertEqual(res["IF37"], "FAIL")
        self.assertEqual(res["IF38"], "FAIL")
        self.assertEqual(res["IF39"], "FAIL")


if __name__ == "__main__":
    unittest.main()
