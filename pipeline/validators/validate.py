#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py —— 知识单元校验程序（M1 版）

用法：
    python3 validators/validate.py units/ku_qimen_000001     校验一个单元
    python3 validators/validate.py --all                      校验 units/ 下所有单元
    python3 validators/validate.py examples/negative/ku_qimen_bad001   也可校验样例

规矩：只报错，绝不修改任何文件。
输出：PASS，或每行一条错误（错误码 | 文件 | 原因）。
退出码：0 = 全部通过；1 = 有错误。
"""

import hashlib
import re
import sys
from pathlib import Path

import yaml

# 本文件位于 pipeline/validators/，pipeline 根目录是它的上一级
PIPELINE_ROOT = Path(__file__).resolve().parent.parent

STATUS_ENUM = {
    "source_verified", "machine_extracted", "cross_model_reviewed",
    "disputed", "needs_expert", "expert_verified", "deprecated",
}
RELATION_ENUM = {"supports", "qualifies", "opposes"}
SUPPORT_TYPE_ENUM = {"direct", "interpreted"}
RIGHTS_ENUM = {"public_domain", "licensed"}  # unknown 不在枚举内 = 阻断

ID_PATTERNS = {
    "unit_id": re.compile(r"^ku_[a-z]+_\d{6}$"),
    "assertion_id": re.compile(r"^as_[a-z]+_\d{6}$"),
    "proposition_id": re.compile(r"^pr_[a-z]+_\d{6}$"),
    "source_span_id": re.compile(r"^ss_[a-z0-9]+_ed\d{2}_p\d{4}_s\d{2,4}$"),  # s 允许 2–4 位：整页超 99 段的场景（如 ed02 全文 110 段一页）
    "source_id": re.compile(r"^src_[a-z0-9]+_ed\d{2}$"),
}


class Report:
    def __init__(self):
        self.errors = []

    def err(self, code, where, message):
        self.errors.append(f"{code} | {where} | {message}")

    def ok(self):
        return not self.errors


def load_yaml(path, report):
    """读 YAML。失败时报 SCH_001 并返回 None。"""
    if not path.exists():
        report.err("SCH_001", str(path), "文件不存在")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        report.err("SCH_001", str(path), f"YAML 无法解析: {e}")
        return None


def require(data, fields, where, report):
    """检查必填字段。返回 True 表示齐全。"""
    missing = [f for f in fields if f not in (data or {})]
    for f in missing:
        report.err("SCH_001", where, f"缺少必填字段: {f}")
    return not missing


def check_id(kind, value, where, report):
    pattern = ID_PATTERNS[kind]
    if not isinstance(value, str) or not pattern.match(value):
        report.err("ID_001", where, f"{kind} 格式错误: {value!r}（应符合 {pattern.pattern}）")
        return False
    return True


def find_manifest(source_id, report):
    """在 corpus/ 下按 source_id 找 manifest.yaml。"""
    for mf in (PIPELINE_ROOT / "corpus").rglob("manifest.yaml"):
        data = load_yaml(mf, report)
        if data and data.get("source_id") == source_id:
            return mf, data
    return None, None


def validate_manifest(mf_path, data, report):
    where = str(mf_path.relative_to(PIPELINE_ROOT))
    require(data, ["source_id", "work_title", "technique_id", "rights_status", "files"], where, report)
    check_id("source_id", data.get("source_id", ""), where, report)
    if data.get("rights_status") not in RIGHTS_ENUM:
        report.err("SCH_002", where, f"rights_status 非法或为 unknown（阻断）: {data.get('rights_status')!r}")
    transcripts = {}
    for f in data.get("files", []):
        fpath = mf_path.parent / f.get("path", "")
        fwhere = f"{where} -> {f.get('path')}"
        if not fpath.exists():
            report.err("SRC_001", fwhere, "来源文件缺失")
            continue
        actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
        if f.get("sha256") and f["sha256"] != actual:
            report.err("SRC_003", fwhere, f"哈希不匹配：登记 {f['sha256'][:12]}…，实际 {actual[:12]}…")
        if f.get("role") == "transcript":
            transcripts[f["path"]] = fpath.read_text(encoding="utf-8")
    return transcripts


def validate_unit(unit_dir):
    report = Report()
    unit_dir = Path(unit_dir).resolve()
    rel = lambda p: str(p.relative_to(PIPELINE_ROOT)) if PIPELINE_ROOT in p.parents or p == PIPELINE_ROOT else str(p)

    unit = load_yaml(unit_dir / "unit.yaml", report)
    prov = load_yaml(unit_dir / "provenance.yaml", report)
    asserts = load_yaml(unit_dir / "assertions.yaml", report)
    if unit is None:
        return report

    uw = rel(unit_dir / "unit.yaml")
    require(unit, ["unit_id", "technique_id", "source_id", "title", "span_ids", "status"], uw, report)
    check_id("unit_id", unit.get("unit_id", ""), uw, report)
    if unit.get("status") not in STATUS_ENUM:
        report.err("SCH_002", uw, f"status 非法枚举值: {unit.get('status')!r}")

    # 来源登记与转录文本
    transcripts = {}
    source_id = unit.get("source_id", "")
    if check_id("source_id", source_id, uw, report):
        mf_path, mf_data = find_manifest(source_id, report)
        if mf_path is None:
            report.err("REF_001", uw, f"corpus/ 里找不到 source_id 为 {source_id} 的 manifest.yaml")
        else:
            transcripts = validate_manifest(mf_path, mf_data, report)

    # 证据片段：编号格式＋逐字比对
    span_ids = set()
    pw = rel(unit_dir / "provenance.yaml")
    for span in (prov or {}).get("source_spans", []):
        sid = span.get("source_span_id", "")
        if not check_id("source_span_id", sid, pw, report):
            continue
        if sid in span_ids:
            report.err("ID_002", pw, f"source_span_id 重复: {sid}")
        span_ids.add(sid)
        quote = span.get("quote", "")
        if not quote:
            report.err("SCH_001", pw, f"{sid} 缺少 quote")
            continue
        if transcripts:
            joined = "\n".join(transcripts.values())
            if quote not in joined:
                report.err("TXT_001", pw, f"{sid} 的引用与原文不一致（逐字比对失败）: {quote!r}")

    # unit 声明的 span 必须存在
    for sid in unit.get("span_ids", []):
        if sid not in span_ids:
            report.err("REF_001", uw, f"unit 声明的 span 在 provenance.yaml 中不存在: {sid}")

    # 主张：格式＋证据绑定
    aw = rel(unit_dir / "assertions.yaml")
    seen_assert = set()
    for a in (asserts or {}).get("assertions", []):
        aid = a.get("assertion_id", "?")
        check_id("assertion_id", aid, aw, report)
        if aid in seen_assert:
            report.err("ID_002", aw, f"assertion_id 重复: {aid}")
        seen_assert.add(aid)
        require(a, ["proposition", "proposition_id", "relation", "evidence", "status"], f"{aw}:{aid}", report)
        check_id("proposition_id", a.get("proposition_id", ""), f"{aw}:{aid}", report)
        if a.get("relation") not in RELATION_ENUM:
            report.err("SCH_002", f"{aw}:{aid}", f"relation 非法: {a.get('relation')!r}")
        if a.get("status") not in STATUS_ENUM:
            report.err("SCH_002", f"{aw}:{aid}", f"status 非法: {a.get('status')!r}")
        evidence = a.get("evidence") or []
        if not evidence:
            report.err("SEM_001", f"{aw}:{aid}", "主张没有任何证据（禁止无出处主张）")
        for ev in evidence:
            esid = ev.get("source_span_id", "")
            if esid not in span_ids:
                report.err("REF_001", f"{aw}:{aid}", f"引用的证据片段不存在: {esid}")
            if ev.get("support_type") not in SUPPORT_TYPE_ENUM:
                report.err("SCH_002", f"{aw}:{aid}", f"support_type 非法: {ev.get('support_type')!r}")

    return report


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)

    if args[0] == "--all":
        targets = sorted(p.parent for p in (PIPELINE_ROOT / "units").rglob("unit.yaml"))
        if not targets:
            print("units/ 下没有任何单元")
            sys.exit(2)
    else:
        targets = [Path(a) for a in args]

    any_error = False
    for t in targets:
        report = validate_unit(t)
        name = t.name
        if report.ok():
            print(f"PASS  {name}")
        else:
            any_error = True
            print(f"FAIL  {name}  （{len(report.errors)} 条错误）")
            for e in report.errors:
                print(f"      {e}")
    sys.exit(1 if any_error else 0)


if __name__ == "__main__":
    main()
