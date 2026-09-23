"""M7 增量汇编 F 波：mini_release01 多版次金标 fixture 验收测试（act/impl-07/20）。

本文件只读 fixture 与已验收模块；**不读 var/**（运行时账本，`.gitignore:16`）。
真书 m6 实跑证据见 `pipeline/corpus/_fixture/mini_release01/tools/probe_real_m6.py`
与回报文件，不进单元测试。
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.assembly import model as m7_model
from pipeline.assembly.canonical import canonical_json
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.gate import evaluate_genesis
from pipeline.assembly.orchestrate import assemble as assemble_incremental
from pipeline.assembly.orchestrate import knowledge_equivalent
from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

#: 对勘四类（apply.COLLATION_KINDS 的独立副本：判据不 import 被验模块的行为常量）
COLLATION_KINDS = ("alignment", "variant_reading", "addition", "omission")

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
MINI_ED01_SPANS = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"

# 冻结金标（impl-07 README §1.2：mini_ed01 spans.yaml 金标 sha256）
MINI_ED01_SPANS_SHA256 = "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef"

# M7 上游视图允许出现的已登记前缀家族（登记册 §3.1–§3.4）。
# 明确排除：`ent_`/`rel_`（M8 下游）、`ku_`（旧管线）、`hg_`（Contract Registry）。
UPSTREAM_ID_FAMILIES = {
    "src_", "ss_", "sem_", "as_", "pr_", "co_", "co_shared_",
    "pat_", "sch_", "sv_", "cg_", "art_", "rev_", "pkg_", "prun_", "srun_",
}

# 夹具中文档里语义为「标识」的键名（前缀护栏只扫这些键的值）
ID_TYPED_KEYS = {
    "source_id",
    "edition_part_artifact_id",
    "corpus_spans_revision_id",
    "source_span_id",
    "entity_id",
    "artifact_id",
    "artifact_revision_id",
    "snapshot_artifact_id",
    "snapshot_revision_id",
    "base_snapshot_revision_id",
    "prev_revision_id",
    "supersedes_revision_id",
    "candidate_set_revision_id",
    "candidate_package_revision_id",
    "validation_package_revision_id",
    "decision_revision_id",
    "reviewed_edition_revision_id",
    "reviewed_edition_package_artifact_id",
    "reviewed_edition_package_revision_id",
    "reviewed_edition_artifact_id",
    "school_view_id",
    "school_id",
    "conflict_group_id",
    "pattern_id",
    "assertion_id",
    "proposition_id",
    "concept_ref",
    "step_run_id",
    "m4_step_run_id",
    "m6_step_run_id",
    "processing_run_id",
    "stage_package_id",
    "m6_stage_package_id",
    "m6_package_revision_id",
    "from_entity_id",
    "to_entity_id",
    # 复数形态（同一组标识的列表）：一并纳入护栏，避免用复数键绕过扫描
    "assertion_ids",
    "school_view_ids",
    "source_span_ids",
    "member_school_view_ids",
    "edition_part_artifact_ids",
    "decision_revision_ids",
    "correction_request_revision_ids",
    "claim_refs",
    "concept_refs",
    "school_ids",
}


def load_yaml(path):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_manifest():
    return load_yaml(FIXTURE / "manifest.yaml")


def declared_present_keys(candidate_set):
    """视图**声明**为 present 的可比单元键（独立重算，不读引擎中间量）。"""
    keys = set()
    for unit in candidate_set.get("collation_units") or []:
        if unit.get("collation_key") and unit.get("present", True):
            keys.add(unit["collation_key"])
    for assertion in candidate_set.get("assertions") or []:
        if assertion.get("collation_key"):
            keys.add(assertion["collation_key"])
    return keys


def iter_id_values(node, key=None):
    """深度遍历文档，产出 (key, value) 中语义为标识的字符串值。"""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_id_values(v, k)
    elif isinstance(node, list):
        for item in node:
            yield from iter_id_values(item, key)
    elif isinstance(node, str) and key in ID_TYPED_KEYS:
        yield key, node


class TestReleaseFixture(unittest.TestCase):
    # ---------------------------------------------------------------- 具名用例 1
    def test_mini_release01_has_at_least_two_editions(self):
        manifest = load_manifest()
        editions = manifest["editions"]
        self.assertGreaterEqual(
            len(editions), 2, "mini_release01 必须至少含两个版次（增量汇编的最小可测形状）"
        )
        source_ids = [ed["source_id"] for ed in editions]
        self.assertEqual(len(set(source_ids)), len(source_ids), "版次 source_id 不得重复")
        for ed in editions:
            view_dir = FIXTURE / ed["views_dir"]
            self.assertTrue(view_dir.is_dir(), "版次视图目录缺失: %s" % view_dir)
            for name in ed["view_files"]:
                self.assertTrue((view_dir / name).is_file(), "视图文件缺失: %s/%s" % (ed["views_dir"], name))

    # ---------------------------------------------------------------- 具名用例 2
    def test_mini_release01_span_refs_anchor_to_mini_ed01_golden(self):
        manifest = load_manifest()
        anchor = manifest["span_anchor"]
        self.assertEqual(
            hashlib.sha256(MINI_ED01_SPANS.read_bytes()).hexdigest(),
            MINI_ED01_SPANS_SHA256,
            "mini_ed01/spans.yaml 金标字节已变（本夹具锚定它，金标一字不许动）",
        )
        self.assertEqual(anchor["sha256"], MINI_ED01_SPANS_SHA256, "manifest.span_anchor.sha256 与金标不符")

        spans_doc = load_yaml(MINI_ED01_SPANS)
        spans = {s["span_id"]: s for s in spans_doc["spans"]}
        self.assertEqual(anchor["evidence_level"], spans_doc["evidence_level"], "evidence_level 须与金标一致")

        seen_links = 0
        for ed in manifest["editions"]:
            cset = load_json(FIXTURE / ed["views_dir"] / "candidate_set.json")
            reviewed = load_json(FIXTURE / ed["views_dir"] / "reviewed_edition.json")
            self.assertEqual(cset["evidence_level"], spans_doc["evidence_level"])
            self.assertEqual(cset["source_id"], ed["source_id"])
            self.assertEqual(cset["edition_part_artifact_id"], ed["edition_part_artifact_id"])
            self.assertEqual(reviewed["edition_part_artifact_id"], ed["edition_part_artifact_id"])

            links = []
            for a in cset["assertions"]:
                links.extend(a.get("evidence", []))
            links.extend(reviewed.get("evidence_links", []))
            self.assertTrue(links, "版次 %s 视图没有任何证据链" % ed["edition_key"])
            for link in links:
                span = spans.get(link["source_span_id"])
                self.assertIsNotNone(
                    span, "证据 span 未锚定 mini_ed01 金标: %s" % link["source_span_id"]
                )
                self.assertEqual(link["start_offset"], span["start_offset"], "offset 与金标 span 不符")
                self.assertEqual(link["end_offset"], span["end_offset"], "offset 与金标 span 不符")
                self.assertEqual(
                    link["quote_sha256"],
                    hashlib.sha256(span["text"].encode("utf-8")).hexdigest(),
                    "quote_sha256 与金标 span 文本不符",
                )
                if "quote" in link:
                    self.assertEqual(link["quote"], span["text"], "quote 与金标 span 文本不符")
                if "corpus_spans_revision_id" in link:
                    self.assertEqual(
                        link["corpus_spans_revision_id"], anchor["corpus_spans_revision_id"]
                    )
                seen_links += 1
        self.assertGreater(seen_links, 0)

    # ---------------------------------------------------------------- 具名用例 3
    def test_mini_release01_verify_sh_needs_no_page_assets(self):
        verify = FIXTURE / "verify.sh"
        self.assertTrue(verify.is_file(), "fixture 必须自带 verify.sh")

        images = [
            p.name
            for p in FIXTURE.rglob("*")
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf")
        ]
        self.assertEqual(images, [], "fixture 内不得出现页图/PDF 资产: %s" % images)

        proc = subprocess.run(
            ["bash", str(verify)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=dict(os.environ, FIXTURE_ASSET_ROOT="/nonexistent", FIXTURE_DIR=str(FIXTURE)),
        )
        out = proc.stdout
        self.assertNotIn("BLOCKED_SOURCE_ASSET_MISSING", out, "夹具不得要求任何页图")
        self.assertNotIn("BLOCKED_ENV", out)
        self.assertEqual(proc.returncode, 0, "verify.sh 退出码 %d\n%s\n%s" % (proc.returncode, out, proc.stderr))
        self.assertEqual(out.strip().splitlines()[-1], "FIXTURE OK")

    # ---------------------------------------------------------------- 具名用例 4
    def test_release_run_scope_key_creates_checkpoint_chain(self):
        """D-02 采纳 A：ReleaseRun 以新 `art_` 作 scope 键（Checkpoint 链键），零 Ledger 改动。"""
        tmp = tempfile.mkdtemp(prefix="m7_release_scope_")
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(service.close)

        scope_key = ids.new_id("artifact_id")
        proc_id = service.create_processing_run("release_run", scope_key, "qizheng")
        cfg_artifact_id, cfg_rev_id = service.put_run_artifact(
            proc_id,
            "configuration",
            canonical_json({"stage": "m7", "task": "assemble", "scope_key": scope_key}),
            artifact_id=scope_key,
            producer_module="pipeline.assembly",
            producer_version="0.1.0-draft",
        )
        self.assertEqual(cfg_artifact_id, scope_key, "configuration Artifact 身份须等于 scope 键 X")

        step_run_id = service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "step_run_id": ids.new_id("step_run_id"),
                "processing_run_id": proc_id,
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": cfg_rev_id,
            }
        )
        for task in ("propose_r1", "seal_snapshot"):
            service.write_checkpoint(
                step_run_id,
                edition_part_id=scope_key,
                stage="m7",
                completed_tasks=[{"task_id": task, "artifact_revision_id": cfg_rev_id, "status": "succeeded"}],
                human_decisions=[],
                pending_queue=[],
                next_pointer=None,
            )

        chain = service.list_checkpoints(scope_key, "m7")
        self.assertEqual(len(chain), 2, "同一 ReleaseRun 的 Checkpoint 链须落在 scope 键下")
        self.assertIsNone(chain[0]["prev_checkpoint_revision_id"])
        self.assertEqual(chain[1]["prev_checkpoint_revision_id"], chain[0]["artifact_revision_id"])

        # 第二个 ReleaseRun 独占另一条链，互不覆写（D-02 A 的并发含义）
        second_key = ids.new_id("artifact_id")
        second_proc = service.create_processing_run("release_run", second_key, "qizheng")
        _, second_cfg = service.put_run_artifact(
            second_proc,
            "configuration",
            canonical_json({"stage": "m7", "task": "assemble"}),
            artifact_id=second_key,
            producer_module="pipeline.assembly",
            producer_version="0.1.0-draft",
        )
        second_step = service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "step_run_id": ids.new_id("step_run_id"),
                "processing_run_id": second_proc,
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": second_cfg,
            }
        )
        service.write_checkpoint(
            second_step,
            edition_part_id=second_key,
            stage="m7",
            completed_tasks=[{"task_id": "propose_r1", "artifact_revision_id": second_cfg, "status": "succeeded"}],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        self.assertEqual(len(service.list_checkpoints(second_key, "m7")), 1)
        self.assertEqual(len(service.list_checkpoints(scope_key, "m7")), 2, "第一个 Run 的链不得被覆写")

    # ---------------------------------------------------------------- 具名用例 5
    def test_snapshot_identity_is_stable_per_technique(self):
        """D-03 采纳 A：每 technique 一个 Snapshot Artifact，每轮写新 `rev_`，prev 指向基底。"""
        manifest = load_manifest()
        plan = load_yaml(FIXTURE / manifest["expected"]["snapshot_revisions"])

        artifact_id = plan["snapshot_artifact_id"]
        ids.validate("artifact_id", artifact_id)
        self.assertEqual(plan["technique_id"], manifest["technique_id"])

        revisions = plan["revisions"]
        self.assertGreaterEqual(len(revisions), 2, "增量金标须含两轮（创世 + 增量）")
        rev_ids = [r["snapshot_revision_id"] for r in revisions]
        self.assertEqual(len(set(rev_ids)), len(rev_ids), "每轮须写新 rev_")
        for rev_id in rev_ids:
            ids.validate("artifact_revision_id", rev_id)
        self.assertEqual(
            sorted(revisions, key=lambda r: r["assembly_seq"]), revisions, "revisions 须按 assembly_seq 升序"
        )

        first = revisions[0]
        self.assertIsNone(first["base_snapshot_revision_id"], "创世轮无基底")
        self.assertIsNone(first["prev_revision_id"])
        for prev, cur in zip(revisions, revisions[1:]):
            self.assertEqual(cur["base_snapshot_revision_id"], prev["snapshot_revision_id"])
            self.assertEqual(cur["prev_revision_id"], prev["snapshot_revision_id"], "同 Artifact 续修订")
            self.assertEqual(cur.get("supersedes_revision_id"), prev["snapshot_revision_id"])

        for rev in revisions:
            knowledge_file = FIXTURE / rev["knowledge_file"]
            self.assertTrue(knowledge_file.is_file(), "金标 knowledge 文件缺失: %s" % rev["knowledge_file"])
            raw = knowledge_file.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), rev["knowledge_sha256"])
            knowledge = json.loads(raw.decode("utf-8"))
            self.assertEqual(knowledge["technique_id"], manifest["technique_id"])
            self.assertEqual(
                raw,
                canonical_json(knowledge),
                "金标 knowledge 须为规范 JSON 字节（sort_keys + 紧凑分隔符 + 末尾换行）",
            )

    # ---------------------------------------------------------------- 具名用例 6
    def test_fixture_uses_no_registered_id_prefix(self):
        """前缀护栏：约定标记不得取前缀形态；夹具不得引入未登记前缀，也不得越用下游前缀。"""
        manifest = load_manifest()
        conventions = manifest["conventions"]

        for marker in conventions["non_prefix_markers"]:
            self.assertIsNone(
                ids.kind_of(marker), "约定标记 %r 不得取已登记前缀形态" % marker
            )
            self.assertNotIn("_", marker, "约定标记 %r 不得含下划线（避免被当成新前缀）" % marker)

        declared = set(manifest["id_families_used"])
        self.assertTrue(
            declared <= UPSTREAM_ID_FAMILIES,
            "夹具声明的前缀家族越界（含新前缀或下游前缀）: %s" % sorted(declared - UPSTREAM_ID_FAMILIES),
        )

        docs = [("manifest.yaml", manifest)]
        for ed in manifest["editions"]:
            for name in ed["view_files"]:
                docs.append(("%s/%s" % (ed["views_dir"], name), load_json(FIXTURE / ed["views_dir"] / name)))
        docs.append((manifest["expected"]["snapshot_revisions"], load_yaml(FIXTURE / manifest["expected"]["snapshot_revisions"])))
        for key in ("round1", "round2"):
            path = manifest["expected"][key]
            docs.append((path, load_json(FIXTURE / path)))

        for doc_name, doc in docs:
            for key, value in iter_id_values(doc):
                family = ids.kind_of(value)
                self.assertIsNotNone(
                    family, "%s 出现未登记前缀形态的标识 %s=%r" % (doc_name, key, value)
                )
                prefix = value.split("_", 1)[0] + "_"
                if prefix == "co_shared_":
                    prefix = "co_shared_"
                self.assertIn(
                    prefix, UPSTREAM_ID_FAMILIES, "%s 的 %s=%r 用了上游不合法的前缀" % (doc_name, key, value)
                )
                self.assertIn(prefix, declared, "%s 的 %s 用了未声明的前缀家族 %s" % (doc_name, key, prefix))

    # ---------------------------------------------------------------- 附加用例
    def test_release_fixture_views_pass_m7_validation(self):
        manifest = load_manifest()
        for ed in manifest["editions"]:
            view_dir = FIXTURE / ed["views_dir"]
            cset = load_json(view_dir / "candidate_set.json")
            reviewed = load_json(view_dir / "reviewed_edition.json")
            package = load_json(view_dir / "reviewed_edition_package.json")
            res_cset = m7_model.validate_candidate_set(cset)
            res_re = m7_model.validate_reviewed_edition(reviewed)
            res_pkg = m7_model.validate_reviewed_package(package)
            self.assertEqual(res_cset["technique_id"], manifest["technique_id"])
            self.assertEqual(res_re["edition_part_artifact_id"], ed["edition_part_artifact_id"])
            self.assertEqual(
                res_pkg["reviewed_edition_revision_id"],
                ed["ledger_constants"]["reviewed_edition_revision_id"],
            )
            self.assertEqual(
                res_re["candidate_package_revision_id"],
                ed["ledger_constants"]["candidate_package_revision_id"],
            )

    def test_release_fixture_round1_matches_accepted_genesis_engine(self):
        """r1 金标必须逐字节等于已验收创世引擎在这份 ed01 视图上的输出。"""
        manifest = load_manifest()
        ed01 = manifest["editions"][0]
        view_dir = FIXTURE / ed01["views_dir"]
        cset = load_json(view_dir / "candidate_set.json")
        reviewed = load_json(view_dir / "reviewed_edition.json")

        prop = propose_genesis(cset, reviewed)
        asm = assemble_genesis(cset, reviewed, prop["proposals"], id_range=manifest["id_range"])

        golden = (FIXTURE / manifest["expected"]["round1"]).read_bytes()
        self.assertEqual(golden, asm["knowledge_bytes"], "r1 金标与创世引擎输出不一致")

        gate = evaluate_genesis(candidate_set=cset, reviewed_edition=reviewed, knowledge=asm["knowledge"])
        failed = {k: v["detail"] for k, v in gate["checks"].items() if not v["passed"]}
        self.assertEqual(failed, {}, "r1 金标未通过创世独立 Gate: %s" % failed)

    # ---------------------------------------------------------------- 具名用例（ACT 26 一.1）
    def test_r2_incremental_matches_rebuilt_gold_byte_for_byte(self):
        """r2 金标必须与增量**实跑**逐字节相同（CHARTER §19.3：逐字节比对放纯函数层）。

        基底号用 `expected/snapshot_revisions.yaml` 里的固定常量（纯函数层可以钉死）；
        Ledger 路径上基底号是每轮新发的，那里只比「除 `meta` 外相同」。
        """
        manifest = load_manifest()
        ed99 = manifest["editions"][1]
        view_dir = FIXTURE / ed99["views_dir"]
        views = [
            {
                "source_id": ed99["source_id"],
                "candidate_set": load_json(view_dir / "candidate_set.json"),
                "reviewed_edition": load_json(view_dir / "reviewed_edition.json"),
            }
        ]
        base = load_json(FIXTURE / manifest["expected"]["round1"])
        plan = load_yaml(FIXTURE / manifest["expected"]["snapshot_revisions"])
        base_rev = plan["revisions"][0]["snapshot_revision_id"]

        golden = (FIXTURE / manifest["expected"]["round2"]).read_bytes()
        self.assertEqual(
            golden,
            canonical_json(json.loads(golden.decode("utf-8"))),
            "r2 金标必须是规范 JSON 字节（sort_keys + 紧凑分隔符 + 末尾换行）",
        )

        res = assemble_incremental(
            base, views, [], incremental=True, base_snapshot_revision_id=base_rev
        )
        self.assertEqual(res["status"], "complete", "夹具 ed99 增量轮必须完成合并")
        self.assertEqual(
            res["result"]["knowledge_bytes"], golden, "r2 金标与增量实跑产出不是字节等价的"
        )

        # 同一输入再跑一次：逐字节相同（可复现性）
        again = assemble_incremental(
            base, views, [], incremental=True, base_snapshot_revision_id=base_rev
        )
        self.assertEqual(again["result"]["knowledge_bytes"], golden, "同一输入两次运行字节不同")

        # 增量 ≡ 全量重算（CHARTER §6 完成定义）
        full = assemble_incremental(
            base, views, [], incremental=False, base_snapshot_revision_id=base_rev
        )
        self.assertTrue(
            knowledge_equivalent(res["result"]["knowledge"], full["result"]["knowledge"]),
            "增量汇编结果必须与全量重算逐字节相同",
        )

    # ---------------------------------------------------------------- 具名用例（ACT 26 一.2）
    def test_not_comparable_units_have_no_collation_relation(self):
        """对勘只许落在**两侧都声明 present** 的可比单元上（README §6）。

        §19.2 把缺文/增文/异文降为 I 波缺口，本波只覆盖对齐；但「不可比单元上不得
        出现任何对勘关系」这条仍要真验：
          1. 无 `collation_key` 的单元必须如实计进 `collation.not_comparable`（不得静默跳过）；
          2. 每条对勘关系两端的断言键必须落在「两侧都声明 present」的键集里；
          3. 反向：只被一侧声明的键（ed01 的 `sanche-0002/0003`，ed99 未声明）上不得出现对勘关系。
        """
        manifest = load_manifest()
        ed01, ed99 = manifest["editions"]
        views = []
        declared = {}
        for edition in (ed01, ed99):
            view_dir = FIXTURE / edition["views_dir"]
            cset = load_json(view_dir / "candidate_set.json")
            declared[edition["source_id"]] = declared_present_keys(cset)
            views.append(
                {
                    "source_id": edition["source_id"],
                    "candidate_set": cset,
                    "reviewed_edition": load_json(view_dir / "reviewed_edition.json"),
                }
            )
        base = load_json(FIXTURE / manifest["expected"]["round1"])
        plan = load_yaml(FIXTURE / manifest["expected"]["snapshot_revisions"])

        res = assemble_incremental(
            base,
            [views[1]],
            [],
            incremental=True,
            base_snapshot_revision_id=plan["revisions"][0]["snapshot_revision_id"],
        )
        knowledge = res["result"]["knowledge"]
        collation = res["result"]["collation"]

        # 1. 不可比单元如实入册（夹具恰有 1 个「声明了位置但无 collation_key」的单元）
        rows = collation["not_comparable"]
        self.assertEqual(len(rows), 1, "夹具恰有 1 个无 collation_key 的可比单元: %r" % rows)
        self.assertEqual(rows[0]["reason"], "missing_collation_key")
        self.assertIsNone(rows[0]["collation_key"])

        # 2. 对勘关系必须落在两侧都声明 present 的键上
        both_sides = declared[ed01["source_id"]] & declared[ed99["source_id"]]
        self.assertIn("sanche-0001", both_sides, "夹具的对齐单元必须两侧都声明")
        relations = [
            rel for rel in knowledge["relations"] if rel["relation_kind"] in COLLATION_KINDS
        ]
        self.assertEqual(
            [rel["relation_kind"] for rel in relations],
            ["alignment"],
            "§19.2：本波只覆盖对齐，其余三类是 I 波缺口，不得悄悄冒出",
        )
        by_assertion = {item["assertion_id"]: item for item in knowledge["assertions"]}
        for rel in relations:
            endpoints = [
                entity_id
                for entity_id in (rel.get("from_entity_id"), rel.get("to_entity_id"))
                if entity_id
            ]
            keys = {
                by_assertion[entity_id].get("collation_key")
                for entity_id in endpoints
                if entity_id in by_assertion
            }
            self.assertTrue(keys, "对勘关系两端必须落在断言上: %r" % rel)
            self.assertTrue(
                keys <= both_sides,
                "对勘关系 %s 落在不是「两侧都声明 present」的单元上: %r" % (rel["relation_key"], keys),
            )

        # 3. 反向：只有 ed01 声明的键上不得出现任何对勘关系（否则就是臆造缺文）
        undeclared = declared[ed01["source_id"]] - declared[ed99["source_id"]]
        self.assertTrue(undeclared, "夹具必须有「一侧未声明」的键，否则本判据是空转的")
        for rel in relations:
            endpoints = [rel.get("from_entity_id"), rel.get("to_entity_id")]
            keys = {
                by_assertion[entity_id].get("collation_key")
                for entity_id in endpoints
                if entity_id in by_assertion
            }
            self.assertFalse(keys & undeclared, "未声明的单元上出现了对勘关系: %r" % rel)

    def test_release_fixture_round2_passes_snapshot_validation(self):
        manifest = load_manifest()
        knowledge = load_json(FIXTURE / manifest["expected"]["round2"])
        m7_model.validate_snapshot_knowledge(knowledge)

        source_ids = [ed["source_id"] for ed in knowledge["editions"]]
        self.assertEqual(source_ids, sorted(source_ids), "editions 须按 source_id 升序")
        self.assertEqual(
            source_ids,
            sorted(ed["source_id"] for ed in manifest["editions"]),
            "r2 金标须并入全部版次",
        )
        self.assertGreaterEqual(len(knowledge["relations"]), 1, "增量轮须表达身份关系（至少 distinct_from）")
        for pattern in knowledge["patterns"]:
            self.assertNotIn("content_status", pattern)

    def test_release_fixture_seeds_into_temp_ledger_and_runs_genesis(self):
        """夹具视图可灌入临时 Ledger，并经 run_m7 产出与 r1 金标逐字节相同的 Snapshot。"""
        from pipeline.assembly.fixture_seed import seed_release_package
        from pipeline.assembly.step import run_m7

        manifest = load_manifest()
        tmp = tempfile.mkdtemp(prefix="m7_release_seed_")
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(service.close)

        seeded = seed_release_package(service, FIXTURE)
        self.assertEqual(len(seeded["editions"]), len(manifest["editions"]))

        ed01 = manifest["editions"][0]
        first = seeded["editions"][ed01["edition_key"]]
        res = run_m7(
            service,
            ed01["edition_part_artifact_id"],
            technique_id=manifest["technique_id"],
            reviewed_package_revision_ids=[first["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        self.assertEqual(res["status"], "succeeded", "夹具 ed01 视图在创世引擎上须成功")
        snap_rev = service.get_revision(res["snapshot_revision_id"])
        snap_bytes = service.objects.get(snap_rev["sha256"])
        self.assertEqual(snap_bytes, (FIXTURE / manifest["expected"]["round1"]).read_bytes())

        # 上游 M6 包在运行后不可变
        self.assertEqual(service.get_revision(first["m6_package_revision_id"])["status"], "sealed")


if __name__ == "__main__":
    unittest.main()
