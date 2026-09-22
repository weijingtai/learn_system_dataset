"""M7 汇编输入解析（spec §17, P5, act/g0-04；act/impl-07/21 扩多包与基底读取）。

只读解析上游 M6 与 M4 产物，严格验证契约与 P5（所属 StepRun 恒为 succeeded）。

本模块**只做解析与校验**：不合并、不发号、不写 Ledger（ACT 21 contract 一/二）。
"""

import json
from typing import Any, Dict, List

import yaml

from pipeline.assembly.errors import AssemblyRefused

# 基底 Snapshot 的 artifact_type 取**已登记名** `canonical_snapshot`
# （impl-07 README §0.3 末条：草稿名 `canonical_knowledge_snapshot` 未采用，
#  M7 现行产出（step.py 7.1）写的也是 `canonical_snapshot`）。
BASE_SNAPSHOT_ARTIFACT_TYPE = "canonical_snapshot"


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


def _package_error(index: int, revision_id: str, message: str, code: str) -> AssemblyRefused:
    """定位到「第几个包」的拒收（ACT 21 contract 一.1：消息须指明包序号与修订 id）。"""
    return AssemblyRefused(
        "第 %d 个包（reviewed_package_revision_ids[%d]，修订 %s）: %s"
        % (index + 1, index, revision_id, message),
        code=code,
    )


def _resolve_one_package(service, m6_rev_id: str, index: int) -> Dict[str, Any]:
    """解析单个 reviewed package（四项校验 + 派生视图），失败消息带上包序号。"""
    # 1. 检查修订状态是否为 sealed
    rev = service.get_revision(m6_rev_id)
    if rev is None:
        raise _package_error(index, m6_rev_id, "入参修订不存在", "REF_001")
    if rev.get("status") != "sealed":
        raise _package_error(
            index, m6_rev_id, "入参修订未 sealed (status=%s)" % rev.get("status"), "SCH_002"
        )

    # 2. 检查 stage_package
    art_type = _get_artifact_type(service, m6_rev_id)
    if art_type != "stage_package":
        raise _package_error(
            index, m6_rev_id, "入参修订类型必须为 stage_package (type=%s)" % art_type, "SCH_002"
        )

    m6_stage_package_id, stage = _get_stage_package_info(service, rev["artifact_id"])
    if stage != "m6":
        raise _package_error(
            index,
            m6_rev_id,
            "stage_package stage 必须为 'm6' (%s, stage=%s)" % (m6_stage_package_id, stage),
            "SCH_002",
        )

    m6_pkg_doc = _read_doc(service, m6_rev_id)
    manifest = m6_pkg_doc.get("manifest", {})
    m6_step_run_id = manifest.get("step_run_id")
    if not m6_step_run_id:
        raise _package_error(index, m6_rev_id, "stage_package 缺失 manifest.step_run_id", "SCH_002")

    m6_step = service.get_step_run(m6_step_run_id)
    if m6_step is None or m6_step.get("status") != "succeeded":
        status = m6_step.get("status") if m6_step else "None"
        raise _package_error(
            index,
            m6_rev_id,
            "m6 所属 StepRun 必须 succeeded (P5): %s (status=%s)" % (m6_step_run_id, status),
            "REF_001",
        )

    # 3. manifest.output_artifacts 恰 1 个 reviewed_edition_package
    rep_outputs = [
        item for item in manifest.get("output_artifacts", [])
        if item.get("artifact_type") == "reviewed_edition_package"
    ]
    if len(rep_outputs) != 1:
        raise _package_error(
            index,
            m6_rev_id,
            "manifest.output_artifacts 必须恰含 1 个 reviewed_edition_package，实际: %d" % len(rep_outputs),
            "SCH_002",
        )
    rep_rev_id = rep_outputs[0]["artifact_revision_id"]

    # 4. manifest.lineage.upstream_artifacts 含 candidate_package
    lineage = m6_pkg_doc.get("lineage", {})
    cp_upstreams = [
        item for item in lineage.get("upstream_artifacts", [])
        if item.get("artifact_type") == "candidate_package"
    ]
    if not cp_upstreams:
        raise _package_error(
            index,
            m6_rev_id,
            "manifest.lineage.upstream_artifacts 必须包含 candidate_package",
            "SCH_002",
        )
    candidate_pkg_rev_id = cp_upstreams[0]["artifact_revision_id"]

    # 5. 解析 reviewed_edition_package → reviewed_edition
    rep_rev = service.get_revision(rep_rev_id)
    if rep_rev is None or rep_rev.get("status") != "sealed":
        raise _package_error(
            index, m6_rev_id, "reviewed_edition_package 修订未 sealed: %s" % rep_rev_id, "SCH_002"
        )
    rep_doc = _read_doc(service, rep_rev_id)

    re_rev_id = rep_doc.get("reviewed_edition_revision_id")
    if not re_rev_id:
        raise _package_error(
            index, m6_rev_id, "reviewed_edition_package 缺少 reviewed_edition_revision_id", "SCH_002"
        )

    re_rev = service.get_revision(re_rev_id)
    if re_rev is None or re_rev.get("status") != "sealed":
        raise _package_error(
            index, m6_rev_id, "reviewed_edition 修订未 sealed: %s" % re_rev_id, "SCH_002"
        )
    re_doc = _read_doc(service, re_rev_id)

    # 6. 解析 candidate_package 与所属 m4 StepRun
    cp_rev = service.get_revision(candidate_pkg_rev_id)
    if cp_rev is None or cp_rev.get("status") != "sealed":
        raise _package_error(
            index, m6_rev_id, "candidate_package 修订未 sealed: %s" % candidate_pkg_rev_id, "SCH_002"
        )

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
        raise _package_error(
            index,
            m6_rev_id,
            "candidate_package 所属 m4 StepRun 必须 succeeded (P5): status=%s" % status,
            "REF_001",
        )

    # 7. 解析 candidate_set
    cset_rev_id = re_doc.get("candidate_set_revision_id")
    if not cset_rev_id:
        raise _package_error(index, m6_rev_id, "reviewed_edition 缺少 candidate_set_revision_id", "SCH_002")
    cset_rev = service.get_revision(cset_rev_id)
    if cset_rev is None or cset_rev.get("status") != "sealed":
        raise _package_error(index, m6_rev_id, "candidate_set 修订未 sealed: %s" % cset_rev_id, "SCH_002")
    cset_doc = _read_doc(service, cset_rev_id)

    # 8. 该包的来源与版次分区（D-14 替换识别的键：(source_id, edition_part_ids 集合)）
    source_id = cset_doc.get("source_id")
    edition_part_ids = sorted(
        {
            part
            for part in (
                re_doc.get("edition_part_artifact_id"),
                cset_doc.get("edition_part_artifact_id"),
            )
            if part
        }
    )

    return {
        # 与本包相关的既有键（单包时与旧返回结构逐字一致）
        "technique_id": cset_doc.get("technique_id"),
        "m6_stage_package_id": m6_stage_package_id,
        "reviewed_package_artifact_id": rev["artifact_id"],
        "reviewed_package_revision_id": m6_rev_id,
        "reviewed_edition_package_revision_id": rep_rev_id,
        "reviewed_edition_revision_id": re_rev_id,
        "candidate_package_revision_id": candidate_pkg_rev_id,
        "candidate_set_revision_id": cset_rev_id,
        "edition_part_artifact_id": re_doc.get("edition_part_artifact_id"),
        "reviewed_package": rep_doc,
        "reviewed_edition": re_doc,
        "candidate_set": cset_doc,
        # 多包解析新增（附加信息，不改变上述键的取值）
        # 注意：**不放**入参下标——返回结构必须与入参顺序无关（ACT 21 contract 一「硬性」）。
        "created_at": rev.get("created_at"),
        "source_id": source_id,
        "edition_part_ids": edition_part_ids,
    }


def _mark_replacements(packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """D-14：同一 ``(source_id, edition_part_ids 集合)`` 出现多次 → 如实标记替换关系。

    **只标记，不实现继承**（继承逻辑属 D 波，ACT 21 contract 一.2）。
    「部分重叠 / 不相交」的判定要与基底 Snapshot 比对，本波不做。
    每组内新旧按 ``(created_at, 修订 id)`` 升序判定，与入参顺序无关。
    """
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for package in packages:
        key = (package.get("source_id"), tuple(package.get("edition_part_ids") or []))
        groups.setdefault(key, []).append(package)

    relations: List[Dict[str, Any]] = []
    for key in sorted(groups, key=lambda item: (str(item[0]), item[1])):
        members = groups[key]
        for older, newer in zip(members, members[1:]):
            relations.append(
                {
                    "relation": "replaces",
                    "source_id": key[0],
                    "edition_part_ids": list(key[1]),
                    "replaced_revision_id": older["reviewed_package_revision_id"],
                    "replacement_revision_id": newer["reviewed_package_revision_id"],
                }
            )
    return relations


def resolve_m7_inputs(service, reviewed_package_revision_ids: List[str]) -> Dict[str, Any]:
    """只读解析 M7 汇编输入（P5）。

    逐包验证上游 M6 包及其派生的 candidate_package / candidate_set（四项校验 + P5），
    并返回**全部**包（不再只取 ``[0]``）。

    返回结构的向后兼容口径（ACT 21 contract 一.3）：
    - 单包（创世路径）时，既有 11 个键的取值逐字不变；
    - 多包时，既有键取「规范化排序（按 created_at 与修订 id 升序）后的第一个包」，
      因而**与入参顺序无关**；
    - ``packages`` / ``replaces`` 为新增的附加键（不改变既有键语义）。
    """
    if not reviewed_package_revision_ids or not isinstance(reviewed_package_revision_ids, list):
        raise AssemblyRefused("reviewed_package_revision_ids 必须为非空列表", code="SCH_001")

    packages = [
        _resolve_one_package(service, revision_id, index)
        for index, revision_id in enumerate(reviewed_package_revision_ids)
    ]
    # 规范化排序：结果不得依赖入参顺序（ACT 21 contract 一「硬性」）
    packages.sort(key=lambda p: (p.get("created_at") or "", p["reviewed_package_revision_id"]))

    first = packages[0]
    result: Dict[str, Any] = {
        "technique_id": first["technique_id"],
        "m6_stage_package_id": first["m6_stage_package_id"],
        "reviewed_package_revision_id": first["reviewed_package_revision_id"],
        "reviewed_edition_package_revision_id": first["reviewed_edition_package_revision_id"],
        "reviewed_edition_revision_id": first["reviewed_edition_revision_id"],
        "candidate_package_revision_id": first["candidate_package_revision_id"],
        "candidate_set_revision_id": first["candidate_set_revision_id"],
        "edition_part_artifact_id": first["edition_part_artifact_id"],
        "reviewed_package": first["reviewed_package"],
        "reviewed_edition": first["reviewed_edition"],
        "candidate_set": first["candidate_set"],
    }
    result["packages"] = packages
    result["replaces"] = _mark_replacements(packages)
    return result


def resolve_base_snapshot(service, revision_id: str) -> Dict[str, Any]:
    """只读读取并校验基底 CanonicalKnowledgeSnapshot 修订（ACT 21 contract 二/四）。

    校验顺序与错误码：
    - 修订不存在 → ``REF_001``
    - 已 ``superseded`` → ``SCH_002``（D-15 前半：这类基底在 ``begin_step_run`` 之前拒收）
    - 未 ``sealed`` → ``SCH_002``
    - ``artifact_type`` 非 :data:`BASE_SNAPSHOT_ARTIFACT_TYPE` → ``SCH_002``

    **只读**：不合并、不发号、不写 Ledger。返回基底的内容，供后续波次使用。
    """
    rev = service.get_revision(revision_id)
    if rev is None:
        raise AssemblyRefused("基底修订不存在: %s" % revision_id, code="REF_001")

    status = rev.get("status")
    if status == "superseded":
        raise AssemblyRefused(
            "基底修订已 superseded，不可作为基底（D-15）: %s" % revision_id, code="SCH_002"
        )
    if status != "sealed":
        raise AssemblyRefused(
            "基底修订未 sealed: %s (status=%s)" % (revision_id, status), code="SCH_002"
        )

    art_type = _get_artifact_type(service, revision_id)
    if art_type != BASE_SNAPSHOT_ARTIFACT_TYPE:
        raise AssemblyRefused(
            "基底修订类型必须为 %s: %s (type=%s)"
            % (BASE_SNAPSHOT_ARTIFACT_TYPE, revision_id, art_type),
            code="SCH_002",
        )

    return {
        "revision_id": revision_id,
        "artifact_id": rev["artifact_id"],
        "artifact_type": art_type,
        "sha256": rev.get("sha256"),
        "status": status,
        "doc": _read_doc(service, revision_id),
    }
