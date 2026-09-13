"""ACT impl-08/01：Adapter 替换判定（conformance）的单元测试（规格 §20.10）。

先写本文件，全红后再实现 `pipeline/contract_registry/conformance.py`。
假 Adapter 为内存对象，实现闭集方法（多数空实现）。
"""

import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

from pipeline.contract_registry.conformance import (  # noqa: E402
    normalize_outcome,
    substitution_report,
)
from pipeline.contract_registry.ports import (  # noqa: E402
    LEDGER_PORT_METHODS,
    DirectLedgerAdapter,
)
from pipeline.ledger import ids  # noqa: E402


def make_fake_port(*, events=("created",), step_status="succeeded"):
    """构造一个实现 LEDGER_PORT_METHODS 的内存假 Adapter。"""

    def run_status(self, processing_run_id):
        return {"status": "succeeded", "step_runs": [dict(self._step)]}

    def get_step_run(self, step_run_id):
        return dict(self._step)

    def list_transformations(self, step_run_id):
        return []

    def list_step_run_events(self, step_run_id):
        return [{"event_type": event} for event in self._events]

    namespace = {
        "run_status": run_status,
        "get_step_run": get_step_run,
        "list_transformations": list_transformations,
        "list_step_run_events": list_step_run_events,
    }
    for name in LEDGER_PORT_METHODS:
        namespace.setdefault(name, lambda self, *args, **kwargs: None)
    cls = type("FakePort", (object,), namespace)
    port = cls()
    port._events = list(events)
    port._step = {
        "step_run_id": "srun_" + "a" * 32,
        "stage": "m1",
        "status": step_status,
        "status_version": 1,
        "request_json": json.dumps({"input_artifact_ids": []}),
        "result_json": json.dumps({"output_artifact_ids": []}),
        "supersedes_step_run_id": None,
        "created_at": "2026-01-01T00:00:00.000000Z",
        "updated_at": "2026-01-01T00:00:01.000000Z",
    }
    return port


def _factory(port, calls=None, adapter_id="x"):
    def factory():
        if calls is not None:
            calls.append(adapter_id)
        return port, lambda: calls.append("cleanup:" + adapter_id) if calls is not None else None

    return factory


class TestConformance(unittest.TestCase):
    """覆盖 BDD §2.3：替换判定的真/假与问题文本。"""

    def test_two_equal_adapters_substitutable(self):
        suites = []
        factories = {
            "a": lambda: (make_fake_port(), lambda: None),
            "b": lambda: (make_fake_port(), lambda: None),
        }
        report = substitution_report(
            "storage", factories, lambda port: suites.append(port) or "prun_x",
            fingerprint=lambda adapter_id: "same",
        )
        self.assertTrue(report["substitutable"])
        self.assertTrue(report["outcomes_equal"])
        self.assertTrue(report["interface_equal"])
        self.assertEqual(report["problems"], [])

    def test_single_adapter_not_substitutable_with_problem_text(self):
        factories = {"a": lambda: (make_fake_port(), lambda: None)}
        report = substitution_report(
            "storage", factories, lambda port: "prun_x",
            fingerprint=lambda adapter_id: "same",
        )
        self.assertFalse(report["substitutable"])
        self.assertTrue(
            any("端口 storage 仅 1 个 Adapter" in p for p in report["problems"])
        )

    def test_outcome_difference_not_substitutable(self):
        factories = {
            "a": lambda: (make_fake_port(events=("created",)), lambda: None),
            "b": lambda: (make_fake_port(events=("created", "extra")), lambda: None),
        }
        report = substitution_report(
            "storage", factories, lambda port: "prun_x",
            fingerprint=lambda adapter_id: "same",
        )
        self.assertFalse(report["outcomes_equal"])
        self.assertFalse(report["substitutable"])

    def test_fingerprint_difference_not_substitutable(self):
        factories = {
            "a": lambda: (make_fake_port(), lambda: None),
            "b": lambda: (make_fake_port(), lambda: None),
        }
        report = substitution_report(
            "storage", factories, lambda port: "prun_x",
            fingerprint=lambda adapter_id: "fp-" + adapter_id,
        )
        self.assertTrue(report["outcomes_equal"])
        self.assertFalse(report["interface_equal"])
        self.assertFalse(report["substitutable"])

    def test_suite_exception_marks_adapter_nonconformant_and_cleanup_called(self):
        calls = []

        def suite(port):
            raise RuntimeError("套件炸了")

        factories = {
            "a": _factory(make_fake_port(), calls, "a"),
            "b": _factory(make_fake_port(), calls, "b"),
        }
        report = substitution_report(
            "storage", factories, suite, fingerprint=lambda adapter_id: "same"
        )
        self.assertFalse(report["conformant"]["a"])
        self.assertFalse(report["substitutable"])
        self.assertIn("cleanup:a", calls)
        self.assertIn("cleanup:b", calls)
        self.assertTrue(
            any(p.startswith("a: RuntimeError: 套件炸了") for p in report["problems"])
        )

    def test_missing_port_method_marks_nonconformant(self):
        class Incomplete:
            pass

        factories = {
            "a": lambda: (Incomplete(), lambda: None),
            "b": lambda: (make_fake_port(), lambda: None),
        }
        report = substitution_report(
            "storage", factories, lambda port: "prun_x",
            fingerprint=lambda adapter_id: "same",
        )
        self.assertFalse(report["conformant"]["a"])
        self.assertFalse(report["substitutable"])

    def test_normalize_outcome_strips_ids_and_times(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            adapter_a, prun_a = _seed_run(Path(tmp_a) / "ledger")
            adapter_b, prun_b = _seed_run(Path(tmp_b) / "ledger")
            self.addCleanup(adapter_a.close)
            self.addCleanup(adapter_b.close)
            outcome_a = normalize_outcome(adapter_a, prun_a)
            outcome_b = normalize_outcome(adapter_b, prun_b)
            self.assertEqual(outcome_a, outcome_b)
            blob = json.dumps(outcome_a, ensure_ascii=False)
            for prefix in ("prun_", "srun_", "rev_"):
                self.assertNotIn(prefix, blob)

    def test_suite_receives_port_guard(self):
        def suite(port):
            port.store  # PortGuard 必须拦截

        factories = {
            "a": lambda: (make_fake_port(), lambda: None),
            "b": lambda: (make_fake_port(), lambda: None),
        }
        report = substitution_report(
            "storage", factories, suite, fingerprint=lambda adapter_id: "same"
        )
        self.assertFalse(report["substitutable"])
        self.assertFalse(report["conformant"]["a"])


def _seed_run(root):
    """在临时 Ledger 上建一个形状固定的 ProcessingRun（一个 succeeded StepRun）。"""
    adapter = DirectLedgerAdapter(root)
    processing_run_id = adapter.create_processing_run(
        "edition_run", ids.new_id("artifact_id"), "qizheng"
    )
    configuration = json.dumps({"stage": "m1", "module_id": "stub.m1"}).encode("utf-8")
    _artifact_id, configuration_revision_id = adapter.put_run_artifact(
        processing_run_id,
        "configuration",
        configuration,
        producer_module="tests",
        producer_version="1.0",
    )
    step_run_id = ids.new_id("step_run_id")
    adapter.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": configuration_revision_id,
        }
    )
    adapter.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )
    return adapter, processing_run_id


if __name__ == "__main__":
    unittest.main()
