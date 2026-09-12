"""M5 输出装配：gate_results 与 validation_package（代码草案 0.1.0-draft）。

本模块只做纯装配，不访问 Ledger、不写文件；两处返回结构均由
``tests/test_step.py`` 逐键断言（P3：不新增 ``openspec/schemas/`` 文件）。
"""

from . import M5_TOOL, M5_TOOL_VERSION
from .findings import gate_summary

# 目标级别下转成返工任务的阶段归属（D-11 取 A：字符/页登记/终态归 m2，其余归 m3）
_M2_CHECKS = frozenset(
    {
        "unresolved_glyph",
        "unproofread_glyphs",
        "forbidden_char_in_text",
        "page_set_mismatch",
        "page_hash_mismatch",
        "terminal_state_mismatch",
        "page_missing",
        "page_unregistered",
        "excluded_page_no_evidence",
    }
)

# 未执行门禁与理由（D-12 取 A：逐条写 {gate, check, reason}，行名取 §19 第一列）
_NOT_EVALUATED = (
    {"gate": "G4", "check": "content_layering"},
    {"gate": "G5", "check": "concept_search"},
    {"gate": "G6", "check": "rule_executability"},
    {"gate": "G3", "check": "candidate_evidence"},
)
_NOT_EVALUATED_REASON = "M4 Knowledge Extraction"


def _rework_stage(check):
    return "m2" if check in _M2_CHECKS else "m3"


def _gate_verdict(gate_code, findings, reports, target_level):
    """单个 G 代号的结论：failed / passed_with_warnings / passed。"""
    gate_reports = [r for r in reports if r["gate"] == gate_code]
    if any(r["task_status"] != "succeeded" for r in gate_reports):
        return "failed"
    gate_findings = [f for f in findings if f["gate"] == gate_code]
    if any(f["severity"][target_level] == "error" for f in gate_findings):
        return "failed"
    if any(f["severity"][target_level] == "warning" for f in gate_findings):
        return "passed_with_warnings"
    return "passed"


def assemble_gate_results(
    level_verdicts,
    findings,
    reports,
    *,
    target_consumption_level,
    scope="corpus_only",
    validator_version=M5_TOOL_VERSION,
):
    """装配 ``gate_results`` 主内容（键序见 §5.3，逐键被测试断言）。"""
    findings = list(findings or [])
    reports = list(reports or [])
    target = target_consumption_level

    validators = [
        {
            "validator_id": report["validator_id"],
            "gate": report["gate"],
            "version": report["version"],
            "task_status": report["task_status"],
            "report_revision_id": report.get("report_revision_id"),
        }
        for report in reports
    ]

    failures = [f for f in findings if f["severity"][target] == "error"]
    warnings = [f for f in findings if f["severity"][target] == "warning"]
    passed_checks = [
        report["validator_id"]
        for report in reports
        if report["task_status"] == "succeeded"
        and not any(
            f["severity"][target] == "error" for f in report["findings"]
        )
    ]

    broken_relations = [
        {
            "relation": finding["relation"],
            "subject": finding["subject"],
            "code": finding["code"],
            "detail": finding["detail"],
        }
        for finding in findings
        if finding["relation"] == "artifact_ref"
    ]

    rework_groups = {}
    for finding in failures:
        stage = _rework_stage(finding["check"])
        key = (stage, finding["validator_id"], finding["check"])
        group = rework_groups.setdefault(
            key,
            {
                "rework_stage": stage,
                "validator_id": finding["validator_id"],
                "check": finding["check"],
                "code": finding["code"],
                "subjects": [],
            },
        )
        group["subjects"].append(finding["subject"])
    rework_tasks = [rework_groups[key] for key in sorted(rework_groups)]

    not_evaluated = [
        {"gate": item["gate"], "check": item["check"], "reason": _NOT_EVALUATED_REASON}
        for item in _NOT_EVALUATED
    ]

    gates = {
        "G1": _gate_verdict("G1", findings, reports, target),
        "G2": _gate_verdict("G2", findings, reports, target),
        "G3": _gate_verdict("G3", findings, reports, target),
        "G4": "not_evaluated",
        "G5": "not_evaluated",
        "G6": "not_evaluated",
        "G7": "deferred_to_m8",
    }

    gate = gate_summary(target, findings, reports)

    spans_checked = max(
        (report.get("checked", {}).get("spans", 0) for report in reports),
        default=0,
    )
    pages_checked = max(
        (report.get("checked", {}).get("pages", 0) for report in reports),
        default=0,
    )

    return {
        "schema_version": "0.1.0-draft",
        "scope": scope,
        "target_consumption_level": target,
        "validator_suite": M5_TOOL,
        "validator_version": validator_version,
        "validators": validators,
        "gates": gates,
        "passed_checks": passed_checks,
        "failures": failures,
        "warnings": warnings,
        "broken_relations": broken_relations,
        "rework_tasks": rework_tasks,
        "not_evaluated": not_evaluated,
        "level_verdicts": dict(level_verdicts),
        "gate": gate,
        "counts": {
            "validators": len(reports),
            "findings": len(findings),
            "failures": len(failures),
            "warnings": len(warnings),
            "broken_relations": len(broken_relations),
            "rework_tasks": len(rework_tasks),
            "spans_checked": int(spans_checked or 0),
            "pages_checked": int(pages_checked or 0),
        },
    }


def assemble_validation_package(
    gate_results,
    inputs,
    gate,
    level_verdicts,
    *,
    target_consumption_level,
    scope="corpus_only",
    gate_results_revision_id=None,
    edition_part_id=None,
):
    """装配 ``validation_package`` 阶段输出索引（键序见 §5.3）。"""
    return {
        "schema_version": "0.1.0-draft",
        "edition_part_id": edition_part_id,
        "technique_id": inputs.get("technique_id"),
        "scope": scope,
        "target_consumption_level": target_consumption_level,
        "validator_version": M5_TOOL_VERSION,
        "gate_results_revision_id": gate_results_revision_id,
        "corpus_package_revision_id": inputs["corpus_package_revision_id"],
        "corpus_spans_revision_id": inputs["corpus_spans_revision_id"],
        "m3_stage_package_id": inputs["m3_stage_package_id"],
        "m3_package_revision_id": inputs["m3_package_revision_id"],
        "candidate_package_revision_id": None,
        "gate": dict(gate),
        "level_verdicts": dict(level_verdicts),
    }
