"""Unit tests for M3 electronic text coverage gate and StagePackage assembly (Ruling 78, act/03).

synthetic_fixture: true
"""

import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema

from pipeline.corpus_compiler.assemble_offset import assemble_m3_text_stage_package
from pipeline.corpus_compiler.gate_offset import evaluate_text_coverage

# 护栏自检时把 AST 扫描目标指向临时副本；未设时扫描工作树中的真实源文件
GATE_SOURCE_ENV = "M3_GATE_OFFSET_SOURCE"


def _gate_source_path():
    """AST 护栏扫描的源文件路径（自检时经环境变量指向临时副本，绝不改动真实源文件）。"""
    override = os.environ.get(GATE_SOURCE_ENV)
    return Path(override) if override else Path(__file__).parent.parent / "gate_offset.py"


def _module_copies_of_this_file():
    """``sys.modules`` 里 ``__file__`` 指向本文件的模块名（排序后，用于范围无关断言）。

    同一文件在进程里只应有一个模块对象；出现两个说明有人按硬编码路径又导入了一份。
    """
    target = os.path.abspath(__file__)
    return sorted(
        name
        for name, module in list(sys.modules.items())
        if getattr(module, "__file__", None)
        and os.path.abspath(module.__file__) == target
    )


def _create_golden_fixture():
    """构造一份符合全量 Golden 标准的输入与 spans_doc（synthetic_fixture: true）。"""
    raw_text = "天地玄黄。\n【广告】\n宇宙洪荒。"
    cleaned_text = "天地玄黄。\n宇宙洪荒。"
    patches = [
        {
            "patch_id": "patch_001",
            "raw_start": 6,
            "raw_end": 11,
            "cleaned_start": 6,
            "cleaned_end": 6,
            "action": "deletion",
            "basis": "watermark",
        }
    ]
    # span 1: "天地玄黄。\n" -> c: [0, 6), raw: [0, 6)
    # span 2: "宇宙洪荒。" -> c: [6, 11), raw: [11, 16)
    quote1 = "天地玄黄。\n"
    quote2 = "宇宙洪荒。"
    spans = [
        {
            "span_id": "ss_qianyuan_ed01_o0000000",
            "sequence": 1,
            "start_offset": 0,
            "end_offset": 6,
            "text": quote1,
            "quote_sha256": hashlib.sha256(quote1.encode("utf-8")).hexdigest(),
            "evidence_level": "offset_level",
            "source_anchor": {
                "raw_text_revision_id": "art_rev_00000000000000000000000000000001",
                "raw_start": 0,
                "raw_end": 6,
                "cleaned_text_revision_id": "art_rev_00000000000000000000000000000002",
                "start_offset": 0,
                "end_offset": 6,
                "quote_sha256": hashlib.sha256(quote1.encode("utf-8")).hexdigest(),
            },
        },
        {
            "span_id": "ss_qianyuan_ed01_o0000011",
            "sequence": 2,
            "start_offset": 6,
            "end_offset": 11,
            "text": quote2,
            "quote_sha256": hashlib.sha256(quote2.encode("utf-8")).hexdigest(),
            "evidence_level": "offset_level",
            "source_anchor": {
                "raw_text_revision_id": "art_rev_00000000000000000000000000000001",
                "raw_start": 11,
                "raw_end": 16,
                "cleaned_text_revision_id": "art_rev_00000000000000000000000000000002",
                "start_offset": 6,
                "end_offset": 11,
                "quote_sha256": hashlib.sha256(quote2.encode("utf-8")).hexdigest(),
            },
        },
    ]
    spans_doc = {
        "work": "qianyuan",
        "source_id": "src_qianyuan_ed01",
        "edition_part_artifact_id": "art_000000000000000000000000000000e1",
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": 2,
        "spans": spans,
    }
    return raw_text, cleaned_text, patches, spans_doc


class TestGateOffset(unittest.TestCase):
    """测试 M3 电子文本结构 Gate 判定与 StagePackage 组装（act/03）。"""

    def setUp(self):
        self.raw_text, self.cleaned_text, self.patches, self.spans_doc = _create_golden_fixture()

    def test_evaluate_text_coverage_golden_all_pass(self):
        """测试标准用例通过 Gate 全部 6 项检查，返回 passed=True。"""
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=self.spans_doc,
        )
        self.assertTrue(res["passed"])
        expected_checks = [
            "text_contiguous_coverage",
            "text_strict_offset",
            "raw_anchor_fidelity",
            "identity_and_stability",
            "evidence_level_honest",
            "header_counts",
        ]
        self.assertEqual(list(res["checks"].keys()), expected_checks)
        for name, check in res["checks"].items():
            self.assertTrue(check["ok"], f"检查 {name} 意外失败: {check['detail']}")

    def test_gate_offset_does_not_import_compiler_modules(self):
        """第 88 条护栏用例：通过 AST 解析断言 gate_offset.py 未 import 编译模块，防止同错同过。

        源文件路径取自 ``_gate_source_path()``：默认是工作树中的真实源文件；护栏自检时指向
        临时副本，故自检绝不会触碰（更不会损坏）真实源文件。
        """
        source = _gate_source_path().read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)
                for alias in node.names:
                    imported_modules.append(alias.name)
        forbidden = ["text_compiler", "step_offset", "assemble_offset"]
        for mod in imported_modules:
            for forb in forbidden:
                self.assertNotIn(forb, mod, f"gate_offset.py 违规引入了编译模块 {mod}")

    def test_drop_span_fails_contiguous_coverage(self):
        """丢弃片段导致全文未 100% 覆盖时，text_contiguous_coverage 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"] = [tampered_doc["spans"][0]]  # 丢失第二句
        tampered_doc["span_count"] = 1
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["text_contiguous_coverage"]["ok"])

    def test_overlap_spans_fails_contiguous_coverage(self):
        """片段重叠时，text_contiguous_coverage 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        # 故意将第二段 start 设为 5（与第一段 [0, 6) 产生重叠）
        tampered_doc["spans"][1]["start_offset"] = 5
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["text_contiguous_coverage"]["ok"])

    def test_tampered_quote_fails_strict_offset_check(self):
        """引文切片文本篡改时，text_strict_offset 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"][0]["text"] = "篡改文本。\n"
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["text_strict_offset"]["ok"])

    def test_tampered_quote_hash_fails_strict_offset_check(self):
        """引文哈希不一致时，text_strict_offset 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"][0]["quote_sha256"] = "0" * 64
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["text_strict_offset"]["ok"])

    def test_tampered_patch_mapping_fails_raw_anchor_fidelity(self):
        """补丁映射漂移导致锚点无法还原时，raw_anchor_fidelity 判错。"""
        tampered_patches = copy.deepcopy(self.patches)
        # 篡改补丁使得 cleaned 偏移映射失效
        tampered_patches[0]["cleaned_start"] = 2
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=tampered_patches,
            spans_doc=self.spans_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["raw_anchor_fidelity"]["ok"])

    def test_raw_start_mismatch_fails_raw_anchor_fidelity(self):
        """source_anchor 中的 raw_start 与补丁换算不符时，raw_anchor_fidelity 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"][1]["source_anchor"]["raw_start"] = 99
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["raw_anchor_fidelity"]["ok"])

    def test_duplicate_span_id_fails_identity_and_stability(self):
        """存在重复 span_id 时，identity_and_stability 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"][1]["span_id"] = tampered_doc["spans"][0]["span_id"]
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["identity_and_stability"]["ok"])

    def test_invalid_span_id_format_fails_identity_and_stability(self):
        """span_id 格式不符时，identity_and_stability 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["spans"][0]["span_id"] = "invalid_id_format"
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["identity_and_stability"]["ok"])

    def test_upgraded_glyphbox_fails_evidence_level_honest(self):
        """若伪造为 glyphbox_level，evidence_level_honest 必判 FAIL。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["evidence_level"] = "glyphbox_level"
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["evidence_level_honest"]["ok"])

        tampered_doc2 = copy.deepcopy(self.spans_doc)
        tampered_doc2["spans"][0]["evidence_level"] = "glyphbox_level"
        res2 = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc2,
        )
        self.assertFalse(res2["passed"])
        self.assertFalse(res2["checks"]["evidence_level_honest"]["ok"])

    def test_span_count_mismatch_fails_header_counts(self):
        """顶层 span_count 与 spans 列表长度不符时，header_counts 判错。"""
        tampered_doc = copy.deepcopy(self.spans_doc)
        tampered_doc["span_count"] = 99
        res = evaluate_text_coverage(
            raw_text=self.raw_text,
            cleaned_text=self.cleaned_text,
            patches=self.patches,
            spans_doc=tampered_doc,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["header_counts"]["ok"])

    def _frozen_ref(self, revision_id, artifact_type):
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": "art_" + revision_id[len("rev_"):],
            "artifact_revision_id": revision_id,
            "artifact_type": artifact_type,
        }

    def _assemble(self, **overrides):
        """按新签名组装一个 m3 StagePackage（默认值为 synthetic 正例）。"""
        frozen_refs = overrides.pop(
            "frozen_artifact_refs",
            [
                self._frozen_ref("rev_00000000000000000000000000000011", "raw_text"),
                self._frozen_ref("rev_00000000000000000000000000000012", "cleaned_text_revision"),
                self._frozen_ref(
                    "rev_00000000000000000000000000000013", "deterministic_patch_set"
                ),
                self._frozen_ref("rev_00000000000000000000000000000014", "sanitization_report"),
            ],
        )
        params = dict(
            stage_package_id="pkg_m3_" + "0" * 32,
            artifact_revision_id="rev_" + "0" * 32,
            processing_run_id="prun_" + "0" * 32,
            step_run_id="srun_00000000000000000000000000000001",
            spans_revision_id="rev_00000000000000000000000000000001",
            spans_bytes=json.dumps(self.spans_doc, ensure_ascii=False).encode("utf-8"),
            counts={"spans": len(self.spans_doc["spans"]), "batches": 1},
            coverage={"qianyuan_ed01_text": 1.0},
            excluded_pages={},
            frozen_artifact_refs=frozen_refs,
            corpus_package_ref=self._frozen_ref(
                "rev_00000000000000000000000000000021", "corpus_package"
            ),
            validation_report_refs=[
                self._frozen_ref("rev_00000000000000000000000000000022", "validation_report")
            ],
            log_refs=[self._frozen_ref("rev_00000000000000000000000000000023", "step_log")],
            transformations=[],
        )
        params.update(overrides)
        return assemble_m3_text_stage_package(**params)

    def test_assemble_m3_text_stage_package_conforms_to_schema(self):
        """StagePackage 通过 openspec/schemas/stage_package.schema.json 校验（act/03 contract 2）。"""
        pkg = self._assemble()
        schema_path = (
            Path(__file__).resolve().parents[3]
            / "openspec"
            / "schemas"
            / "stage_package.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        resolver = jsonschema.RefResolver(
            base_uri="%s/" % schema_path.parent.as_uri(), referrer=schema
        )
        validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
        validator.validate(pkg)

    def test_assemble_m3_text_stage_package_payload_keys(self):
        """payload 键名与键序逐字对齐 OCR 路线；evidence_level 不入 payload（第 102 条 Q4⑤）。"""
        pkg = self._assemble()
        payload = pkg["payload"]
        self.assertEqual(
            list(payload.keys()),
            [
                "spans_revision_id",
                "coverage",
                "excluded_pages",
                "gate_profile",
                "semantic",
            ],
        )
        self.assertEqual(payload["spans_revision_id"], "rev_00000000000000000000000000000001")
        self.assertEqual(payload["coverage"], {"qianyuan_ed01_text": 1.0})
        self.assertEqual(payload["excluded_pages"], {})
        self.assertEqual(payload["gate_profile"], "structural_only")
        self.assertEqual(payload["semantic"], "not_evaluated")
        self.assertNotIn("evidence_level", payload)

    def test_assemble_m3_text_stage_package_key_sets_match_ocr_route(self):
        """各层键名/键序逐字等于 OCR 路线（step.py），下游不得另写读取分支（第 100 条 D2）。"""
        pkg = self._assemble()
        ocr_top = [
            "schema_version",
            "stage_package_id",
            "artifact_revision_id",
            "stage",
            "status",
            "payload",
            "manifest",
            "validation",
            "lineage",
            "logs",
            "failures",
        ]
        self.assertEqual(list(pkg.keys()), ocr_top)
        self.assertEqual(
            list(pkg["manifest"].keys()),
            [
                "schema_version",
                "processing_run_id",
                "step_run_id",
                "input_artifacts",
                "output_artifacts",
                "counts",
                "content_sha256",
            ],
        )
        self.assertEqual(list(pkg["manifest"]["counts"].keys()), ["spans", "batches"])
        self.assertEqual(list(pkg["validation"].keys()), ["passed", "report_artifacts"])
        self.assertEqual(list(pkg["lineage"].keys()), ["upstream_artifacts", "transformations"])
        self.assertEqual(
            list(pkg["validation"]["report_artifacts"][0].keys()),
            [
                "schema_version",
                "artifact_kind",
                "artifact_id",
                "artifact_revision_id",
                "artifact_type",
            ],
        )

    def test_assemble_m3_text_stage_package_manifest_sha256(self):
        """manifest.content_sha256 与实际内容字节重算一致，counts.spans 与实际片段数一致。"""
        spans_bytes = json.dumps(self.spans_doc, ensure_ascii=False).encode("utf-8")
        pkg = self._assemble(spans_bytes=spans_bytes)
        self.assertEqual(
            pkg["manifest"]["content_sha256"], hashlib.sha256(spans_bytes).hexdigest()
        )
        self.assertEqual(pkg["manifest"]["counts"]["spans"], len(self.spans_doc["spans"]))

    def test_assemble_m3_text_stage_package_lineage(self):
        """lineage.upstream_artifacts 指向本次冻结的 M2 四件产物（第 102 条 Q4④）。"""
        spans_revision_id = "rev_00000000000000000000000000000001"
        transformations = [
            {
                "operation": "compile_corpus",
                "step_run_id": "srun_00000000000000000000000000000001",
                "configuration_artifact_revision_id": "rev_00000000000000000000000000000004",
                "input_artifact_revision_ids": [spans_revision_id],
                "output_artifact_revision_ids": [
                    "rev_00000000000000000000000000000002"
                ],
            }
        ]
        pkg = self._assemble(
            spans_revision_id=spans_revision_id, transformations=transformations
        )
        lineage = pkg["lineage"]
        self.assertEqual(list(lineage.keys()), ["upstream_artifacts", "transformations"])
        self.assertEqual(
            [ref["artifact_type"] for ref in lineage["upstream_artifacts"]],
            [
                "raw_text",
                "cleaned_text_revision",
                "deterministic_patch_set",
                "sanitization_report",
            ],
        )
        # manifest.input_artifacts 与 lineage.upstream_artifacts 同源（同为本次冻结输入）
        self.assertEqual(pkg["manifest"]["input_artifacts"], lineage["upstream_artifacts"])
        self.assertEqual(lineage["transformations"], transformations)
        self.assertEqual(
            lineage["transformations"][0]["input_artifact_revision_ids"],
            [spans_revision_id],
        )


class TestGateOffsetImportGuard(unittest.TestCase):
    """第 88/93 条护栏实战用例——注入三种编译模块导入，验证全部被检出。

    纪律：注入一律落在**临时副本**上（``tempfile.TemporaryDirectory``），由环境变量
    ``M3_GATE_OFFSET_SOURCE`` 把 AST 护栏指向该副本；工作树中的真实源文件**绝不改动**，
    因此进程被强杀也不会损坏源文件。
    """

    def _inject_and_run(self, text_to_add):
        """把违规 import 注入临时副本，运行 Gate 用例，返回 (失败计数, 结果)。

        嵌套运行只加载本文件内的 ``TestGateOffset``（含 AST 护栏用例），
        **不得**把 ``TestGateOffsetImportGuard`` 一并载入：那会让本类递归调用自身，
        套件永不终止（护栏仍能检出注入，且不再自噬）。

        Q5（ACT 19）测试设施隔离，三条都是范围无关的前提：
        1. 模块对象取 ``sys.modules[__name__]``（**当前已导入的那一份**），
           不得按硬编码绝对路径 ``__import__``：按不同 discover 顶层
           （``-t .`` → ``pipeline.…``；``-t pipeline`` → ``corpus_compiler.…``）
           后者会再导入一份副本，同一文件出现两个模块对象，Selfcheck 作用在
           「另一份」上，结果随发现范围而异。
        2. 环境变量用 ``mock.patch.dict`` 隔离，异常路径也保证还原。
        3. 嵌套 runner 的输出导入 ``StringIO``，**不写公共流**：嵌套运行本来就
           要红（那是它的目的），但它只能体现在返回的 ``result`` 里；写进公共
           stdout/stderr 会让按输出聚合的复核看到假红。
        """
        source_path = Path(__file__).parent.parent / "gate_offset.py"
        module = sys.modules[__name__]
        with tempfile.TemporaryDirectory() as tmpdir:
            copied = Path(tmpdir) / "gate_offset.py"
            copied.write_text(
                text_to_add.rstrip() + "\n" + source_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            suite = unittest.TestLoader().loadTestsFromTestCase(module.TestGateOffset)
            with mock.patch.dict(os.environ, {GATE_SOURCE_ENV: str(copied)}):
                runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
                result = runner.run(suite)
            failed = len(result.failures) + len(result.errors)
            return failed, result

    def _assert_guard_detected(self, result, injected):
        """断言 AST 护栏用例本身转红（而非仅仅「有东西失败了」）。"""
        names = [str(case) for case, _ in result.failures + result.errors]
        self.assertTrue(
            any(
                "test_gate_offset_does_not_import_compiler_modules" in name
                for name in names
            ),
            "%s 未被 AST 护栏检出，失败用例：%s" % (injected, names),
        )

    def _assert_real_source_untouched(self, before, injected):
        """断言真实源文件在注入自检前后逐字节不变。"""
        after = hashlib.sha256(
            (Path(__file__).parent.parent / "gate_offset.py").read_bytes()
        ).hexdigest()
        self.assertEqual(after, before, "%s 自检改动了真实源文件" % injected)

    def test_from_dot_import_text_compiler(self):
        """注入 from . import text_compiler（临时副本），应被护栏检出转红。"""
        injected = "from . import text_compiler"
        before = hashlib.sha256(
            (Path(__file__).parent.parent / "gate_offset.py").read_bytes()
        ).hexdigest()
        failed, result = self._inject_and_run(injected)
        self.assertGreater(failed, 0, "%s 未被护栏检出" % injected)
        self._assert_guard_detected(result, injected)
        self._assert_real_source_untouched(before, injected)

    def test_from_dot_text_compiler_import(self):
        """注入 from .text_compiler import segment_cleaned_text（临时副本），应被护栏检出转红。"""
        injected = "from .text_compiler import segment_cleaned_text"
        before = hashlib.sha256(
            (Path(__file__).parent.parent / "gate_offset.py").read_bytes()
        ).hexdigest()
        failed, result = self._inject_and_run(injected)
        self.assertGreater(failed, 0, "%s 未被护栏检出" % injected)
        self._assert_guard_detected(result, injected)
        self._assert_real_source_untouched(before, injected)

    def test_absolute_import_text_compiler(self):
        """注入 import pipeline.corpus_compiler.text_compiler（临时副本），应被护栏检出转红。"""
        injected = "import pipeline.corpus_compiler.text_compiler"
        before = hashlib.sha256(
            (Path(__file__).parent.parent / "gate_offset.py").read_bytes()
        ).hexdigest()
        failed, result = self._inject_and_run(injected)
        self.assertGreater(failed, 0, "%s 未被护栏检出" % injected)
        self._assert_guard_detected(result, injected)
        self._assert_real_source_untouched(before, injected)

    # ---- Q5（ACT 19）：测试设施隔离——自检不得污染公共流/模块表/环境 ----

    def test_selfcheck_emits_no_failure_text_to_shared_stream(self):
        """自检的嵌套运行**本来**就会红（那正是它的目的），但只能体现在 ``result``
        对象里；写进公共输出（stdout/stderr）会让按 discover 范围聚合输出的复核看到
        「假红」。本断言对发现范围不敏感。
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self._inject_and_run("from . import text_compiler")
        leaked = out.getvalue() + err.getvalue()
        self.assertNotIn("FAIL:", leaked, "自检把 FAIL 文本泄漏到公共输出:\n%s" % leaked)
        self.assertNotIn(
            "FAILED", leaked, "自检把 FAILED 汇总泄漏到公共输出:\n%s" % leaked
        )

    @classmethod
    def setUpClass(cls):
        """在**本类跑任何自检之前**记录本文件的模块对象集合（范围无关断言的基准）。"""
        cls._module_copies_before_class = _module_copies_of_this_file()

    def test_selfcheck_keeps_single_module_object_for_this_file(self):
        """自检不得让同一文件在 ``sys.modules`` 里出现第二份模块对象。

        按不同 discover 顶层跑（``-t .`` → ``pipeline.…``；``-t pipeline`` →
        ``corpus_compiler.…``）模块名不同；若自检按硬编码路径 ``__import__``，
        在其中一种范围下会再导入一份副本——同一文件两个模块对象，自检作用在
        「另一份」上，结果随范围而异。此断言在两种范围下都必须成立。
        """
        self._inject_and_run("from . import text_compiler")
        self.assertEqual(
            _module_copies_of_this_file(),
            self._module_copies_before_class,
            "自检导入了本文件的第二份模块副本",
        )

    def test_selfcheck_restores_gate_source_env(self):
        """自检结束（含被注入用例转红）后 ``GATE_SOURCE_ENV`` 必须还原。"""
        before = os.environ.get(GATE_SOURCE_ENV)
        self._inject_and_run("from . import text_compiler")
        self.assertEqual(os.environ.get(GATE_SOURCE_ENV), before)


if __name__ == "__main__":
    unittest.main()