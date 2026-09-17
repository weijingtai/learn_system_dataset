"""M1 电子文本入库验收（第 101 条：对宿主原文实跑 M1，再与独立期望比对）。

提供 check_m1_intake 函数，供 m1-intake.sh 调用。

宿主目录契约（README §7.2 / G7-RULINGS 第 95、101 条）：
- 原文：宿主内唯一的 ``*.md`` 文件（逐字节原样）
- 申报：``source_info.yaml``（M1 的来源申报输入，非流水线产物）
- 独立期望：``expected/m1_source_expected.yaml``（主 Agent 独立核验的事实，
  **不来自 M1 输出**）；``expected/SHA256SUMS`` 覆盖期望文件防篡改。

三态（第 96 条 D2 / 第 101 条）：
- 宿主/原文缺失 → BLOCKED
- 期望缺失或 SHA256SUMS 校验不符 → BLOCKED（期望不可信即不可判定，不是 FAIL）
- 齐备 → 在临时 Ledger（tempfile，用完即删）上实跑 M1，逐项比对 → PASS/FAIL

比对本函数只读取被测模块（pipeline.intake）的**产出**，期望一律来自宿主
``expected/`` 目录；不得以任何产出反向生成或修正期望（第 95 条反自证）。
"""

import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from pipeline.intake.errors import SourceAssetMissing
from pipeline.intake.source import read_source_files
from pipeline.intake.step import run_m1
from pipeline.ledger.service import LedgerService


def _verify_expected_checksums(expected_dir: Path, required_file: str = "m1_source_expected.yaml") -> str | None:
    """校验 expected/SHA256SUMS。返回 None 表示通过，否则返回 BLOCKED 文案。"""
    sums_path = expected_dir / "SHA256SUMS"
    if not sums_path.is_file():
        return f"期望校验文件缺失: expected/SHA256SUMS（{expected_dir}）"
    # 逐行重算 sha256（不信任外部 shasum 输出格式差异，仅用标准库）
    entries = []
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, name = line.partition("  ")
        if not digest or not name:
            return f"SHA256SUMS 格式不合法: {line!r}"
        entries.append((digest.lower(), name.strip()))
    if not entries:
        return "SHA256SUMS 为空"
    names = {name for _, name in entries}
    if required_file not in names:
        return f"期望文件被改动: SHA256SUMS 未包含必需文件 {required_file}"
    for digest, name in entries:
        target = expected_dir / name
        if not target.is_file():
            return f"期望文件被改动: SHA256SUMS 列出的 {name} 不存在"
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            return f"期望文件被改动: {name} sha256 与 SHA256SUMS 不符"
    return None


def _run_m1_on_temp_ledger(fixture_dir: Path) -> tuple[dict | None, list[dict]]:
    """对宿主原文实跑 M1。返回 (比对事实 dict, 附加结果列表)。

    任何阻塞/失败都折叠为 results 里的一条 BLOCKED/FAIL，不抛异常。
    """
    results: list[dict] = []
    info_path = fixture_dir / "source_info.yaml"
    if not info_path.is_file():
        return None, [{
            "check": "source_info_present",
            "status": "BLOCKED",
            "detail": f"来源申报缺失: source_info.yaml（{fixture_dir}）",
        }]
    try:
        source_info = yaml.safe_load(info_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [{
            "check": "source_info_present",
            "status": "BLOCKED",
            "detail": f"source_info.yaml 解析失败: {exc}",
        }]

    # 走 M1 的规范读文件路径（编码探测 + 双哈希，pipeline/intake/source.py read_source_files），
    # 不在验收器里另写一套字节处理——否则验收与实现会各算各的。
    # read_source_files 找不到 pages 列出的文件时抛 SourceAssetMissing → BLOCKED。
    try:
        files = read_source_files(str(fixture_dir), source_info["pages"])
    except SourceAssetMissing as exc:
        return None, [{
            "check": "source_present",
            "status": "BLOCKED",
            "detail": f"宿主原文缺失: {exc}",
        }]
    except Exception as exc:
        return None, [{
            "check": "source_present",
            "status": "FAIL",
            "detail": f"宿主原文读取失败: {exc}",
        }]

    # 临时 Ledger：tempfile 创建，用完即删（第 101 条）
    tmp = tempfile.mkdtemp(prefix="m1_accept_ledger_")
    try:
        service = LedgerService(tmp)
        try:
            m1 = run_m1(service, source_info, files, source_info["edition_part"]["artifact_id"])
            # 在临时 Ledger 删除前抓取比对所需事实（只读被测模块产出）
            facts: dict = {}
            if "manifest_revision_id" in m1:
                manifest = yaml.safe_load(
                    service.objects.get(
                        service.get_revision(m1["manifest_revision_id"])["sha256"]
                    ).decode("utf-8")
                )
                step_run = service.get_step_run(m1["step_run_id"])
                raw_revs = []
                for rid in m1.get("raw_text_revision_ids", []):
                    rev = service.get_revision(rid)
                    raw_revs.append({
                        "sha256": rev["sha256"],
                        "size_bytes": rev["size_bytes"],
                        "chars": len(service.objects.get(rev["sha256"]).decode("utf-8")),
                    })
                m1_facts = {
                    "manifest": manifest,
                    "step_status": step_run["status"] if step_run else None,
                    "raw_revs": raw_revs,
                }
            else:
                m1_facts = None
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if m1_facts is None:
        return None, [{
            "check": "m1_run",
            "status": "FAIL",
            "detail": f"M1 实跑未成功: {m1.get('error') or m1}",
        }]
    return m1_facts, results


def _compare_m1(facts: dict, expected: dict) -> list[dict]:
    """把实跑事实与独立期望逐项比对，每项一行 PASS/FAIL（第 101 条 M1 清单）。"""
    results: list[dict] = []
    manifest = facts["manifest"]
    asset = (manifest.get("source_assets") or [{}])[0]

    def _add(check: str, ok: bool, detail: str) -> None:
        results.append({"check": check, "status": "PASS" if ok else "FAIL", "detail": detail})

    # 1. source_assets[].sha256 == 期望 sha256（磁盘原始字节哈希）
    _add(
        "source_sha256",
        asset.get("sha256") == expected.get("sha256"),
        f"sha256 实跑 {asset.get('sha256')} vs 期望 {expected.get('sha256')}",
    )
    # 2. normalized_sha256
    _add(
        "source_normalized_sha256",
        asset.get("normalized_sha256") == expected.get("normalized_sha256"),
        f"normalized_sha256 实跑 {asset.get('normalized_sha256')} vs 期望 {expected.get('normalized_sha256')}",
    )
    # 3. original_encoding
    _add(
        "source_original_encoding",
        asset.get("original_encoding") == expected.get("original_encoding"),
        f"original_encoding 实跑 {asset.get('original_encoding')!r} vs 期望 {expected.get('original_encoding')!r}",
    )
    # 4. size
    _add(
        "source_size",
        asset.get("size") == expected.get("size_bytes"),
        f"size 实跑 {asset.get('size')} vs 期望 {expected.get('size_bytes')}",
    )
    # 5. raw_text 字符数
    chars = facts["raw_revs"][0]["chars"] if facts["raw_revs"] else None
    _add(
        "raw_text_chars",
        chars == expected.get("text_length_chars"),
        f"raw_text 字符数 实跑 {chars} vs 期望 {expected.get('text_length_chars')}",
    )
    # 6. repo_commit
    _add(
        "repo_commit",
        asset.get("repo_commit") == expected.get("repo_commit"),
        f"repo_commit 实跑 {asset.get('repo_commit')} vs 期望 {expected.get('repo_commit')}",
    )
    # 7. source_site
    _add(
        "source_site",
        asset.get("source_site") == expected.get("source_site"),
        f"source_site 实跑 {asset.get('source_site')} vs 期望 {expected.get('source_site')}",
    )
    # 8. rights_status（manifest 顶层）
    _add(
        "rights_status",
        manifest.get("rights_status") == expected.get("rights_status"),
        f"rights_status 实跑 {manifest.get('rights_status')!r} vs 期望 {expected.get('rights_status')!r}",
    )
    # 9. release_policy
    _add(
        "release_policy",
        manifest.get("release_policy") == expected.get("release_policy"),
        f"release_policy 实跑 {manifest.get('release_policy')} vs 期望 {expected.get('release_policy')}",
    )
    # 10. yaml_metadata 非空
    _add(
        "yaml_metadata_present",
        bool(asset.get("yaml_metadata")),
        "source_assets[0].yaml_metadata 应非空",
    )
    # 11. StepRun 终态 succeeded
    _add(
        "m1_step_run_succeeded",
        facts["step_status"] == "succeeded",
        f"M1 StepRun 终态实跑 {facts['step_status']!r} vs 期望 succeeded",
    )
    return results


def check_m1_intake(fixture_dir: Path, fixture_path: Path | None = None) -> list[dict]:
    """对宿主原文实跑 M1，并与独立期望逐项比对。

    参数：
        fixture_dir：验收宿主目录（含原文、source_info.yaml、expected/）
        fixture_path：兼容旧签名的可选参数（忽略）

    返回：
        [{"check": str, "status": "PASS"|"FAIL"|"BLOCKED", "detail": str}]
    """
    results: list[dict] = []
    fixture_dir = Path(fixture_dir)

    # --- 状态一：宿主或原文缺失 → BLOCKED ---
    if not fixture_dir.is_dir():
        return [{
            "check": "host_exists",
            "status": "BLOCKED",
            "detail": f"电子文本验收宿主不存在: {fixture_dir}",
        }]

    expected_dir = fixture_dir / "expected"
    expected_file = expected_dir / "m1_source_expected.yaml"
    if not expected_file.is_file():
        results.append({
            "check": "expected_present",
            "status": "BLOCKED",
            "detail": f"M1 独立期望缺失: {expected_file}",
        })
        return results

    # --- SHA256SUMS 校验：期望不可信即不可判定 → BLOCKED（不是 FAIL）---
    sums_error = _verify_expected_checksums(expected_dir)
    if sums_error is not None:
        results.append({
            "check": "expected_checksums",
            "status": "BLOCKED",
            "detail": sums_error,
        })
        return results

    try:
        expected = yaml.safe_load(expected_file.read_text(encoding="utf-8"))
    except Exception as exc:
        results.append({
            "check": "expected_parse",
            "status": "BLOCKED",
            "detail": f"m1_source_expected.yaml 解析失败: {exc}",
        })
        return results

    # --- 实跑 M1（临时 Ledger）---
    facts, run_results = _run_m1_on_temp_ledger(fixture_dir)
    results.extend(run_results)
    if facts is None:
        return results

    # --- 逐项比对（期望 = m1_source_expected.yaml；产出 = 实跑）---
    results.extend(_compare_m1(facts, expected))
    return results


if __name__ == "__main__":
    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out = check_m1_intake(fixture)
    for r in out:
        print(f'{r["status"]} {r["check"]} {r.get("detail", "")}')
    sys.exit(0)
