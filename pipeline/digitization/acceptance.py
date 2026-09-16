"""M2 电子文本清洗验收检查。

提供 check_m2_sanitization 函数，供 m2-sanitization.sh 调用。
"""

from pathlib import Path
from typing import Any


def check_m2_sanitization(ledger_dir: Path, fixture_path: Path | None = None) -> list[dict]:
    """检查 M2 电子文本清洗的验收项。

    参数：
        ledger_dir：Ledger 目录，期望包含 sanitization_report, patches, cleaned_text_revision 等
        fixture_path：验收宿主片段路径（可选）。若缺失或目录不存在，
                     返回 BLOCKED 状态。

    返回：
        [{"check": str, "status": "PASS"|"FAIL"|"BLOCKED", "detail": str}]，
        共 7 个检查项：
        1. report_exists：sanitization_report 存在
        2. report_shape：report 结构合法（findings、summary）
        3. patches_exists：deterministic_patch_set 存在
        4. cleaned_exists：cleaned_text_revision 存在
        5. gate_passed：M2 Gate 通过
        6. no_deferred：无 deferred findings
        7. finding_coverage：§4.4 十三项各至少一条记录
    """
    results: list[dict] = []

    # --- 0. 宿主存在检查（核心：缺宿主 → BLOCKED）---
    if not ledger_dir.is_dir():
        results.append({
            "check": "ledger_dir_exists",
            "status": "BLOCKED",
            "detail": f"Ledger 目录不存在: {ledger_dir}",
        })
        return results

    # --- 1. report_exists ---
    report_path = ledger_dir / "sanitization_report.yaml"
    if not report_path.is_file():
        results.append({
            "check": "report_exists",
            "status": "FAIL",
            "detail": "sanitization_report 不存在",
        })
    else:
        results.append({
            "check": "report_exists",
            "status": "PASS",
            "detail": "sanitization_report 存在",
        })

    # --- 2. report_shape ---
    if any(r["check"] == "report_exists" and r["status"] == "PASS" for r in results):
        try:
            import yaml
            with open(report_path, encoding="utf-8") as f:
                report = yaml.safe_load(f)
            if isinstance(report, dict) and "findings" in report and "summary" in report:
                results.append({
                    "check": "report_shape",
                    "status": "PASS",
                    "detail": "report 结构合法（findings、summary）",
                })
            else:
                results.append({
                    "check": "report_shape",
                    "status": "FAIL",
                    "detail": "report 缺少 findings 或 summary 键",
                })
        except Exception as exc:
            results.append({
                "check": "report_shape",
                "status": "FAIL",
                "detail": f"report 读取错误: {exc}",
            })

    # --- 3. patches_exists ---
    patches_path = ledger_dir / "deterministic_patch_set.yaml"
    if any(r["check"] == "report_exists" and r["status"] == "PASS" for r in results):
        if patches_path.is_file():
            results.append({
                "check": "patches_exists",
                "status": "PASS",
                "detail": "deterministic_patch_set 存在",
            })
        else:
            results.append({
                "check": "patches_exists",
                "status": "FAIL",
                "detail": "deterministic_patch_set 不存在",
            })

    # --- 4. cleaned_exists ---
    cleaned_path = ledger_dir / "cleaned_text_revision"
    if any(r["check"] == "report_exists" and r["status"] == "PASS" for r in results):
        if cleaned_path.is_file():
            results.append({
                "check": "cleaned_exists",
                "status": "PASS",
                "detail": "cleaned_text_revision 存在",
            })
        else:
            results.append({
                "check": "cleaned_exists",
                "status": "FAIL",
                "detail": "cleaned_text_revision 不存在",
            })

    # --- 5. gate_passed 与 6. no_deferred ---
    if any(r["check"] == "report_exists" and r["status"] == "PASS" for r in results):
        try:
            import yaml
            with open(report_path, encoding="utf-8") as f:
                report = yaml.safe_load(f)
            summary = report.get("summary", {})
            deferred_count = summary.get("deferred_count", 0)

            # no_deferred：deferred_count 为 0
            if deferred_count == 0:
                results.append({
                    "check": "no_deferred",
                    "status": "PASS",
                    "detail": "无 deferred findings",
                })
            else:
                results.append({
                    "check": "no_deferred",
                    "status": "FAIL",
                    "detail": f"有 deferred findings：deferred_count={deferred_count}",
                })

            # gate_passed：no_deferred 通过 且 findings kind 合法
            from pipeline.digitization.gate import FINDING_KINDS, evaluate_m2_gate
            findings = report.get("findings", [])
            gate_result = evaluate_m2_gate(report)
            if gate_result.passed:
                results.append({
                    "check": "gate_passed",
                    "status": "PASS",
                    "detail": "M2 Gate 通过",
                })
            else:
                results.append({
                    "check": "gate_passed",
                    "status": "FAIL",
                    "detail": f"M2 Gate 未通过：{gate_result.failed_checks}",
                })
        except Exception as exc:
            results.append({
                "check": "gate_passed",
                "status": "FAIL",
                "detail": f"Gate 检查错误: {exc}",
            })

    # --- 7. finding_coverage：§4.4 十三项各至少一条记录 ---
    if any(r["check"] == "report_exists" and r["status"] == "PASS" for r in results):
        try:
            import yaml
            from pipeline.digitization import FINDING_KINDS as DKINDS
            with open(report_path, encoding="utf-8") as f:
                report = yaml.safe_load(f)
            findings = report.get("findings", [])
            kind_counts = {}
            for f in findings:
                k = f.get("kind", "")
                if k:
                    kind_counts[k] = kind_counts.get(k, 0) + 1
            all_covered = all(k in kind_counts for k in DKINDS)
            if all_covered:
                results.append({
                    "check": "finding_coverage",
                    "status": "PASS",
                    "detail": "§4.4 十三项各至少一条记录",
                })
            else:
                missing = [k for k in DKINDS if k not in kind_counts]
                results.append({
                    "check": "finding_coverage",
                    "status": "FAIL",
                    "detail": f"缺少 kind: {missing}",
                })
        except Exception as exc:
            results.append({
                "check": "finding_coverage",
                "status": "FAIL",
                "detail": f"finding_coverage 读取错误: {exc}",
            })

    return results
if __name__ == "__main__":
    import sys
    from pathlib import Path

    ledger_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    results = check_m2_sanitization(ledger_dir)
    for r in results:
        status = r["status"]
        check = r["check"]
        detail = r.get("detail", "")
        prefix = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOCKED"}.get(status, "INFO")
        print(f'{prefix} {check} {detail}')
    sys.exit(0)

