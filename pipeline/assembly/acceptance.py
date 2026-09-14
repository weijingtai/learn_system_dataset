"""M7 创世汇编验收（spec §19.0 判据）：十六项判定（10 PASS + 6 BLOCKED）。

本模块不 import ``genesis``；判定只读 Ledger 与 tests/data 金标，不信任
``run_m7`` 返回的 Gate 报告与结果对象。
依赖真实消费 M6 产出的判定恒 BLOCKED（第 66 条）。
"""

import argparse
import ast
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

from pipeline.assembly import fixture_seed
from pipeline.assembly.canonical import canonical_json
from pipeline.assembly.gate import evaluate_genesis
from pipeline.assembly.step import run_m7
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"
DATA_DIR = Path(__file__).resolve().parent / "tests" / "data"
GENESIS_PACKAGE_PATH = DATA_DIR / "genesis_package.json"
GOLDEN_KNOWLEDGE_PATH = DATA_DIR / "genesis_expected_knowledge.json"

BLOCKED_CHECKS = (
    (
        "incremental_multi_edition",
        "多 Edition 增量对勘未实现（§15:655）",
    ),
    (
        "edition_collation",
        "Alignment/VariantReading/Addition/Omission 未实现",
    ),
    (
        "identity_delta",
        "跨版本身份迁移未实现（§6.3、§16:732）",
    ),
    (
        "rework_replacement",
        "M6 返工替换未实现（D-14）",
    ),
    (
        "upstream_m6_real",
        "「消费真实 M6 产出」的判定在 impl-06 实现并验收前恒 BLOCKED（第 66 条）；本切片输入为合成 ReviewedEditionPackage，不伪造",
    ),
    (
        "run_all_20_5",
        "§20.5 未接线（Q29 采纳 C）",
    ),
)


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
    assembly_dir = REPO_ROOT / "pipeline" / "assembly"
    errors = []
    forbidden = {"requests", "openai", "anthropic", "httpx"}

    for py_file in assembly_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
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
)


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

        try:
            for name, func in COMPUTED_CHECKS:
                try:
                    errs = func(world)
                except Exception as exc:
                    errs = ["%s: %s" % (type(exc).__name__, exc)]

                if errs:
                    failed += 1
                    print("FAIL %s %s" % (name, "; ".join(str(e) for e in errs[:3])))
                else:
                    passed += 1
                    print("PASS %s" % name)

            for name, desc in BLOCKED_CHECKS:
                blocked += 1
                print("BLOCKED %s %s" % (name, desc))

        finally:
            service.close()

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
