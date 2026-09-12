"""ACT impl-02/01：纯函数结构编译器 compile_structural 的测试。

测试只读 fixture 文件（``pipeline/corpus/_fixture/mini_ed01/``）作为纯函数
输入与金标，不 import fixture 的生成工具 ``build_fixture.py``。terminal_states
取自 ``anomalies.yaml`` 的 ``entries``。
"""

import copy
import json
import os
import unittest

import yaml

from pipeline.corpus_compiler.compiler import compile_structural
from pipeline.corpus_compiler.errors import CompileRefused
from pipeline.corpus_compiler.serialize import dump_yaml
from pipeline.ledger.errors import InvalidIdentifier, SchemaViolation

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir, os.pardir, os.pardir))
_FIXTURE_DIR = os.path.join(_REPO_ROOT, "pipeline", "corpus", "_fixture", "mini_ed01")


def _load_yaml(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def _load_bytes(name):
    with open(os.path.join(_FIXTURE_DIR, name), "rb") as handle:
        return handle.read()


def _base_inputs():
    """返回 (manifest, page_docs, terminal_states) 三元组（每次全新对象）。"""
    manifest = _load_yaml("manifest.yaml")
    page_docs = {
        "page_001": _load_json("pages/page_001.json"),
        "page_002": _load_json("pages/page_002.json"),
        "page_003": _load_json("pages/page_003.json"),
    }
    anomalies = _load_yaml("anomalies.yaml")
    terminal_states = {
        entry["page"]: entry["terminal_state"] for entry in anomalies["entries"]
    }
    return manifest, page_docs, terminal_states


def _transcript_sections(text):
    """把机器转录 markdown 按 `## <page>` 拆成 {page: 正文块}（正文行以 "\\n" 连接）。"""
    blocks = {}
    current = None
    buf = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if current is not None:
                while buf and buf[-1] == "":
                    buf.pop()
                blocks[current] = "\n".join(buf)
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        while buf and buf[-1] == "":
            buf.pop()
        blocks[current] = "\n".join(buf)
    return blocks


class CompileStructuralGoldenTests(unittest.TestCase):
    """金标字节、哈希、计数与页块对齐测试。"""

    def test_golden_spans_bytes_equal_fixture(self):
        manifest, page_docs, terminal_states = _base_inputs()
        result = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        golden = _load_bytes("spans.yaml")
        self.assertEqual(result["spans_bytes"], golden)

    def test_golden_sha256(self):
        manifest, page_docs, terminal_states = _base_inputs()
        result = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        self.assertEqual(
            result["spans_sha256"],
            "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef",
        )

    def test_counts_batches_coverage_excluded(self):
        manifest, page_docs, terminal_states = _base_inputs()
        result = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        self.assertEqual(len(result["spans"]), 43)
        self.assertEqual(
            result["batches"],
            ["sanche_b001", "sanche_b002", "sanche_b003", "sanche_b004", "sanche_b005"],
        )
        self.assertEqual(result["coverage"], {"page_001": 1.0, "page_003": 1.0})
        self.assertEqual(result["excluded_pages"], {"page_002": "known_unrecognizable"})

    def test_page_blocks_equal_fixture_transcript_sections(self):
        manifest, page_docs, terminal_states = _base_inputs()
        result = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        transcript = _load_bytes("source/transcript_v1.md").decode("utf-8")
        sections = _transcript_sections(transcript)
        self.assertEqual(result["page_blocks"]["page_001"], sections["page_001"])
        self.assertEqual(result["page_blocks"]["page_003"], sections["page_003"])

    def test_deterministic_twice_identical_bytes(self):
        manifest, page_docs, terminal_states = _base_inputs()
        first = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        second = compile_structural(
            manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
        )
        self.assertEqual(first["spans_bytes"], second["spans_bytes"])

    def test_batch_size_20_gives_three_batches(self):
        manifest, page_docs, terminal_states = _base_inputs()
        result = compile_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states,
            batch_size=20,
        )
        self.assertEqual(
            result["batches"], ["sanche_b001", "sanche_b002", "sanche_b003"]
        )


class CompileStructuralRefusalTests(unittest.TestCase):
    """异常终态、缺页、页序不符、非法枚举等拒绝路径测试。"""

    def test_deferred_page_refused(self):
        manifest, page_docs, terminal_states = _base_inputs()
        terminal_states = dict(terminal_states)
        terminal_states["page_003"] = "deferred"
        with self.assertRaises(CompileRefused) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertIn("deferred", str(ctx.exception))
        self.assertIn("§10.1", str(ctx.exception))

    def test_known_unrecognizable_page_with_lines_refused(self):
        manifest, page_docs, terminal_states = _base_inputs()
        terminal_states = dict(terminal_states)
        terminal_states["page_003"] = "known_unrecognizable"
        with self.assertRaises(CompileRefused):
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )

    def test_text_page_without_lines_refused(self):
        manifest, page_docs, terminal_states = _base_inputs()
        terminal_states = dict(terminal_states)
        del terminal_states["page_002"]
        with self.assertRaises(CompileRefused) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertIn("漏编", str(ctx.exception))

    def test_missing_page_doc_refused_REF_001(self):
        manifest, page_docs, terminal_states = _base_inputs()
        page_docs = dict(page_docs)
        del page_docs["page_003"]
        with self.assertRaises(CompileRefused) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_extra_page_doc_refused_SCH_002(self):
        manifest, page_docs, terminal_states = _base_inputs()
        page_docs = dict(page_docs)
        page_docs["page_099"] = {"page": "page_099", "lines": [], "chars": []}
        with self.assertRaises(CompileRefused) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_unknown_terminal_state_SCH_002(self):
        manifest, page_docs, terminal_states = _base_inputs()
        terminal_states = dict(terminal_states)
        terminal_states["page_001"] = "bogus_state"
        with self.assertRaises(SchemaViolation) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_missing_image_sha_refused_REF_001(self):
        manifest, page_docs, terminal_states = _base_inputs()
        manifest = copy.deepcopy(manifest)
        manifest["source_assets"] = [
            item for item in manifest["source_assets"] if item["page"] != "page_003"
        ]
        with self.assertRaises(CompileRefused) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_span_id_overflow_ID_001(self):
        lines = [
            {
                "id": "p%03d" % i,
                "box": {"x": 0, "y": 0, "w": 1, "h": 1},
                "text": "字",
            }
            for i in range(100)
        ]
        page_doc = {"page": "page_001", "lines": lines, "chars": []}
        manifest = {
            "source_id": "src_sanche_ed01",
            "work_title": "测试底本",
            "edition_part": {"artifact_id": "art_test0000000000000000000000000001", "pages": ["page_001"]},
            "source_assets": [{"page": "page_001", "sha256": "a" * 64}],
        }
        with self.assertRaises(InvalidIdentifier) as ctx:
            compile_structural(
                manifest=manifest, page_docs={"page_001": page_doc}, terminal_states={}
            )
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_invalid_source_id_ID_001(self):
        manifest, page_docs, terminal_states = _base_inputs()
        manifest = copy.deepcopy(manifest)
        manifest["source_id"] = "not-a-valid-id"
        with self.assertRaises(InvalidIdentifier) as ctx:
            compile_structural(
                manifest=manifest, page_docs=page_docs, terminal_states=terminal_states
            )
        self.assertEqual(ctx.exception.code, "ID_001")


class DumpYamlTests(unittest.TestCase):
    """序列化模块不得污染全局 SafeDumper。"""

    def test_dump_yaml_does_not_touch_global_safedumper(self):
        before = dict(yaml.SafeDumper.yaml_representers)
        dump_yaml({"a": 1, "b": ["x", "y"]})
        after = dict(yaml.SafeDumper.yaml_representers)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
