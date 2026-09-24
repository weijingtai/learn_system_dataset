"""M2 电子文本清洗验收（第 101 条：对宿主原文实跑 M1→M2，再与独立金标比对）。

提供 check_m2_sanitization 函数，供 m2-sanitization.sh 调用。

宿主目录契约（README §7.2 / G7-RULINGS 第 95、98、101 条）：
- 原文 + source_info.yaml（同 M1 宿主）
- 独立金标：``expected/golden_findings.yaml``（不读、不运行 pipeline/** 代码的
  独立分析 Agent 产出，原样不改）；``expected/SHA256SUMS`` 覆盖期望文件防篡改。

三态（第 96 条 D2 / 第 101 条）：
- 宿主/原文缺失 → BLOCKED
- 金标缺失或 SHA256SUMS 校验不符 → BLOCKED（期望不可信即不可判定，不是 FAIL）
- 齐备 → 临时 Ledger（tempfile，用完即删）实跑 M1→M2，逐项比对 → PASS/FAIL

比对口径（第 98/99/101 条）：
- StepRun 终态 succeeded、Gate passed、deferred_count 与金标实测一致；
- 12 类发现逐类各一行：``escape_residue`` 比较**字符偏移覆盖集合**，其余 11 类
  比较 ``(raw_start, raw_end)`` 集合；
- 第 98 条①范围规则：金标中落在 YAML 头区间内的条目，除「YAML 头与正文分离」
  那条 ``escape_residue`` 外不计入比对。YAML 头区间由**本模块自己的正则**从原文
  识别（``\\A---\\n … \\n---\\n``），**不得**调用 pipeline.digitization 的函数去算
  （第 95 条反自证；``test_compare_does_not_import_digitization_for_header_range``
  守护这一点）；
- 每条 M2 发现须满足 ``raw[raw_start:raw_end] == raw_excerpt``；
- 本模块不得以任何方式读取 M2 输出去生成或修正期望。
"""

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from pipeline.digitization import FINDING_KINDS
from pipeline.digitization.step import run_m2
from pipeline.intake.errors import SourceAssetMissing
from pipeline.intake.source import read_source_files
from pipeline.intake.step import run_m1
from pipeline.ledger.service import LedgerService

# 第 98 条③口径：该类逐字符登记，比字符偏移覆盖集合而非逐条位置
_COVERAGE_KIND = "escape_residue"

# 比对器自己的 YAML front matter 识别（第 101 条：不得调用被测模块计算）。
# 只认「文件开头的围栏」：\A---\n … \n---\n（含尾换行）。
_YAML_FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# 第 98 条①：头内金标条目里豁免的那一条，其依据必须含「分离」字样
_SEPARATION_MARK = "分离"


def _verify_expected_checksums(expected_dir: Path, required_file: str = "golden_findings.yaml") -> str | None:
    """校验 expected/SHA256SUMS。返回 None 表示通过，否则返回 BLOCKED 文案。"""
    sums_path = expected_dir / "SHA256SUMS"
    if not sums_path.is_file():
        return f"期望校验文件缺失: expected/SHA256SUMS（{expected_dir}）"
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


def detect_yaml_front_matter_end(text: str) -> int:
    """从原文识别 YAML front matter 区间（[0, end)），比对器自有实现。

    独立函数便于测试断言本模块未从 pipeline.digitization 导入头区间计算。
    """
    m = _YAML_FRONT_MATTER_RE.match(text)
    return m.end() if m else 0


def _run_m1m2_on_temp_ledger(fixture_dir: Path) -> tuple[dict | None, list[dict]]:
    """对宿主原文实跑 M1→M2，返回 (比对事实, results)。

    临时 Ledger 用完即删；删除前抓取全部比对所需事实（只读被测模块产出）。
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

    tmp = tempfile.mkdtemp(prefix="m2_accept_ledger_")
    try:
        service = LedgerService(tmp)
        try:
            m1 = run_m1(service, source_info, files, source_info["edition_part"]["artifact_id"])
            if "error" in m1 or "raw_text_revision_ids" not in m1:
                return None, [{
                    "check": "m1_run",
                    "status": "FAIL",
                    "detail": f"M1 实跑未成功（M2 前置）: {m1.get('error') or m1}",
                }]
            raw_rev_id = m1["raw_text_revision_ids"][0]
            m2 = run_m2(
                service,
                raw_rev_id,
                source_info,
                source_info["edition_part"]["artifact_id"],
            )

            # 在临时 Ledger 删除前抓取全部比对事实（只读产出，不生成期望）
            facts: dict | None = None
            if "report_revision_id" in m2:
                raw_rev = service.get_revision(raw_rev_id)
                raw_text = service.read_object(raw_rev["sha256"]).decode("utf-8")
                report = json.loads(
                    service.read_object(
                        service.get_revision(m2["report_revision_id"])["sha256"]
                    ).decode("utf-8")
                )
                gate = m2.get("gate_result")
                step_run = service.get_step_run(m2["step_run_id"])
                facts = {
                    "raw_text": raw_text,
                    "report_findings": report.get("findings", []),
                    "deferred_count": report.get("summary", {}).get("deferred_count"),
                    "gate_passed": bool(getattr(gate, "passed", False)) if gate else False,
                    "step_status": step_run["status"] if step_run else None,
                }
            else:
                gate = m2.get("gate_result")
                return None, [{
                    "check": "m2_run",
                    "status": "FAIL",
                    "detail": (
                        f"M2 实跑未成功: gate_failed={getattr(gate, 'failed_checks', None)}"
                        f" error={m2.get('error')}"
                    ),
                }]
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return facts, results


def _compare_m2(facts: dict, golden: dict) -> list[dict]:
    """把 M2 实跑事实与独立金标逐项比对（第 98/99/101 条口径），每行一项。"""
    results: list[dict] = []
    raw_text: str = facts["raw_text"]
    m_findings: list[dict] = facts["report_findings"]
    g_findings: list[dict] = golden.get("findings", [])

    def _add(check: str, ok: bool, detail: str) -> None:
        results.append({"check": check, "status": "PASS" if ok else "FAIL", "detail": detail})

    # --- 1. StepRun 终态与 Gate ---
    _add(
        "m2_step_run_succeeded",
        facts["step_status"] == "succeeded",
        f"M2 StepRun 终态实跑 {facts['step_status']!r} vs 期望 succeeded",
    )
    _add(
        "m2_gate_passed",
        facts["gate_passed"] is True,
        "M2 Gate 应通过",
    )

    # --- 2. YAML 头区间：比对器自有识别（第 95/101 条，不调用被测模块）---
    head_end = detect_yaml_front_matter_end(raw_text)

    # 第 98 条①范围规则：金标中头内条目除「YAML 头与正文分离」外不计入比对
    kept_golden = [
        f for f in g_findings
        if not (f["raw_end"] <= head_end and _SEPARATION_MARK not in f.get("basis", ""))
    ]
    excluded = len(g_findings) - len(kept_golden)

    # --- 3. 12 类逐类比对（oc-j4b.txt 第 3 节：12 类逐类各一行）---
    for kind in FINDING_KINDS:
        if kind == _COVERAGE_KIND:
            # 字符偏移覆盖集合（第 98 条③：逐字符登记口径）
            g_set: set[int] = set()
            for f in kept_golden:
                if f["kind"] == kind:
                    g_set.update(range(f["raw_start"], f["raw_end"]))
            m_set: set[int] = set()
            for f in m_findings:
                if f["kind"] == kind:
                    m_set.update(range(f["raw_start"], f["raw_end"]))
            _add(
                f"finding_kind_{kind}",
                g_set == m_set,
                f"字符偏移覆盖集合 金标 {len(g_set)} 偏移 vs 实跑 {len(m_set)} 偏移"
                + ("" if g_set == m_set else f"；差异样例 gold-only={sorted(g_set - m_set)[:5]} m2-only={sorted(m_set - g_set)[:5]}"),
            )
        else:
            # (raw_start, raw_end) 集合
            g_set = {(f["raw_start"], f["raw_end"]) for f in kept_golden if f["kind"] == kind}
            m_set = {(f["raw_start"], f["raw_end"]) for f in m_findings if f["kind"] == kind}
            _add(
                f"finding_kind_{kind}",
                g_set == m_set,
                f"(raw_start,raw_end) 集合 金标 {sorted(g_set)[:3]}{'…' if len(g_set) > 3 else ''}"
                f" vs 实跑 {sorted(m_set)[:3]}{'…' if len(m_set) > 3 else ''}"
                + ("" if g_set == m_set else f"；gold-only {len(g_set - m_set)} 处、m2-only {len(m_set - g_set)} 处"),
            )

    # --- 4. deferred_count 与金标实测一致 ---
    # 金标侧口径：missing 类终态恒 deferred（README §4.4）；
    # 第 98 条实测金标 70 条无 missing，M2 deferred_count=0，两侧一致。
    g_deferred = facts_deferred_expected(kept_golden)
    _add(
        "deferred_count",
        facts["deferred_count"] == g_deferred,
        f"deferred_count 实跑 {facts['deferred_count']} vs 金标实测 {g_deferred}",
    )

    # --- 5. 每条 M2 发现 raw[raw_start:raw_end] == raw_excerpt ---
    bad = [
        f for f in m_findings
        if raw_text[f["raw_start"]:f["raw_end"]] != f.get("raw_excerpt")
    ]
    _add(
        "finding_excerpt_consistent",
        not bad,
        f"{len(bad)} 条发现的摘录与原文切片不符" + (f": {[(f['kind'], f['raw_start']) for f in bad[:3]]}" if bad else ""),
    )

    # --- 范围规则的可见化：排除了几条头内金标条目（含那条 watermark）---
    results.append({
        "check": "yaml_header_scope_rule",
        "status": "PASS",
        "detail": f"金标头内条目按第 98 条①排除 {excluded} 条（不计入比对）",
    })
    return results


def facts_deferred_expected(kept_golden: list[dict]) -> int:
    """金标侧 deferred 计数：missing 类终态恒 deferred（README §4.4）。

    第 98 条实测：金标 70 条无 missing 类，M2 deferred_count=0，两侧一致。
    """
    return sum(1 for f in kept_golden if f.get("kind") == "missing")


def check_m2_sanitization(fixture_dir: Path, fixture_path: Path | None = None) -> list[dict]:
    """对宿主原文实跑 M1→M2，并与独立金标逐项比对。

    参数：
        fixture_dir：验收宿主目录（含原文、source_info.yaml、expected/）
        fixture_path：兼容旧签名的可选参数（忽略）

    返回：
        [{"check": str, "status": "PASS"|"FAIL"|"BLOCKED", "detail": str}]
    """
    fixture_dir = Path(fixture_dir)

    # --- 状态一：宿主缺失 → BLOCKED ---
    if not fixture_dir.is_dir():
        return [{
            "check": "host_exists",
            "status": "BLOCKED",
            "detail": f"电子文本验收宿主不存在: {fixture_dir}",
        }]

    expected_dir = fixture_dir / "expected"
    golden_file = expected_dir / "golden_findings.yaml"
    if not golden_file.is_file():
        return [{
            "check": "golden_present",
            "status": "BLOCKED",
            "detail": f"M2 独立金标缺失: {golden_file}",
        }]

    # --- SHA256SUMS 校验：期望不可信即不可判定 → BLOCKED（不是 FAIL）---
    sums_error = _verify_expected_checksums(expected_dir)
    if sums_error is not None:
        return [{
            "check": "golden_checksums",
            "status": "BLOCKED",
            "detail": sums_error,
        }]

    try:
        golden = yaml.safe_load(golden_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return [{
            "check": "golden_parse",
            "status": "BLOCKED",
            "detail": f"golden_findings.yaml 解析失败: {exc}",
        }]

    # --- 实跑 M1→M2（临时 Ledger）---
    facts, results = _run_m1m2_on_temp_ledger(fixture_dir)
    results = list(results)
    if facts is None:
        return results

    # --- 逐项比对（期望 = 金标；产出 = 实跑）---
    results.extend(_compare_m2(facts, golden))
    return results


if __name__ == "__main__":
    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out = check_m2_sanitization(fixture)
    for r in out:
        print(f'{r["status"]} {r["check"]} {r.get("detail", "")}')
    sys.exit(0)
