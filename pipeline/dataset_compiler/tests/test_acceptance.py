"""ACT impl-04/07：m8-span-identity 验收（acceptance.py 两组判定 + shell）测试。"""

import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.dataset_compiler import acceptance, packs
from pipeline.dataset_compiler.tests._ledger_helpers import (
    FIXTURE,
    REPO_ASSET_ROOT,
    REPO_ROOT,
    assets_available,
)
from pipeline.ledger import fixture_ingest

SHELL = REPO_ROOT / "openspec" / "acceptance" / "m8-span-identity.sh"


def _last_line(text):
    return text.strip().splitlines()[-1]


def _first_line(text):
    return text.strip().splitlines()[0]


class AcceptanceMainTests(unittest.TestCase):
    """直接调用 acceptance.main 的判定输出与退出码。"""

    def _run(self, argv, env=None):
        buffer = io.StringIO()
        manager = mock.patch.dict(os.environ, env) if env else contextlib.nullcontext()
        with manager:
            with contextlib.redirect_stdout(buffer):
                code = acceptance.main(argv)
        return code, buffer.getvalue()

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_span_identity_seven_pass_one_blocked_exit_2(self):
        code, out = self._run(["--fixture", str(FIXTURE), "--check", "span_identity"])
        self.assertEqual(code, 2)
        self.assertEqual(_last_line(out), "SUMMARY pass=7 fail=0 blocked=1")

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_publication_eight_pass_one_blocked_exit_2(self):
        code, out = self._run(["--fixture", str(FIXTURE), "--check", "publication"])
        self.assertEqual(code, 2)
        self.assertEqual(_last_line(out), "SUMMARY pass=8 fail=0 blocked=1")

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_legacy_collision_exposed_numbers_recomputed(self):
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "span_identity"])
        self.assertIn(
            "PASS legacy_collision_exposed "
            "legacy_keys=39 collision_groups=4 pack_keys=43",
            out,
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_mentions_mapping_blocked_exact_text(self):
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "span_identity"])
        self.assertIn(
            "BLOCKED mentions_mapping 前置缺失: M4 Knowledge Extraction；"
            "concept→span mentions 映射未产出；SearchIndexPack 未产出（D14-C）",
            out,
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_knowledge_chain_blocked_exact_text(self):
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "publication"])
        self.assertIn(
            "BLOCKED knowledge_chain 前置缺失: KnowledgeEntry→Assertion→EvidenceLink；"
            "knowledge_chain=not_compiled",
            out,
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_tampered_span_golden_fails(self):
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-golden-")
        try:
            copy = Path(tmp) / "fx"
            shutil.copytree(FIXTURE, copy)
            spans_path = copy / "spans.yaml"
            document = yaml.safe_load(spans_path.read_bytes())
            document["spans"].pop()
            spans_path.write_bytes(
                yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")
            )
            code, out = self._run(["--fixture", str(copy), "--check", "span_identity"])
            self.assertEqual(code, 1)
            self.assertIn("FAIL span_key_unique", out)
        finally:
            shutil.rmtree(tmp, True)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_dropped_entry_fails(self):
        original = packs.build_evidence_map_pack

        def tampered(*args, **kwargs):
            result = original(*args, **kwargs)
            entries = dict(result["pack"]["entries"])
            entries.pop(next(iter(entries)))
            result["pack"] = dict(result["pack"], entries=entries)
            return result

        packs.build_evidence_map_pack = tampered
        try:
            code, out = self._run(["--fixture", str(FIXTURE), "--check", "publication"])
            self.assertEqual(code, 1)
            self.assertIn("FAIL evidence_chain_closure", out)
        finally:
            packs.build_evidence_map_pack = original

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_prepare_failure_exits_1(self):
        original = fixture_ingest.ingest

        def boom(*args, **kwargs):
            raise RuntimeError("模拟准备失败")

        fixture_ingest.ingest = boom
        try:
            code, out = self._run(["--fixture", str(FIXTURE)])
            self.assertEqual(code, 1)
            self.assertTrue(
                _first_line(out).startswith("FAIL m8_acceptance 宿主准备失败: RuntimeError")
            )
        finally:
            fixture_ingest.ingest = original

    def test_missing_fixture_exit_3(self):
        code, _ = self._run(["--fixture", "/nonexistent/path/definitely-missing"])
        self.assertEqual(code, 3)

    def test_missing_assets_exit_3(self):
        empty = tempfile.mkdtemp(prefix="m8-acceptance-noassets-")
        try:
            code, _ = self._run(
                ["--fixture", str(FIXTURE)],
                env={"FIXTURE_ASSET_ROOT": empty},
            )
            self.assertEqual(code, 3)
        finally:
            shutil.rmtree(empty, True)


class AcceptanceShellTests(unittest.TestCase):
    """shell 脚本行为。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_shell_exit_2_on_fixture(self):
        proc = subprocess.run(
            ["bash", str(SHELL)], capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        self.assertEqual(_last_line(proc.stdout), "SUMMARY pass=7 fail=0 blocked=1")

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_shell_never_trusts_copy_verify(self):
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-copy-")
        try:
            copy = Path(tmp) / "fx"
            shutil.copytree(FIXTURE, copy)
            spans_path = copy / "spans.yaml"
            document = yaml.safe_load(spans_path.read_bytes())
            document["spans"].pop()
            spans_path.write_bytes(
                yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")
            )
            (copy / "verify.sh").write_text("echo FIXTURE OK; exit 0\n", encoding="utf-8")
            env = dict(os.environ)
            env["FIXTURE_DIR"] = str(copy)
            env["FIXTURE_ASSET_ROOT"] = str(REPO_ASSET_ROOT)
            proc = subprocess.run(
                ["bash", str(SHELL)],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                env=env,
            )
            self.assertEqual(proc.returncode, 1, msg=proc.stderr)
            self.assertTrue(_first_line(proc.stdout).startswith("FAIL fixture_host"))
        finally:
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
