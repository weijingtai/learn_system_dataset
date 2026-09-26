"""M8 验收：span_identity 与 publication 两组判定（§19.0 判据）。

独立实现：只读 Ledger 与 ``--fixture`` 金标，自行重算；**不 import** ``packs`` /
``gate``，也不读取 ``run_m8`` 返回的 gate 报告。宿主经 ``--fixture`` 与
``FIXTURE_ASSET_ROOT`` 读取（D2）。

用法::

    python -m pipeline.dataset_compiler.acceptance --fixture <dir> [--check span_identity|publication] [--keep]

路线（D-W8-16 三）按 ``--fixture`` 目录内 ``spans.yaml`` 的 ``evidence_level`` 分派：
``glyphbox_level`` 走 ``ingest(m1,m2)`` → ``run_m3`` → ``register_source_assets``（逐字不变）；
``offset_level`` 走 ``run_m1`` → ``run_m2`` → ``run_m3_text``（无页图）。
不适用当前证据级别的子判据输出 ``NOT_APPLICABLE``（不计入 pass/fail/blocked，
不得冒充 pass；裁定 107 Q-M8-08）。

退出码：0 全 PASS；1 任一 FAIL 或准备/运行抛异常；2 无 FAIL 有 BLOCKED；3 宿主缺失。
"""

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.corpus_compiler.step_offset import run_m3_text
from pipeline.dataset_compiler.shim.m1_shim_source_assets import register_source_assets
from pipeline.dataset_compiler.step import run_m8
from pipeline.digitization.step import run_m2
from pipeline.intake.source import read_source_files
from pipeline.intake.step import run_m1
from pipeline.ledger import fixture_ingest
from pipeline.ledger.service import LedgerReader, LedgerService

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
DEFAULT_ASSET_ROOT = REPO_ROOT / "ocr" / "data_work" / "sanche_pages"

# 路线枚举（D-W8-16 三）：判定权威 = 夹具目录内 spans.yaml 的 evidence_level 取值。
ROUTE_GLYPHBOX = "glyphbox_level"
ROUTE_OFFSET = "offset_level"
_ROUTES = (ROUTE_GLYPHBOX, ROUTE_OFFSET)

# 裁定 107 Q-M8-08 口径：不适用当前证据级别的子判据输出 not_applicable，不得冒充 pass。
NOT_APPLICABLE = "NOT_APPLICABLE"
_OFFSET_NOT_APPLICABLE_DETAIL = "不适用证据级别 offset_level（依赖页/字框）"

# offset 档依赖页/字框、在电子文本路线**不存在对应事实**的子判据。
_OFFSET_NA_SPAN_CHECKS = (
    "legacy_collision_exposed",
    "span_page_binding",
    "anchor_to_page_image",
    "glyph_closure",
    "reverse_index",
)
_OFFSET_NA_PUBLICATION_CHECKS = ("coordinate_frame",)
# publication 的 evidence_chain_closure 内依赖页/字框的子步（T04 Q9，同 Q-M8-08 口径）：offset 档
# 逐项标 NOT_APPLICABLE 并写进该判据的说明，不静默跳过、不按通过计。
_OFFSET_NA_CLOSURE_STEPS = ("span_page_binding", "glyph_anchor_closure")
# text_offsets 子步里依赖「行」的字段（T20，用户 2026-09-26 裁决 (a)）：电子文本没有行，offset 档不比，
# 逐项披露 NOT_APPLICABLE；offset/text/quote_sha256/content_status 照比。
_OFFSET_NA_TEXT_OFFSET_FIELDS = ("line_index",)
# watermark_disclosure 里依赖「页面上的框」的字段（T21，用户 2026-09-26 裁决）：电子文本没有框可高亮，
# offset 档不据 highlight_level 推 glyph_text_mismatch，披露 NOT_APPLICABLE；水印与其余已知缺陷照判。
_OFFSET_NA_WATERMARK_FIELDS = ("highlight_level",)

# TODO.md T02（2026-09-23）：以下各判据一律**看 M8 实际产出**再下结论，不许无条件输出 BLOCKED。
# 子包没产出 → BLOCKED，理由写实测事实；子包产出了但内容校验尚未实现 → FAIL（防止接上函数就自动变绿）。
_CONTENT_CHECK_PENDING = "已产出 %s，但本判据的内容校验尚未实现（TODO.md %s）——不许按已通过处理"

_SUBPACK_TYPES = (
    "source_asset_pack",
    "evidence_map_pack",
    "release_manifest",
    "publication_package",
)
_SPAN_TAIL_RE = re.compile(r"_p([0-9]{4})_s([0-9]{2})$")


# ------------------------------------------------------------------ 基础读取
def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(obj):
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _read_revision_bytes(service, revision_id):
    revision = service.get_revision(revision_id)
    return service.read_object(revision["sha256"])


def _read_revision_json(service, revision_id):
    """读取修订内容对象：优先 JSON，回退 YAML（corpus_spans 为 YAML）。"""
    raw = _read_revision_bytes(service, revision_id).decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError:
        return yaml.safe_load(raw)


# ------------------------------------------------------------------ 路线与准备
def _detect_route(fixture_dir):
    """路线判定权威 = 夹具目录内 ``spans.yaml`` 的 ``evidence_level``（D-W8-16 三）。

    不许按目录名猜、不许新增环境变量指定路线。缺 ``spans.yaml`` 或取值不在闭集时
    返回 ``None``，由调用方按宿主缺失 BLOCKED。
    """
    spans_path = Path(fixture_dir) / "spans.yaml"
    if not spans_path.is_file():
        return None
    try:
        document = yaml.safe_load(spans_path.read_bytes())
    except Exception:  # noqa: BLE001 - 判定依据读不出即不可判定
        return None
    if not isinstance(document, dict):
        return None
    level = document.get("evidence_level")
    return level if level in _ROUTES else None


def _prepare_ledger(service, fixture_dir, asset_root, route):
    """按路线装配宿主，返回 edition_part_id（D-W8-16 一/三）。

    glyphbox 档：``ingest(m1,m2)`` → ``run_m3`` → ``register_source_assets``（逐字不变）。
    offset 档：M1 入库 → M2 清洗 → ``run_m3_text``；文本 SourceAsset 由 M1 登记
    （``source_manifest`` + ``raw_text``），**不**走 ``fixture_ingest``、**不**登记页图。
    """
    if route == ROUTE_OFFSET:
        return _prepare_ledger_offset(service, fixture_dir)
    summary = fixture_ingest.ingest(fixture_dir, service, stages=("m1", "m2"))
    edition_part_id = summary["edition_part_id"]
    run_m3(service, edition_part_id)
    register_source_assets(service, edition_part_id, asset_root)
    return edition_part_id


def _prepare_ledger_offset(service, fixture_dir):
    """电子文本路线：``run_m1`` → ``run_m2`` → ``run_m3_text``（ACT 16 三）。"""
    source_info = yaml.safe_load((Path(fixture_dir) / "source_info.yaml").read_bytes())
    edition_part_id = source_info["edition_part"]["artifact_id"]
    files = read_source_files(str(fixture_dir), source_info["pages"])
    m1 = run_m1(service, source_info, files, edition_part_id)
    if m1.get("error"):
        raise RuntimeError("M1 入库失败: %s" % m1["error"])
    m2 = run_m2(service, m1["raw_text_revision_ids"][0], source_info, edition_part_id)
    if m2.get("error"):
        raise RuntimeError("M2 清洗失败: %s" % m2["error"])
    run_m3_text(service, edition_part_id)
    return edition_part_id


def _find_m8_package(service, edition_part_id):
    """返回 (m8_step_run_id, package_revision_id, package)；缺失部分为 None。"""
    step_run_id = None
    for checkpoint in service.list_checkpoints(edition_part_id, "m8"):
        step_run_id = checkpoint["content"]["step_run_id"]
    if step_run_id is None:
        return None, None, None
    rows = service.list_step_run_revisions(
        step_run_id, artifact_type="stage_package", status="sealed"
    )
    if not rows:
        return step_run_id, None, None
    package_revision_id = rows[0]["artifact_revision_id"]
    package = _read_revision_json(service, package_revision_id)
    return step_run_id, package_revision_id, package


def _discover_inputs(service, edition_part_id, package):
    """从 m8 包 input_artifacts 与 m1 Checkpoint 反查 spans/页/页图修订。"""
    spans_revision_id = None
    manifest_revision_id = None
    page_revision_ids = {}
    for reference in package["manifest"]["input_artifacts"]:
        artifact_type = reference["artifact_type"]
        revision_id = reference["artifact_revision_id"]
        if artifact_type == "corpus_spans":
            spans_revision_id = revision_id
        elif artifact_type == "source_manifest":
            manifest_revision_id = revision_id
        elif artifact_type == "ocr_page":
            page_revision_ids[_read_revision_json(service, revision_id)["page"]] = revision_id
    asset_revision_ids = {}
    for checkpoint in service.list_checkpoints(edition_part_id, "m1"):
        step_run = service.get_step_run(checkpoint["content"]["step_run_id"])
        if step_run is None or step_run["status"] != "succeeded":
            continue
        for task in checkpoint["content"].get("completed_tasks", []):
            if task["task_id"].startswith("source_asset_") and task["status"] == "succeeded":
                asset_revision_ids[task["task_id"][len("source_asset_"):]] = task[
                    "artifact_revision_id"
                ]
    return spans_revision_id, manifest_revision_id, page_revision_ids, asset_revision_ids


def _build_context(service, edition_part_id, fixture_dir, asset_root, route):
    step_run_id, package_revision_id, package = _find_m8_package(service, edition_part_id)
    manifest = yaml.safe_load((Path(fixture_dir) / "manifest.yaml").read_bytes())
    spans_golden = yaml.safe_load((Path(fixture_dir) / "spans.yaml").read_bytes())
    return {
        "service": service,
        "route": route,
        "edition_part_id": edition_part_id,
        "fixture_dir": Path(fixture_dir),
        "asset_root": Path(asset_root),
        "manifest": manifest,
        "spans_golden": spans_golden,
        "m3_gate_profile": _m3_gate_profile(service, edition_part_id),
        "m8_step_run_id": step_run_id,
        "package_revision_id": package_revision_id,
        "package": package,
    }


def _m3_gate_profile(service, edition_part_id):
    """从 m3 StagePackage 的 payload 读 gate_profile。"""
    step_run_id = None
    for checkpoint in service.list_checkpoints(edition_part_id, "m3"):
        step_run = service.get_step_run(checkpoint["content"]["step_run_id"])
        if step_run is not None and step_run["status"] == "succeeded":
            step_run_id = checkpoint["content"]["step_run_id"]
    if step_run_id is None:
        return None
    rows = service.list_step_run_revisions(
        step_run_id, artifact_type="stage_package", status="sealed"
    )
    if not rows:
        return None
    package = _read_revision_json(service, rows[0]["artifact_revision_id"])
    return (package.get("payload") or {}).get("gate_profile")


def _load_span_context(context):
    """载入 entries / spans_doc / page_docs / 资产修订等；无包返回 None。"""
    service = context["service"]
    package = context["package"]
    if package is None:
        return None
    publication = _read_revision_json(
        service, package["payload"]["publication_package_revision_id"]
    )
    evidence = _read_revision_json(service, publication["packs"]["evidence_map_pack"])
    spans_revision_id, _manifest, page_revision_ids, asset_revision_ids = _discover_inputs(
        service, context["edition_part_id"], package
    )
    spans_doc = _read_revision_json(service, spans_revision_id)
    page_docs = {
        page: _read_revision_json(service, revision_id)
        for page, revision_id in page_revision_ids.items()
    }
    return {
        "publication": publication,
        "evidence": evidence,
        "spans_doc": spans_doc,
        "page_docs": page_docs,
        "asset_revision_ids": asset_revision_ids,
        "page_revision_ids": page_revision_ids,
    }


def _load_span_context_or_none(context):
    """载入失败返回 (None, 详情)，供判定函数把异常转该项 FAIL。"""
    try:
        return _load_span_context(context), None
    except Exception as exc:  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


# ------------------------------------------------------------------ 判定：span_identity
def _check_span_key_unique(loaded, golden):
    entries = loaded["evidence"]["entries"]
    spans_doc = loaded["spans_doc"]
    keys = set(entries.keys())
    corpus_ids = {span["span_id"] for span in spans_doc["spans"]}
    golden_ids = {span["span_id"] for span in golden["spans"]}
    if keys != corpus_ids:
        return False, "entries 键 != corpus_spans span_id 集合"
    if keys != golden_ids:
        return False, "entries 键 != fixture spans.yaml 金标 span_id 集合"
    # 计数闸门取自上游事实、两档同一口径：entries 数 == spans_doc 表头 == 该夹具
    # 自己 spans.yaml 金标的 span_count。**数字一律不写进代码**（hardcoded 常量
    # 会把 OCR 夹具的片段数当成全局真值，电子文本档必然误判）。
    if not (len(entries) == spans_doc["span_count"] == golden["span_count"]):
        return False, "计数不一致: entries=%d span_count=%s golden_span_count=%s" % (
            len(entries),
            spans_doc["span_count"],
            golden["span_count"],
        )
    return True, "pack_keys=%d" % len(keys)


def _check_legacy_collision(loaded):
    entries = loaded["evidence"]["entries"]
    source_id = loaded["spans_doc"]["source_id"]
    groups = {}
    for span_id in entries:
        sequence = int(span_id.rsplit("_s", 1)[1])
        groups.setdefault((source_id, sequence), []).append(span_id)
    legacy_keys = len(groups)
    collision_groups = sum(1 for members in groups.values() if len(members) > 1)
    pack_keys = len(entries)
    detail = "legacy_keys=%d collision_groups=%d pack_keys=%d" % (
        legacy_keys,
        collision_groups,
        pack_keys,
    )
    if (legacy_keys, collision_groups, pack_keys) != (39, 4, 43):
        return False, detail
    return True, detail


def _check_span_page_binding(loaded):
    entries = loaded["evidence"]["entries"]
    by_id = {span["span_id"]: span for span in loaded["spans_doc"]["spans"]}
    page_order = loaded["page_order"]
    for span_id, entry in entries.items():
        match = _SPAN_TAIL_RE.search(span_id)
        if match is None:
            return False, "span_id 无法解析: %s" % span_id
        if int(match.group(1)) != int(entry["page"][5:]):
            return False, "页号段与 entry.page 不符: %s" % span_id
        if int(match.group(2)) != entry["line_index"] + 1:
            return False, "行序段与 line_index+1 不符: %s" % span_id
        if entry["page"] != by_id[span_id]["page"]:
            return False, "entry.page 与 spans_doc 不符: %s" % span_id
        if entry["page"] not in page_order:
            return False, "entry.page 不在清单页序: %s" % entry["page"]
    return True, "页号/行序绑定一致"


def _check_anchor_to_page_image(service, loaded, manifest, asset_root):
    entries = loaded["evidence"]["entries"]
    manifest_assets = {item["page"]: item for item in manifest["source_assets"]}
    for span_id, entry in entries.items():
        page = entry["page"]
        if page not in loaded["asset_revision_ids"]:
            return False, "页图未登记: %s" % page
        image_sha = _sha256_hex(
            _read_revision_bytes(service, loaded["asset_revision_ids"][page])
        )
        if entry["image_sha256"] != manifest_assets[page]["sha256"]:
            return False, "entry.image_sha256 与清单不符: %s" % span_id
        if image_sha != manifest_assets[page]["sha256"]:
            return False, "页图对象字节哈希与清单不符: %s" % page
    return True, "锚点图像哈希 == 清单 == 页图对象字节"


def _check_glyph_closure(loaded):
    entries = loaded["evidence"]["entries"]
    glyph_count = 0
    line_bbox_count = 0
    for span_id, entry in entries.items():
        doc = loaded["page_docs"][entry["page"]]
        line_id = entry["line_id"]
        recomputed = [
            {"char_index": index, "glyph_id": char["id"], "char": char["char"], "box": char["box"]}
            for index, char in enumerate(doc["chars"])
            if char["parent"] == line_id
        ]
        if entry["glyphs"] != recomputed:
            return False, "glyphs 与页 JSON 重算不符: %s" % span_id
        joined = "".join(glyph["char"] for glyph in recomputed)
        equal = joined == entry["text"]
        if entry["glyph_text_equal"] != equal:
            return False, "glyph_text_equal 与重算不符: %s" % span_id
        expected_level = "glyph" if equal else "line_bbox"
        if entry["highlight_level"] != expected_level:
            return False, "highlight_level 与重算不符: %s" % span_id
        if equal:
            glyph_count += 1
        else:
            line_bbox_count += 1
    if not (glyph_count == 41 and line_bbox_count == 2):
        return False, "glyph/line_bbox 计数不符: %d/%d" % (glyph_count, line_bbox_count)
    return True, "glyph=%d line_bbox=%d" % (glyph_count, line_bbox_count)


def _check_reverse_index(loaded, manifest):
    page_order = manifest["edition_part"]["pages"]
    page_index = loaded["evidence"]["page_index"]
    by_page = {}
    for span in loaded["spans_doc"]["spans"]:
        by_page.setdefault(span["page"], []).append(span["span_id"])
    if list(page_index.keys()) != page_order:
        return False, "page_index 键顺序与清单页序不符"
    for page in page_order:
        if page_index[page] != by_page.get(page, []):
            return False, "page_index[%s] 与 spans_doc 顺序不符" % page
    if page_index.get("page_002") != []:
        return False, "排除页 page_002 反向索引非空"
    if loaded["evidence"]["excluded_pages"] != {"page_002": "known_unrecognizable"}:
        return False, "excluded_pages 与金标不符"
    return True, "page_001=4 page_002=0 page_003=39"


# ------------------------------------------------------------------ 判定：publication
def _check_text_offsets(loaded, route):
    entries = loaded["evidence"]["entries"]
    by_id = {span["span_id"]: span for span in loaded["spans_doc"]["spans"]}
    content_status = loaded["spans_doc"]["content_status"]
    for span_id, entry in entries.items():
        span = by_id[span_id]
        if route == ROUTE_OFFSET:
            # 不适用的字段必须真的不在；出现了说明混进了页/行档数据，不做「有就比」
            for field in _OFFSET_NA_TEXT_OFFSET_FIELDS:
                if field in entry or field in span:
                    return False, "offset 档不应有 %s: %s" % (field, span_id)
            line_differs = False
        else:
            line_differs = entry["line_index"] != span["line_index"]
        if (
            entry["start_offset"] != span["start_offset"]
            or entry["end_offset"] != span["end_offset"]
            or line_differs
            or entry["text"] != span["text"]
        ):
            return False, "offset/text 与 spans_doc 不符: %s" % span_id
        if entry["quote_sha256"] != _sha256_hex(entry["text"].encode("utf-8")):
            return False, "quote_sha256 与 text 不符: %s" % span_id
        if entry["content_status"] != content_status:
            return False, "content_status 与 spans_doc 不符: %s" % span_id
    return True, "offset/quote/content_status 一致"


def _check_coordinate_frame(loaded, manifest):
    entries = loaded["evidence"]["entries"]
    manifest_assets = {item["page"]: item for item in manifest["source_assets"]}
    for span_id, entry in entries.items():
        doc = loaded["page_docs"][entry["page"]]
        frame = entry["frame"]
        if frame != {"width": doc["width"], "height": doc["height"]}:
            return False, "frame 与页 JSON 不符: %s" % span_id
        if (frame["width"], frame["height"]) != (
            manifest_assets[entry["page"]]["width"],
            manifest_assets[entry["page"]]["height"],
        ):
            return False, "frame 与清单不符: %s" % span_id
        for box in [entry["bbox"]] + [glyph["box"] for glyph in entry["glyphs"]]:
            if (
                box["x"] < 0
                or box["y"] < 0
                or box["x"] + box["w"] > frame["width"]
                or box["y"] + box["h"] > frame["height"]
            ):
                return False, "框越界: %s" % span_id
    return True, "frame 与页 JSON/清单同源，框均在框内"


def _check_release_manifest_hashes(service, loaded):
    evidence = loaded["evidence"]
    publication = loaded["publication"]
    release_manifest = _read_revision_json(
        service, loaded["release_manifest_revision_id"]
    )
    pack_bytes = {
        "evidence_map_pack": _read_revision_bytes(
            service, publication["packs"]["evidence_map_pack"]
        ),
        "source_asset_pack": _read_revision_bytes(
            service, publication["packs"]["source_asset_pack"]
        ),
    }
    pack_dicts = {
        "evidence_map_pack": evidence,
        "source_asset_pack": _read_revision_json(
            service, publication["packs"]["source_asset_pack"]
        ),
    }
    by_type = {item["pack_type"]: item for item in release_manifest["packs"]}
    if set(by_type) != set(pack_bytes):
        return False, "packs 的 pack_type 集合不符"
    for pack_type, data in pack_bytes.items():
        if by_type[pack_type]["sha256"] != _sha256_hex(data):
            return False, "%s sha256 不符" % pack_type
        if by_type[pack_type]["size"] != len(data):
            return False, "%s size 不符" % pack_type
        if json.loads(data.decode("utf-8")) != pack_dicts[pack_type]:
            return False, "%s 字节内容不符" % pack_type
    expected = _sha256_hex(
        _canonical_bytes(
            [[pack_type, by_type[pack_type]["sha256"]] for pack_type in sorted(by_type)]
        )
    )
    if release_manifest["canonical_hash"] != expected:
        return False, "canonical_hash 不符"
    return True, "子包哈希与 canonical_hash 均可重算"


def _check_input_reconciliation(service, context, loaded):
    release_manifest = _read_revision_json(
        service, loaded["release_manifest_revision_id"]
    )
    frozen = {
        (
            reference["artifact_revision_id"],
            reference["artifact_type"],
            _sha256_hex(_read_revision_bytes(service, reference["artifact_revision_id"])),
        )
        for reference in context["package"]["manifest"]["input_artifacts"]
    }
    given = {
        (item["artifact_revision_id"], item["artifact_type"], item["sha256"])
        for item in release_manifest["input_reconciliation"]
    }
    if frozen != given:
        return False, "input_reconciliation 与冻结输入不一致"
    return True, "input_reconciliation 与冻结输入一致"


def _check_consumption_level(service, loaded):
    release_manifest = _read_revision_json(
        service, loaded["release_manifest_revision_id"]
    )
    content_status = loaded["spans_doc"]["content_status"]
    expected_release = "release" if content_status == "expert_verified" else "dev"
    if release_manifest["consumption_level"] != "INTERNAL_DEMO":
        return False, "consumption_level 非 INTERNAL_DEMO"
    if release_manifest["isolation"] != "internal_only":
        return False, "isolation 非 internal_only"
    if release_manifest["authoritative"] is not False:
        return False, "authoritative 非 False"
    if release_manifest["completeness_claim"] != "partial":
        return False, "completeness_claim 非 partial"
    if release_manifest["source_release"] != expected_release:
        return False, "source_release 推导不符"
    return True, "INTERNAL_DEMO/internal_only/partial/dev"


def _check_watermark_disclosure(service, loaded, route):
    release_manifest = _read_revision_json(
        service, loaded["release_manifest_revision_id"]
    )
    entries = loaded["evidence"]["entries"]
    content_status = loaded["spans_doc"]["content_status"]
    if content_status.startswith("machine_"):
        for span_id, entry in entries.items():
            if entry["watermark"] is not True:
                return False, "entry.watermark 未置真: %s" % span_id
        if release_manifest["watermark"]["required"] is not True:
            return False, "watermark.required 未置真"
        if not release_manifest["watermark"]["text"]:
            return False, "watermark.text 为空"
    required = set()
    if loaded["evidence"]["excluded_pages"]:
        required.add("excluded_page")
    if route == ROUTE_OFFSET:
        # 不适用的字段必须真的不在；出现了说明混进了字框档数据，不做「有就看」
        for span_id, entry in entries.items():
            for field in _OFFSET_NA_WATERMARK_FIELDS:
                if field in entry:
                    return False, "offset 档不应有 %s: %s" % (field, span_id)
    elif any(entry["highlight_level"] == "line_bbox" for entry in entries.values()):
        required.add("glyph_text_mismatch")
    if loaded["evidence"]["knowledge_chain"] != "compiled":
        required.add("knowledge_chain_not_compiled")
    if content_status.startswith("machine_"):
        required.add("machine_content")
    rights_status = loaded["manifest"]["rights_status"]
    if isinstance(rights_status, str) and "unconfirmed" in rights_status:
        required.add("rights_unconfirmed")
    if loaded["m3_gate_profile"] == "structural_only":
        required.add("semantic_not_evaluated")
    given = {item["code"] for item in release_manifest["known_defects"]}
    missing = required - given
    if missing:
        return False, "known_defects 缺少: %s" % ",".join(sorted(missing))
    if route == ROUTE_OFFSET:
        return True, "水印与已知缺陷披露完整（%s：%s）" % (
            "、".join("%s=%s" % (field, NOT_APPLICABLE) for field in _OFFSET_NA_WATERMARK_FIELDS),
            "电子文本无页面字框，不据此推 glyph_text_mismatch",
        )
    return True, "水印与已知缺陷披露完整"


def _check_fail_closed_levels(context):
    """在另起的两份临时 Ledger 上证明 DEV_SEARCH / PUBLIC_RELEASE 准入失败且无子包。"""
    outcomes = []
    for level in ("DEV_SEARCH", "PUBLIC_RELEASE"):
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-fc-")
        service = LedgerService(Path(tmp) / "ledger")
        try:
            edition_part_id = _prepare_ledger(
                service, context["fixture_dir"], context["asset_root"], context["route"]
            )
            result = run_m8(service, edition_part_id, consumption_level=level)
            counts = {
                artifact_type: service.count_artifacts(artifact_type)
                for artifact_type in _SUBPACK_TYPES
            }
            ok = (
                result.get("status") == "failed"
                and result.get("failed_check") == "admission"
                and all(count == 0 for count in counts.values())
            )
        finally:
            service.close()
            shutil.rmtree(tmp, True)
        outcomes.append((level, ok))
    if not all(ok for _level, ok in outcomes):
        return False, "fail-closed 未达成: %s" % outcomes
    return True, "DEV_SEARCH/PUBLIC_RELEASE 均 admission 失败且无子包修订"


# ------------------------------------------------------------------ 产出事实（T02）
def _m8_output_facts(context):
    """读出 M8 这次**实际**产出了什么：发布包里的子包、knowledge_chain 状态、是否以 M7 Snapshot 为输入、evidence 里的 mentions。"""
    service = context["service"]
    package = context["package"]
    if package is None:
        return None
    payload = package.get("payload") or {}
    publication = _read_revision_json(service, payload["publication_package_revision_id"])
    packs = dict(publication.get("packs") or {})
    evidence = _read_revision_json(service, packs["evidence_map_pack"]) if "evidence_map_pack" in packs else {}
    input_refs = list((package.get("manifest") or {}).get("input_artifacts") or [])
    input_types = sorted({ref.get("artifact_type") for ref in input_refs} - {None})
    return {
        "packs": packs,
        "knowledge_chain": payload.get("knowledge_chain"),
        "input_types": input_types,
        "mentions": evidence.get("mentions"),
        # T04B：内容校验要回到 Ledger 独立读子包、冻结输入与发号表
        "service": service,
        "publication": publication,
        "input_refs": input_refs,
        "m8_step_run_id": context.get("m8_step_run_id"),
    }


def _check_mentions_mapping(facts):
    packs = sorted(facts["packs"])
    if facts["mentions"]:
        return ("mentions_mapping", "FAIL", _CONTENT_CHECK_PENDING % ("concept→span mentions", "T05a"))
    if "search_index_pack" in facts["packs"]:
        return ("mentions_mapping", "FAIL", _CONTENT_CHECK_PENDING % ("search_index_pack", "T05b"))
    return (
        "mentions_mapping",
        "BLOCKED",
        "实测 evidence_map_pack 无 mentions、发布包无 search_index_pack（发布包子包: %s）；"
        "M8 未产出 concept→span 映射与 SearchIndexPack（TODO.md T05a/T05b）" % packs,
    )


def _check_knowledge_chain(facts):
    state = facts["knowledge_chain"]
    packs = sorted(facts["packs"])
    has_pack = "knowledge_data_pack" in facts["packs"]
    if state == "compiled" and not has_pack:
        return ("knowledge_chain", "FAIL", "knowledge_chain=compiled，但发布包没有 knowledge_data_pack（子包: %s）" % packs)
    if has_pack:
        if state != "compiled":
            return (
                "knowledge_chain",
                "FAIL",
                "发布包有 knowledge_data_pack，但 knowledge_chain=%s（子包: %s）" % (state, packs),
            )
        ok, detail = _run_content_check(_verify_knowledge_chain, facts)
        return ("knowledge_chain", "PASS" if ok else "FAIL", detail)
    has_snapshot = "canonical_snapshot" in facts["input_types"]
    return (
        "knowledge_chain",
        "BLOCKED",
        "实测 knowledge_chain=%s；M8 输入%s M7 Snapshot（输入类型: %s）；发布包子包: %s；"
        "run_m8 尚未产出 KnowledgeDataPack（TODO.md T05f）"
        % (state, "含" if has_snapshot else "不含", facts["input_types"], packs),
    )


def _check_subpack_produced(name, facts, pack_key, todo_id, why_absent):
    packs = sorted(facts["packs"])
    if pack_key in facts["packs"]:
        return (name, "FAIL", _CONTENT_CHECK_PENDING % (pack_key, todo_id))
    return (name, "BLOCKED", "实测发布包无 %s（子包: %s）；%s（TODO.md %s）" % (pack_key, packs, why_absent, todo_id))


def _check_graph_projection(facts):
    """GraphProjectionPack：没产出 → BLOCKED（写实测）；产出了 → 同源、往返无损内容校验。"""
    if "graph_projection_pack" not in facts["packs"]:
        return _check_subpack_produced(
            "graph_projection", facts, "graph_projection_pack", "T05d",
            "run_m8 尚未产出 GraphProjectionPack",
        )
    ok, detail = _run_content_check(_verify_graph_projection, facts)
    return ("graph_projection", "PASS" if ok else "FAIL", detail)


# ------------------------------------------------------------------ 内容校验（T04B）
# 独立实现：只从 Ledger 读 M8 冻结输入（M7 Snapshot、corpus_spans、清单、页 JSON、RawText）
# 与发布包子包，自行重算；不 import packs / gate，不信任 run_m8 的返回值与 gate 报告。
_ENTRY_ID_RE = re.compile(r"^ent_[0-9a-f]{32}$")
# §16:705-712 固定七段；INTERFACES §3.10：前 5 键公共，第 6/7 键按证据级别分派，键序即段序
_CHAIN_KEYS = {
    "glyphbox_level": [
        "entry_id", "assertion_id", "evidence_link", "source_span", "source_anchor",
        "ocr_page", "source_asset",
    ],
    "offset_level": [
        "entry_id", "assertion_id", "evidence_link", "source_span", "source_anchor",
        "text_mapping", "source_asset",
    ],
}


def _run_content_check(verify, facts):
    """执行一项内容校验；任何异常都记为 FAIL（核对不了就不许判 PASS）。"""
    try:
        ok, detail = verify(facts)
    except Exception as exc:  # noqa: BLE001 - 读不到/形状不符都属未通过
        return False, "内容校验无法执行（%s: %s）" % (type(exc).__name__, exc)
    return ok, detail if ok else "内容校验未过：" + detail


def _frozen_input(facts, artifact_type):
    """m8 冻结输入里恰 1 个该类型的修订号。"""
    revision_ids = [
        ref["artifact_revision_id"]
        for ref in facts["input_refs"]
        if ref.get("artifact_type") == artifact_type
    ]
    if len(revision_ids) != 1:
        raise ValueError("m8 冻结输入 %s 数量 != 1: %d" % (artifact_type, len(revision_ids)))
    return revision_ids[0]


def _verify_chain_tail(facts, chain, span, level, manifest):
    """第 6/7 段：glyphbox 回到页 JSON 与清单资产；offset 回到 RawText / 补丁集冻结输入。"""
    service = facts["service"]
    page_assets = manifest.get("source_assets") or []
    if level == "glyphbox_level":
        page = span["page"]
        page_docs = [
            _read_revision_json(service, ref["artifact_revision_id"])
            for ref in facts["input_refs"]
            if ref.get("artifact_type") == "ocr_page"
        ]
        page_doc = next((doc for doc in page_docs if doc.get("page") == page), None)
        if page_doc is None:
            return "span %s 所在页 %s 不在 m8 冻结的 ocr_page 里" % (span["span_id"], page)
        glyph_ids = [
            char["id"]
            for char in page_doc["chars"]
            if char["parent"] == span["source_anchor"]["line_id"]
        ]
        if not glyph_ids or chain["ocr_page"] != {"page": page, "glyph_ids": glyph_ids}:
            return "ocr_page 与页 JSON 该行字框重算不符: %s" % span["span_id"]
        assets = [item for item in page_assets if item.get("page") == page]
        if len(assets) != 1 or chain["source_asset"] != {
            "page": page,
            "image_sha256": assets[0]["sha256"],
        }:
            return "source_asset 与清单页图哈希不符: %s" % span["span_id"]
        return None
    raw_text_revision_id = _frozen_input(facts, "raw_text")
    raw_sha256 = service.get_revision(raw_text_revision_id)["sha256"]
    anchor = span["source_anchor"]
    expected_mapping = {
        "raw_text_revision_id": raw_text_revision_id,
        "cleaned_text_revision_id": _frozen_input(facts, "cleaned_text_revision"),
        "patch_set_revision_id": _frozen_input(facts, "deterministic_patch_set"),
        "raw_start": anchor["raw_start"],
        "raw_end": anchor["raw_end"],
    }
    if anchor["raw_text_revision_id"] != raw_text_revision_id or chain["text_mapping"] != expected_mapping:
        return "text_mapping 与 m8 冻结的 RawText/清洗文本/补丁集及锚点不符: %s" % span["span_id"]
    assets = [item for item in page_assets if item.get("sha256") == raw_sha256]
    if len(assets) != 1 or chain["source_asset"] != {"page": assets[0]["page"], "sha256": raw_sha256}:
        return "source_asset 与清单底本 / RawText 修订哈希不符: %s" % span["span_id"]
    return None


def _verify_knowledge_chain(facts):
    """知识链闭合 + 证据链可回指到 span（§16:703-715，INTERFACES §3.8/§3.9/§3.10，I-11）。"""
    service = facts["service"]
    publication = facts["publication"]
    snapshot = _read_revision_json(service, _frozen_input(facts, "canonical_snapshot"))
    spans_doc = _read_revision_json(service, _frozen_input(facts, "corpus_spans"))
    manifest = _read_revision_json(service, _frozen_input(facts, "source_manifest"))
    release_manifest = _read_revision_json(service, publication["release_manifest_revision_id"])
    knowledge = _read_revision_json(service, facts["packs"]["knowledge_data_pack"])
    chain_doc = _read_revision_json(service, facts["packs"]["evidence_chain"])

    release_id = publication["release_id"]
    for label, value in (
        ("release_manifest", release_manifest.get("release_id")),
        ("knowledge_data_pack", knowledge.get("release_id")),
        ("evidence_chain", chain_doc.get("release_id")),
    ):
        if value != release_id:
            return False, "%s.release_id %r 与发布包 %r 不符" % (label, value, release_id)

    # 1) 词条：由 Snapshot 双轨显式引用独立重算（第 107 条 Q-M8-01，不推断）
    assertions = {item["assertion_id"]: item for item in snapshot.get("assertions") or []}
    expected_subjects = {}
    for pattern in snapshot.get("patterns") or []:
        if pattern.get("assertion_ids"):
            expected_subjects.setdefault(pattern["pattern_id"], set()).update(pattern["assertion_ids"])
    for item in assertions.values():
        for concept_id in item.get("concept_refs") or []:
            expected_subjects.setdefault(concept_id, set()).add(item["assertion_id"])
    entries = knowledge.get("entries") or []
    if not entries:
        return False, "KnowledgeDataPack 无任何词条（知识链为空，第 107 条：如实失败）"
    entry_subjects = {}
    for entry in entries:
        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str) or _ENTRY_ID_RE.match(entry_id) is None:
            return False, "entry_id 非法: %r" % (entry_id,)
        if not entry.get("assertion_ids"):
            return False, "词条 %s 没有断言（每个 KnowledgeEntry 至少追溯到一个 Assertion）" % entry_id
        if entry["subject_entity_id"] in entry_subjects:
            return False, "主体 %s 出了多个词条" % entry["subject_entity_id"]
        entry_subjects[entry["subject_entity_id"]] = set(entry["assertion_ids"])
    if len({entry["entry_id"] for entry in entries}) != len(entries):
        return False, "entry_id 重复"
    if entry_subjects != expected_subjects:
        return False, "词条主体/断言与 Snapshot 显式引用重算不符: 包 %s，Snapshot %s" % (
            {key: sorted(value) for key, value in sorted(entry_subjects.items())},
            {key: sorted(value) for key, value in sorted(expected_subjects.items())},
        )
    pack_assertions = {item["assertion_id"]: item for item in knowledge.get("assertions") or []}
    if set(pack_assertions) != set(assertions):
        return False, "KnowledgeDataPack 断言集合与 Snapshot 不符"
    for assertion_id, item in pack_assertions.items():
        if item.get("proposition") != assertions[assertion_id].get("proposition"):
            return False, "断言 %s 的 proposition 与 Snapshot 不符" % assertion_id

    # 2) 发号表（INTERFACES §3.16）：本次 M8 封存的 entry_id_allocation 与词条一一对应
    rows = service.list_step_run_revisions(
        facts["m8_step_run_id"], artifact_type="entry_id_allocation", status="sealed"
    )
    if len(rows) != 1:
        return False, "m8 StepRun 名下 sealed entry_id_allocation 数量 != 1: %d" % len(rows)
    allocation = _read_revision_json(service, rows[0]["artifact_revision_id"])
    allocated = {item["subject_entity_id"]: item["entry_id"] for item in allocation.get("allocations") or []}
    if allocated != {entry["subject_entity_id"]: entry["entry_id"] for entry in entries}:
        return False, "发号表与词条 entry_id 不一一对应"

    # 3) 无主体断言如实披露（INTERFACES §3.8：assertion_without_subject: N 并逐条列 ID）
    in_entries = set().union(*entry_subjects.values())
    orphans = sorted(set(assertions) - in_entries)
    disclosed = [
        item for item in release_manifest.get("known_defects") or []
        if item.get("code") == "assertion_without_subject"
    ]
    expected_disclosure = (
        [{"code": "assertion_without_subject", "detail": "%d: %s" % (len(orphans), ",".join(orphans))}]
        if orphans
        else []
    )
    if disclosed != expected_disclosure:
        return False, "无主体断言披露不符: 应 %s，实 %s" % (expected_disclosure, disclosed)

    # 4) 七段证据链逐条回指 span（键序即段序；EvidenceLink 不绕过 Assertion；偏移按 I-11）
    level = spans_doc["evidence_level"]
    keys = _CHAIN_KEYS.get(level)
    if keys is None:
        return False, "evidence_level 不在闭集: %r" % (level,)
    redacted = manifest.get("release_policy") == "reference_and_hash_only"
    spans = {span["span_id"]: span for span in spans_doc["spans"]}
    entry_by_id = {entry["entry_id"]: entry for entry in entries}
    chains = chain_doc.get("chains") or []
    if not chains:
        return False, "evidence_chain.chains 为空（INTERFACES §3.10 minItems 1）"
    got_links = []
    for index, chain in enumerate(chains):
        where = "chains[%d]" % index
        if list(chain) != keys:
            return False, "%s 键序/键集 %s 不是固定七段 %s" % (where, list(chain), keys)
        entry = entry_by_id.get(chain["entry_id"])
        if entry is None:
            return False, "%s entry_id 悬空: %s" % (where, chain["entry_id"])
        link = chain["evidence_link"]
        if chain["assertion_id"] not in entry["assertion_ids"] or link.get("assertion_id") != chain["assertion_id"]:
            return False, "%s EvidenceLink 绕过 Assertion：%s 不属词条 %s 的断言" % (
                where, chain["assertion_id"], chain["entry_id"],
            )
        span = spans.get(link.get("source_span_id"))
        if span is None:
            return False, "%s 回指的 span 不在 m8 冻结的 corpus_spans 里: %s" % (where, link.get("source_span_id"))
        local_start = link["start_offset"] - span["start_offset"]
        local_end = link["end_offset"] - span["start_offset"]
        if not (0 <= local_start <= local_end <= len(span["text"])):
            return False, "%s 证据偏移 [%d,%d) 越出 span %s（I-11 绝对偏移）" % (
                where, link["start_offset"], link["end_offset"], span["span_id"],
            )
        quote = span["text"][local_start:local_end]
        if _sha256_hex(quote.encode("utf-8")) != link.get("quote_sha256"):
            return False, "%s quote_sha256 与 span 原文切片重算不符" % where
        if link.get("quote") != (None if redacted else quote):
            return False, "%s evidence_link.quote 与 span 原文切片不符" % where
        expected_span = {
            "source_span_id": span["span_id"],
            "source_id": spans_doc["source_id"],
            "page": span.get("page"),
            "start_offset": span["start_offset"],
            "end_offset": span["end_offset"],
            "text": None if redacted else span["text"],
        }
        if chain["source_span"] != expected_span:
            return False, "%s source_span 与 corpus_spans 不符" % where
        if chain["source_anchor"] != span["source_anchor"]:
            return False, "%s source_anchor 与 corpus_spans 锚点不符" % where
        problem = _verify_chain_tail(facts, chain, span, level, manifest)
        if problem is not None:
            return False, "%s %s" % (where, problem)
        got_links.append(
            (chain["entry_id"], chain["assertion_id"], link["source_span_id"],
             link["start_offset"], link["end_offset"], link["quote_sha256"])
        )
    expected_links = set()
    for entry in entries:
        for assertion_id in entry["assertion_ids"]:
            for evidence in assertions[assertion_id].get("evidence") or []:
                expected_links.add(
                    (entry["entry_id"], assertion_id, evidence["source_span_id"],
                     evidence["start_offset"], evidence["end_offset"], evidence["quote_sha256"])
                )
    if len(set(got_links)) != len(got_links) or set(got_links) != expected_links:
        return False, "证据链与 Snapshot 证据独立推导不一致（缺链/多链/重复）: 包 %d 条，应 %d 条" % (
            len(got_links), len(expected_links),
        )
    return True, (
        "知识链闭合：%d 个词条、%d 条断言；%d 条七段证据链逐条回指 span（I-11 绝对偏移、quote_sha256 重算一致）；"
        "无主体断言 %d 条已按 §3.8 披露" % (len(entries), len(assertions), len(chains), len(orphans))
    )


def _verify_graph_projection(facts):
    """GraphProjectionPack 与移动端数据（KnowledgeDataPack）同源、往返无损（§16:725，INTERFACES §3.15）。"""
    service = facts["service"]
    publication = facts["publication"]
    if "knowledge_data_pack" not in facts["packs"]:
        return False, "发布包没有同源的移动端数据 knowledge_data_pack，无法核对往返"
    _frozen_input(facts, "canonical_snapshot")  # 两者须出自本次冻结的同一 Snapshot
    graph = _read_revision_json(service, facts["packs"]["graph_projection_pack"])
    knowledge = _read_revision_json(service, facts["packs"]["knowledge_data_pack"])
    release_manifest = _read_revision_json(service, publication["release_manifest_revision_id"])

    # 1) 同源标识：release_id / canonical_hash / consumption_level
    if not (graph.get("release_id") == knowledge.get("release_id") == release_manifest.get("release_id") == publication["release_id"]):
        return False, "release_id 不一致（图投影/移动端数据/清单/发布包）"
    if not (graph.get("canonical_hash") == release_manifest.get("canonical_hash") == publication["canonical_hash"]):
        return False, "graph_projection.canonical_hash 与 ReleaseManifest/发布包不符"
    if not (graph.get("consumption_level") == knowledge.get("consumption_level") == release_manifest.get("consumption_level")):
        return False, "consumption_level 不一致"

    # 2) 形状（INTERFACES §3.15）
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if graph.get("node_count") != len(nodes) or graph.get("edge_count") != len(edges):
        return False, "node_count/edge_count 与实际不符"
    node_ids = [node["node_id"] for node in nodes]
    if node_ids != sorted(set(node_ids)):
        return False, "nodes 未按 node_id 升序或有重复"
    triples = [(edge["source"], edge["relation"], edge["target"]) for edge in edges]
    if triples != sorted(set(triples)):
        return False, "edges 未按 (source, relation, target) 升序或有重复"
    if any("edge_id" in edge or "id" in edge for edge in edges):
        return False, "边带了独立 ID（【I-10】）"

    # 3) 往返无损：由移动端数据独立重建应有的节点与关系，须与图投影逐一相等
    entries = knowledge.get("entries") or []
    expected_nodes = {}
    for concept in knowledge.get("concepts") or []:
        expected_nodes[concept["concept_id"]] = ("concept", concept["name"], None)
    for assertion in knowledge.get("assertions") or []:
        expected_nodes[assertion["assertion_id"]] = ("assertion", assertion["proposition"], assertion["status"])
    for entry in entries:
        if entry["subject_entity_id"].startswith("pat_"):
            expected_nodes[entry["subject_entity_id"]] = ("pattern", entry["title"], None)
    for view in knowledge.get("school_views") or []:
        expected_nodes[view["school_view_id"]] = ("school_view", view["school_view_id"], view["content_status"])
    got_nodes = {}
    for node in nodes:
        expected = expected_nodes.get(node["node_id"])
        status = node.get("content_status") if expected is not None and expected[2] is not None else None
        got_nodes[node["node_id"]] = (node["kind"], node["label"], status)
    if got_nodes != expected_nodes:
        missing = sorted(set(expected_nodes) - set(got_nodes))
        extra = sorted(set(got_nodes) - set(expected_nodes))
        changed = sorted(
            node_id for node_id in set(got_nodes) & set(expected_nodes)
            if got_nodes[node_id] != expected_nodes[node_id]
        )
        return False, "图节点与移动端数据往返不符: 缺 %s 多 %s 变 %s" % (missing, extra, changed)
    expected_edges = set()
    for entry in entries:
        subject = entry["subject_entity_id"]
        for assertion_id in entry["assertion_ids"]:
            if subject.startswith("pat_"):
                expected_edges.add((subject, "has_assertion", assertion_id))
            elif subject.startswith("co_"):
                expected_edges.add((assertion_id, "belongs_to_concept", subject))
    for assertion in knowledge.get("assertions") or []:
        if (assertion.get("subject_entity_id") or "").startswith("co_"):
            expected_edges.add((assertion["assertion_id"], "belongs_to_concept", assertion["subject_entity_id"]))
    for view in knowledge.get("school_views") or []:
        if view.get("conflict_group_id"):
            expected_edges.add((view["school_view_id"], "in_conflict_group", view["conflict_group_id"]))
    if set(triples) != expected_edges:
        return False, "图关系与移动端数据往返不符: 缺 %s 多 %s" % (
            sorted(expected_edges - set(triples)), sorted(set(triples) - expected_edges),
        )
    return True, (
        "GraphProjectionPack 与 KnowledgeDataPack 同源（release_id/canonical_hash/consumption_level 一致），"
        "往返无损：%d 节点、%d 条关系逐一可由移动端数据重建" % (len(nodes), len(edges))
    )


# ------------------------------------------------------------------ 组装结果
def _route_check_status(name, route, na_checks, fail_detail):
    """按路线给出子判据状态：offset 档的不适用项 → NOT_APPLICABLE，否则 FAIL。

    裁定 107 Q-M8-08：不适用**不得冒充 pass**，也不得写成 ok。
    """
    if route == ROUTE_OFFSET and name in na_checks:
        return (name, NOT_APPLICABLE, _OFFSET_NOT_APPLICABLE_DETAIL)
    return (name, "FAIL", fail_detail)


def _evaluate_span_identity(context):
    route = context.get("route")
    service = context["service"]
    results = []
    step_run_id = context["m8_step_run_id"]
    step_run = service.get_step_run(step_run_id) if step_run_id else None
    results.append(
        (
            "run_succeeded",
            "PASS" if (step_run and step_run["status"] == "succeeded") else "FAIL",
            "m8 StepRun=%s" % (step_run["status"] if step_run else None),
        )
    )
    loaded, load_error = _load_span_context_or_none(context)
    if loaded is None:
        detail = load_error or "m8 StagePackage 缺失"
        for name in (
            "span_key_unique",
            "legacy_collision_exposed",
            "span_page_binding",
            "anchor_to_page_image",
            "glyph_closure",
            "reverse_index",
        ):
            results.append(
                _route_check_status(name, route, _OFFSET_NA_SPAN_CHECKS, detail)
            )
        results.append(("mentions_mapping", "FAIL", "m8 StagePackage 缺失，无法核对 mentions: %s" % detail))
        return results

    loaded["page_order"] = context["manifest"]["edition_part"]["pages"]
    checks = [
        ("span_key_unique", lambda: _check_span_key_unique(loaded, context["spans_golden"])),
        ("legacy_collision_exposed", lambda: _check_legacy_collision(loaded)),
        ("span_page_binding", lambda: _check_span_page_binding(loaded)),
        (
            "anchor_to_page_image",
            lambda: _check_anchor_to_page_image(
                service, loaded, context["manifest"], context["asset_root"]
            ),
        ),
        ("glyph_closure", lambda: _check_glyph_closure(loaded)),
        ("reverse_index", lambda: _check_reverse_index(loaded, context["manifest"])),
    ]
    for name, func in checks:
        if route == ROUTE_OFFSET and name in _OFFSET_NA_SPAN_CHECKS:
            results.append((name, NOT_APPLICABLE, _OFFSET_NOT_APPLICABLE_DETAIL))
        else:
            results.append(_safe(name, func))
    facts = _m8_output_facts(context)
    results.append(_check_mentions_mapping(facts))
    return results


def _evaluate_publication(context):
    route = context.get("route")
    service = context["service"]
    results = []
    step_run_id = context["m8_step_run_id"]
    step_run = service.get_step_run(step_run_id) if step_run_id else None
    results.append(
        (
            "run_succeeded",
            "PASS" if (step_run and step_run["status"] == "succeeded") else "FAIL",
            "m8 StepRun=%s" % (step_run["status"] if step_run else None),
        )
    )
    loaded, load_error = _load_span_context_or_none(context)
    if loaded is None:
        detail = load_error or "m8 StagePackage 缺失"
        for name in (
            "evidence_chain_closure",
            "coordinate_frame",
            "release_manifest_hashes",
            "input_reconciliation",
            "consumption_level",
            "watermark_disclosure",
        ):
            results.append(
                _route_check_status(name, route, _OFFSET_NA_PUBLICATION_CHECKS, detail)
            )
        results.append(("fail_closed_levels", "FAIL", detail))
        for name in ("knowledge_chain", "graph_projection", "identity_migration"):
            results.append((name, "FAIL", "m8 StagePackage 缺失，无法核对: %s" % detail))
        return results

    loaded["page_order"] = context["manifest"]["edition_part"]["pages"]
    loaded["release_manifest_revision_id"] = context["package"]["payload"][
        "release_manifest_revision_id"
    ]
    loaded["manifest"] = context["manifest"]
    loaded["m3_gate_profile"] = context["m3_gate_profile"]

    def evidence_chain_closure():
        checked = []
        # 适用级别事先声明：offset 档这些子步一律披露为 NOT_APPLICABLE，不论后续子步成败
        not_applicable = (
            ["%s=%s" % (name, NOT_APPLICABLE) for name in _OFFSET_NA_CLOSURE_STEPS]
            + [
                "text_offsets.%s=%s" % (field, NOT_APPLICABLE)
                for field in _OFFSET_NA_TEXT_OFFSET_FIELDS
            ]
            if route == ROUTE_OFFSET
            else []
        )
        for name, func in (
            ("span_identity", lambda: _check_span_key_unique(loaded, context["spans_golden"])),
            ("span_page_binding", lambda: _check_span_page_binding(loaded)),
            ("text_offsets", lambda: _check_text_offsets(loaded, route)),
            ("glyph_anchor_closure", lambda: _check_glyph_closure(loaded)),
        ):
            if route == ROUTE_OFFSET and name in _OFFSET_NA_CLOSURE_STEPS:
                continue
            try:
                ok, detail = func()
            except Exception as exc:  # noqa: BLE001 - 子步异常按该子步失败，保留不适用披露
                ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
            if not ok:
                failure = "%s: %s" % (name, detail)
                if not_applicable:
                    failure += "（%s：%s）" % ("、".join(not_applicable), _OFFSET_NOT_APPLICABLE_DETAIL)
                return False, failure
            checked.append(name)
        if not not_applicable:
            return True, "链 1–5 闭合"
        return True, "已核 %s 闭合（%s：%s）" % (
            "、".join(checked), "、".join(not_applicable), _OFFSET_NOT_APPLICABLE_DETAIL
        )

    checks = [
        ("evidence_chain_closure", evidence_chain_closure),
        ("coordinate_frame", lambda: _check_coordinate_frame(loaded, context["manifest"])),
        ("release_manifest_hashes", lambda: _check_release_manifest_hashes(service, loaded)),
        ("input_reconciliation", lambda: _check_input_reconciliation(service, context, loaded)),
        ("consumption_level", lambda: _check_consumption_level(service, loaded)),
        ("watermark_disclosure", lambda: _check_watermark_disclosure(service, loaded, route)),
        ("fail_closed_levels", lambda: _check_fail_closed_levels(context)),
    ]
    for name, func in checks:
        if route == ROUTE_OFFSET and name in _OFFSET_NA_PUBLICATION_CHECKS:
            results.append((name, NOT_APPLICABLE, _OFFSET_NOT_APPLICABLE_DETAIL))
        else:
            results.append(_safe(name, func))
    facts = _m8_output_facts(context)
    results.append(_check_knowledge_chain(facts))
    results.append(_check_graph_projection(facts))
    results.append(
        _check_subpack_produced(
            "identity_migration", facts, "identity_migration_map", "T05e",
            "本次只编译 1 个 Release，且 run_m8 尚未由 M7 identity_delta 生成 IdentityMigrationMap",
        )
    )
    return results


def _safe(name, func):
    try:
        ok, detail = func()
    except Exception as exc:  # noqa: BLE001 - 判定内异常转该项 FAIL
        return (name, "FAIL", "%s: %s" % (type(exc).__name__, exc))
    return (name, "PASS" if ok else "FAIL", detail)


# ------------------------------------------------------------------ 入口
def main(argv=None):
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.dataset_compiler.acceptance",
        description="M8 验收：span_identity / publication（§19.0）",
    )
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="fixture 根目录")
    parser.add_argument(
        "--check",
        choices=("span_identity", "publication"),
        default="span_identity",
    )
    parser.add_argument("--keep", action="store_true", help="保留临时 Ledger")
    parser.add_argument(
        "--ledger",
        help="判定既有账本（只读打开，不装配宿主、不跑 M8）；缺省在临时 Ledger 上现场装配（T04 Q9）",
    )
    args = parser.parse_args(argv)

    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("BLOCKED m8_acceptance 前置缺失: 测试宿主匮乏；yaml/jsonschema 不可导入")
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    fixture_dir = Path(args.fixture).resolve()
    if not (fixture_dir / "manifest.yaml").is_file():
        print("BLOCKED m8_acceptance 宿主缺失: 缺 fixture manifest.yaml")
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    route = _detect_route(fixture_dir)
    if route is None:
        # D-W8-16 三：夹具缺少判定依据时不可判定，按宿主缺失 BLOCKED。
        missing_reason = (
            "无法判定证据级别"
            if (fixture_dir / "spans.yaml").is_file()
            else "缺 fixture spans.yaml"
        )
        print("BLOCKED m8_acceptance 宿主缺失: %s" % missing_reason)
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    asset_root = Path(
        os.environ.get("FIXTURE_ASSET_ROOT") or str(DEFAULT_ASSET_ROOT)
    ).resolve()
    if route == ROUTE_GLYPHBOX:
        # 页图只对 OCR 路线是宿主前置；电子文本路线不读任何页图（ACT 16 四）。
        missing = [
            str(asset_root / ("page_%03d.png" % number))
            for number in (1, 2, 3)
            if not (asset_root / ("page_%03d.png" % number)).is_file()
        ]
        if missing:
            print(
                "BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING %s"
                % " ".join(missing)
            )
            print("SUMMARY pass=0 fail=0 blocked=1")
            return 3

    tmp = None
    if args.ledger:
        ledger_root = Path(args.ledger).resolve()
        if not (ledger_root / "ledger.sqlite").is_file():
            print("BLOCKED m8_acceptance 宿主缺失: 账本不存在 %s" % ledger_root)
            print("SUMMARY pass=0 fail=0 blocked=1")
            return 3
        # 只读：判定的是账本里已有的 M8 事实，不写入（mode=ro，不取写锁）
        service = LedgerReader(ledger_root)
    else:
        tmp = tempfile.mkdtemp(prefix="m8-acceptance-")
        service = LedgerService(Path(tmp) / "ledger")
    try:
        try:
            if args.ledger:
                manifest = yaml.safe_load((fixture_dir / "manifest.yaml").read_bytes())
                edition_part_id = manifest["edition_part"]["artifact_id"]
            else:
                edition_part_id = _prepare_ledger(service, fixture_dir, asset_root, route)
                run_m8(service, edition_part_id, consumption_level="INTERNAL_DEMO")
            context = _build_context(
                service, edition_part_id, fixture_dir, asset_root, route
            )
        except Exception as exc:  # noqa: BLE001 - 准备/运行异常 → exit 1
            print("FAIL m8_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
            print("SUMMARY pass=0 fail=1 blocked=0")
            return 1

        results = (
            _evaluate_publication(context)
            if args.check == "publication"
            else _evaluate_span_identity(context)
        )
        passed = failed = blocked = 0
        for name, status, detail in results:
            if status == "PASS":
                passed += 1
                print("PASS %s %s" % (name, detail) if detail else "PASS %s" % name)
            elif status == "FAIL":
                failed += 1
                print("FAIL %s %s" % (name, detail))
            elif status == NOT_APPLICABLE:
                # 不适用当前证据级别：不计入 pass/fail/blocked，不得冒充 pass（裁定 107 Q-M8-08）
                print("NOT_APPLICABLE %s %s" % (name, detail))
            else:
                blocked += 1
                print("BLOCKED %s %s" % (name, detail))
        print("SUMMARY pass=%d fail=%d blocked=%d" % (passed, failed, blocked))
        if failed:
            return 1
        if blocked:
            return 2
        return 0
    finally:
        service.close()
        if tmp is not None and not args.keep:
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    raise SystemExit(main())
