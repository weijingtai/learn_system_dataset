"""M7 薄适配入口：把发布段调度接到 ``run_m7``（TODO T04B）。

调度器按 ``legacy_self_driving`` 约定调用 ``(service, edition_part_id, **entry_kwargs)``。
本模块只做参数搬运，不改变 ``run_m7`` 的签名与产出：

- M6 输入取自 Ledger 事实：该 EditionPart 名下**最新** succeeded 的 m6 StepRun
  所封存的唯一 StagePackage（只经 LedgerPort 公开读方法）；
- ``technique_id`` 取自该包的只读解析结果（``resolve_m7_inputs``，不写 Ledger）；
- 只走创世路径（``base_snapshot_revision_id=None``）；
- ``run_m7`` 自建 ``release_run`` ProcessingRun（登记表 ``owns_processing_run: true``），
  其返回值不带 ``processing_run_id``，由本层从 StepRun 事实补上。

begin 之前的任何拒绝都原样外抛（零写入）。
"""

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.inputs import resolve_m7_inputs
from pipeline.assembly.step import run_m7 as _run_m7


def _latest_m6_package_revision_id(service, edition_part_id):
    """该 EditionPart 最新 succeeded 的 m6 StepRun 封存的唯一 StagePackage 修订号。"""
    succeeded = [
        row["step_run_id"]
        for row in service.list_step_runs(edition_part_id, "m6")
        if row.get("status") == "succeeded"
    ]
    if not succeeded:
        raise AssemblyRefused(
            "M6 未签发：EditionPart %s 没有 succeeded 的 m6 StepRun" % edition_part_id,
            code="REF_001",
        )
    rows = service.list_step_run_revisions(
        succeeded[-1], artifact_type="stage_package", status="sealed"
    )
    if len(rows) != 1:
        raise AssemblyRefused(
            "m6 StepRun %s 名下 sealed StagePackage 数量异常: %d" % (succeeded[-1], len(rows)),
            code="REF_001",
        )
    return rows[0]["artifact_revision_id"]


def run_m7(service, edition_part_id, *, id_range=None):
    """调度器入口：以该 EditionPart 最新签发的 M6 包做一次 M7 创世汇编。"""
    package_revision_id = _latest_m6_package_revision_id(service, edition_part_id)
    technique_id = resolve_m7_inputs(service, [package_revision_id])["technique_id"]
    summary = _run_m7(
        service,
        edition_part_id,
        technique_id=technique_id,
        reviewed_package_revision_ids=[package_revision_id],
        id_range=id_range,
    )
    step = service.get_step_run(summary["step_run_id"])
    return dict(summary, processing_run_id=step["processing_run_id"])
