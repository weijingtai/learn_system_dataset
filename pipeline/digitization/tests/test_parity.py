"""M1→M2 产出与 M3 输入解析等价性验证（act/06，synthetic_fixture: true）。

不修改任何生产代码，只读 Ledger。全部断言建立在真实数值之上——Ledger 修订内容、
Object Store 字节、patch 映射与 sha256 比对——不使用「键存在」这类空转断言。
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.digitization.step import run_m2
from pipeline.intake.step import run_m1
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[3]

# 合成电子文本样例（synthetic_fixture: true）：
# 含 BOM、零宽字符、Markdown 转义残留、水印链接与繁简混杂，确保清洗有实际效果。
# 不含替换字符（? / □ / U+FFFD）与 PUA 码位——这两类的终态为 known_unresolvable，
# 会使 M2 Gate 的 findings_valid 不通过，与本文件要验证的等价性无关。
FIXTURE_TEXT = (
    "\ufeff"
    + "乾元秘旨\n" * 3
    + "太極圖說\n"
    + "无极大极，动而生阳。\n"
    + "此處有零寬字符\u200b插入。\n"
    + "轉義殘留\\-與\\[須還原。\n"
    + "本站下載自\u200bhttps://example.org/qianyuan\n"
    + "結語。\n"
)

# README §3：source_manifest 顶层键序逐字
MANIFEST_TOP_KEYS = [
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

# cleaner 对 action == "patched" 各类 finding 的处理规则（README §4.3 / patcher.py）
_STRIPPED_KINDS = ("control_char", "encoding_issue", "watermark", "header_footer")


def _m1_files(data: bytes) -> list[dict]:
    """构造 M1 输入文件对象列表（synthetic_fixture: true）。"""
    return [
        {
            "page": "page_001",
            "path_ref": "page_001.txt",
            "data": data,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
    ]


class _ParityBase(unittest.TestCase):
    """在真实临时 Ledger 上运行 M1，供各用例继续做 M2 与 M3 消费。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.service = LedgerService(self._tmp.name)
        self.addCleanup(self.service.close)

        self.data = FIXTURE_TEXT.encode("utf-8")
        self.source_info = {
            "source_id": "src_qianyuan_ed01",
            "work_title": "乾元秘旨",
            "edition_note": "殆知阁电子文本",
            "technique_id": "qizheng",
            "rights_status": "站方声明免费下载、未附许可证",
            "release_policy": "reference_and_hash_only",
            "edition_part": {
                "artifact_id": "art_000000000000000000000000000000e1",
                "label": "卷一·太极图说",
                "pages": ["page_001"],
            },
            "source_site": "daizhige.org",
            "source_url": "https://daizhige.org/qianyuan/01.txt",
            "file_sha256": hashlib.sha256(self.data).hexdigest(),
            "pages": ["page_001"],
        }
        self.edition_part_id = self.source_info["edition_part"]["artifact_id"]
        self.m1_result = run_m1(
            self.service, self.source_info, _m1_files(self.data), self.edition_part_id
        )
        self.raw_text_revision_id = self.m1_result["raw_text_revision_ids"][0]

    def _revision_bytes(self, revision_id: str) -> tuple[dict, bytes]:
        """取回修订记录与 Object Store 中的真实字节。"""
        rev = self.service.get_revision(revision_id)
        self.assertIsNotNone(rev, f"修订不存在: {revision_id}")
        data = self.service.objects.get(rev["sha256"])
        self.assertIsNotNone(data, f"对象内容缺失: {rev['sha256']}")
        return rev, data

    def _run_m2(self) -> dict:
        """运行 M2 并断言 Gate 放行。"""
        res = run_m2(
            self.service, self.raw_text_revision_id, self.source_info, self.edition_part_id
        )
        gate = res.get("gate_result")
        self.assertIsNotNone(gate, f"M2 未返回 gate_result: {res}")
        self.assertTrue(gate.passed, f"M2 Gate 未放行: {res.get('error') or gate.failed_checks}")
        return res

    def _m3_inputs(self):
        """M3 电子文本输入解析入口（impl-10，消费 M2 四类产物）。"""
        from pipeline.corpus_compiler.step_offset import resolve_m3_text_inputs

        return resolve_m3_text_inputs(self.service, self.edition_part_id)


class TestM1ManifestParseableByM3(_ParityBase):
    """M1 产出的 source_manifest 可被 M3 输入解析。"""

    def test_m1_manifest_parseable_by_m3(self):
        """synthetic_fixture: true，manifest 对象哈希自洽、键序逐字、来源哈希回到磁盘文件。"""
        rev, raw_bytes = self._revision_bytes(self.m1_result["manifest_revision_id"])

        # 1. 修订已封存，且内容哈希与修订记录登记值一致（真实 sha256 复算）
        self.assertEqual(rev["status"], "sealed")
        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), rev["sha256"])

        # 2. 内容可解析，顶层键序逐字等于 README §3
        manifest = yaml.safe_load(raw_bytes.decode("utf-8"))
        self.assertEqual(list(manifest.keys()), MANIFEST_TOP_KEYS)
        self.assertNotIn("source_sites", manifest)

        # 3. source_assets[].sha256 回到磁盘原始文件字节（追踪链末端的锚）
        asset = manifest["source_assets"][0]
        self.assertEqual(asset["sha256"], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(asset["size"], len(self.data))
        self.assertNotEqual(asset["source_site"], "")
        self.assertNotEqual(asset["source_url"], "")

        # 4. M3 输入解析确实消费了这份 M1 产出：读回的 raw_text 就是 M1 冻结的修订
        self._run_m2()
        m3_inputs = self._m3_inputs()
        self.assertEqual(m3_inputs.raw_text_revision_id, self.raw_text_revision_id)
        raw_rev, raw_bytes_m1 = self._revision_bytes(self.raw_text_revision_id)
        self.assertEqual(raw_rev["status"], "sealed")
        self.assertEqual(m3_inputs.raw_text.encode("utf-8"), raw_bytes_m1)


class TestM2OutputParseableByM3(_ParityBase):
    """M2 产出的 cleaned_text + patch + report 可被 M3 相关解析消费。"""

    def test_m2_output_parseable_by_m3(self):
        """synthetic_fixture: true，三类产物封存自洽，且被 M3 入口按 revision_id 精确消费。"""
        m2 = self._run_m2()

        # 1. 三类产物修订均封存，内容哈希与登记值一致（真实 sha256 复算）
        for key in ("cleaned_revision_id", "patch_revision_id", "report_revision_id"):
            rev, data = self._revision_bytes(m2[key])
            self.assertEqual(rev["status"], "sealed")
            self.assertEqual(hashlib.sha256(data).hexdigest(), rev["sha256"])

        # 2. M3 入口解析出的正是这三个修订，且内容字节级一致
        m3_inputs = self._m3_inputs()
        self.assertEqual(m3_inputs.cleaned_text_revision_id, m2["cleaned_revision_id"])
        self.assertEqual(m3_inputs.patch_set_revision_id, m2["patch_revision_id"])
        self.assertEqual(m3_inputs.report_revision_id, m2["report_revision_id"])

        _, cleaned_bytes = self._revision_bytes(m2["cleaned_revision_id"])
        self.assertEqual(m3_inputs.cleaned_text.encode("utf-8"), cleaned_bytes)

        # 3. patch 与 report 结构可消费，且 finding ↔ patch 关联成立
        self.assertTrue(m3_inputs.patches, "M2 应产出确定性 patch")
        findings = m3_inputs.sanitization_report["findings"]
        self.assertTrue(findings, "M2 应产出 sanitization finding")
        self.assertEqual(m3_inputs.sanitization_report["summary"]["deferred_count"], 0)

        patch_ids = {p["patch_id"] for p in m3_inputs.patches}
        for finding in findings:
            pid = finding["patch_id"]
            if pid is not None:
                self.assertIn(pid, patch_ids)
                patch = next(p for p in m3_inputs.patches if p["patch_id"] == pid)
                self.assertEqual(patch["raw_start"], finding["raw_start"])
                self.assertEqual(patch["raw_end"], finding["raw_end"])


class TestRawTextFrozen(_ParityBase):
    """M2 运行后 raw_text 修订不变。"""

    def test_raw_text_frozen(self):
        """synthetic_fixture: true，M2 前后 raw_text 的对象字节、sha256 与修订记录三者皆不变。"""
        rev_before, bytes_before = self._revision_bytes(self.raw_text_revision_id)
        sha_before = hashlib.sha256(bytes_before).hexdigest()
        self.assertEqual(sha_before, rev_before["sha256"])

        self._run_m2()

        rev_after, bytes_after = self._revision_bytes(self.raw_text_revision_id)
        # 字节级不变（不是「键还在」）
        self.assertEqual(bytes_before, bytes_after)
        self.assertEqual(hashlib.sha256(bytes_after).hexdigest(), sha_before)
        self.assertEqual(rev_before, rev_after)
        self.assertEqual(rev_after["status"], "sealed")

        # 封存后不可再封存（不可变性由写路径拒绝，而非仅靠约定）
        with self.assertRaises(Exception):
            self.service.seal_revision(self.raw_text_revision_id)


class TestCleanedTextNotEqualRaw(_ParityBase):
    """清洗后文本不等于原始文本，清洗有实际效果。"""

    def test_cleaned_text_not_equal_raw(self):
        """synthetic_fixture: true，逐条 patch 映射成立，且按映射重建清洗文本与 Ledger 全等。"""
        self._run_m2()
        m3_inputs = self._m3_inputs()
        raw_text = m3_inputs.raw_text
        cleaned_text = m3_inputs.cleaned_text

        # 1. 清洗确实改变了文本
        self.assertNotEqual(cleaned_text, raw_text)
        self.assertLess(len(cleaned_text), len(raw_text))

        # 2. 逐条 patch：清洗侧切片 == 记录的 replacement，原始侧切片 == finding.raw_excerpt
        findings = m3_inputs.sanitization_report["findings"]
        finding_by_patch = {
            f["patch_id"]: f for f in findings if f.get("patch_id") is not None
        }
        for patch in m3_inputs.patches:
            self.assertEqual(
                cleaned_text[patch["cleaned_start"]:patch["cleaned_end"]],
                patch["replacement"],
                f"{patch['patch_id']} 的 cleaned 区间与 replacement 不一致",
            )
            finding = finding_by_patch.get(patch["patch_id"])
            self.assertIsNotNone(finding, f"{patch['patch_id']} 无对应 finding")
            self.assertEqual(
                raw_text[patch["raw_start"]:patch["raw_end"]], finding["raw_excerpt"]
            )

        # 3. 按 patch 映射重建清洗文本，必须与 Ledger 中冻结的 cleaned_text 逐字相同
        chars: list[str] = []
        cursor = 0
        for patch in sorted(m3_inputs.patches, key=lambda p: p["raw_start"]):
            if patch["raw_start"] > cursor:
                chars.append(raw_text[cursor:patch["raw_start"]])
            kind = finding_by_patch[patch["patch_id"]]["kind"]
            if kind == "escape_residue":
                chars.append(raw_text[patch["raw_start"]:patch["raw_end"]][1:])
            elif kind in _STRIPPED_KINDS:
                chars.append("")
            else:
                chars.append(raw_text[patch["raw_start"]:patch["raw_end"]])
            cursor = max(cursor, patch["raw_end"])
        if cursor < len(raw_text):
            chars.append(raw_text[cursor:])
        self.assertEqual("".join(chars), cleaned_text)


class TestAcceptanceShellNoSilentPass(unittest.TestCase):
    """D3 护栏（G7-RULINGS 第 94 条）：验收脚本不得在入口失败时静默返回 0。

    做法：把脚本复制进伪仓库根（`SCRIPT_DIR/../..` 指向临时目录），并在其中放置一个
    行为可控的 `.venv/bin/python`，从而在不改动任何生产代码的前提下注入「必崩」或
    「零输出」的 acceptance 入口，断言脚本不返回 0。
    """

    SCRIPTS = ("m1-intake.sh", "m2-sanitization.sh")

    def _run_sandboxed(self, script_name: str, fake_python: str) -> subprocess.CompletedProcess:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        dest = root / "openspec" / "acceptance" / script_name
        dest.parent.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "openspec" / "acceptance" / script_name, dest)

        py = root / ".venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text(fake_python, encoding="utf-8")
        py.chmod(0o755)

        # 宿主目录存在，使脚本越过 BLOCKED 前置检查、真正走到调用验收入口这一步
        fixture = root / "fixture"
        fixture.mkdir()

        env = dict(os.environ, FIXTURE_DIR=str(fixture))
        return subprocess.run(
            ["bash", str(dest)], capture_output=True, text=True, env=env
        )

    def test_shell_no_silent_pass_on_empty_output(self):
        """synthetic_fixture: true，入口退出 0 但零输出 → 脚本不得返回 0。"""
        for script in self.SCRIPTS:
            with self.subTest(script=script):
                proc = self._run_sandboxed(script, "#!/bin/sh\nexit 0\n")
                self.assertNotEqual(
                    proc.returncode,
                    0,
                    f"{script} 在零输出时静默返回 0：{proc.stdout}",
                )

    def test_shell_no_silent_pass_on_nonzero_rc(self):
        """synthetic_fixture: true，入口非零退出（即便输出了一行 PASS）→ 脚本不得返回 0。"""
        fake = '#!/bin/sh\necho "PASS manifest_exists 伪造的绿灯"\nexit 7\n'
        for script in self.SCRIPTS:
            with self.subTest(script=script):
                proc = self._run_sandboxed(script, fake)
                self.assertNotEqual(
                    proc.returncode,
                    0,
                    f"{script} 在入口 rc=7 时静默返回 0：{proc.stdout}",
                )


if __name__ == "__main__":
    unittest.main()
