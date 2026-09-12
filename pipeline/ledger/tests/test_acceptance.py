"""ACT impl-01/05：``acceptance.py`` 的 20.2 / 20.3 场景判定测试（§20 第 2/3 条）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.acceptance` 尚不存在而全红。
判据不允许是永真的：篡改 Ledger 后同名检查必须变 FAIL。
"""

import io
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from pipeline.ledger import acceptance

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class AcceptanceTestBase(unittest.TestCase):
    """公共脚手架：准备一个已灌入的临时 Ledger（调用方负责关闭与清理）。"""

    def prepare(self):
        root, service, summary, fixture = acceptance.prepare(FIXTURE_DIR)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.addCleanup(service.close)
        return root, service, summary, fixture

    def run_main(self, argv):
        """跑 ``acceptance.main`` 并捕获 stdout。"""
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = acceptance.main(argv)
        return code, buffer.getvalue()


class TestAcceptanceChecks(AcceptanceTestBase):
    """覆盖 §20 第 2/3 条：宿主真实 Ledger 上的可恢复性与语义转换记录完整性。"""

    def test_check_20_2_passes_on_fixture(self):
        code, output = self.run_main(
            ["--fixture", str(FIXTURE_DIR), "--check", "20_2"]
        )
        self.assertEqual(code, 0, output)
        lines = [line for line in output.splitlines() if line.startswith("PASS ")]
        names = [line.split()[1] for line in lines]
        self.assertEqual(names, list(acceptance.CHECK_NAMES["20_2"]))
        self.assertEqual(len(names), 5)
        self.assertFalse(
            [line for line in output.splitlines() if line.startswith("FAIL ")]
        )

    def test_check_20_3_passes_on_fixture(self):
        code, output = self.run_main(
            ["--fixture", str(FIXTURE_DIR), "--check", "20_3"]
        )
        self.assertEqual(code, 0, output)
        names = [
            line.split()[1]
            for line in output.splitlines()
            if line.startswith("PASS ")
        ]
        self.assertEqual(names, list(acceptance.CHECK_NAMES["20_3"]))
        self.assertFalse(
            [line for line in output.splitlines() if line.startswith("FAIL ")]
        )

    def test_check_20_2_fails_when_checkpoint_missing(self):
        root, service, summary, fixture = self.prepare()
        last = service.list_checkpoints(summary["edition_part_id"], "m3")[-1]
        service.store.conn.execute(
            "DELETE FROM stage_checkpoints WHERE artifact_revision_id=?",
            (last["artifact_revision_id"],),
        )
        results = acceptance.evaluate("20_2", service, summary, fixture)
        by_name = {item["name"]: item for item in results}
        self.assertFalse(by_name["chain_lengths"]["ok"])
        self.assertIn("m3", by_name["chain_lengths"]["reason"])
        self.assertEqual(acceptance.checks_exit_code(results), 1)

    def test_check_20_3_fails_when_validation_report_missing(self):
        root, service, summary, fixture = self.prepare()
        row = service.store.conn.execute(
            "SELECT t.id FROM transformations t JOIN step_runs s "
            "ON s.step_run_id = t.step_run_id WHERE s.stage='m2'"
        ).fetchone()
        service.store.conn.execute(
            "UPDATE transformations SET validation_report_revision_id=NULL WHERE id=?",
            (row[0],),
        )
        results = acceptance.evaluate("20_3", service, summary, fixture)
        by_name = {item["name"]: item for item in results}
        self.assertFalse(by_name["validation_recorded"]["ok"])
        self.assertEqual(acceptance.checks_exit_code(results), 1)

    def test_prepare_failure_exits_1(self):
        """灌入抛异常必须按 FAIL 处理：main 返回 1，而不是冒充环境缺失的 3。"""

        def _boom(fixture, service):
            raise RuntimeError("灌入路径炸了")

        with mock.patch("pipeline.ledger.fixture_ingest.ingest", new=_boom):
            code, output = self.run_main(
                ["--fixture", str(FIXTURE_DIR), "--check", "20_2"]
            )
        self.assertEqual(code, 1)
        self.assertTrue(
            output.splitlines()[0].startswith(
                "FAIL 20_2 宿主准备失败: RuntimeError"
            ),
            output,
        )

    def test_evaluate_failure_exits_1(self):
        """evaluate 抛异常同样按 FAIL 处理：main 返回 1。"""
        with mock.patch.object(
            acceptance, "evaluate", side_effect=RuntimeError("判定路径炸了")
        ):
            code, output = self.run_main(
                ["--fixture", str(FIXTURE_DIR), "--check", "20_3"]
            )
        self.assertEqual(code, 1)
        self.assertTrue(
            output.splitlines()[0].startswith(
                "FAIL 20_3 宿主准备失败: RuntimeError"
            ),
            output,
        )

    def test_missing_fixture_exit_3(self):
        code, output = self.run_main(
            [
                "--fixture",
                str(REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "not_here"),
                "--check",
                "20_2",
            ]
        )
        self.assertEqual(code, 3)
        self.assertTrue(output.strip())


if __name__ == "__main__":
    unittest.main()
