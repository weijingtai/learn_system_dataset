"""M7 增量汇编 A 波：多包输入解析 + 基底 Snapshot 读取 + ReleaseRun scope 键（act/impl-07/21）。

本文件只读 fixture 与已验收模块；**不读 var/**（运行时账本，`.gitignore:16`）。
真书 m6 实跑证据见回报文件与 `mini_release01/tools/probe_real_m6.py`，不进单元测试。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.assembly import fixture_seed
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.inputs import resolve_m7_inputs
from pipeline.assembly.step import run_m7
from pipeline.assembly.tests.fixture_decisions import decisions_for_round
from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"

# 创世路径的返回键（act/21 contract 一.3：这些键与取值必须逐字不变）
LEGACY_KEYS = (
    "technique_id",
    "m6_stage_package_id",
    "reviewed_package_revision_id",
    "reviewed_edition_package_revision_id",
    "reviewed_edition_revision_id",
    "candidate_package_revision_id",
    "candidate_set_revision_id",
    "edition_part_artifact_id",
    "reviewed_package",
    "reviewed_edition",
    "candidate_set",
)

# 「返工包」= 同一 (source_id, edition_part_ids) 的第二份 m6 包，
# 只用合成保留号段（fixture 约定），不新增 ID 前缀。
REWORK_LEDGER_CONSTANTS = {
    "processing_run_id": "prun_00000000000000000000000000000026",
    "m4_step_run_id": "srun_00000000000000000000000000000020",
    "candidate_set_artifact_id": "art_00000000000000000000000000000020",
    "candidate_set_revision_id": "rev_00000000000000000000000000000020",
    "candidate_package_artifact_id": "art_00000000000000000000000000000021",
    "candidate_package_revision_id": "rev_00000000000000000000000000000021",
    "reviewed_edition_artifact_id": "art_00000000000000000000000000000022",
    "reviewed_edition_revision_id": "rev_00000000000000000000000000000022",
    "reviewed_edition_package_artifact_id": "art_00000000000000000000000000000023",
    "reviewed_edition_package_revision_id": "rev_00000000000000000000000000000023",
    "m6_stage_package_id": "pkg_m6_00000000000000000000000000000024",
    "m6_package_revision_id": "rev_00000000000000000000000000000024",
    "m6_step_run_id": "srun_00000000000000000000000000000025",
}


def load_manifest():
    return yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def load_view(view_dir, name):
    return json.loads((FIXTURE / view_dir / name).read_text(encoding="utf-8"))


class IncrementalInputsCase(unittest.TestCase):
    """临时 Ledger 上灌入 mini_release01 两版次（ed01 真实金标 + ed99 合成保留号）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m7_inc_a_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.service = LedgerService(Path(self.tmp) / "ledger")
        self.addCleanup(self.service.close)

        self.manifest = load_manifest()
        self.technique_id = self.manifest["technique_id"]
        self.id_range = self.manifest["id_range"]
        self.ed01 = self.manifest["editions"][0]
        self.ed99 = self.manifest["editions"][1]
        self.seeded = fixture_seed.seed_release_package(self.service, FIXTURE)["editions"]

    # ---------------------------------------------------------------- 测试夹具
    def ed01_m6_rev(self):
        return self.seeded[self.ed01["edition_key"]]["m6_package_revision_id"]

    def ed99_m6_rev(self):
        return self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]

    def seed_rework_package(self):
        """再灌一份同 (source_id, edition_part_ids) 的 m6 包（M6 返工，D-14）。"""
        lc = dict(self.ed01["ledger_constants"])
        lc.update(REWORK_LEDGER_CONSTANTS)
        view_dir = self.ed01["views_dir"]
        cset = load_view(view_dir, "candidate_set.json")
        reviewed = dict(
            load_view(view_dir, "reviewed_edition.json"),
            candidate_set_revision_id=lc["candidate_set_revision_id"],
            candidate_package_revision_id=lc["candidate_package_revision_id"],
        )
        package = dict(
            load_view(view_dir, "reviewed_edition_package.json"),
            reviewed_edition_revision_id=lc["reviewed_edition_revision_id"],
        )
        self.service.create_processing_run(
            "release_run",
            self.ed01["edition_part_artifact_id"],
            self.technique_id,
            processing_run_id=lc["processing_run_id"],
        )
        return fixture_seed._seed_one_edition(
            self.service,
            self.technique_id,
            self.ed01["edition_part_artifact_id"],
            lc["processing_run_id"],
            lc,
            cset,
            reviewed,
            package,
        )

    def make_snapshot_revision(self, payload=None):
        """造一个已 sealed 的 canonical_snapshot 修订（只当基底用，不做合并）。"""
        prun = self.service.create_processing_run(
            "release_run", ids.new_id("artifact_id"), self.technique_id
        )
        _, cfg_rev = self.service.put_run_artifact(
            prun,
            "configuration",
            json.dumps({"stage": "m7", "synthetic_base": True}, sort_keys=True).encode("utf-8"),
            producer_module="pipeline.assembly.tests",
            producer_version="0.1.0-draft",
        )
        step_run = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "step_run_id": ids.new_id("step_run_id"),
                "processing_run_id": prun,
                "input_artifact_ids": [],
                "technique_profile_id": self.technique_id,
                "configuration_artifact_id": cfg_rev,
            }
        )
        data = json.dumps(
            payload if payload is not None else {"technique_id": self.technique_id},
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        art_id, rev_id = self.service.put_artifact(
            step_run,
            "canonical_snapshot",
            data,
            producer_module="pipeline.assembly.tests",
            producer_version="0.1.0-draft",
        )
        self.service.seal_revision(rev_id)
        return art_id, rev_id, step_run

    def make_superseded_base(self):
        """基底修订 → superseded（D-15 前半要拒收的那种）。"""
        art_id, old_rev, step_run = self.make_snapshot_revision()
        data = json.dumps({"technique_id": self.technique_id, "round": 2}, sort_keys=True).encode("utf-8")
        # 只传 prev_revision_id：put_artifact 复用 prev 所属 Artifact
        # （显式传已存在的 artifact_id 会被 _new_or_explicit 拒为 ID_002）
        new_art, new_rev = self.service.put_artifact(
            step_run,
            "canonical_snapshot",
            data,
            prev_revision_id=old_rev,
            producer_module="pipeline.assembly.tests",
            producer_version="0.1.0-draft",
        )
        self.assertEqual(new_art, art_id)
        self.service.seal_revision(new_rev)
        self.service.supersede_revision(old_rev, new_rev)
        return art_id, old_rev, new_rev

    def ledger_row_counts(self):
        conn = self.service.store.conn
        return {
            name: conn.execute("SELECT count(*) FROM %s" % name).fetchone()[0]
            for name in ("artifact_revisions", "step_runs", "stage_checkpoints", "audit_log")
        }

    # ------------------------------------------------- 具名用例 1（多包接受）
    def test_resolve_inputs_accepts_multiple_reviewed_packages(self):
        res = resolve_m7_inputs(self.service, [self.ed01_m6_rev(), self.ed99_m6_rev()])

        self.assertEqual(len(res["packages"]), 2, "两个 reviewed package 都必须被解析，不得只取第一个")
        rev_ids = {pkg["reviewed_package_revision_id"] for pkg in res["packages"]}
        self.assertEqual(rev_ids, {self.ed01_m6_rev(), self.ed99_m6_rev()})
        source_ids = {pkg["source_id"] for pkg in res["packages"]}
        self.assertEqual(source_ids, {self.ed01["source_id"], self.ed99["source_id"]})
        for pkg in res["packages"]:
            self.assertEqual(pkg["technique_id"], self.technique_id)
            self.assertEqual(pkg["edition_part_ids"], [self.ed01["edition_part_artifact_id"]]
                             if pkg["source_id"] == self.ed01["source_id"]
                             else [self.ed99["edition_part_artifact_id"]])

        # 两包来源不同（source_id 互异）→ 不是替换
        self.assertEqual(res["replaces"], [])

        # 旧键仍在，且与「规范化排序后第一个包」一致
        for key in LEGACY_KEYS:
            self.assertIn(key, res)
        first = res["packages"][0]
        self.assertEqual(res["reviewed_package_revision_id"], first["reviewed_package_revision_id"])
        self.assertEqual(res["candidate_set_revision_id"], first["candidate_set_revision_id"])

    # --------------------------------------- 具名用例 2（坏包报错须指明第几个）
    def test_resolve_inputs_rejects_bad_package_naming_its_index(self):
        missing = "rev_000000000000000000000000000000ff"
        with self.assertRaises(AssemblyRefused) as ctx:
            resolve_m7_inputs(self.service, [self.ed01_m6_rev(), missing, self.ed99_m6_rev()])
        message = str(ctx.exception)
        self.assertIn("第 2 个包", message, "错误消息必须指明是第几个包: %s" % message)
        self.assertIn(missing, message, "错误消息必须指明修订 id: %s" % message)
        self.assertEqual(ctx.exception.code, "REF_001")

        # 类型不对（candidate_package 不是 stage_package）同样要指名道姓
        bad_rev = self.ed01["ledger_constants"]["candidate_package_revision_id"]
        with self.assertRaises(AssemblyRefused) as ctx2:
            resolve_m7_inputs(self.service, [self.ed01_m6_rev(), bad_rev])
        message2 = str(ctx2.exception)
        self.assertIn("第 2 个包", message2)
        self.assertIn(bad_rev, message2)
        self.assertEqual(ctx2.exception.code, "SCH_002")

    # --------------------------------------------- 具名用例 3（顺序无关）
    def test_resolve_inputs_order_does_not_affect_result(self):
        forward = resolve_m7_inputs(self.service, [self.ed01_m6_rev(), self.ed99_m6_rev()])
        backward = resolve_m7_inputs(self.service, [self.ed99_m6_rev(), self.ed01_m6_rev()])
        self.assertEqual(forward, backward, "入参顺序不得影响返回结构")
        # 同一输入两次调用逐字节相同
        again = resolve_m7_inputs(self.service, [self.ed01_m6_rev(), self.ed99_m6_rev()])
        self.assertEqual(
            json.dumps(forward, sort_keys=True, ensure_ascii=False),
            json.dumps(again, sort_keys=True, ensure_ascii=False),
        )

    # ----------------------------------- 具名用例 4（只标记替换，不实现继承）
    def test_resolve_inputs_marks_replacement_without_applying_it(self):
        rework = self.seed_rework_package()
        rework_rev = rework["m6_package_revision_id"]
        res = resolve_m7_inputs(self.service, [self.ed01_m6_rev(), rework_rev])

        self.assertEqual(len(res["packages"]), 2, "替换关系不得让任何一包被丢弃或合并")
        self.assertEqual(len(res["replaces"]), 1, "同一 (source_id, edition_part_ids) 须标记一次替换")
        relation = res["replaces"][0]
        self.assertEqual(relation["source_id"], self.ed01["source_id"])
        self.assertEqual(relation["edition_part_ids"], [self.ed01["edition_part_artifact_id"]])
        self.assertEqual(
            {relation["replaced_revision_id"], relation["replacement_revision_id"]},
            {self.ed01_m6_rev(), rework_rev},
        )
        # 新旧方向按 Ledger 的 created_at 判定（不按入参顺序）
        older = min(
            [self.ed01_m6_rev(), rework_rev],
            key=lambda rev: self.service.get_revision(rev)["created_at"],
        )
        self.assertEqual(relation["replaced_revision_id"], older)
        # 本波不实现继承：旧键仍是「规范化排序第一包」，未被替换包顶替
        self.assertEqual(
            res["reviewed_package_revision_id"],
            res["packages"][0]["reviewed_package_revision_id"],
        )

    # ---------------------------------- 具名用例 5（创世返回结构向后兼容护栏）
    def test_genesis_path_return_shape_unchanged(self):
        res = resolve_m7_inputs(self.service, [self.ed01_m6_rev()])

        lc = self.ed01["ledger_constants"]
        view_dir = self.ed01["views_dir"]
        for key in LEGACY_KEYS:
            self.assertIn(key, res, "创世路径返回键缺失: %s" % key)
        self.assertEqual(res["technique_id"], self.technique_id)
        self.assertEqual(res["m6_stage_package_id"], lc["m6_stage_package_id"])
        self.assertEqual(res["reviewed_package_revision_id"], lc["m6_package_revision_id"])
        self.assertEqual(res["reviewed_edition_package_revision_id"], lc["reviewed_edition_package_revision_id"])
        self.assertEqual(res["reviewed_edition_revision_id"], lc["reviewed_edition_revision_id"])
        self.assertEqual(res["candidate_package_revision_id"], lc["candidate_package_revision_id"])
        self.assertEqual(res["candidate_set_revision_id"], lc["candidate_set_revision_id"])
        self.assertEqual(res["edition_part_artifact_id"], self.ed01["edition_part_artifact_id"])
        self.assertEqual(res["reviewed_package"], load_view(view_dir, "reviewed_edition_package.json"))
        self.assertEqual(res["reviewed_edition"], load_view(view_dir, "reviewed_edition.json"))
        self.assertEqual(res["candidate_set"], load_view(view_dir, "candidate_set.json"))

        # 新增键只是附加信息（单包时恰一条、无替换关系）
        self.assertEqual(len(res["packages"]), 1)
        self.assertEqual(res["replaces"], [])
        for key in LEGACY_KEYS:
            self.assertEqual(res["packages"][0][key], res[key], "单包时 packages[0] 须与旧键逐字一致")

    # --------------------------------------- 具名用例 6（基底读取与校验）
    def test_resolve_base_snapshot_reads_and_validates(self):
        from pipeline.assembly.inputs import resolve_base_snapshot

        payload = {"technique_id": self.technique_id, "patterns": [], "round": 1}
        _, rev_id, _ = self.make_snapshot_revision(payload)

        base = resolve_base_snapshot(self.service, rev_id)
        self.assertEqual(base["revision_id"], rev_id)
        self.assertEqual(base["artifact_type"], "canonical_snapshot")
        self.assertEqual(base["status"], "sealed")
        self.assertEqual(base["doc"], payload, "必须读出基底 Snapshot 内容（供后续波次使用）")

        # 不存在 → REF_001
        with self.assertRaises(AssemblyRefused) as ctx:
            resolve_base_snapshot(self.service, "rev_000000000000000000000000000000ff")
        self.assertEqual(ctx.exception.code, "REF_001")

        # 类型不对 → SCH_002
        with self.assertRaises(AssemblyRefused) as ctx2:
            resolve_base_snapshot(self.service, self.ed01_m6_rev())
        self.assertEqual(ctx2.exception.code, "SCH_002")
        self.assertIn("canonical_snapshot", str(ctx2.exception))

        # superseded → SCH_002
        _, old_rev, _ = self.make_superseded_base()
        with self.assertRaises(AssemblyRefused) as ctx3:
            resolve_base_snapshot(self.service, old_rev)
        self.assertEqual(ctx3.exception.code, "SCH_002")
        self.assertIn("superseded", str(ctx3.exception))

    # ------------------------------------- 具名用例 7（接受 sealed 基底）
    def test_run_m7_accepts_sealed_base_snapshot(self):
        """A 波判据：sealed 基底不得再被前置拒绝。

        事实再次变了（D 波 ACT 24 接通合并）：无待决提案的增量轮直接完成合并并写新 Snapshot。
        断言随之从「只出提案」改为「接受基底并完成合并」；基底进配置修订与冻结输入不变，
        名实一致护栏见 ``test_incremental_orchestration``。
        """
        payload = {
            "technique_id": self.technique_id,
            "id_range": {"pat_%s" % self.technique_id: list(self.id_range["pattern"])},
            "id_allocation": {"pat_%s" % self.technique_id: 0},
            "allocated_pattern_ids": [],
            "retired_entity_ids": [],
            "editions": [],
            "concepts": [],
            "patterns": [],
            "assertions": [],
            "school_views": [],
            "conflict_groups": [],
            "relations": [],
        }
        base_art_id, base_rev_id, _ = self.make_snapshot_revision(payload)
        res = run_m7(
            self.service,
            self.ed01["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.ed01_m6_rev()],
            base_snapshot_revision_id=base_rev_id,
            id_range=self.id_range,
        )
        self.assertEqual(res["status"], "succeeded", "sealed 基底必须被接受并完成合并")
        self.assertIsNotNone(res["snapshot_revision_id"], "无待决时必须写出新 Snapshot")
        self.assertEqual(res["base_snapshot_revision_id"], base_rev_id)

        # 基底进配置修订与冻结输入
        step = self.service.get_step_run(res["step_run_id"])
        req = json.loads(step["request_json"])
        self.assertIn(base_rev_id, req["input_artifact_ids"])
        cfg_doc = json.loads(
            self.service.objects.get(self.service.get_revision(req["configuration_artifact_id"])["sha256"]).decode("utf-8")
        )
        self.assertEqual(cfg_doc["base_snapshot_revision_id"], base_rev_id)

        # 新 Snapshot 与基底同 Artifact，prev 指向基底，且 meta 同步（§9.3）
        scope_row = self.service.store.conn.execute(
            "SELECT edition_part_id FROM processing_runs WHERE processing_run_id=?",
            (step["processing_run_id"],),
        ).fetchone()
        chain = self.service.list_checkpoints(scope_row[0], "m7")
        self.assertGreaterEqual(len(chain), 1)
        new_rev = self.service.get_revision(res["snapshot_revision_id"])
        self.assertEqual(new_rev["artifact_id"], base_art_id)
        self.assertEqual(new_rev["prev_revision_id"], base_rev_id)
        new_knowledge = json.loads(self.service.objects.get(new_rev["sha256"]).decode("utf-8"))
        self.assertEqual(new_knowledge["meta"]["base_snapshot_revision_id"], base_rev_id)

        rows = self.service.store.conn.execute(
            "SELECT count(*) FROM artifact_revisions WHERE artifact_id=? AND status='sealed'",
            (base_art_id,),
        ).fetchone()
        self.assertEqual(rows[0], 2, "基底 + 增量轮各一条 sealed 修订")

    # ------------------------- 具名用例 8（superseded 基底在 begin 之前拒收）
    def test_run_m7_refuses_superseded_base_before_begin(self):
        _, old_rev, new_rev = self.make_superseded_base()
        before = self.ledger_row_counts()

        with self.assertRaises(AssemblyRefused) as ctx:
            run_m7(
                self.service,
                self.ed01["edition_part_artifact_id"],
                technique_id=self.technique_id,
                reviewed_package_revision_ids=[self.ed01_m6_rev()],
                base_snapshot_revision_id=old_rev,
                id_range=self.id_range,
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        # D-15 前半要求 superseded 基底有**独立、可辨认**的拒收；
        # 若只靠「未 sealed」兜住，这条判据就分不出「已退役」与「还没封存」。
        self.assertIn(
            "已 superseded",
            str(ctx.exception),
            "superseded 基底须给出独立拒收理由，不得与「未 sealed」混为一谈: %s" % ctx.exception,
        )
        self.assertEqual(self.ledger_row_counts(), before, "begin 之前拒收不得有任何写入")
        self.assertEqual(self.service.get_revision(new_rev)["status"], "sealed")

    # ------------------------- 具名用例 9（D-02 A：两个独立 ReleaseRun 各自成链）
    def test_release_run_scope_key_allows_two_independent_runs(self):
        first = run_m7(
            self.service,
            self.ed01["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.ed01_m6_rev()],
            id_range=self.id_range,
        )
        self.assertEqual(first["status"], "succeeded")
        genesis_chain = self.service.list_checkpoints(self.ed01["edition_part_artifact_id"], "m7")

        second = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.ed99_m6_rev()],
            base_snapshot_revision_id=first["snapshot_revision_id"],
            id_range=self.id_range,
            # 第二版次带一条同名歧义提案（R03b）：决定集是夹具数据
            decisions=decisions_for_round(2),
        )
        self.assertEqual(
            second["status"], "succeeded", "第二个 ReleaseRun 不得撞上「已封存拒绝续写」"
        )

        step2 = self.service.get_step_run(second["step_run_id"])
        prun2 = self.service.store.conn.execute(
            "SELECT kind, edition_part_id, technique_id FROM processing_runs WHERE processing_run_id=?",
            (step2["processing_run_id"],),
        ).fetchone()
        scope_key = prun2[1]
        self.assertEqual(prun2[0], "release_run")
        self.assertEqual(prun2[2], self.technique_id)
        ids.validate("artifact_id", scope_key)
        self.assertNotIn(
            scope_key,
            (self.ed01["edition_part_artifact_id"], self.ed99["edition_part_artifact_id"]),
            "第二个 ReleaseRun 的 scope 键须是本 Run 自己的配置 Artifact 身份（D-02 A）",
        )
        # 配置 Artifact 身份 == scope 键（act/21 contract 三.3）
        req2 = json.loads(step2["request_json"])
        cfg_rev2 = self.service.get_revision(req2["configuration_artifact_id"])
        self.assertEqual(cfg_rev2["artifact_id"], scope_key)

        chain2 = self.service.list_checkpoints(scope_key, "m7")
        self.assertGreaterEqual(len(chain2), 1, "第二个 Run 须独占自己的 Checkpoint 链")
        self.assertEqual(
            self.service.list_checkpoints(self.ed01["edition_part_artifact_id"], "m7"),
            genesis_chain,
            "第一个 Run 的链不得被覆写",
        )
        self.assertNotEqual(second["step_run_id"], first["step_run_id"])

        # §9.3：第二个 Run 的 Snapshot 必须两侧一致（prev 与 meta 同时非空）
        snapshots = [
            row[0]
            for row in self.service.store.conn.execute(
                "SELECT r.artifact_revision_id FROM artifact_revisions r "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE a.artifact_type='canonical_snapshot' AND r.status='sealed'"
            ).fetchall()
        ]
        self.assertEqual(
            sorted(snapshots), sorted([first["snapshot_revision_id"], second["snapshot_revision_id"]])
        )

    def test_resolve_m4_fallback_query_is_broken_today(self):
        """证明现状：当 m4 StepRun 的 result_json 不含 candidate_package 修订号时，
        走入回退查询，因 transformations 表缺少 output_artifact_revision_id 列而抛出
        sqlite3.OperationalError: no such column: t.output_artifact_revision_id。"""
        import sqlite3

        # 破坏 m4 step_run 的 result_json，使主查询 LIKE 匹配落空
        self.service.store.conn.execute("UPDATE step_runs SET result_json = '{}' WHERE stage='m4'")
        self.service.store.conn.commit()

        with self.assertRaises(sqlite3.OperationalError) as ctx:
            resolve_m7_inputs(self.service, [self.ed01_m6_rev()])
        self.assertIn("no such column", str(ctx.exception).lower())
        self.assertIn("output_artifact_revision_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

