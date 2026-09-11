import unittest
import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.resolve()
VALIDATOR = TOOLS_DIR / "validate_fixtures.py"
SPEC_DIR = TOOLS_DIR.parent
REAL_FIXTURES = SPEC_DIR / "fixtures" / "community"
STATE_MACHINES = SPEC_DIR / "contracts" / "state-machines.md"

# Import load_enum_table from validate_fixtures
sys.path.insert(0, str(TOOLS_DIR))
import validate_fixtures

class TestValidateFixtures(unittest.TestCase):
    def setUp(self):
        # Helper to create a temp fixture tree with contracts
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        (base / "spec" / "contracts").mkdir(parents=True)
        shutil.copy(STATE_MACHINES, base / "spec" / "contracts" / "state-machines.md")
        shutil.copytree(REAL_FIXTURES, base / "spec" / "fixtures" / "community")
        self.fixture_dir = base / "spec" / "fixtures" / "community"

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_validator(self, target_dir):
        res = subprocess.run(
            [sys.executable, str(VALIDATOR), str(target_dir)],
            capture_output=True,
            text=True
        )
        return res

    def test_real_fixtures_pass(self):
        res = self.run_validator(REAL_FIXTURES)
        self.assertEqual(res.returncode, 0, f"Validator failed on real fixtures: {res.stderr} {res.stdout}")
        lines = res.stdout.strip().splitlines()
        self.assertTrue(lines, "stdout should not be empty")
        self.assertEqual(lines[-1], "FIXTURES_OK 9 files 198 cases")

    def test_missing_expected_red(self):
        path = self.fixture_dir / "limit_cases.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        del data["cases"][0]["expected"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        res = self.run_validator(self.fixture_dir)
        self.assertEqual(res.returncode, 1)
        self.assertIn("limit_cases.json#note_markdown_exactly_1MiB: missing expected", res.stdout)

    def test_unknown_state_red(self):
        path = self.fixture_dir / "state_combinations.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["cases"][0]["lifecycle"] = "Purged"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        res = self.run_validator(self.fixture_dir)
        self.assertEqual(res.returncode, 1)
        self.assertIn("unknown state value 'Purged'", res.stdout)

    def test_bad_id_red(self):
        path = self.fixture_dir / "comment_reply_cases.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["cases"][0]["request"]["thread_id"] = "thr_XYZ"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        res = self.run_validator(self.fixture_dir)
        self.assertEqual(res.returncode, 1)
        self.assertIn("bad id 'thr_XYZ'", res.stdout)

    def test_equal_hash_to_red(self):
        path = self.fixture_dir / "content_hash_cases.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for c in data["cases"]:
            if c.get("name") == "C02_object_keys_reordered":
                # modify last hex character of expected_hash
                h = c["expected_hash"]
                c["expected_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
                break
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        res = self.run_validator(self.fixture_dir)
        self.assertEqual(res.returncode, 1)
        self.assertIn("equal_hash_to mismatch", res.stdout)

    def test_missing_dir_exit2(self):
        non_existent = self.fixture_dir.parent / "non_existent_dir_12345"
        res = self.run_validator(non_existent)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(res.stdout, "")
        stderr_lines = res.stderr.strip().splitlines()
        self.assertEqual(len(stderr_lines), 1, f"Expected exactly 1 line in stderr, got: {res.stderr}")
        self.assertNotIn("Traceback", res.stderr)

    def test_enum_table_parsed(self):
        rows, enum_values = validate_fixtures.load_enum_table(STATE_MACHINES)
        self.assertEqual(len(rows), 11, f"Expected 11 rows in enum table, got {len(rows)}")
        self.assertEqual(len(enum_values), 41, f"Expected 41 unique enum values, got {len(enum_values)}")
        for expected_val in ["purge_pending", "ime_composing", "retained", "degraded", "visible"]:
            self.assertIn(expected_val, enum_values, f"Expected '{expected_val}' in enum values")

if __name__ == "__main__":
    unittest.main()
