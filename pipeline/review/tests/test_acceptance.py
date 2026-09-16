import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.ledger.service import LedgerService
from pipeline.review import acceptance

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
DATA_DIR = ROOT / "pipeline" / "review" / "testing" / "data"
SHELL = ROOT / "openspec" / "acceptance" / "m6-data-fields.sh"


def _run_main(argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = acceptance.main(argv)
    return code, stream.getvalue()


class TestAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.service, cls.world = acceptance._prepare(
            FIXTURE_DIR, DATA_DIR / "expected_review.yaml"
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _clone_world(self):
        test_tmp = tempfile.mkdtemp(prefix="m6-test-clone-")
        self.addCleanup(lambda: shutil.rmtree(test_tmp, ignore_errors=True))
        shutil.copytree(self.tmp, test_tmp, dirs_exist_ok=True)
        s2 = LedgerService(Path(test_tmp) / "ledger")
        w2 = dict(self.world)
        w2["service"] = s2
        w2["expected"] = copy.deepcopy(self.world["expected"])
        return w2

    def test_fixture_yields_thirteen_pass_two_blocked_exit_2(self):
        code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 2)
        lines = out.splitlines()
        self.assertEqual(len([l for l in lines if l.startswith("PASS ")]), 13)
        self.assertEqual(len([l for l in lines if l.startswith("BLOCKED ")]), 2)
        self.assertEqual(lines[-1], "SUMMARY pass=13 fail=0 blocked=2")

    def test_blocked_lines_exact_text(self):
        _code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertNotIn("BLOCKED snapshot_projection", out)
        self.assertIn(
            "BLOCKED legacy_workbench_seed 前置缺失: M6 Review Workbench；"
            "pattern_knowledge_workbench 旧数据体未迁入（准入判定见 run_all 20.7）",
            out,
        )
        self.assertIn(
            "BLOCKED upstream_real 前置缺失: 真实 expert_verified 签发决定表由用户撰写（第 80 条签发决定表）；旧工作台数据迁入；M5 候选级校验未实现",
            out,
        )

    def test_expected_review_tampered_fails(self):
        tmp = tempfile.mkdtemp(prefix="m6-acceptance-expected-")
        self.addCleanup(shutil.rmtree, tmp, True)
        expected = yaml.safe_load((DATA_DIR / "expected_review.yaml").read_text(encoding="utf-8"))
        expected["rework"]["invalidated_count"] = expected["rework"]["invalidated_count"] + 1
        tampered = Path(tmp) / "expected_review.yaml"
        tampered.write_text(yaml.safe_dump(expected, allow_unicode=True), encoding="utf-8")

        code, out = _run_main(
            ["--fixture", str(FIXTURE_DIR), "--expected", str(tampered)]
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL precise_invalidation", out)

    def test_deleted_decision_event_fails(self):
        original = acceptance._step.record_decision
        counter = {"calls": 0}

        def wrapper(service, step_run_id, token, **kwargs):
            counter["calls"] += 1
            if counter["calls"] != 1:
                return original(service, step_run_id, token, **kwargs)
            original_write_checkpoint = service.write_checkpoint
            service.write_checkpoint = lambda *a, **k: None
            try:
                return original(service, step_run_id, token, **kwargs)
            finally:
                service.write_checkpoint = original_write_checkpoint

        with mock.patch.object(acceptance._step, "record_decision", side_effect=wrapper):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL checkpoint_per_decision", out)

    def test_cross_module_status_change_detected(self):
        original = acceptance._prepare

        def wrapper(fixture_dir, expected_path):
            tmp, service, world = original(fixture_dir, expected_path)
            row = service.store.conn.execute(
                "SELECT r.artifact_revision_id FROM artifact_revisions r "
                "JOIN step_runs s ON s.step_run_id = r.step_run_id "
                "WHERE s.stage='m4' AND r.status='sealed' LIMIT 1"
            ).fetchone()
            service.invalidate_revision(row[0], "acceptance-test")
            return tmp, service, world

        with mock.patch.object(acceptance, "_prepare", side_effect=wrapper):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL no_cross_module_status_change", out)

    def test_prepare_failure_exits_1(self):
        with mock.patch.object(
            acceptance, "seed_upstream", side_effect=RuntimeError("boom")
        ):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertTrue(
            out.splitlines()[0].startswith(
                "FAIL m6_acceptance 宿主准备失败: RuntimeError"
            ),
            out.splitlines()[0],
        )

    def test_missing_fixture_exit_3(self):
        code, out = _run_main(["--fixture", "/nonexistent-fixture-dir-xyz"])
        self.assertEqual(code, 3)
        self.assertIn("BLOCKED m6_acceptance 前置缺失", out)

    def _run_shell(self, fixture_dir=None):
        env = os.environ.copy()
        env["LC_ALL"] = "en_US.UTF-8"
        env["PYTHONPATH"] = str(ROOT)
        if fixture_dir is not None:
            env["FIXTURE_DIR"] = str(fixture_dir)
        return subprocess.run(
            ["bash", str(SHELL)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )

    def test_shell_exit_2_on_fixture(self):
        res = self._run_shell()
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        lines = [l for l in res.stdout.splitlines() if l.strip()]
        self.assertEqual(lines[-1], "SUMMARY pass=13 fail=0 blocked=2")

    def test_shell_never_trusts_copy_verify(self):
        tmp = tempfile.mkdtemp(prefix="m6-acceptance-copy-")
        self.addCleanup(shutil.rmtree, tmp, True)
        copy_dir = Path(tmp) / "mini_ed01"
        shutil.copytree(FIXTURE_DIR, copy_dir)
        spans_path = copy_dir / "spans.yaml"
        spans_doc = yaml.safe_load(spans_path.read_text(encoding="utf-8"))
        spans_doc["spans"] = spans_doc["spans"][:-1]
        spans_doc["span_count"] = len(spans_doc["spans"])
        spans_path.write_text(
            yaml.safe_dump(spans_doc, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        fake_verify = copy_dir / "verify.sh"
        fake_verify.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_verify.chmod(0o755)

        res = self._run_shell(fixture_dir=copy_dir)
        self.assertEqual(res.returncode, 1, res.stderr + res.stdout)
        first = res.stdout.splitlines()[0]
        self.assertTrue(first.startswith("FAIL fixture_host"), first)

    def test_snapshot_projection_passes_and_approved_match(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        re_doc = acceptance._doc(w["service"], w["rework_close"]["reviewed_edition_revision_id"])
        snap_rev = w["service"].get_revision(w["snapshot_revision_id"])
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        k = snap_doc.get("knowledge", snap_doc)
        app_assertions = {a["entity_id"] for a in re_doc.get("approved", []) if a.get("kind") == "assertion"}
        snap_assertions = {a["assertion_id"] for a in k.get("assertions", [])}
        self.assertEqual(app_assertions, snap_assertions)
        app_svs = {a["entity_id"] for a in re_doc.get("approved", []) if a.get("kind") == "school_view"}
        snap_svs = {s["school_view_id"] for s in k.get("school_views", [])}
        self.assertEqual(app_svs, snap_svs)

    def test_snapshot_projection_detects_approved_mismatch(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        snap_rev_id = w["snapshot_revision_id"]
        snap_rev = w["service"].get_revision(snap_rev_id)
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        # 破坏 approved：从 Snapshot assertions 中移除一个对象，断言检出 approved 不符
        k = snap_doc.get("knowledge", snap_doc)
        k["assertions"] = k["assertions"][:-1]
        new_bytes = json.dumps(snap_doc).encode("utf-8")
        new_sha = hashlib.sha256(new_bytes).hexdigest()
        w["service"].objects.put(new_bytes)
        w["service"].store.conn.execute(
            "UPDATE artifact_revisions SET sha256=? WHERE artifact_revision_id=?",
            (new_sha, snap_rev_id),
        )
        w["service"].store.conn.commit()
        errs = acceptance._check_snapshot_projection(w)
        self.assertTrue(
            any("approved assertions 与 Snapshot assertions 不符" in e for e in errs),
            errs,
        )

    def test_snapshot_projection_evidence_links_consistent(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        re_doc = acceptance._doc(w["service"], w["rework_close"]["reviewed_edition_revision_id"])
        snap_rev = w["service"].get_revision(w["snapshot_revision_id"])
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        k = snap_doc.get("knowledge", snap_doc)
        re_evidence = {e["source_span_id"] for e in re_doc.get("evidence_links", [])}
        snap_evidence = {
            ev["source_span_id"]
            for a in k.get("assertions", [])
            for ev in a.get("evidence", [])
            if ev.get("source_span_id")
        }
        self.assertEqual(re_evidence, snap_evidence)

    def test_snapshot_projection_detects_evidence_links_mismatch(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        snap_rev_id = w["snapshot_revision_id"]
        snap_rev = w["service"].get_revision(snap_rev_id)
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        # 破坏 evidence_links：篡改 Snapshot 中 assertion 的 source_span_id，断言检出不一致
        k = snap_doc.get("knowledge", snap_doc)
        k["assertions"][0]["evidence"][0]["source_span_id"] = "ss_sanche_ed01_p0099_s99"
        new_bytes = json.dumps(snap_doc).encode("utf-8")
        new_sha = hashlib.sha256(new_bytes).hexdigest()
        w["service"].objects.put(new_bytes)
        w["service"].store.conn.execute(
            "UPDATE artifact_revisions SET sha256=? WHERE artifact_revision_id=?",
            (new_sha, snap_rev_id),
        )
        w["service"].store.conn.commit()
        errs = acceptance._check_snapshot_projection(w)
        self.assertTrue(
            any("evidence_links 不一致" in e for e in errs),
            errs,
        )

    def test_snapshot_projection_content_status_expert_verified(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        snap_rev = w["service"].get_revision(w["snapshot_revision_id"])
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        k = snap_doc.get("knowledge", snap_doc)
        for a in k.get("assertions", []):
            self.assertEqual(a.get("content_status"), "expert_verified")

    def test_snapshot_projection_detects_content_status_mismatch(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        snap_rev_id = w["snapshot_revision_id"]
        snap_rev = w["service"].get_revision(snap_rev_id)
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        # 破坏 content_status：将 approved assertion 的 content_status 改为 machine_extracted，断言检出
        k = snap_doc.get("knowledge", snap_doc)
        k["assertions"][0]["content_status"] = "machine_extracted"
        new_bytes = json.dumps(snap_doc).encode("utf-8")
        new_sha = hashlib.sha256(new_bytes).hexdigest()
        w["service"].objects.put(new_bytes)
        w["service"].store.conn.execute(
            "UPDATE artifact_revisions SET sha256=? WHERE artifact_revision_id=?",
            (new_sha, snap_rev_id),
        )
        w["service"].store.conn.commit()
        errs = acceptance._check_snapshot_projection(w)
        self.assertTrue(
            any("content_status 非 expert_verified" in e for e in errs),
            errs,
        )

    def test_snapshot_projection_rejected_not_in_snapshot(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        re_doc = acceptance._doc(w["service"], w["rework_close"]["reviewed_edition_revision_id"])
        snap_rev = w["service"].get_revision(w["snapshot_revision_id"])
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        k = snap_doc.get("knowledge", snap_doc)
        rejected_ids = {r["entity_id"] for r in re_doc.get("rejected", [])}
        snap_ids = {a["assertion_id"] for a in k.get("assertions", [])} | {
            s["school_view_id"] for s in k.get("school_views", [])
        }
        self.assertTrue(rejected_ids)
        self.assertEqual(rejected_ids & snap_ids, set())

    def test_snapshot_projection_detects_rejected_in_snapshot(self):
        w = self._clone_world()
        errors = acceptance._check_snapshot_projection(w)
        self.assertEqual(errors, [])
        snap_rev_id = w["snapshot_revision_id"]
        snap_rev = w["service"].get_revision(snap_rev_id)
        snap_doc = json.loads(w["service"].objects.get(snap_rev["sha256"]).decode("utf-8"))
        # 破坏 rejected_not_in_snapshot：将 rejected ID 注入 Snapshot assertions，断言检出泄漏
        k = snap_doc.get("knowledge", snap_doc)
        leaked_obj = copy.deepcopy(k["assertions"][0])
        leaked_obj["assertion_id"] = "as_qizheng_000002"
        k["assertions"].append(leaked_obj)
        new_bytes = json.dumps(snap_doc).encode("utf-8")
        new_sha = hashlib.sha256(new_bytes).hexdigest()
        w["service"].objects.put(new_bytes)
        w["service"].store.conn.execute(
            "UPDATE artifact_revisions SET sha256=? WHERE artifact_revision_id=?",
            (new_sha, snap_rev_id),
        )
        w["service"].store.conn.commit()
        errs = acceptance._check_snapshot_projection(w)
        self.assertTrue(
            any("rejected entity_id 出现在 Snapshot 中" in e for e in errs),
            errs,
        )

    def test_first_review_counts_match(self):
        w = self._clone_world()
        errors = acceptance._check_first_review_counts(w)
        self.assertEqual(errors, [])

    def test_first_review_counts_detects_mismatch(self):
        w = self._clone_world()
        w["expected"]["first_review"]["decisions"] = 999
        errors = acceptance._check_first_review_counts(w)
        self.assertTrue(
            any("first_review.decisions 计数 999 != human_decisions 计数 5" in e for e in errors),
            errors,
        )

    def test_shell_summary_pass_13_fail_0_blocked_2(self):
        res = self._run_shell()
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        lines = [l for l in res.stdout.splitlines() if l.strip()]
        self.assertEqual(lines[-1], "SUMMARY pass=13 fail=0 blocked=2")


if __name__ == "__main__":
    unittest.main()
