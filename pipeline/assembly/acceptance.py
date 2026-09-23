"""M7 汇编验收（spec §19.0 判据）：十七项判定，每条都由**实际运行结果**决定。

本模块不 import ``genesis``；判定只读 Ledger 与夹具金标，不信任 ``run_m7`` 返回的 Gate 报告。

- ``upstream_m6_real``：真实 M6 **注入路径**（输入是合成桩，见 ``NOTE`` 行）。
- ``incremental_multi_edition`` / ``edition_collation`` / ``identity_delta`` / ``rework_replacement``：
  在临时 Ledger 上**实跑** mini_release01 的 r1 → ed99 → ed01r2 三轮（决定集来自夹具数据），
  再按 CHARTER §19.3 比对：纯函数层逐字节；Ledger 层「除 ``meta`` 外相同 + ``meta`` 指向本轮实际基底」。
- ``run_all_20_5``：验证 ``run_all.sh`` 的 20.5 段确实按 ``m7-assembler.sh`` 的退出码映射。
- ``upstream_m6_real_book``：在 ``var/ledgers/qianyuan_w8`` 的**副本**上跑真书第二轮，正本只读。
"""

import argparse
import ast
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

try:
    import jsonschema
except ImportError:
    jsonschema = None

from pipeline.assembly import fixture_seed
from pipeline.assembly.canonical import canonical_json
from pipeline.assembly.gate import evaluate_genesis
from pipeline.assembly.model import validate_snapshot_knowledge
from pipeline.assembly.step import run_m7
from pipeline.ledger.service import LedgerService
from pipeline.review.testing.upstream_stub import seed_upstream as m6_seed_upstream
import pipeline.review.step as _review_step

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"
DATA_DIR = Path(__file__).resolve().parent / "tests" / "data"
GENESIS_PACKAGE_PATH = DATA_DIR / "genesis_package.json"
GOLDEN_KNOWLEDGE_PATH = DATA_DIR / "genesis_expected_knowledge.json"

RELEASE_FIXTURE = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
REAL_LEDGER_DIR = REPO_ROOT / "var" / "ledgers" / "qianyuan_w8"
RUN_ALL_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "run_all.sh"
M7_SHELL_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "m7-assembler.sh"

#: 对勘四类（``apply.COLLATION_KINDS`` 的独立副本：判据不 import 被验模块的行为常量）
COLLATION_KINDS = ("alignment", "variant_reading", "addition", "omission")

#: ``upstream_m6_real`` 的输入是合成桩（CHARTER §2 P2 更正），判据名不改但必须如实写明
UPSTREAM_M6_REAL_NOTE = (
    "输入为合成桩（pipeline/review/testing/upstream_stub 的 mini_ed01），非真书；"
    "真书判定见 upstream_m6_real_book"
)


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _release_manifest() -> dict:
    return yaml.safe_load((RELEASE_FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def _release_decisions(round_no: int) -> list:
    """读夹具登记的第 ``round_no`` 轮决定集（`build_fixture.py` 从真实提案推出）。"""
    rows = [row for row in _release_manifest().get("decisions") or [] if row.get("round") == round_no]
    if not rows:
        raise RuntimeError("夹具未登记第 %d 轮的决定集" % round_no)
    return _load_json(RELEASE_FIXTURE / rows[0]["file"])["decisions"]


def _release_view(edition: dict) -> dict:
    views = RELEASE_FIXTURE / edition["views_dir"]
    return {
        "source_id": edition["source_id"],
        "candidate_set": _load_json(views / "candidate_set.json"),
        "reviewed_edition": _load_json(views / "reviewed_edition.json"),
    }


def _declared_present_keys(candidate_set: dict) -> set:
    """视图**声明**为 present 的可比单元键（独立重算，不看引擎中间量）。"""
    keys = set()
    for unit in candidate_set.get("collation_units") or []:
        if unit.get("collation_key") and unit.get("present", True):
            keys.add(unit["collation_key"])
    for assertion in candidate_set.get("assertions") or []:
        if assertion.get("collation_key"):
            keys.add(assertion["collation_key"])
    return keys


def _prepare_release_rounds(tmp_root: Path) -> dict:
    """在临时 Ledger 上把 mini_release01 的三轮**实跑**一遗。

    决定集全部来自夹具数据，**不手工构造任何提案**。同时算纯函数层 r2/r3
    （基底号用 `expected/snapshot_revisions.yaml` 的固定常量），以便按 §19.3 逐字节比对。
    返回的 dict 里带 ``service``，由调用方负责关闭。
    """
    from pipeline.assembly import fixture_seed
    from pipeline.assembly.orchestrate import assemble as assemble_incremental

    manifest = _release_manifest()
    technique_id = manifest["technique_id"]
    plan = yaml.safe_load(
        (RELEASE_FIXTURE / manifest["expected"]["snapshot_revisions"]).read_text(encoding="utf-8")
    )
    ed01, ed99, rework = manifest["editions"][0], manifest["editions"][1], manifest["rework"]

    service = LedgerService(tmp_root / "release_ledger")
    try:
        seeded = fixture_seed.seed_release_package(service, RELEASE_FIXTURE)["editions"]
        # 返工版次（同 source_id、同 edition_part_ids）不在 editions[] 里，单独播种
        lc = rework["ledger_constants"]
        rework_views = RELEASE_FIXTURE / rework["views_dir"]
        service.create_processing_run(
            "release_run",
            rework["edition_part_artifact_id"],
            technique_id,
            processing_run_id=lc["processing_run_id"],
        )
        rework_seeded = fixture_seed._seed_one_edition(
            service,
            technique_id,
            rework["edition_part_artifact_id"],
            lc["processing_run_id"],
            lc,
            _load_json(rework_views / "candidate_set.json"),
            dict(
                _load_json(rework_views / "reviewed_edition.json"),
                candidate_set_revision_id=lc["candidate_set_revision_id"],
                candidate_package_revision_id=lc["candidate_package_revision_id"],
            ),
            dict(
                _load_json(rework_views / "reviewed_edition_package.json"),
                reviewed_edition_revision_id=lc["reviewed_edition_revision_id"],
            ),
        )

        def _run(edition_part_id, m6_rev, base_rev=None, decisions=None):
            return run_m7(
                service,
                edition_part_id,
                technique_id=technique_id,
                reviewed_package_revision_ids=[m6_rev],
                base_snapshot_revision_id=base_rev,
                id_range=manifest["id_range"],
                decisions=decisions,
            )

        m6_revisions = {
            "ed01": seeded[ed01["edition_key"]]["m6_package_revision_id"],
            "ed99": seeded[ed99["edition_key"]]["m6_package_revision_id"],
            "ed01r2": rework_seeded["m6_package_revision_id"],
        }
        runs = {}
        runs["r1"] = _run(ed01["edition_part_artifact_id"], m6_revisions["ed01"])
        runs["r2"] = _run(
            ed99["edition_part_artifact_id"],
            m6_revisions["ed99"],
            runs["r1"].get("snapshot_revision_id"),
            _release_decisions(2),
        )
        runs["r3"] = _run(
            rework["edition_part_artifact_id"],
            m6_revisions["ed01r2"],
            runs["r2"].get("snapshot_revision_id"),
            _release_decisions(3),
        )

        def _revision_bytes(revision_id):
            if not revision_id:
                return None
            revision = service.get_revision(revision_id)
            return service.objects.get(revision["sha256"])

        def _revision_doc(revision_id):
            raw = _revision_bytes(revision_id)
            return json.loads(raw.decode("utf-8")) if raw is not None else None

        snapshots = {
            key: _revision_doc(run.get("snapshot_revision_id")) for key, run in runs.items()
        }
        snapshot_bytes = {
            key: _revision_bytes(run.get("snapshot_revision_id")) for key, run in runs.items()
        }
        validations = {
            key: _revision_doc(run.get("validation_report_revision_id")) for key, run in runs.items()
        }
        packages = {
            key: _revision_doc(run.get("assembly_package_revision_id")) for key, run in runs.items()
        }

        pure = {
            "r2": assemble_incremental(
                _load_json(RELEASE_FIXTURE / manifest["expected"]["round1"]),
                [_release_view(ed99)],
                _release_decisions(2),
                incremental=True,
                base_snapshot_revision_id=plan["revisions"][0]["snapshot_revision_id"],
            ),
            "r3": assemble_incremental(
                _load_json(RELEASE_FIXTURE / manifest["expected"]["round2"]),
                [_release_view(rework)],
                _release_decisions(3),
                incremental=True,
                base_snapshot_revision_id=plan["revisions"][1]["snapshot_revision_id"],
            ),
        }
        goldens = {
            "r2": (RELEASE_FIXTURE / manifest["expected"]["round2"]).read_bytes(),
            "r3": (RELEASE_FIXTURE / manifest["expected"]["round3"]).read_bytes(),
        }
    except Exception:
        service.close()
        raise

    return {
        "service": service,
        "manifest": manifest,
        "plan": plan,
        "runs": runs,
        "m6_revisions": m6_revisions,
        "snapshots": snapshots,
        "snapshot_bytes": snapshot_bytes,
        "validations": validations,
        "packages": packages,
        "pure": pure,
        "goldens": goldens,
    }


def _require_release(world) -> dict:
    if world.get("release") is None:
        raise RuntimeError("夹具实跑准备失败: %s" % world.get("release_error"))
    return world["release"]


def _golden_doc(manifest: dict, key: str) -> dict:
    return _load_json(RELEASE_FIXTURE / manifest["expected"][key])


def _meta_excluded_mismatch(produced: dict, golden: dict, base_rev, label: str) -> list:
    """§19.3 的 Ledger 层口径：除 `meta` 外逐字节相同 + `meta` 指向本轮实际基底。"""
    failures = []
    if sorted(produced.get("meta") or {}) != sorted(golden.get("meta") or {}):
        failures.append("%s: meta 字段集与金标不一致" % label)
    left = {k: v for k, v in produced.items() if k != "meta"}
    right = {k: v for k, v in golden.items() if k != "meta"}
    if canonical_json(left) != canonical_json(right):
        failures.append("%s: 除 meta 外产出与金标不是逐字节相同" % label)
    got = (produced.get("meta") or {}).get("base_snapshot_revision_id")
    if base_rev is not None and got != base_rev:
        failures.append(
            "%s: meta.base_snapshot_revision_id=%r != 本轮实际基底 %r" % (label, got, base_rev)
        )
    return failures


def _prepare_with_real_m6():
    """在临时 Ledger 上用真实 M6 产出准备验收环境，返回 (tmp_dir, service, world)。"""
    from pipeline.review.testing.upstream_stub import load_data as m6_load_data

    tmp = Path(tempfile.mkdtemp(prefix="m7_real_m6_"))
    ledger_dir = tmp / "ledger"
    service = LedgerService(ledger_dir)
    try:
        fixture_dir = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
        seed = m6_seed_upstream(service, fixture_dir)
        edition_part_id = seed["edition_part_id"]

        # 驱动 M6 review 流程
        first_open = _review_step.open_review(service, edition_part_id)
        step_run_id = first_open["step_run_id"]
        token = first_open["resume_token"]
        decisions = m6_load_data("m6_decisions")["decisions"]
        for d in decisions:
            _review_step.record_decision(
                service, step_run_id, token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
        first_close = _review_step.close_review(service, step_run_id, token)
        if first_close.get("status") != "succeeded":
            raise RuntimeError("real M6 close_review 未成功: %r" % first_close.get("failed_check"))

        # 查找 m6 StagePackage 修订
        m6_pkg_row = service.store.conn.execute(
            "SELECT ar.artifact_revision_id FROM artifact_revisions ar "
            "JOIN stage_packages sp ON ar.artifact_id = sp.artifact_id "
            "WHERE sp.stage='m6'",
        ).fetchone()
        if not m6_pkg_row:
            raise RuntimeError("未找到 m6 StagePackage")
        m6_pkg_rev_id = m6_pkg_row[0]

        m6_before = service.get_revision(m6_pkg_rev_id)

        # 查找 reviewed_edition 修订
        re_row = service.store.conn.execute(
            "SELECT ar.artifact_revision_id FROM artifact_revisions ar "
            "JOIN artifacts a ON a.artifact_id = ar.artifact_id "
            "WHERE a.artifact_type='reviewed_edition'",
        ).fetchone()
        re_rev_id = re_row[0] if re_row else None

        # 查找 reviewed_edition_package 修订
        rep_row = service.store.conn.execute(
            "SELECT ar.artifact_revision_id FROM artifact_revisions ar "
            "JOIN artifacts a ON a.artifact_id = ar.artifact_id "
            "WHERE a.artifact_type='reviewed_edition_package'",
        ).fetchone()
        rep_rev_id = rep_row[0] if rep_row else None

        # 运行 M7
        technique_id = "qizheng"
        res = run_m7(
            service,
            edition_part_id,
            technique_id=technique_id,
            reviewed_package_revision_ids=[m6_pkg_rev_id],
            base_snapshot_revision_id=None,
        )

        m6_after = service.get_revision(m6_pkg_rev_id)

        snap_rev = service.get_revision(res["snapshot_revision_id"])
        snap_bytes = service.objects.get(snap_rev["sha256"])
        snap_doc = json.loads(snap_bytes.decode("utf-8"))

        # 读 reviewed_edition 内容
        re_doc = None
        if re_rev_id:
            re_rev = service.get_revision(re_rev_id)
            re_doc = json.loads(service.objects.get(re_rev["sha256"]).decode("utf-8"))

        world = {
            "service": service,
            "run_result": res,
            "snapshot_doc": snap_doc,
            "snapshot_revision_id": res["snapshot_revision_id"],
            "real_m6_before": m6_before,
            "real_m6_after": m6_after,
            "real_decisions": decisions,
            "reviewed_edition": re_doc,
        }
        return tmp, service, world
    except Exception:
        service.close()
        raise


def _prepare(tmp_root: Path):
    """准备临时 Ledger 并运行一次 run_m7，返回 (tmp_dir, service, world)。"""
    ledger_dir = tmp_root / "ledger"
    service = LedgerService(ledger_dir)
    try:
        fixture_doc = json.loads(GENESIS_PACKAGE_PATH.read_text(encoding="utf-8"))
        seed_res = fixture_seed.seed_genesis_package(service, fixture_doc)

        edition_part_id = fixture_doc["ledger_constants"]["edition_part_artifact_id"]
        technique_id = fixture_doc["ledger_constants"]["technique_id"]
        m6_pkg_rev_id = seed_res["m6_package_revision_id"]
        re_rev_id = seed_res["reviewed_edition_revision_id"]

        # 记录上游运行前快照
        upstream_before = {
            "m6_pkg": service.get_revision(m6_pkg_rev_id),
            "re": service.get_revision(re_rev_id),
        }

        res = run_m7(
            service,
            edition_part_id,
            technique_id=technique_id,
            reviewed_package_revision_ids=[m6_pkg_rev_id],
            base_snapshot_revision_id=None,
        )

        upstream_after = {
            "m6_pkg": service.get_revision(m6_pkg_rev_id),
            "re": service.get_revision(re_rev_id),
        }

        snap_rev = service.get_revision(res["snapshot_revision_id"])
        snap_bytes = service.objects.get(snap_rev["sha256"])
        snap_doc = json.loads(snap_bytes.decode("utf-8"))

        # 在独立干净临时 Ledger 中运行第二次同一输入，验证纯函数/确定性
        tmp2 = Path(tempfile.mkdtemp(prefix="m7_acc_r2_"))
        try:
            service2 = LedgerService(tmp2 / "ledger")
            try:
                seed_res2 = fixture_seed.seed_genesis_package(service2, fixture_doc)
                res2 = run_m7(
                    service2,
                    edition_part_id,
                    technique_id=technique_id,
                    reviewed_package_revision_ids=[seed_res2["m6_package_revision_id"]],
                    base_snapshot_revision_id=None,
                )
                snap_rev2 = service2.get_revision(res2["snapshot_revision_id"])
                snap_bytes_r2 = service2.objects.get(snap_rev2["sha256"])
            finally:
                service2.close()
        finally:
            shutil.rmtree(tmp2, True)

        world = {
            "service": service,
            "run_result": res,
            "step_run_id": res["step_run_id"],
            "edition_part_id": edition_part_id,
            "technique_id": technique_id,
            "m6_pkg_rev_id": m6_pkg_rev_id,
            "candidate_set": fixture_doc["candidate_set"],
            "reviewed_edition": fixture_doc["reviewed_edition"],
            "fixture_doc": fixture_doc,
            "upstream_before": upstream_before,
            "upstream_after": upstream_after,
            "snapshot_bytes": snap_bytes,
            "snapshot_bytes_r2": snap_bytes_r2,
            "snapshot_doc": snap_doc,
            "snapshot_revision_id": res["snapshot_revision_id"],
            "assembly_package_revision_id": res["assembly_package_revision_id"],
        }
        return tmp_root, service, world
    except Exception:
        service.close()
        raise


# ------------------------------------------------------------ 10 项 PASS 判定
def check_genesis_snapshot(world) -> list[str]:
    service: LedgerService = world["service"]
    res = world["run_result"]
    step = service.store.get_step_run(res["step_run_id"])
    errors = []
    if step["status"] != "succeeded":
        errors.append("step_run 状态非 succeeded: %s" % step["status"])

    golden_bytes = GOLDEN_KNOWLEDGE_PATH.read_bytes()
    if world["snapshot_bytes"] != golden_bytes:
        errors.append("Snapshot 修订规范字节与金标 genesis_expected_knowledge.json 不一致")

    if world["snapshot_bytes"] != world["snapshot_bytes_r2"]:
        errors.append("同一输入再次运行生成的 Snapshot 字节不一致（非确定性）")

    return errors


def check_configuration_and_scope(world) -> list[str]:
    service: LedgerService = world["service"]
    step = service.store.get_step_run(world["step_run_id"])
    errors = []

    row = service.store.conn.execute(
        "SELECT * FROM processing_runs WHERE processing_run_id=?",
        (step["processing_run_id"],),
    ).fetchone()
    if not row:
        errors.append("ProcessingRun 不存在: %s" % step["processing_run_id"])
        return errors
    prun = dict(row)
    if prun.get("kind") != "release_run":
        errors.append("ProcessingRun kind 须为 release_run，实际: %s" % prun.get("kind"))
    if prun.get("edition_part_id") != world["edition_part_id"]:
        errors.append(
            "ProcessingRun edition_part_id 须为 %s，实际: %s"
            % (world["edition_part_id"], prun.get("edition_part_id"))
        )

    req = json.loads(step["request_json"])
    cfg_rev_id = req["configuration_artifact_id"]
    cfg_rev = service.get_revision(cfg_rev_id)
    cfg_doc = json.loads(service.objects.get(cfg_rev["sha256"]).decode("utf-8"))
    if cfg_doc.get("stage") != "m7":
        errors.append("configuration.stage 须为 m7，实际: %s" % cfg_doc.get("stage"))

    return errors


def check_package_lineage(world) -> list[str]:
    service: LedgerService = world["service"]
    step = service.store.get_step_run(world["step_run_id"])
    errors = []

    # 查 stage_package revision
    row = service.store.conn.execute(
        "SELECT ar.artifact_revision_id FROM artifact_revisions ar "
        "JOIN stage_packages sp ON ar.artifact_id = sp.artifact_id "
        "WHERE ar.step_run_id=? AND sp.stage='m7'",
        (step["step_run_id"],),
    ).fetchone()
    if not row:
        errors.append("未找到 m7 stage_package 修订")
        return errors

    stage_pkg_rev_id = row[0]
    stage_pkg_rev = service.get_revision(stage_pkg_rev_id)
    stage_pkg_doc = json.loads(service.objects.get(stage_pkg_rev["sha256"]).decode("utf-8"))

    # 过 schema（使用 service._validate 自动绑定引用 Registry）
    try:
        service._validate("stage_package.schema.json", stage_pkg_doc, "StagePackage")
    except Exception as e:
        errors.append("stage_package 未通过 stage_package.schema.json: %s" % e)

    raw_upstream = stage_pkg_doc.get("lineage", {}).get("upstream_artifacts", [])
    lineage_inputs = set()
    for item in raw_upstream:
        if isinstance(item, dict):
            lineage_inputs.add(item.get("artifact_revision_id"))
        else:
            lineage_inputs.add(str(item))

    req = json.loads(step["request_json"])
    frozen_inputs = set(req.get("input_artifact_ids", []))
    if lineage_inputs != frozen_inputs:
        errors.append("stage_package lineage 输入集合 (%s) != frozen_inputs (%s)" % (lineage_inputs, frozen_inputs))

    outputs = stage_pkg_doc.get("manifest", {}).get("output_artifacts", [])
    output_rev_ids = [o.get("artifact_revision_id") if isinstance(o, dict) else o for o in outputs]
    if len(output_rev_ids) != 1 or output_rev_ids[0] != world["assembly_package_revision_id"]:
        errors.append("stage_package output_artifacts 须恰含 1 个 assembly_package 修订，实际: %s" % output_rev_ids)

    return errors


def check_identity_and_allocation(world) -> list[str]:
    k = world["snapshot_doc"]
    errors = []

    id_range = k.get("id_range", {})
    pat_range = id_range.get("pat_" + world["technique_id"])
    if not pat_range or len(pat_range) != 2:
        errors.append("id_range 格式非法: %s" % id_range)
        return errors

    start, end = pat_range
    allocated = k.get("allocated_pattern_ids", [])
    seen = set()
    for pid in allocated:
        if pid in seen:
            errors.append("新发 pat_ 号重复: %s" % pid)
        seen.add(pid)
        m = re.match(r"^pat_[a-z][a-z0-9]*_([0-9]{6})$", pid)
        if not m:
            errors.append("新发 pat_ 号非法: %s" % pid)
        else:
            seq = int(m.group(1))
            if not (start <= seq <= end):
                errors.append("新发 pat_ 号超出 id_range 区间: %d not in [%d, %d]" % (seq, start, end))

    # 不与保留 M4 号重复
    m4_pids = {p["pattern_id"] for p in world["candidate_set"].get("patterns", [])}
    overlap = seen & m4_pids
    if overlap:
        errors.append("新发 pat_ 号与保留 M4 号重复: %s" % overlap)

    # id_allocation == max(活对象号 ∪ 补发号)
    all_pids = [p["pattern_id"] for p in k.get("patterns", [])] + allocated
    max_seq = 0
    for pid in all_pids:
        m = re.match(r"^pat_[a-z][a-z0-9]*_([0-9]{6})$", pid)
        if m:
            max_seq = max(max_seq, int(m.group(1)))

    alloc_dict = k.get("id_allocation", {})
    if alloc_dict.get("pat_" + world["technique_id"]) != max_seq:
        errors.append("id_allocation (%s) != max(活对象号 ∪ 补发号) (%d)" % (alloc_dict, max_seq))

    # retired_entity_ids 为空
    if k.get("retired_entity_ids") != []:
        errors.append("创世 Snapshot retired_entity_ids 须为空，实际: %s" % k.get("retired_entity_ids"))

    return errors


def check_provenance_and_fidelity(world) -> list[str]:
    cset = world["candidate_set"]
    ed = world["reviewed_edition"]
    k = world["snapshot_doc"]

    gate_res = evaluate_genesis(candidate_set=cset, reviewed_edition=ed, knowledge=k)
    errors = []
    if not gate_res.get("passed"):
        errors.append("gate.evaluate_genesis 未通过")

    for name, c in gate_res.get("checks", {}).items():
        if not c.get("passed"):
            errors.append("Gate 检查 %s 未通过: %s" % (name, c.get("message")))

    return errors


def check_no_silent_fold_and_display(world) -> list[str]:
    k = world["snapshot_doc"]
    cset = world["candidate_set"]
    errors = []

    # 冲突组成员与 first_layer_display 与视图一致
    cg_views: dict[str, list[str]] = {}
    for sv in k.get("school_views", []):
        cg_id = sv.get("conflict_group_id")
        if cg_id:
            cg_views.setdefault(cg_id, []).append(sv["school_view_id"])

    for cg in k.get("conflict_groups", []):
        cg_id = cg["conflict_group_id"]
        members = cg.get("member_school_view_ids", [])
        expected_members = cg_views.get(cg_id, [])
        if sorted(members) != sorted(expected_members):
            errors.append("冲突组 %s 成员 (%s) 与 school_views (%s) 不一致" % (cg_id, members, expected_members))
        if not cg.get("first_layer_display"):
            errors.append("创世冲突组 %s first_layer_display 须为 true" % cg_id)

    return errors


def check_upstream_immutable(world) -> list[str]:
    errors = []
    m6_0 = world["upstream_before"]["m6_pkg"]
    m6_1 = world["upstream_after"]["m6_pkg"]
    if m6_0["status"] != m6_1["status"] or m6_0["sha256"] != m6_1["sha256"]:
        errors.append("m6 包在运行后发生变异")

    re_0 = world["upstream_before"]["re"]
    re_1 = world["upstream_after"]["re"]
    if re_0["status"] != re_1["status"] or re_0["sha256"] != re_1["sha256"]:
        errors.append("reviewed_edition 在运行后发生变异")

    return errors


def check_checkpoints(world) -> list[str]:
    service: LedgerService = world["service"]
    cps = service.list_checkpoints(world["edition_part_id"], "m7")
    errors = []
    if len(cps) < 2:
        errors.append("m7 Checkpoint 数量不足 2: %d" % len(cps))
        return errors

    tasks = []
    for cp in cps:
        for t in cp.get("content", {}).get("completed_tasks", []):
            tasks.append(t["task_id"])

    if "propose_r1" not in tasks:
        errors.append("Checkpoint 缺少 propose_r1")
    if "seal_snapshot" not in tasks:
        errors.append("Checkpoint 缺少 seal_snapshot")

    for i in range(1, len(cps)):
        if cps[i].get("prev_checkpoint_revision_id") != cps[i - 1].get("artifact_revision_id"):
            errors.append("Checkpoint 前驱链断裂: %s -> %s" % (cps[i].get("prev_checkpoint_revision_id"), cps[i - 1].get("artifact_revision_id")))

    return errors


def check_closed_set_types(world) -> list[str]:
    service: LedgerService = world["service"]
    res = world["run_result"]
    errors = []

    rev_ids = [
        res["snapshot_revision_id"],
        res["assembly_package_revision_id"],
        res["validation_report_revision_id"],
    ]
    types = set()
    for rid in rev_ids:
        rev = service.get_revision(rid)
        row = service.store.conn.execute(
            "SELECT artifact_type FROM artifacts WHERE artifact_id=?",
            (rev["artifact_id"],),
        ).fetchone()
        if row:
            types.add(row[0])

    expected = {"canonical_snapshot", "assembly_package", "validation_report"}
    if types != expected:
        errors.append("产出修订的 artifact_type 集合 (%s) != %s" % (types, expected))

    return errors


def check_no_model_calls(world) -> list[str]:
    assembly_dir = world.get("_scan_dir", REPO_ROOT / "pipeline" / "assembly")
    extra_files = world.get("_extra_files", [])
    errors = []
    forbidden = {"requests", "openai", "anthropic", "httpx"}

    py_files = list(assembly_dir.rglob("*.py")) + [Path(f) for f in extra_files]
    for py_file in py_files:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append("%s 解析失败: %s" % (py_file.name, exc))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in forbidden:
                        errors.append("%s 包含模型/网络库 import %s" % (py_file.name, a.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden:
                    errors.append("%s 包含模型/网络库 import %s" % (py_file.name, node.module))

    return errors


def check_upstream_m6_real(world) -> list[str]:
    """独立核对真实 M6 产出经 M7 后的 Snapshot（第 83 条）。"""
    errors = []
    tmp, service, real_world = _prepare_with_real_m6()
    try:
        snap_doc = real_world["snapshot_doc"]

        # 1. Snapshot 修订的 knowledge 字段包含 patterns/assertions 键
        if "patterns" not in snap_doc:
            errors.append("Snapshot knowledge 缺少 patterns 键")
        if "assertions" not in snap_doc:
            errors.append("Snapshot knowledge 缺少 assertions 键")

        # 2. Snapshot 修订的 knowledge 经 validate_snapshot_knowledge 校验通过
        try:
            validate_snapshot_knowledge(snap_doc)
        except Exception as exc:
            errors.append("validate_snapshot_knowledge 失败: %s" % exc)

        # 3. m6 StagePackage 在运行前后 status/sha256 不变
        before = real_world["real_m6_before"]
        after = real_world["real_m6_after"]
        if before["status"] != after["status"] or before["sha256"] != after["sha256"]:
            errors.append("真实 M6 StagePackage 在 M7 运行后发生变异")
    finally:
        service.close()
        shutil.rmtree(tmp, True)
    return errors


# --------------------------------------------- 增量/对勘/返工四条的实跑判定（ACT 27）
def check_incremental_multi_edition(world) -> tuple:
    """§15:655：新版次加入同一部书，来一个汇一个——r1 → ed99 增量实跑必须全过。"""
    release = _require_release(world)
    manifest = release["manifest"]
    failures = []

    status = release["runs"]["r2"].get("status")
    if status != "succeeded":
        failures.append("ed99 增量轮 status=%r（期望 succeeded）" % status)

    validation = release["validations"]["r2"]
    if validation is None:
        failures.append("ed99 增量轮未产出 validation_report")
    else:
        gate = validation.get("incremental_gate") or {}
        bad = sorted(
            name for name, check in (gate.get("checks") or {}).items() if not check.get("passed")
        )
        if not gate.get("passed") or bad:
            failures.append("增量 Gate 未全过: %r" % (bad or gate))

    if release["pure"]["r2"]["result"]["knowledge_bytes"] != release["goldens"]["r2"]:
        failures.append("纯函数层增量产出与 snapshot_r2.json 不是逐字节相同")

    produced = release["snapshots"]["r2"]
    if produced is None:
        failures.append("ed99 增量轮未写出 Snapshot")
    else:
        failures.extend(
            _meta_excluded_mismatch(
                produced,
                _golden_doc(manifest, "round2"),
                release["runs"]["r1"].get("snapshot_revision_id"),
                "r2",
            )
        )

    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    note = (
        "本判据只覆盖「同一 EditionPart 逐版次汇入」；单个 Run 一次汇多个 M6 包不是 §15:655 的要求，"
        "不计入本判据（现口径：%s）" % _multi_package_observed(release)
    )
    return ("PASS", note)


def _multi_package_observed(release: dict) -> str:
    """如实描述现口径（**不据此判定**）：一次 Run 汇两个 M6 包会怎样。

    `resolve_m7_inputs` 已能解析多包；拒收发生在 `run_m7` 的 begin 之前（无写入）。
    """
    manifest = release["manifest"]
    try:
        run_m7(
            release["service"],
            manifest["editions"][0]["edition_part_artifact_id"],
            technique_id=manifest["technique_id"],
            reviewed_package_revision_ids=[
                release["m6_revisions"]["ed01"],
                release["m6_revisions"]["ed99"],
            ],
            id_range=manifest["id_range"],
        )
        return "本机实测：一次 Run 确实汇进了多个包"
    except Exception as exc:  # noqa: BLE001 - 只记录行为，不据此判定
        return "本机实测：仍在前置拒收（%s，code=%s）：%s" % (
            type(exc).__name__,
            getattr(exc, "code", None),
            str(exc)[:80],
        )


def _collation_signature(document: dict) -> list:
    """对勘关系签名 (kind, from, to, detail.collation_key)，含 R07b 拒绝落成的 distinct_from（CHARTER §29 Q10）。"""
    assertion_ids = {item.get("assertion_id") for item in document.get("assertions") or []}
    rows = []
    for rel in document.get("relations") or []:
        kind = rel.get("relation_kind")
        key = (rel.get("detail") or {}).get("collation_key")
        ends = (rel.get("from_entity_id"), rel.get("to_entity_id"))
        if kind in COLLATION_KINDS or (
            kind == "distinct_from" and key and all(end in assertion_ids for end in ends)
        ):
            rows.append((kind,) + ends + (key,))
    return sorted(rows, key=lambda row: tuple(str(part) for part in row))


def _collation_expected(old_view: dict, new_view: dict) -> tuple:
    """只凭夹具两份视图的**声明**独立推出可比单元与 not_comparable 清单（§25.5、§28 Q7、§29 Q11）。

    旧版 = 基底版次（ed01），新版 = 本轮视图（ed99）。返回 ``(units, rows)``：
    ``units[collation_key] = (kind, 新版断言号, 旧版断言号)``，kind ∈ pair / addition / omission；
    ``rows`` 为已排序的 not_comparable 清单，每项恰 ``{source_id, collation_key, assertion_id, reason}``。
    """

    def declared(view: dict) -> dict:
        return {
            unit["collation_key"]: bool(unit.get("present", True))
            for unit in view["candidate_set"].get("collation_units") or []
            if unit.get("collation_key")
        }

    def approved_by_key(view: dict) -> tuple:
        approved = {
            item.get("entity_id")
            for item in view["reviewed_edition"].get("approved") or []
            if item.get("kind") == "assertion"
        }
        keyed, keyless = {}, []
        for item in view["candidate_set"].get("assertions") or []:
            if item.get("assertion_id") not in approved:
                continue
            if item.get("collation_key"):
                keyed.setdefault(item["collation_key"], []).append(item["assertion_id"])
            else:
                keyless.append(item["assertion_id"])
        return keyed, keyless

    new_source, old_source = new_view["source_id"], old_view["source_id"]
    new_declared, old_declared = declared(new_view), declared(old_view)
    new_ids, keyless = approved_by_key(new_view)
    old_ids, _ = approved_by_key(old_view)

    def row(key, assertion_id, reason):
        return {
            "source_id": new_source,
            "collation_key": key,
            "assertion_id": assertion_id,
            "reason": reason,
        }

    rows = [row(None, assertion_id, "missing_collation_key") for assertion_id in keyless]
    rows += [
        row(None, None, "missing_collation_key")
        for unit in new_view["candidate_set"].get("collation_units") or []
        if not unit.get("collation_key")
    ]
    units = {}
    for key in sorted(set(new_declared) | set(new_ids)):
        new, old = new_ids.get(key) or [], old_ids.get(key) or []
        if key not in new_declared:
            rows.append(row(key, None, "view_undeclared"))
        elif new_source == old_source:
            rows.append(row(key, None, "same_source"))
        elif key not in old_declared:
            rows.append(row(key, None, "base_undeclared"))
        elif len(new) > 1 or len(old) > 1:
            rows.append(row(key, None, "multiple_assertions_per_unit"))
        elif (new_declared[key] and not new) or (old_declared[key] and not old):
            rows.append(row(key, None, "declared_without_assertion"))
        elif new_declared[key] and old_declared[key]:
            units[key] = ("pair", new[0], old[0])
        elif new_declared[key]:
            units[key] = ("addition", new[0], None)
        elif old_declared[key]:
            units[key] = ("omission", None, old[0])
    rows.sort(key=lambda r: (r["source_id"], r["collation_key"] or "", r["assertion_id"] or ""))
    return units, rows


def _judge_edition_collation(
    *, produced: dict, golden: dict, old_view: dict, new_view: dict, reported_rows, reported_count
) -> list:
    """edition_collation 的判定本体（纯函数）：返回失败项列表，空列表即 PASS。"""
    failures = []
    got, want = _collation_signature(produced), _collation_signature(golden)
    if got != want:
        failures.append("对勘关系集与 r2 金标不一致: 实跑 %r / 金标 %r" % (got, want))
    missing = [kind for kind in COLLATION_KINDS if kind not in {row[0] for row in got}]
    if missing:
        failures.append("四类对勘关系须各至少一条，实跑缺 %r" % missing)

    units, rows = _collation_expected(old_view, new_view)
    if not any(r["reason"] in ("base_undeclared", "view_undeclared") for r in rows):
        failures.append("夹具必须有「一侧未声明」的单元，否则「不可比单元上无对勘关系」是空转的")
    assertions = {item.get("assertion_id"): item for item in produced.get("assertions") or []}
    for kind, left, right, key in got:
        unit = units.get(key)
        if unit is None:
            failures.append("对勘关系 %s %s→%s 落在不可比单元 %r 上" % (kind, left, right, key))
            continue
        if kind != "alignment":
            continue
        # 对齐关系正确性：新版 → 旧版在该位置各自的断言（不许自环、不许同版次），文本相同
        ends = (assertions.get(left) or {}, assertions.get(right) or {})
        if (
            left == right
            or unit[0] != "pair"
            or (left, right) != unit[1:]
            or ends[0].get("source_id") != new_view["source_id"]
            or ends[1].get("source_id") != old_view["source_id"]
            or not ends[0].get("text_sha256")
            or ends[0].get("text_sha256") != ends[1].get("text_sha256")
        ):
            failures.append(
                "对齐关系 %s→%s@%s 不正确：须是新版 → 旧版在该位置各自的断言且文本相同（推出 %r）"
                % (left, right, key, unit)
            )

    if reported_rows != rows:
        failures.append(
            "not_comparable 清单与夹具声明独立推出的不一致: 实报 %r / 推出 %r" % (reported_rows, rows)
        )
    if reported_count != len(rows):
        failures.append(
            "not_comparable_count=%r 与夹具声明推出的 %d 项不一致" % (reported_count, len(rows))
        )
    return failures


def check_edition_collation(world) -> tuple:
    """多版次对勘（CHARTER §25.9、§28、§29）：读 r1 → ed99 实跑产出的 knowledge，按夹具声明独立判定。

    四类关系各至少一条；对勘关系集与 r2 金标一致；不可比单元上无对勘关系；对齐关系正确；
    not_comparable 清单逐项（含理由）与计数都等于从夹具两份视图声明独立推出的那份。
    任何一项不成立 → FAIL 并写明哪一项；不再有 BLOCKED。清单取纯函数层的 ``collation``
    （即 ``edition_collation_set``），计数取 Ledger 里 r2 的 ``assembly_report``。
    """
    release = _require_release(world)
    manifest = release["manifest"]
    ed01, ed99 = manifest["editions"][0], manifest["editions"][1]
    report = (release["packages"]["r2"] or {}).get("assembly_report") or {}
    collation = ((release["pure"]["r2"] or {}).get("result") or {}).get("collation") or {}
    failures = _judge_edition_collation(
        produced=release["snapshots"]["r2"] or {},
        golden=_golden_doc(manifest, "round2"),
        old_view=_release_view(ed01),
        new_view=_release_view(ed99),
        reported_rows=collation.get("not_comparable"),
        reported_count=report.get("not_comparable_count"),
    )
    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    return ("PASS", "")


def check_identity_delta(world) -> tuple:
    """跨版本身份迁移：r2 → ed01r2 实跑的 identity_delta 与金标一致，理由引用都指向本轮提案键。"""
    release = _require_release(world)
    manifest = release["manifest"]
    failures = []

    package = release["packages"]["r3"]
    if package is None:
        return ("FAIL", "返工轮未产出 assembly_package（identity_delta 无处可查）")

    delta = package.get("identity_delta") or {}
    golden = _golden_doc(manifest, "identity_delta_r3")
    if canonical_json(delta.get("entries") or []) != canonical_json(golden["entries"]):
        failures.append(
            "identity_delta.entries 与金标不一致: %r" % json.dumps(delta.get("entries"), ensure_ascii=False)
        )

    base_rev = release["runs"]["r2"].get("snapshot_revision_id")
    base_bytes = release["snapshot_bytes"]["r2"]
    if base_bytes is None or delta.get("base_knowledge_sha256") != hashlib.sha256(base_bytes).hexdigest():
        failures.append("base_knowledge_sha256 不等于本轮实际基底修订的字节哈希")
    if base_rev is None:
        failures.append("r2 未产出 Snapshot，返工轮没有基底")

    round_keys = set((release["runs"]["r3"].get("report") or {}).get("round_proposal_keys") or [])
    if not round_keys:
        failures.append("r3 report 缺 round_proposal_keys（无法校验理由引用）")
    for entry in delta.get("entries") or []:
        key = (entry.get("reason_ref") or {}).get("proposal_key")
        if key not in round_keys:
            failures.append(
                "%s 的 reason_ref.proposal_key=%r 不在本轮 round_proposal_keys 里"
                % (entry.get("change_type"), key)
            )
    if sorted(entry.get("change_type") for entry in delta.get("entries") or []) != [
        "merged",
        "retired",
    ]:
        failures.append("本夹具的变更类型应为 merged + retired")

    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    return ("PASS", "")


def check_rework_replacement(world) -> tuple:
    """D-14 返工替换：ed01r2 被识别为 ed01 的替换、退役/沿用/产出与金标一致。"""
    release = _require_release(world)
    manifest = release["manifest"]
    ed01, rework = manifest["editions"][0], manifest["rework"]
    failures = []

    if (
        rework["source_id"] != ed01["source_id"]
        or rework["edition_part_artifact_id"] != ed01["edition_part_artifact_id"]
    ):
        failures.append("夹具前置不成立：ed01r2 与 ed01 不是同一 (source_id, edition_part_ids)")

    produced = release["snapshots"]["r3"]
    if produced is None:
        return ("FAIL", "返工轮未写出 Snapshot")
    golden = _golden_doc(manifest, "round3")
    failures.extend(
        _meta_excluded_mismatch(
            produced, golden, release["runs"]["r2"].get("snapshot_revision_id"), "r3"
        )
    )

    sources = [ed.get("source_id") for ed in produced.get("editions") or []]
    if sources != sorted(ed["source_id"] for ed in manifest["editions"]):
        failures.append("替换轮后 editions 不是「两个版次各一条」（替换不得新增条目）: %r" % (sources,))

    base = release["snapshots"]["r2"] or {}
    base_edition = [
        ed for ed in base.get("editions") or [] if ed.get("source_id") == ed01["source_id"]
    ]
    now_edition = [
        ed for ed in produced.get("editions") or [] if ed.get("source_id") == ed01["source_id"]
    ]
    if len(base_edition) == 1 and len(now_edition) == 1:
        if canonical_json(base_edition[0]) != canonical_json(now_edition[0]):
            failures.append("替换后的版次条目必须继承基底该版次的 reviewed_edition_* 身份字段")
        if now_edition[0].get("reviewed_edition_revision_id") == rework["ledger_constants"][
            "reviewed_edition_revision_id"
        ]:
            failures.append("替换不得把本轮新包的修订号当成该版次的身份（D-14：按基底身份识别）")
    else:
        failures.append("基底/产出里 src_sanche_ed01 的版次条目不是恰好一条")

    delta = (release["packages"]["r3"] or {}).get("identity_delta") or {}
    entries = delta.get("entries") or []
    retired = [entry for entry in entries if entry.get("change_type") == "retired"]
    if not retired:
        failures.append("返工删掉的断言必须以 change_type=retired 记进 identity_delta")
    if sorted(produced.get("retired_entity_ids") or []) != sorted(
        entry.get("from_entity_id") for entry in entries
    ):
        failures.append(
            "retired_entity_ids 必须恰好是 identity_delta 的 from 端: %r"
            % (produced.get("retired_entity_ids"),)
        )
    declared_before = _declared_present_keys(_release_view(ed01)["candidate_set"])
    declared_after = _declared_present_keys(_release_view(rework)["candidate_set"])
    removed = declared_before - declared_after
    if not removed:
        failures.append("夹具必须在返工视图里删掉至少一个可比单元（否则本判据空转）")
    by_key = {
        item.get("collation_key"): item["assertion_id"]
        for item in (base.get("assertions") or [])
        if item.get("collation_key")
    }
    for entry in retired:
        if entry.get("entity_kind") != "assertion":
            continue
        if by_key.get(next(iter(removed), None)) != entry.get("from_entity_id"):
            failures.append(
                "退役的断言必须是「基底声明过、返工视图不再声明」的那条: %r" % (entry.get("from_entity_id"),)
            )

    if [rel for rel in produced.get("relations") or [] if rel.get("relation_kind") == "merged_into"]:
        failures.append("合并不得写成 merged_into 关系（关系两端必须存活）")

    report = release["runs"]["r3"].get("report") or {}
    if not report.get("carried"):
        failures.append("未变对象必须走 carried（report.carried 为空）")

    merge_entry = next(
        (entry for entry in entries if entry.get("change_type") == "merged"), None
    )
    if merge_entry is None:
        failures.append("返工轮的合并必须以 change_type=merged 记进 identity_delta")
    else:
        pair = {merge_entry.get("from_entity_id")} | set(merge_entry.get("to_entity_ids") or [])
        internal = [
            rel
            for rel in base.get("relations") or []
            if {rel.get("from_entity_id"), rel.get("to_entity_id")} == pair
        ]
        expected_dropped = sorted(
            ({"relation_key": rel["relation_key"], "reason": "merge_internal"} for rel in internal),
            key=lambda row: row["relation_key"],
        )
        if sorted(report.get("dropped_relations") or [], key=lambda row: row["relation_key"]) != expected_dropped:
            failures.append(
                "合并双方之间的基底关系必须如实进 report.dropped_relations: 实报 %r / 独立推出 %r"
                % (report.get("dropped_relations"), expected_dropped)
            )

    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    return ("PASS", "")


def check_run_all_20_5(world) -> tuple:
    """§20.5 的判定必须由 m7-assembler.sh 的真实退出码决定（0/1/2/3 → PASS/FAIL/BLOCKED/BLOCKED）。"""
    failures = []
    if not RUN_ALL_SCRIPT.exists():
        return ("FAIL", "run_all.sh 缺失: %s" % RUN_ALL_SCRIPT)

    block = _run_all_20_5_block()
    if "m7-assembler.sh" not in block:
        failures.append("run_all.sh 的 20.5 段未调用 m7-assembler.sh（写死的判定）")

    observed = {}
    for exit_code, expected in ((0, "PASS"), (1, "FAIL"), (2, "BLOCKED"), (3, "BLOCKED")):
        line = _probe_20_5_mapping(exit_code)
        observed[exit_code] = line.split()[0] if line.split() else line
        if not line.startswith(expected):
            failures.append(
                "m7-assembler.sh 退出码 %d 应映射为 %s，实际: %s" % (exit_code, expected, line)
            )

    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    return (
        "PASS",
        "退出码映射 %s" % json.dumps({str(k): v for k, v in observed.items()}),
    )


def _run_all_20_5_block() -> str:
    text = RUN_ALL_SCRIPT.read_text(encoding="utf-8")
    start = text.find("\n    20.5)")
    if start < 0:
        raise RuntimeError("run_all.sh 未找到 20.5 段")
    end = text.find("\n    ;;", start)
    return text[start:end]


def _probe_20_5_mapping(exit_code: int) -> str:
    """把**真实**的 run_all.sh 放进假仓库，用一个按 `exit_code` 退出的 m7-assembler.sh 桩驱动它。"""
    import subprocess

    tmp = Path(tempfile.mkdtemp(prefix="m7_acc_20_5_"))
    try:
        acc_dir = tmp / "openspec" / "acceptance"
        acc_dir.mkdir(parents=True)
        (acc_dir / "run_all.sh").write_text(
            RUN_ALL_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
        )
        stub = acc_dir / "m7-assembler.sh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            "echo 'BLOCKED stub_check 桩判定'\n"
            "echo 'SUMMARY pass=0 fail=0 blocked=1'\n"
            "exit %d\n" % exit_code,
            encoding="utf-8",
        )
        stub.chmod(0o755)
        proc = subprocess.run(
            ["bash", str(acc_dir / "run_all.sh"), "20.5"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
        )
        for line in proc.stdout.splitlines():
            if line.startswith(("PASS  ", "FAIL  ", "BLOCKED  ")) and "20.5" in line:
                return line
        return "<20.5 无输出>"
    finally:
        shutil.rmtree(tmp, True)


def check_upstream_m6_real_book(world) -> tuple:
    """真书判据：在 `var/ledgers/qianyuan_w8` 的**副本**上以 r1 金标为基底跑真书第二轮。

    宿主要求：无账本时 BLOCKED（不许判 PASS）；跑完核对正本 `ledger.sqlite` 的 mtime/size 未变。
    """
    from pipeline.assembly.inputs import resolve_m7_inputs

    ledger_file = REAL_LEDGER_DIR / "ledger.sqlite"
    if not ledger_file.exists():
        return ("BLOCKED", "宿主缺失: 无真书账本（%s）" % REAL_LEDGER_DIR)

    before = ledger_file.stat()
    before_mark = (before.st_mtime_ns, before.st_size)
    base_bytes = (RELEASE_FIXTURE / "expected" / "snapshot_r1.json").read_bytes()
    failures = []
    tmp_root = Path(tempfile.mkdtemp(prefix="m7_acc_real_book_"))
    work = tmp_root / REAL_LEDGER_DIR.name
    try:
        shutil.copytree(REAL_LEDGER_DIR, work)
        service = LedgerService(work)
        try:
            m6_rev = _newest_sealed_m6_revision(service)
            if m6_rev is None:
                return ("BLOCKED", "宿主缺失: 真书账本里没有 sealed 的 m6 StagePackage")
            inputs = resolve_m7_inputs(service, [m6_rev])
            technique_id = inputs["technique_id"]
            base_rev = _seal_base_snapshot(service, base_bytes, technique_id)
            res = run_m7(
                service,
                inputs["candidate_set"].get("source_id"),
                technique_id=technique_id,
                reviewed_package_revision_ids=[m6_rev],
                base_snapshot_revision_id=base_rev,
                id_range={"pattern": [1, 10000]},
            )
            if res.get("status") != "succeeded":
                failures.append(
                    "真书第二轮 status=%r（期望 succeeded）" % res.get("status")
                )
            validation = _revision_doc(service, res.get("validation_report_revision_id"))
            gate = (validation or {}).get("incremental_gate") or {}
            bad = sorted(
                name for name, check in (gate.get("checks") or {}).items() if not check.get("passed")
            )
            if not gate.get("passed") or bad:
                failures.append("真书第二轮增量 Gate 未全过: %r" % (bad or gate.get("detail")))
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp_root, True)

    after = ledger_file.stat()
    if (after.st_mtime_ns, after.st_size) != before_mark:
        failures.append("真书正本 ledger.sqlite 被动过（mtime/size 已变）")

    if failures:
        return ("FAIL", "; ".join(failures[:3]))
    return ("PASS", "真书第二轮 succeeded 且增量 Gate 全过（正本只读已核）")


def _newest_sealed_m6_revision(service):
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "WHERE sp.stage='m6' AND r.status='sealed' ORDER BY r.created_at DESC, r.rowid DESC"
    ).fetchall()
    return rows[0][0] if rows else None


def _seal_base_snapshot(service, gold_bytes: bytes, technique_id: str) -> str:
    """把 r1 金标作为 sealed `canonical_snapshot` 灌进副本 Ledger，返回其修订号。"""
    from pipeline.ledger import ids

    processing_run_id = service.create_processing_run(
        "release_run", ids.new_id("artifact_id"), technique_id
    )
    _, config_rev = service.put_run_artifact(
        processing_run_id,
        "configuration",
        json.dumps({"stage": "m7", "acceptance": "upstream_m6_real_book"}, sort_keys=True).encode(
            "utf-8"
        ),
        producer_module="pipeline.assembly.acceptance",
        producer_version="0.1.0-draft",
    )
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": ids.new_id("step_run_id"),
            "processing_run_id": processing_run_id,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_rev,
        }
    )
    _, revision_id = service.put_artifact(
        step_run_id,
        "canonical_snapshot",
        gold_bytes,
        producer_module="pipeline.assembly.acceptance",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(revision_id)
    return revision_id


def _revision_doc(service, revision_id):
    if not revision_id:
        return None
    revision = service.get_revision(revision_id)
    return json.loads(service.objects.get(revision["sha256"]).decode("utf-8"))


def check_upstream_m6_real_with_note(world) -> tuple:
    """``upstream_m6_real`` 判据名不改，但必须如实写明输入是合成桩（CHARTER §2 P2 更正）。"""
    errors = check_upstream_m6_real(world)
    if errors:
        return ("FAIL", "; ".join(str(e) for e in errors[:3]))
    return ("PASS", UPSTREAM_M6_REAL_NOTE)


COMPUTED_CHECKS = (
    ("genesis_snapshot", check_genesis_snapshot),
    ("configuration_and_scope", check_configuration_and_scope),
    ("package_lineage", check_package_lineage),
    ("identity_and_allocation", check_identity_and_allocation),
    ("provenance_and_fidelity", check_provenance_and_fidelity),
    ("no_silent_fold_and_display", check_no_silent_fold_and_display),
    ("upstream_immutable", check_upstream_immutable),
    ("checkpoints", check_checkpoints),
    ("closed_set_types", check_closed_set_types),
    ("no_model_calls", check_no_model_calls),
    ("upstream_m6_real", check_upstream_m6_real_with_note),
    ("incremental_multi_edition", check_incremental_multi_edition),
    ("edition_collation", check_edition_collation),
    ("identity_delta", check_identity_delta),
    ("rework_replacement", check_rework_replacement),
    ("run_all_20_5", check_run_all_20_5),
    ("upstream_m6_real_book", check_upstream_m6_real_book),
)


def _verdict_of(func, world) -> tuple:
    """兼容两种口径：返回 `(status, detail)`，或旧的「errors 列表」。"""
    try:
        verdict = func(world)
    except Exception as exc:  # noqa: BLE001 - 判据内部的任何异常都算 FAIL
        return ("FAIL", "%s: %s" % (type(exc).__name__, exc))
    if isinstance(verdict, list):
        if not verdict:
            return ("PASS", "")
        return ("FAIL", "; ".join(str(item) for item in verdict[:3]))
    status, detail = verdict[0], verdict[1] if len(verdict) > 1 else ""
    return (status, detail)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pipeline.assembly.acceptance")
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    args = parser.parse_args(argv)

    if jsonschema is None:
        print("BLOCKED m7_acceptance 前置缺失: jsonschema 不可导入", file=sys.stderr)
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    tmp_dir = Path(tempfile.mkdtemp(prefix="m7_acceptance_"))
    try:
        try:
            _, service, world = _prepare(tmp_dir)
        except Exception as exc:
            print("FAIL m7_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
            return 1

        passed = 0
        failed = 0
        blocked = 0
        release = None
        try:
            # 夹具三轮实跑只准备一次，六条判定共用（准备失败时逐条 FAIL，不静默降级）
            try:
                release = _prepare_release_rounds(tmp_dir)
                world["release"] = release
            except Exception as exc:  # noqa: BLE001
                world["release"] = None
                world["release_error"] = "%s: %s" % (type(exc).__name__, exc)

            for name, func in COMPUTED_CHECKS:
                status, detail = _verdict_of(func, world)
                if status == "PASS":
                    passed += 1
                    print("PASS %s" % name)
                    if detail:
                        print("NOTE %s %s" % (name, detail))
                elif status == "BLOCKED":
                    blocked += 1
                    print("BLOCKED %s %s" % (name, detail))
                else:
                    failed += 1
                    print("FAIL %s %s" % (name, detail))
        finally:
            service.close()
            if release is not None:
                release["service"].close()

        print("SUMMARY pass=%d fail=%d blocked=%d" % (passed, failed, blocked))
        if failed:
            return 1
        if blocked:
            return 2
        return 0

    finally:
        if not args.keep:
            shutil.rmtree(tmp_dir, True)


if __name__ == "__main__":
    raise SystemExit(main())
