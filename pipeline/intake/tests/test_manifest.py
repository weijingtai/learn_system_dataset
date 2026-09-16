"""M1 纯函数单元测试（synthetic_fixture: true）。"""

import hashlib
import tempfile
import unittest
from pathlib import Path
import yaml

from pipeline.intake.errors import IntakeRefused, SourceAssetMissing
from pipeline.intake.manifest import build_source_manifest, manifest_bytes
from pipeline.intake.serialize import dump_manifest_yaml
from pipeline.intake.source import load_source, read_source_files
from pipeline.intake.tests.helpers import fixture_source, make_text_file


class TestManifest(unittest.TestCase):
    """M1 来源校验、文件读取与 source_manifest 构造测试集。"""

    def test_dump_roundtrip(self):
        """synthetic_fixture: true，dump_manifest_yaml 写出后 safe_load 回来键值不变。"""
        src = fixture_source()
        dumped = dump_manifest_yaml(src)
        loaded = yaml.safe_load(dumped.decode("utf-8"))
        self.assertEqual(loaded, src)

    def test_dump_does_not_touch_global_safedumper(self):
        """synthetic_fixture: true，调用前后 yaml.SafeDumper.yaml_representers 相等。"""
        before_keys = set(yaml.SafeDumper.yaml_representers.keys())
        before_map = dict(yaml.SafeDumper.yaml_representers)

        src = fixture_source()
        _ = dump_manifest_yaml(src)

        after_keys = set(yaml.SafeDumper.yaml_representers.keys())
        after_map = dict(yaml.SafeDumper.yaml_representers)

        self.assertEqual(before_keys, after_keys)
        self.assertEqual(before_map, after_map)

    def test_sha256_quoted_other_strings_plain(self):
        """synthetic_fixture: true，64 位十六进制带双引号；其他字符串不加引号。"""
        data = {
            "hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "plain_text": "普通字符串无引号",
        }
        dumped = dump_manifest_yaml(data).decode("utf-8")
        self.assertIn('"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"', dumped)
        self.assertIn("plain_text: 普通字符串无引号", dumped)

    def test_load_source_valid_returns_new_dict(self):
        """synthetic_fixture: true，返回值键序固定；修改返回值不影响入参。"""
        src = fixture_source()
        loaded = load_source(src)

        expected_order = [
            "source_id",
            "work_title",
            "edition_note",
            "technique_id",
            "rights_status",
            "release_policy",
            "edition_part",
            "source_site",
            "source_url",
            "file_sha256",
            "pages",
            "repo_commit",
            "yaml_metadata",
        ]
        self.assertEqual(list(loaded.keys()), expected_order)

        # 修改返回值不影响入参
        loaded["work_title"] = "已修改书名"
        loaded["edition_part"]["label"] = "已修改分卷"
        self.assertEqual(src["work_title"], "乾元秘旨")
        self.assertEqual(src["edition_part"]["label"], "卷一·太极图说")

    def test_load_source_missing_key_SCH_001(self):
        """synthetic_fixture: true，非 dict 或缺失必填键抛出 SCH_001。"""
        with self.assertRaises(IntakeRefused) as ctx:
            load_source("not_a_dict")
        self.assertEqual(ctx.exception.code, "SCH_001")

        src = fixture_source()
        del src["source_id"]
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_load_source_extra_key_SCH_002(self):
        """synthetic_fixture: true，出现表外键抛出 SCH_002。"""
        src = fixture_source()
        src["unexpected_extra_key"] = "extra_value"
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_load_source_bad_source_url_SCH_002(self):
        """synthetic_fixture: true，非 http:// 或 https:// 开头的 URL 抛出 SCH_002。"""
        src = fixture_source()
        src["source_url"] = "ftp://daizhige.org/01.txt"
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_load_source_bad_file_sha256_SCH_002(self):
        """synthetic_fixture: true，非 64 位十六进制哈希抛出 SCH_002。"""
        src = fixture_source()
        src["file_sha256"] = "invalid_hash"
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_load_source_bad_pages_duplicate_SCH_002(self):
        """synthetic_fixture: true，pages 为空、非法字符或重复时抛出 SCH_002。"""
        src = fixture_source()
        src["pages"] = ["page_001", "page_001"]
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

        src["pages"] = ["invalid page with spaces"]
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

        src["pages"] = []
        with self.assertRaises(IntakeRefused) as ctx:
            load_source(src)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_load_source_optional_repo_commit_accepted(self):
        """synthetic_fixture: true，带 repo_commit 通过；缺省为 None。"""
        src = fixture_source()
        loaded_without = load_source(src)
        self.assertIsNone(loaded_without["repo_commit"])
        self.assertIsNone(loaded_without["yaml_metadata"])

        src_with = fixture_source()
        src_with["repo_commit"] = "a" * 40
        src_with["yaml_metadata"] = {"author": "unknown"}
        loaded_with = load_source(src_with)
        self.assertEqual(loaded_with["repo_commit"], "a" * 40)
        self.assertEqual(loaded_with["yaml_metadata"], {"author": "unknown"})

    def test_read_source_files_collects_all_missing(self):
        """synthetic_fixture: true，按 pages 顺序一次收集全部不存在的路径。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            pages = ["missing_page_01", "missing_page_02"]
            with self.assertRaises(SourceAssetMissing) as ctx:
                read_source_files(td, pages)
            self.assertEqual(ctx.exception.code, "SRC_001")
            self.assertEqual(len(ctx.exception.paths), 2)
            for p in ctx.exception.paths:
                self.assertIn("missing_page", p)
            # 校验 message 格式
            for p in ctx.exception.paths:
                self.assertIn("BLOCKED_SOURCE_ASSET_MISSING %s" % p, str(ctx.exception))

    def test_read_source_files_missing_dir(self):
        """synthetic_fixture: true，source_dir 不是目录抛出 SourceAssetMissing([str(source_dir)])。"""
        non_existent = Path("/non/existent/directory/path/for/test")
        with self.assertRaises(SourceAssetMissing) as ctx:
            read_source_files(non_existent, ["page_001"])
        self.assertEqual(ctx.exception.code, "SRC_001")
        self.assertEqual(ctx.exception.paths, [str(non_existent)])

    def test_read_source_files_reads_utf8(self):
        """synthetic_fixture: true，读取 UTF-8 文件与带 BOM 的 UTF-8 文件统一转为 UTF-8 字节。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            content_text = "乾元秘旨·太极图说\n天地之先。"
            # 无 BOM
            f1 = make_text_file("page_001", content_text, encoding="utf-8", target_dir=td)
            # 带 BOM
            bom_bytes = b"\xef\xbb\xbf" + content_text.encode("utf-8")
            f2 = make_text_file("page_002", bom_bytes, target_dir=td)

            res = read_source_files(td, ["page_001", "page_002"])
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0]["data"], content_text.encode("utf-8"))
            self.assertEqual(res[1]["data"], content_text.encode("utf-8"))

    def test_read_source_files_records_sha256(self):
        """synthetic_fixture: true，校验返回每项包含 page, data, sha256, size。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            content_text = "河图洛书者，象数之源也。"
            make_text_file("page_001", content_text, encoding="utf-8", target_dir=td)

            res = read_source_files(td, ["page_001"])
            self.assertEqual(len(res), 1)
            item = res[0]
            data_bytes = content_text.encode("utf-8")
            self.assertEqual(item["page"], "page_001")
            self.assertEqual(item["data"], data_bytes)
            self.assertEqual(item["sha256"], hashlib.sha256(data_bytes).hexdigest())
            self.assertEqual(item["size"], len(data_bytes))

    def test_build_manifest_key_order(self):
        """synthetic_fixture: true，顶层键序严格固定 11 个键。"""
        src = fixture_source()
        loaded_src = load_source(src)
        files = [
            {
                "page": "page_001",
                "path_ref": "page_001.txt",
                "data": b"sample text",
                "sha256": hashlib.sha256(b"sample text").hexdigest(),
                "size": len(b"sample text"),
            }
        ]
        manifest = build_source_manifest(loaded_src, files)

        expected_top_keys = [
            "source_id",
            "work_title",
            "edition_note",
            "technique_id",
            "rights_status",
            "release_policy",
            "edition_part",
            "source_assets",
            "files",
            "conversion",
            "content_status",
        ]
        self.assertEqual(list(manifest.keys()), expected_top_keys)

    def test_build_manifest_source_assets_key_order(self):
        """synthetic_fixture: true，逐字断言 12 键键序。"""
        src = fixture_source()
        loaded_src = load_source(src)
        files = [
            {
                "page": "page_001",
                "path_ref": "page_001.txt",
                "data": b"sample text",
                "sha256": hashlib.sha256(b"sample text").hexdigest(),
                "size": len(b"sample text"),
            }
        ]
        manifest = build_source_manifest(loaded_src, files)
        self.assertEqual(len(manifest["source_assets"]), 1)
        asset = manifest["source_assets"][0]

        expected_asset_keys = [
            "page",
            "path_ref",
            "sha256",
            "size",
            "width",
            "height",
            "object_store",
            "in_git",
            "yaml_metadata",
            "source_site",
            "source_url",
            "repo_commit",
        ]
        self.assertEqual(list(asset.keys()), expected_asset_keys)
        self.assertIsNone(asset["width"])
        self.assertIsNone(asset["height"])
        self.assertEqual(asset["object_store"], "local")
        self.assertFalse(asset["in_git"])

    def test_build_manifest_no_source_sites(self):
        """synthetic_fixture: true，顶层不含 source_sites，files 为空列表。"""
        src = fixture_source()
        loaded_src = load_source(src)
        files = [
            {
                "page": "page_001",
                "path_ref": "page_001.txt",
                "data": b"sample text",
                "sha256": hashlib.sha256(b"sample text").hexdigest(),
                "size": len(b"sample text"),
            }
        ]
        manifest = build_source_manifest(loaded_src, files)
        self.assertNotIn("source_sites", manifest)
        self.assertEqual(manifest["files"], [])
        self.assertEqual(manifest["content_status"], "machine_extracted")
        self.assertEqual(manifest["conversion"]["note"], "M1 电子文本入库；不做清洗（§9）")

    def test_manifest_bytes_deterministic(self):
        """synthetic_fixture: true，多次序列化输出字节严格一致。"""
        src = fixture_source()
        loaded_src = load_source(src)
        files = [
            {
                "page": "page_001",
                "path_ref": "page_001.txt",
                "data": b"sample text",
                "sha256": hashlib.sha256(b"sample text").hexdigest(),
                "size": len(b"sample text"),
            }
        ]
        b1 = manifest_bytes(loaded_src, files)
        b2 = manifest_bytes(loaded_src, files)
        self.assertEqual(b1, b2)
        self.assertTrue(b1.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
