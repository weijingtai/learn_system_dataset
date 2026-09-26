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

# ACT 16：电子文本验收宿主（§11.8 更正后的路径）
OFFSET_FIXTURE = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"

# ACT 16 三：offset 档依赖页/字框的子判据（必须 NOT_APPLICABLE，不得冒充 PASS）
OFFSET_PAGE_DEPENDENT_CHECKS = (
    "legacy_collision_exposed",
    "span_page_binding",
    "anchor_to_page_image",
    "glyph_closure",
    "reverse_index",
)


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
    def test_publication_eight_pass_three_blocked_exit_2(self):
        # T02 新增 graph_projection、identity_migration 两条（供 run_all 20.9 / 20.11 读取）
        code, out = self._run(["--fixture", str(FIXTURE), "--check", "publication"])
        self.assertEqual(code, 2)
        self.assertEqual(_last_line(out), "SUMMARY pass=8 fail=0 blocked=3")
        blocked = sorted(l.split()[1] for l in out.splitlines() if l.startswith("BLOCKED "))
        self.assertEqual(blocked, ["graph_projection", "identity_migration", "knowledge_chain"])

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_legacy_collision_exposed_numbers_recomputed(self):
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "span_identity"])
        self.assertIn(
            "PASS legacy_collision_exposed "
            "legacy_keys=39 collision_groups=4 pack_keys=43",
            out,
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_mentions_mapping_blocked_states_observed_facts(self):
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "span_identity"])
        line = next(l for l in out.splitlines() if l.startswith("BLOCKED mentions_mapping "))
        self.assertIn("实测 evidence_map_pack 无 mentions", line)
        self.assertIn("search_index_pack", line)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_knowledge_chain_blocked_states_observed_facts(self):
        # TODO.md T02：原先锁的是无条件输出的写死文案；现在理由必须是实测事实
        _, out = self._run(["--fixture", str(FIXTURE), "--check", "publication"])
        line = next(l for l in out.splitlines() if l.startswith("BLOCKED knowledge_chain "))
        self.assertIn("实测 knowledge_chain=not_compiled", line)
        self.assertIn("不含 M7 Snapshot", line)
        self.assertIn("evidence_map_pack", line)

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


class OffsetRouteTests(unittest.TestCase):
    """ACT 16：验收按夹具路线分派（D-W8-16）。

    offset 档（《乾元秘旨》电子文本宿主）的真值：`run_m8` 因 gate.py / step.py 的
    offset 缺口如实失败（见 `act/17.yaml`），**不产出 m8 StagePackage**，因此
    `run_succeeded` 如实 FAIL、依赖页/字框的子判据 NOT_APPLICABLE；
    这是 ACT 16 三 ⚠ 口径更正后的正确结果，不是缺陷。
    """

    def _run(self, argv, env=None):
        buffer = io.StringIO()
        manager = mock.patch.dict(os.environ, env) if env else contextlib.nullcontext()
        with manager:
            with contextlib.redirect_stdout(buffer):
                code = acceptance.main(argv)
        return code, buffer.getvalue()

    def test_prepare_ledger_dispatches_to_run_m3_text_for_offset_fixture(self):
        """offset 档走 M1 → M2 → run_m3_text，不碰 fixture_ingest / run_m3 / 页图登记。"""
        calls = []
        service = mock.Mock()
        with mock.patch.object(
            acceptance,
            "run_m1",
            side_effect=lambda *a, **k: calls.append("m1")
            or {"raw_text_revision_ids": ["rev_" + "1" * 32]},
        ), mock.patch.object(
            acceptance,
            "run_m2",
            side_effect=lambda *a, **k: calls.append("m2")
            or {"cleaned_revision_id": "rev_" + "2" * 32},
        ), mock.patch.object(
            acceptance,
            "run_m3_text",
            side_effect=lambda *a, **k: calls.append("m3_text")
            or {"status": "succeeded"},
        ), mock.patch.object(
            acceptance,
            "run_m3",
            side_effect=AssertionError("offset 档不得调用 OCR 线 run_m3"),
        ), mock.patch.object(
            acceptance,
            "register_source_assets",
            side_effect=AssertionError("offset 档不得登记页图 SourceAsset"),
        ):
            edition_part_id = acceptance._prepare_ledger(
                service, OFFSET_FIXTURE, None, acceptance.ROUTE_OFFSET
            )
        self.assertEqual(calls, ["m1", "m2", "m3_text"])
        self.assertEqual(
            edition_part_id, "art_00000000000000000000000000000001"
        )

    def test_prepare_ledger_ocr_fixture_unchanged(self):
        """glyphbox 档仍走 ingest → run_m3 → register_source_assets（逐字不变）。

        全程 mock，不依赖本机页图，故**不带** skipUnless（避免资产缺失宿主上静默跳过）。
        """
        calls = []
        service = mock.Mock()
        with mock.patch.object(
            acceptance.fixture_ingest,
            "ingest",
            side_effect=lambda *a, **k: calls.append("ingest")
            or {"edition_part_id": "art_000000000000000000000000000000e1"},
        ) as ingest_mock, mock.patch.object(
            acceptance,
            "run_m3",
            side_effect=lambda *a, **k: calls.append("m3") or {"status": "succeeded"},
        ), mock.patch.object(
            acceptance,
            "register_source_assets",
            side_effect=lambda *a, **k: calls.append("assets") or {},
        ), mock.patch.object(
            acceptance,
            "run_m3_text",
            side_effect=AssertionError("glyphbox 档不得调用 run_m3_text"),
        ), mock.patch.object(
            acceptance,
            "run_m1",
            side_effect=AssertionError("glyphbox 档不得调用 run_m1"),
        ):
            edition_part_id = acceptance._prepare_ledger(
                service, FIXTURE, REPO_ASSET_ROOT, acceptance.ROUTE_GLYPHBOX
            )
        self.assertEqual(calls, ["ingest", "m3", "assets"])
        self.assertEqual(edition_part_id, "art_000000000000000000000000000000e1")
        ingest_mock.assert_called_once_with(FIXTURE, service, stages=("m1", "m2"))

    def test_acceptance_blocks_when_fixture_has_no_spans_yaml(self):
        """缺 spans.yaml：与缺 manifest.yaml 同口径 BLOCKED（exit 3）。"""
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-nospans-")
        try:
            shutil.copyfile(
                OFFSET_FIXTURE / "manifest.yaml", Path(tmp) / "manifest.yaml"
            )
            code, out = self._run(["--fixture", tmp])
            self.assertEqual(code, 3)
            self.assertEqual(
                _first_line(out),
                "BLOCKED m8_acceptance 宿主缺失: 缺 fixture spans.yaml",
            )
        finally:
            shutil.rmtree(tmp, True)

    def test_offset_fixture_page_dependent_checks_are_not_applicable(self):
        """offset 档依赖页/字框的子判据一律 NOT_APPLICABLE，绝不为 PASS。"""
        _code, out = self._run(
            ["--fixture", str(OFFSET_FIXTURE), "--check", "span_identity"]
        )
        for name in OFFSET_PAGE_DEPENDENT_CHECKS:
            self.assertIn("NOT_APPLICABLE %s" % name, out)
            self.assertNotIn("PASS %s" % name, out)

    def test_offset_fixture_reaches_verdict_not_host_missing(self):
        """跑到判定而非 BLOCKED 宿主缺失（本用例的唯一意图）。

        原名 ``test_offset_fixture_reports_run_failed_not_host_missing``，其中
        「``run_succeeded`` 如实 FAIL」记录的是 **ACT 17/18 之前** 的状态：当时
        gate/step 的 offset 缺口（尚剩 patch_reversible）让 M8 必失败、StagePackage
        不产出。ACT 18 修好该缺口后（D-W8-18），电子文本档 M8 首次走通全部判定、
        ``run_succeeded`` 转 PASS——**原断言已被正当推翻**，随事实更新（第 97 条，
        主 Agent 2026-09-21 明文批准）。本用例不再断言 run 的成败，只断言
        「不是宿主缺失 BLOCKED」这个从来没变过的意图。
        """
        code, out = self._run(
            ["--fixture", str(OFFSET_FIXTURE), "--check", "span_identity"]
        )
        self.assertNotIn("BLOCKED m8_acceptance 宿主缺失", out)
        self.assertNotIn("FAIL m8_acceptance 宿主准备失败", out)
        self.assertIn("BLOCKED mentions_mapping", out)
        # 跑到判定即契约：有明确结论行（PASS/FAIL/BLOCKED/NOT_APPLICABLE），
        # 且以 SUMMARY 结尾；退出码即由判定结果决定（0/2 或仍有 FAIL 时的 1）。
        self.assertIn("SUMMARY pass=", out)
        self.assertIn(code, (0, 1, 2))

    def test_route_detected_from_spans_evidence_level_not_dir_name(self):
        """路线判定取 spans.yaml 的 evidence_level，与目录名无关。"""
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-route-")
        try:
            # 目录名暗示「text」，但夹具里写的是字框级 → 必须判 glyphbox
            by_name_text = Path(tmp) / "looks_like_a_text_fixture"
            # 目录名暗示 OCR 扫描，但夹具里写的是偏移级 → 必须判 offset
            by_name_scan = Path(tmp) / "mini_ed01_scan_copy"
            no_hint = Path(tmp) / "whatever"
            for path in (by_name_text, by_name_scan, no_hint):
                path.mkdir()
            (by_name_text / "spans.yaml").write_bytes(b"evidence_level: glyphbox_level\n")
            (by_name_scan / "spans.yaml").write_bytes(b"evidence_level: offset_level\n")
            (no_hint / "spans.yaml").write_bytes(b"spans: []\n")

            self.assertEqual(
                acceptance._detect_route(by_name_text), acceptance.ROUTE_GLYPHBOX
            )
            self.assertEqual(
                acceptance._detect_route(by_name_scan), acceptance.ROUTE_OFFSET
            )
            self.assertIsNone(acceptance._detect_route(no_hint))
            self.assertIsNone(acceptance._detect_route(Path(tmp) / "absent"))
        finally:
            shutil.rmtree(tmp, True)

    def test_electronic_fixture_verify_sh_needs_no_page_assets(self):
        """电子文本 verify.sh 不要求任何页图：FIXTURE_ASSET_ROOT 指不存在处仍 exit 0。"""
        env = dict(os.environ)
        env["FIXTURE_ASSET_ROOT"] = "/nonexistent"
        proc = subprocess.run(
            ["bash", str(OFFSET_FIXTURE / "verify.sh")],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("FIXTURE OK", proc.stdout)


class LedgerOptionAndClosureStepsTests(unittest.TestCase):
    """T04 阶段 4 Q9：``--ledger`` 只读判定既有账本；offset 档证据链闭合的页/字框子步输出 NOT_APPLICABLE。"""

    def _run(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = acceptance.main(argv)
        return code, buffer.getvalue()

    def _built_offset_ledger(self):
        """在临时账本上按 offset 档装配宿主并跑一次 M8，返回账本目录。"""
        from pipeline.dataset_compiler.step import run_m8
        from pipeline.ledger.service import LedgerService

        tmp = tempfile.mkdtemp(prefix="m8-acc-ledger-")
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / "ledger"
        service = LedgerService(root)
        try:
            edition_part_id = acceptance._prepare_ledger(
                service, OFFSET_FIXTURE, None, acceptance.ROUTE_OFFSET
            )
            run_m8(service, edition_part_id, consumption_level="INTERNAL_DEMO")
        finally:
            service.close()
        return root

    @staticmethod
    def _table_counts(root):
        import sqlite3

        connection = sqlite3.connect("file:%s?mode=ro" % (root / "ledger.sqlite"), uri=True)
        try:
            return tuple(
                connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
                for table in ("artifact_revisions", "step_runs", "processing_runs", "audit_log")
            )
        finally:
            connection.close()

    def test_ledger_option_judges_an_existing_ledger_read_only(self):
        root = self._built_offset_ledger()
        before = self._table_counts(root)
        code, out = self._run(
            ["--fixture", str(OFFSET_FIXTURE), "--check", "publication", "--ledger", str(root)]
        )
        self.assertEqual(before, self._table_counts(root), "--ledger 不得写入被判定的账本")
        self.assertIn("run_succeeded", out)
        self.assertTrue(_last_line(out).startswith("SUMMARY "), out)
        # 与现场装配的判定逐行一致（同一宿主、同一 M8 事实）
        _code, fresh = self._run(["--fixture", str(OFFSET_FIXTURE), "--check", "publication"])
        self.assertEqual(
            [line.split(" ", 2)[:2] for line in out.strip().splitlines()],
            [line.split(" ", 2)[:2] for line in fresh.strip().splitlines()],
        )

    def test_ledger_option_refuses_a_missing_ledger(self):
        missing = Path(tempfile.mkdtemp(prefix="m8-acc-none-")) / "nope"
        self.addCleanup(shutil.rmtree, missing.parent, True)
        code, out = self._run(
            ["--fixture", str(OFFSET_FIXTURE), "--check", "publication", "--ledger", str(missing)]
        )
        self.assertEqual(code, 3)
        self.assertIn("BLOCKED m8_acceptance", out)
        self.assertFalse(missing.exists(), "不得为缺失的账本新建目录")

    def test_offset_closure_reports_page_steps_not_applicable(self):
        """页/字框子步不再以「span_id 无法解析」判 FAIL，而是逐项披露 NOT_APPLICABLE（不静默跳过）。

        其余子步照判。原先本宿主停在 text_offsets（offset 档 span 无 line_index）而 FAIL；
        T20 裁决 (a) 后 line_index 也披露为不适用，判据结论与篡改探针见 OffsetTextOffsetsTests。
        """
        _code, out = self._run(["--fixture", str(OFFSET_FIXTURE), "--check", "publication"])
        line = next(l for l in out.splitlines() if " evidence_chain_closure " in l)
        self.assertNotIn("span_page_binding: span_id 无法解析", line)
        for step in ("span_page_binding", "glyph_anchor_closure"):
            self.assertIn("%s=%s" % (step, acceptance.NOT_APPLICABLE), line)


class OffsetTextOffsetsTests(unittest.TestCase):
    """T20（用户 2026-09-26 裁决 (a)）：电子文本没有「行」，offset 档 text_offsets 不比 line_index，
    披露为 NOT_APPLICABLE；offset/text/quote_sha256/content_status 照比，任一不符仍 FAIL。"""

    SPAN_ID = "ss_qianyuan_ed01_text_000001"
    TEXT = "去官留煞"

    def _loaded(self, **entry_overrides):
        span = {"span_id": self.SPAN_ID, "start_offset": 10, "end_offset": 14, "text": self.TEXT}
        entry = {
            "start_offset": 10,
            "end_offset": 14,
            "text": self.TEXT,
            "quote_sha256": acceptance._sha256_hex(self.TEXT.encode("utf-8")),
            "content_status": "machine_extracted",
        }
        entry.update(entry_overrides)
        return {
            "evidence": {"entries": {self.SPAN_ID: entry}},
            "spans_doc": {"spans": [span], "content_status": "machine_extracted"},
        }

    def test_offset_route_does_not_require_line_index(self):
        ok, detail = acceptance._check_text_offsets(self._loaded(), acceptance.ROUTE_OFFSET)
        self.assertTrue(ok, detail)

    def test_offset_route_still_rejects_tampered_fields(self):
        """篡改探针：offset、text、quote_sha256、content_status 任一被改，offset 档照样 FAIL。"""
        for field, value in (
            ("start_offset", 11),
            ("end_offset", 15),
            ("text", "贪合忘煞"),
            ("quote_sha256", "0" * 64),
            ("content_status", "expert_verified"),
        ):
            with self.subTest(field=field):
                ok, _detail = acceptance._check_text_offsets(
                    self._loaded(**{field: value}), acceptance.ROUTE_OFFSET
                )
                self.assertFalse(ok, field)

    def test_offset_route_rejects_a_stray_line_index(self):
        """offset 档出现 line_index 说明混进了页/行档数据，判 FAIL，不当作「有就比、没有就算」。"""
        ok, detail = acceptance._check_text_offsets(
            self._loaded(line_index=0), acceptance.ROUTE_OFFSET
        )
        self.assertFalse(ok)
        self.assertIn("line_index", detail)

    def test_glyph_route_still_compares_line_index(self):
        loaded = self._loaded(line_index=1)
        loaded["spans_doc"]["spans"][0]["line_index"] = 0
        ok, _detail = acceptance._check_text_offsets(loaded, acceptance.ROUTE_GLYPHBOX)
        self.assertFalse(ok)

    def test_offset_host_closure_passes_and_discloses_line_index(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            acceptance.main(["--fixture", str(OFFSET_FIXTURE), "--check", "publication"])
        line = next(l for l in buffer.getvalue().splitlines() if " evidence_chain_closure " in l)
        self.assertTrue(line.startswith("PASS "), line)
        self.assertIn("text_offsets", line)
        for step in ("span_page_binding", "glyph_anchor_closure", "text_offsets.line_index"):
            self.assertIn("%s=%s" % (step, acceptance.NOT_APPLICABLE), line)


class OffsetWatermarkDisclosureTests(unittest.TestCase):
    """T21（用户 2026-09-26 裁决）：电子文本没有页面上的框，offset 档 watermark_disclosure 不看
    highlight_level，披露为 NOT_APPLICABLE；水印与其余已知缺陷照判，任一缺失仍 FAIL。"""

    MANIFEST = {
        "watermark": {"required": True, "text": "INTERNAL_DEMO｜机器转录"},
        "known_defects": [
            {"code": "knowledge_chain_not_compiled"},
            {"code": "machine_content"},
            {"code": "semantic_not_evaluated"},
        ],
    }

    def _judge(self, route, entry_overrides=None, manifest=None):
        entry = {"watermark": True}
        entry.update(entry_overrides or {})
        loaded = {
            "release_manifest_revision_id": "rev_x",
            "evidence": {
                "entries": {"ss_x": entry},
                "excluded_pages": {},
                "knowledge_chain": "not_compiled",
            },
            "spans_doc": {"content_status": "machine_extracted"},
            "manifest": {"rights_status": "站方声明免费下载"},
            "m3_gate_profile": "structural_only",
        }
        with mock.patch.object(
            acceptance, "_read_revision_json", return_value=manifest or self.MANIFEST
        ):
            return acceptance._check_watermark_disclosure(None, loaded, route)

    def test_offset_route_does_not_require_highlight_level(self):
        ok, detail = self._judge(acceptance.ROUTE_OFFSET)
        self.assertTrue(ok, detail)
        self.assertIn("highlight_level=%s" % acceptance.NOT_APPLICABLE, detail)

    def test_offset_route_still_requires_watermark_and_defects(self):
        """篡改探针：entry 水印未置真、水印文本为空、缺一条已知缺陷，offset 档照样 FAIL。"""
        ok, _ = self._judge(acceptance.ROUTE_OFFSET, {"watermark": False})
        self.assertFalse(ok)
        ok, _ = self._judge(
            acceptance.ROUTE_OFFSET, manifest=dict(self.MANIFEST, watermark={"required": True, "text": ""})
        )
        self.assertFalse(ok)
        ok, detail = self._judge(
            acceptance.ROUTE_OFFSET, manifest=dict(self.MANIFEST, known_defects=self.MANIFEST["known_defects"][:2])
        )
        self.assertFalse(ok)
        self.assertIn("semantic_not_evaluated", detail)

    def test_offset_route_rejects_a_stray_highlight_level(self):
        ok, detail = self._judge(acceptance.ROUTE_OFFSET, {"highlight_level": "glyph"})
        self.assertFalse(ok)
        self.assertIn("highlight_level", detail)

    def test_glyph_route_still_requires_glyph_text_mismatch_disclosure(self):
        ok, detail = self._judge(acceptance.ROUTE_GLYPHBOX, {"highlight_level": "line_bbox"})
        self.assertFalse(ok)
        self.assertIn("glyph_text_mismatch", detail)

    def test_offset_host_watermark_disclosure_passes(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            acceptance.main(["--fixture", str(OFFSET_FIXTURE), "--check", "publication"])
        line = next(l for l in buffer.getvalue().splitlines() if " watermark_disclosure " in l)
        self.assertTrue(line.startswith("PASS "), line)
        self.assertIn("highlight_level=%s" % acceptance.NOT_APPLICABLE, line)


if __name__ == "__main__":
    unittest.main()
