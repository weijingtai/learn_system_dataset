"""ACT impl-08/00：Contract Registry 目录的单元测试（规格 §5/§19 L2'）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/contract_registry/tests -t .`
因 `pipeline.contract_registry` 尚不存在而全红。

统一脚手架：读仓库 `registry.yaml` 为 dict，deepcopy 后篡改，经 `Registry.from_dict`
构造（tempfile 仅用于路径类用例）。所有用例只读仓库登记表，绝不写 var/ 或 fixture。
"""

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"

from pipeline.contract_registry.catalog import (  # noqa: E402
    HUMAN_QUEUES_EXPECTED,
    L0_SCHEMA_IDS,
    STAGE_ROWS_EXPECTED,
    Registry,
    check_registry,
    interface_fingerprint,
    load_registry,
)
from pipeline.contract_registry.errors import RegistryInvalid  # noqa: E402


def _subprocess_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["LC_ALL"] = "en_US.UTF-8"
    return env


class CatalogTestBase(unittest.TestCase):
    """公共脚手架：仓库登记表副本与问题码提取。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    def mutated(self, fn, *, allow_stub=False):
        doc = copy.deepcopy(self.doc)
        fn(doc)
        return Registry.from_dict(doc, repo_root=REPO_ROOT, allow_stub=allow_stub)

    def codes(self, registry, **kwargs):
        return [problem["code"] for problem in check_registry(registry, **kwargs)]

    def _find_schema(self, doc, schema_id):
        for entry in doc["schemas"]:
            if entry["schema_id"] == schema_id:
                return entry
        raise AssertionError("登记表缺少 schema_id: %s" % schema_id)


class TestRegistryCatalog(CatalogTestBase):
    """覆盖 BDD §1：登记表一致性、闭集、指纹与 CLI。"""

    def test_repository_registry_is_consistent(self):
        self.assertEqual(check_registry(load_registry()), [])

    def test_schema_sha256_mismatch_detected(self):
        def tamper(doc):
            self._find_schema(doc, "step_request")["sha256"] = "0" * 64

        self.assertIn("schema_sha256_mismatch", self.codes(self.mutated(tamper)))

    def test_schema_path_missing_detected(self):
        def tamper(doc):
            self._find_schema(doc, "step_result")["path"] = (
                "openspec/schemas/does_not_exist.schema.json"
            )

        self.assertIn("schema_path_missing", self.codes(self.mutated(tamper)))

    def test_schema_version_not_1_0_0_detected(self):
        def tamper(doc):
            self._find_schema(doc, "artifact_ref")["schema_version"] = "2.0.0"

        self.assertIn("schema_version_invalid", self.codes(self.mutated(tamper)))

    def test_stage_rows_verbatim_section_19(self):
        def tamper(doc):
            doc["stage_rows"]["m6"] = "M6 Review Workshoppe"

        self.assertIn("stage_rows_mismatch", self.codes(self.mutated(tamper)))

    def test_human_queues_verbatim_section_5(self):
        def tamper(doc):
            doc["human_queues"]["m7"] = "M7 待裁定"

        self.assertIn("human_queues_mismatch", self.codes(self.mutated(tamper)))

    def test_module_stage_out_of_closed_set_detected(self):
        def tamper(doc):
            doc["modules"][0]["stage"] = "m9"

        self.assertIn("stage_invalid", self.codes(self.mutated(tamper)))

    def test_duplicate_module_id_detected(self):
        def tamper(doc):
            doc["modules"].append(copy.deepcopy(doc["modules"][0]))

        self.assertIn("module_id_duplicate", self.codes(self.mutated(tamper)))

    def test_imported_with_entry_forbidden(self):
        def tamper(doc):
            doc["modules"][0]["entry"] = "pipeline.foo:bar"

        self.assertIn("entry_forbidden", self.codes(self.mutated(tamper)))

    def test_consumes_from_later_stage_detected(self):
        def tamper(doc):
            doc["modules"][1]["consumes"] = [
                {"artifact_type": "ocr_page_set", "from_stage": "m3"}
            ]

        self.assertIn("consumes_stage_order", self.codes(self.mutated(tamper)))

    def test_stub_in_production_detected_and_allowed_with_flag(self):
        def tamper(doc):
            doc["modules"][0]["kind"] = "stub"

        self.assertIn("stub_in_production", self.codes(self.mutated(tamper)))
        allowed = self.mutated(tamper, allow_stub=True)
        self.assertNotIn("stub_in_production", self.codes(allowed))

    def test_port_closed_set_enforced(self):
        def drop_index(doc):
            doc["ports"] = [p for p in doc["ports"] if p["port_id"] != "index"]

        def add_graph(doc):
            doc["ports"].append(
                {"port_id": "graph", "adjacent_interface": [], "adapters": []}
            )

        self.assertIn("port_invalid", self.codes(self.mutated(drop_index)))
        self.assertIn("port_invalid", self.codes(self.mutated(add_graph)))

    def test_module_for_zero_one_many(self):
        registry = Registry.from_dict(copy.deepcopy(self.doc), repo_root=REPO_ROOT)
        # TODO T04B：m7 已登记生产 Module；「0 个」改用删掉 m7 条目的副本来证。
        self.assertEqual(
            registry.module_for("m7")["module_id"], "m7.incremental_assembly"
        )
        without_m7 = self.mutated(
            lambda doc: doc.__setitem__(
                "modules", [m for m in doc["modules"] if m["stage"] != "m7"]
            )
        )
        self.assertIsNone(without_m7.module_for("m7"))
        self.assertEqual(
            registry.module_for("m5")["module_id"], "m5.automatic_validation"
        )

        doc = copy.deepcopy(self.doc)
        doc["modules"].append(
            {
                "module_id": "m3.other",
                "stage": "m3",
                "kind": "production",
                "binding": "legacy_self_driving",
                "entry": "pipeline.corpus_compiler.step:run_m3",
                "version": "0.1.0",
                "consumes": [],
                "produces": [{"artifact_type": "corpus_package"}],
                "human_queue": False,
                "supports_recovery": False,
                "entry_kwargs": {},
                "owns_processing_run": False,
            }
        )
        many = Registry.from_dict(doc, repo_root=REPO_ROOT)
        with self.assertRaises(RegistryInvalid):
            many.module_for("m3")

    def test_legacy_entry_kwargs_carried(self):
        registry = Registry.from_dict(copy.deepcopy(self.doc), repo_root=REPO_ROOT)
        by_id = registry.modules_by_id()
        self.assertEqual(
            by_id["m5.automatic_validation"]["entry_kwargs"],
            {"target_consumption_level": "INTERNAL_DEMO"},
        )
        self.assertIs(
            by_id["m8.dataset_compilation"]["owns_processing_run"], True
        )
        self.assertEqual(
            by_id["m8.dataset_compilation"]["entry_kwargs"],
            {"consumption_level": "INTERNAL_DEMO"},
        )

        def tamper(doc):
            for module in doc["modules"]:
                if module["module_id"] == "m5.automatic_validation":
                    module["entry_kwargs"] = "INTERNAL_DEMO"
                if module["module_id"] == "m8.dataset_compilation":
                    module["owns_processing_run"] = "yes"

        codes = self.codes(self.mutated(tamper))
        self.assertIn("entry_kwargs_invalid", codes)
        self.assertIn("owns_processing_run_invalid", codes)

    def test_m7_registered_as_release_production_module(self):
        """TODO T04B：M7 登记为发布段生产模块（人工节点 M7 待裁决），M8 消费 M7 Snapshot。"""
        registry = load_registry()
        m7 = registry.module_for("m7")
        self.assertIsNotNone(m7, "m7 未登记")
        self.assertEqual(m7["module_id"], "m7.incremental_assembly")
        self.assertEqual(m7["kind"], "production")
        self.assertEqual(m7["binding"], "legacy_self_driving")
        self.assertEqual(m7["entry"], "pipeline.assembly.entry:run_m7")
        self.assertIs(m7["human_queue"], True)
        # run_m7 自建 release_run ProcessingRun
        self.assertIs(m7["owns_processing_run"], True)
        self.assertIn({"artifact_type": "stage_package", "from_stage": "m6"}, m7["consumes"])
        m8 = registry.module_for("m8")
        self.assertIn(
            {"artifact_type": "canonical_snapshot", "from_stage": "m7"}, m8["consumes"]
        )
        # 登记表一致性（含 entry 可解析）必须仍通过
        self.assertEqual(check_registry(registry, resolve_entries=True), [])

    def test_fingerprint_ignores_version_but_not_produces(self):
        registry = Registry.from_dict(copy.deepcopy(self.doc), repo_root=REPO_ROOT)
        baseline = interface_fingerprint(registry, "m3.corpus_structural")

        doc = copy.deepcopy(self.doc)
        for module in doc["modules"]:
            if module["module_id"] == "m3.corpus_structural":
                module["version"] = "9.9.9"
        versioned = Registry.from_dict(doc, repo_root=REPO_ROOT)
        self.assertEqual(
            baseline, interface_fingerprint(versioned, "m3.corpus_structural")
        )

        doc = copy.deepcopy(self.doc)
        for module in doc["modules"]:
            if module["module_id"] == "m3.corpus_structural":
                module["produces"] = [{"artifact_type": "other_package"}]
        changed = Registry.from_dict(doc, repo_root=REPO_ROOT)
        self.assertNotEqual(
            baseline, interface_fingerprint(changed, "m3.corpus_structural")
        )

    def test_cli_ok_and_invalid_exit_codes(self):
        env = _subprocess_env()
        ok = subprocess.run(
            [sys.executable, "-m", "pipeline.contract_registry", "check"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(ok.returncode, 0, ok.stderr.decode("utf-8"))
        self.assertEqual(
            ok.stdout.decode("utf-8").strip().splitlines()[-1],
            "REGISTRY OK modules=8 ports=4",
        )

        doc = copy.deepcopy(self.doc)
        doc["stage_rows"]["m6"] = "M6 Review Workshoppe"
        bad_path = Path(self._tmp.name) / "bad-registry.yaml"
        bad_path.write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        bad = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.contract_registry",
                "check",
                "--registry",
                str(bad_path),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(bad.returncode, 1, bad.stderr.decode("utf-8"))
        self.assertTrue(
            bad.stdout.decode("utf-8").strip().splitlines()[-1].startswith(
                "REGISTRY INVALID"
            )
        )


if __name__ == "__main__":
    unittest.main()
