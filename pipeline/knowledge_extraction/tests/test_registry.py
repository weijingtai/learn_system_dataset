"""ACT 03 Registry Adapter（technique_profile）的单测（先红后绿）。"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.knowledge_extraction.adapters.registry import (
    build_technique_profile,
    register_technique_profile,
)
from pipeline.ledger.errors import InvalidIdentifier
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
EDITION_PART = "art_000000000000000000000000000000e1"


class RegistryTests(unittest.TestCase):
    def test_profile_concepts_equal_closed_set_sizes(self):
        data = build_technique_profile(technique_id="qizheng", canon_dir=CANON_DIR)
        profile = json.loads(data.decode("utf-8"))
        expected = 0
        for path in sorted(CANON_DIR.glob("*.yaml")):
            expected += yaml.safe_load(path.read_text(encoding="utf-8"))["closed_set_size"]
        self.assertEqual(expected, 49)
        self.assertEqual(len(profile["canon"]["concepts"]), expected)
        self.assertEqual(profile["homographs"], [])
        self.assertEqual(profile["glossary"], [])
        self.assertEqual(profile["schools"], [])
        self.assertEqual(profile["technique_id"], "qizheng")
        self.assertEqual(len(profile["canon"]["files"]), 6)

    def test_profile_bytes_deterministic(self):
        first = build_technique_profile(technique_id="qizheng", canon_dir=CANON_DIR)
        second = build_technique_profile(technique_id="qizheng", canon_dir=CANON_DIR)
        self.assertEqual(first, second)

    def test_profile_rejects_bad_concept_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "canon"
            shutil.copytree(CANON_DIR, target)
            path = target / "stem.yaml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("co_shared_stem_01", "co_shared_bad", 1), encoding="utf-8"
            )
            with self.assertRaises(InvalidIdentifier):
                build_technique_profile(technique_id="qizheng", canon_dir=target)

    def test_register_profile_is_sealed_run_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = LedgerService(Path(tmp) / "ledger")
            self.addCleanup(service.close)
            service.create_processing_run("edition_run", EDITION_PART, "qizheng")
            row = service.store.conn.execute(
                "SELECT processing_run_id FROM processing_runs"
            ).fetchone()
            revision_id = register_technique_profile(
                service, row[0], technique_id="qizheng", canon_dir=CANON_DIR
            )
            stored = service.get_revision(revision_id)
            self.assertEqual(stored["status"], "sealed")
            self.assertEqual(service._artifact_type(revision_id), "technique_profile")


if __name__ == "__main__":
    unittest.main()
