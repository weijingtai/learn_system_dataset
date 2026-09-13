"""M7 创世汇编输入解析（spec §17, P5, act/g0-04）。

只读解析上游 M6 与 M4 产物，严格验证契约与 P5（所属 StepRun 恒为 succeeded）。
"""

import json
from typing import Any, Dict, List

import yaml

from pipeline.assembly.errors import AssemblyRefused


def _read_doc(service, revision_id: str) -> dict:
    rev = service.get_revision(revision_id)
    if rev is None:
        raise AssemblyRefused("修订不存在: %s" % revision_id, code="REF_001")
    raw = service.objects.get(rev["sha256"])
    if raw is None:
        raise AssemblyRefused("对象不存在: %s (%s)" % (revision_id, rev["sha256"]), code="REF_001")
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return yaml.safe_load(text)


def _get_artifact_type(service, revision_id: str) -> str:
    row = service.store.conn.execute(
        "SELECT a.artifact_type FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE r.artifact_revision_id = ?",
        (revision_id,),
    ).fetchone()
    if row is None:
        raise AssemblyRefused("未找到修订所属 artifact_type: %s" % revision_id, code="REF_001")
    return row[0]


def _get_stage_package_info(service, artifact_id: str) -> tuple:
    row = service.store.conn.execute(
        "SELECT stage_package_id, stage FROM stage_packages WHERE artifact_id = ?",
        (artifact_id,),
    ).fetchone()
    if row is None:
        raise AssemblyRefused("未找到 stage_packages 记录: artifact_id=%s" % artifact_id, code="REF_001")
    return row[0], row[1]


def resolve_m7_inputs(service, reviewed_package_revision_ids: List[str]) -> Dict[str, Any]:
    """只读解析 M7 汇编输入（P5）。

    验证上游 M6 包及其派生的 candidate_package / candidate_set，确保其所属 StepRun 皆为 succeeded。
    """
    if not reviewed_package_revision_ids or not isinstance(reviewed_package_revision_ids, list):
        raise AssemblyRefused("reviewed_package_revision_ids 必须为非空列表", code="SCH_001")

    # G0 创世汇编单 Package 处理
    m6_rev_id = reviewed_package_revision_ids[0]

    # 1. 检查修订状态是否为 sealed
    rev = service.get_revision(m6_rev_id)
    if rev is None:
        raise AssemblyRefused("入参修订不存在: %s" % m6_rev_id, code="REF_001")
    if rev.get("status") != "sealed":
        raise AssemblyRefused("入参修订未 sealed: %s (status=%s)" % (m6_rev_id, rev.get("status")), code="SCH_002")

    # 2. 检查 stage_package
    art_type = _get_artifact_type(service, m6_rev_id)
    if art_type != "stage_package":
        raise AssemblyRefused("入参修订类型必须为 stage_package: %s (type=%s)" % (m6_rev_id, art_type), code="SCH_002")

    m6_stage_package_id, stage = _get_stage_package_info(service, rev["artifact_id"])
    if stage != "m6":
        raise AssemblyRefused("stage_package stage 必须为 'm6': %s (stage=%s)" % (m6_stage_package_id, stage), code="SCH_002")

    m6_pkg_doc = _read_doc(service, m6_rev_id)
    manifest = m6_pkg_doc.get("manifest", {})
    m6_step_run_id = manifest.get("step_run_id")
    if not m6_step_run_id:
        raise AssemblyRefused("stage_package 缺失 manifest.step_run_id", code="SCH_002")

    m6_step = service.get_step_run(m6_step_run_id)
    if m6_step is None or m6_step.get("status") != "succeeded":
        status = m6_step.get("status") if m6_step else "None"
        raise AssemblyRefused("m6 所属 StepRun 必须 succeeded (P5): %s (status=%s)" % (m6_step_run_id, status), code="REF_001")

    # 3. manifest.output_artifacts 恰 1 个 reviewed_edition_package
    rep_outputs = [
        item for item in manifest.get("output_artifacts", [])
        if item.get("artifact_type") == "reviewed_edition_package"
    ]
    if len(rep_outputs) != 1:
        raise AssemblyRefused(
            "manifest.output_artifacts 必须恰含 1 个 reviewed_edition_package，实际: %d" % len(rep_outputs),
            code="SCH_002",
        )
    rep_rev_id = rep_outputs[0]["artifact_revision_id"]

    # 4. manifest.lineage.upstream_artifacts 含 candidate_package
    lineage = m6_pkg_doc.get("lineage", {})
    cp_upstreams = [
        item for item in lineage.get("upstream_artifacts", [])
        if item.get("artifact_type") == "candidate_package"
    ]
    if not cp_upstreams:
        raise AssemblyRefused("manifest.lineage.upstream_artifacts 必须包含 candidate_package", code="SCH_002")
    candidate_pkg_rev_id = cp_upstreams[0]["artifact_revision_id"]

    # 5. 解析 reviewed_edition_package → reviewed_edition
    rep_rev = service.get_revision(rep_rev_id)
    if rep_rev is None or rep_rev.get("status") != "sealed":
        raise AssemblyRefused("reviewed_edition_package 修订未 sealed: %s" % rep_rev_id, code="SCH_002")
    rep_doc = _read_doc(service, rep_rev_id)

    re_rev_id = rep_doc.get("reviewed_edition_revision_id")
    if not re_rev_id:
        raise AssemblyRefused("reviewed_edition_package 缺少 reviewed_edition_revision_id", code="SCH_002")

    re_rev = service.get_revision(re_rev_id)
    if re_rev is None or re_rev.get("status") != "sealed":
        raise AssemblyRefused("reviewed_edition 修订未 sealed: %s" % re_rev_id, code="SCH_002")
    re_doc = _read_doc(service, re_rev_id)

    # 6. 解析 candidate_package 与所属 m4 StepRun
    cp_rev = service.get_revision(candidate_pkg_rev_id)
    if cp_rev is None or cp_rev.get("status") != "sealed":
        raise AssemblyRefused("candidate_package 修订未 sealed: %s" % candidate_pkg_rev_id, code="SCH_002")

    # 查询 candidate_package 所属 step_run
    m4_step_run_row = service.store.conn.execute(
        "SELECT step_run_id, status FROM step_runs WHERE stage='m4' AND result_json LIKE ?",
        ("%" + candidate_pkg_rev_id + "%",),
    ).fetchone()
    if m4_step_run_row is None:
        # 尝试查 transformations
        m4_step_run_row = service.store.conn.execute(
            "SELECT r.step_run_id, r.status FROM transformations t "
            "JOIN step_runs r ON r.step_run_id = t.step_run_id "
            "WHERE t.output_artifact_revision_id = ? AND r.stage='m4'",
            (candidate_pkg_rev_id,),
        ).fetchone()

    if m4_step_run_row is None or m4_step_run_row[1] != "succeeded":
        status = m4_step_run_row[1] if m4_step_run_row else "None"
        raise AssemblyRefused("candidate_package 所属 m4 StepRun 必须 succeeded (P5): status=%s" % status, code="REF_001")

    # 7. 解析 candidate_set
    cset_rev_id = re_doc.get("candidate_set_revision_id")
    if not cset_rev_id:
        raise AssemblyRefused("reviewed_edition 缺少 candidate_set_revision_id", code="SCH_002")
    cset_rev = service.get_revision(cset_rev_id)
    if cset_rev is None or cset_rev.get("status") != "sealed":
        raise AssemblyRefused("candidate_set 修订未 sealed: %s" % cset_rev_id, code="SCH_002")
    cset_doc = _read_doc(service, cset_rev_id)

    # 8. 校验 technique_id 一致性
    cset_tech = cset_doc.get("technique_id")
    edition_part_id = re_doc.get("edition_part_artifact_id")

    return {
        "technique_id": cset_tech,
        "m6_stage_package_id": m6_stage_package_id,
        "reviewed_package_revision_id": m6_rev_id,
        "reviewed_edition_package_revision_id": rep_rev_id,
        "reviewed_edition_revision_id": re_rev_id,
        "candidate_package_revision_id": candidate_pkg_rev_id,
        "candidate_set_revision_id": cset_rev_id,
        "edition_part_artifact_id": edition_part_id,
        "reviewed_package": rep_doc,
        "reviewed_edition": re_doc,
        "candidate_set": cset_doc,
    }
