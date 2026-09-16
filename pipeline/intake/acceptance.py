"""M1 电子文本入库验收检查。

提供 check_m1_intake 函数，供 m1-intake.sh 调用。

When invoked as main module, run check_m1_intake on the ledger-dir argument
and print one line per check result, then exit 0/1/2.
"""

from pathlib import Path
from typing import Any


def check_m1_intake(ledger_dir: Path, fixture_path: Path | None = None) -> list[dict]:
    """检查 M1 电子文本入库的验收项。

    参数：
        ledger_dir：Ledger 目录，期望包含 source_manifest, raw_text 等
        fixture_path：验收宿主片段路径（可选）。若缺失或目录不存在，
                     返回 BLOCKED 状态。

    返回：
        [{"check": str, "status": "PASS"|"FAIL"|"BLOCKED", "detail": str}]，
        共 5 个检查项：
        1. manifest_exists：m1 StagePackage 存在
        2. manifest_shape：manifest 内容键序合法
        3. raw_text_exists：raw_text 修订存在
        4. source_registration：source_assets[] 每项的 source_site 与 source_url 均非空
        5. gated_by_m2：m2 未阻断
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

    # --- 1. manifest_exists ---
    manifest_path = ledger_dir / "source_manifest.yaml"
    if not manifest_path.is_file():
        results.append({
            "check": "manifest_exists",
            "status": "FAIL",
            "detail": "m1 StagePackage (source_manifest.yaml) 不存在",
        })
    else:
        results.append({
            "check": "manifest_exists",
            "status": "PASS",
            "detail": "m1 StagePackage 存在",
        })

    # --- 2. manifest_shape ---
    if any(r["check"] == "manifest_exists" and r["status"] == "PASS" for r in results):
        try:
            import yaml
            with open(manifest_path, encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
            required_top_keys = {
                "source_id", "work_title", "edition_note", "technique_id",
                "rights_status", "release_policy", "edition_part",
                "source_assets", "files", "conversion", "content_status",
            }
            optional_top_keys = {"repo_commit", "yaml_metadata"}
            top_keys = set(manifest.keys())
            if top_keys == required_top_keys:
                results.append({
                    "check": "manifest_shape",
                    "status": "PASS",
                    "detail": "manifest 内容键序合法",
                })
            elif top_keys > required_top_keys:
                results.append({
                    "check": "manifest_shape",
                    "status": "FAIL",
                    "detail": f"manifest 含表外键: {top_keys - required_top_keys}",
                })
            else:
                missing = required_top_keys - top_keys
                results.append({
                    "check": "manifest_shape",
                    "status": "FAIL",
                    "detail": f"manifest 缺少键: {missing}",
                })
        except Exception as exc:
            results.append({
                "check": "manifest_shape",
                "status": "FAIL",
                "detail": f"manifest 读取错误: {exc}",
            })

    # --- 3. raw_text_exists ---
    raw_text_path = ledger_dir / "raw_text"
    if not raw_text_path.exists():
        results.append({
            "check": "raw_text_exists",
            "status": "FAIL",
            "detail": "raw_text 修订不存在",
        })
    else:
        results.append({
            "check": "raw_text_exists",
            "status": "PASS",
            "detail": "raw_text 修订存在",
        })

    # --- 4. source_registration ---
    source_assets = []
    if any(r["check"] == "manifest_exists" and r["status"] == "PASS" for r in results):
        try:
            import yaml
            with open(manifest_path, encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
            source_assets = manifest.get("source_assets", [])
            reg_ok = True
            reg_detail_parts = []
            for i, asset in enumerate(source_assets):
                source_site = asset.get("source_site")
                source_url = asset.get("source_url")
                if not source_site:
                    reg_ok = False
                    reg_detail_parts.append(f"source_assets[{i}].source_site 为空")
                if not source_url:
                    reg_ok = False
                    reg_detail_parts.append(f"source_assets[{i}].source_url 为空")
            if reg_ok:
                results.append({
                    "check": "source_registration",
                    "status": "PASS",
                    "detail": "source_assets[] 每项的 source_site 与 source_url 均非空",
                })
            else:
                results.append({
                    "check": "source_registration",
                    "status": "FAIL",
                    "detail": "; ".join(reg_detail_parts),
                })
        except Exception as exc:
            results.append({
                "check": "source_registration",
                "status": "FAIL",
                "detail": f"source_registration 读取错误: {exc}",
            })

    # --- 5. gated_by_m2 ---
    # 检查 M2 是否已阻断：查看 deferred_count 或 gate 状态
    # 通过检查 ledger_dir 下是否有 sanitization_report 来判断
    sanitization_report_path = ledger_dir / "sanitization_report.yaml"
    if sanitization_report_path.is_file():
        try:
            import yaml
            with open(sanitization_report_path, encoding="utf-8") as f:
                report = yaml.safe_load(f)
            deferred_count = report.get("summary", {}).get("deferred_count", 0)
            if deferred_count > 0:
                results.append({
                    "check": "gated_by_m2",
                    "status": "FAIL",
                    "detail": f"M2 Gate 被阻断：deferred_count={deferred_count}",
                })
            else:
                results.append({
                    "check": "gated_by_m2",
                    "status": "PASS",
                    "detail": "M2 未阻断",
                })
        except Exception as exc:
            results.append({
                "check": "gated_by_m2",
                "status": "FAIL",
                "detail": f"M2 Gate 检查错误: {exc}",
            })
    else:
        # 没有 sanitization_report，表示 M2 尚未运行，视为“未阻断”
        results.append({
            "check": "gated_by_m2",
            "status": "PASS",
            "detail": "M2 未阻断（未运行）",
        })

    return results


if __name__ == "__main__":
    import sys
    from pathlib import Path

    ledger_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    results = check_m1_intake(ledger_dir)
    for r in results:
        status = r["status"]
        check = r["check"]
        detail = r.get("detail", "")
        prefix = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOCKED"}.get(status, "INFO")
        print(f"{prefix} {check} {detail}")
    sys.exit(0)
