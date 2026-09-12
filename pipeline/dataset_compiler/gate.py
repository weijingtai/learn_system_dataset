"""M8 独立发布 Gate ``evaluate_publication``（规格 §16:703-715，裁决 D10/D11）。

独立实现，防止与编译器「同错同过」：本模块从页 JSON 与清单重新计算字框锚点、
坐标同源、哈希清单、级别与披露，**不得** import ``packs``/``canonical``/
``levels``/``step``。只 import 标准库。

本函数不抛异常：任一检查内部异常都转成该项 ``{"ok": False, "detail": ...}``。
``knowledge_chain`` 恒为 ``{"ok": None, "status": "not_evaluated"}``。
"""

import hashlib
import json
import re

# 检查名称与固定顺序
_CHECK_NAMES = (
    "span_identity",
    "span_page_binding",
    "text_offsets",
    "glyph_anchor_closure",
    "highlight_level",
    "ocr_page_binding",
    "source_asset_binding",
    "coordinate_frame",
    "reverse_index",
    "release_manifest_hashes",
    "input_reconciliation",
    "consumption_level",
    "watermark_disclosure",
    "knowledge_chain",
)

_SPAN_TAIL_RE = re.compile(r"_p([0-9]{4})_s([0-9]{2})$")


def _fail(detail):
    return {"ok": False, "detail": detail}


def _ok(detail):
    return {"ok": True, "detail": detail}


def _canonical_bytes(obj):
    """本模块内自行实现的规范化 JSON（不 import canonical 模块）。"""
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _spans_by_id(spans_doc):
    return {span["span_id"]: span for span in spans_doc["spans"]}


def _manifest_assets(manifest):
    return {item["page"]: item for item in manifest["source_assets"]}


def evaluate_publication(
    *,
    manifest,
    spans_doc,
    page_docs,
    ocr_page_revision_ids,
    asset_records,
    excluded_pages,
    m3_gate_profile,
    frozen_inputs,
    source_asset_pack,
    evidence_map_pack,
    release_manifest,
    pack_bytes,
    consumption_level,
):
    """独立判定 M8 发布物（§16:703-715）。返回见模块 docstring 与 ACT 契约。"""
    checks = {}

    def run(name, func):
        try:
            checks[name] = func()
        except Exception as exc:  # noqa: BLE001 - 设计上所有异常转该项失败
            checks[name] = _fail("%s: %s" % (type(exc).__name__, exc))

    # 1 span_identity
    def check_span_identity():
        entries = evidence_map_pack["entries"]
        spans = spans_doc["spans"]
        span_ids = [span["span_id"] for span in spans]
        if len(span_ids) != len(set(span_ids)):
            return _fail("spans_doc 存在重复 span_id")
        if set(entries.keys()) != set(span_ids):
            return _fail("entries 键集合与 spans_doc span_id 集合不一致")
        if not (
            len(entries)
            == len(spans)
            == spans_doc["span_count"]
            == evidence_map_pack["span_count"]
        ):
            return _fail("entries/spans/表头计数不一致")
        for key, entry in entries.items():
            if entry["span_id"] != key:
                return _fail("键与 entry.span_id 不一致: %s" % key)
        return _ok("entries 以完整 span_id 为键，共 %d 条" % len(entries))

    # 2 span_page_binding
    def check_span_page_binding():
        entries = evidence_map_pack["entries"]
        by_id = _spans_by_id(spans_doc)
        page_order = manifest["edition_part"]["pages"]
        for key, entry in entries.items():
            match = _SPAN_TAIL_RE.search(key)
            if match is None:
                return _fail("span_id 缺少页号/行序段: %s" % key)
            if int(match.group(1)) != int(entry["page"][5:]):
                return _fail("span_id 页号段与 entry.page 不符: %s" % key)
            if int(match.group(2)) != entry["line_index"] + 1:
                return _fail("span_id 行序段与 line_index+1 不符: %s" % key)
            if entry["page"] != by_id[key]["page"]:
                return _fail("entry.page 与 spans_doc 同 span 的 page 不符: %s" % key)
            if entry["page"] not in page_order:
                return _fail("entry.page 不在清单页序内: %s" % entry["page"])
            if entry["page"] in excluded_pages:
                return _fail("排除页上出现 span: %s" % entry["page"])
        return _ok("span_id 页号/行序与 page/line_index 绑定一致")

    # 3 text_offsets
    def check_text_offsets():
        entries = evidence_map_pack["entries"]
        by_id = _spans_by_id(spans_doc)
        for key, entry in entries.items():
            span = by_id[key]
            if (
                entry["start_offset"] != span["start_offset"]
                or entry["end_offset"] != span["end_offset"]
                or entry["line_index"] != span["line_index"]
                or entry["text"] != span["text"]
            ):
                return _fail("offset/line_index/text 与 spans_doc 不符: %s" % key)
            if entry["quote_sha256"] != _sha256(entry["text"].encode("utf-8")):
                return _fail("quote_sha256 与 text 不符: %s" % key)
            if entry["content_status"] != spans_doc["content_status"]:
                return _fail("entry.content_status 与 spans_doc 不符: %s" % key)
        return _ok("offset、quote_sha256、content_status 与 spans_doc 一致")

    # 4 glyph_anchor_closure
    def check_glyph_anchor_closure():
        entries = evidence_map_pack["entries"]
        for key, entry in entries.items():
            doc = page_docs[entry["page"]]
            line_id = entry["line_id"]
            line = None
            for candidate in doc["lines"]:
                if candidate["id"] == line_id:
                    line = candidate
                    break
            if line is None:
                return _fail("line_id 不在页 JSON lines 中: %s" % key)
            if entry["bbox"] != line["box"]:
                return _fail("entry.bbox 与该行 box 不符: %s" % key)
            recomputed = [
                {
                    "char_index": index,
                    "glyph_id": char["id"],
                    "char": char["char"],
                    "box": char["box"],
                }
                for index, char in enumerate(doc["chars"])
                if char["parent"] == line_id
            ]
            if entry["glyphs"] != recomputed:
                return _fail("glyphs 与页 JSON chars 重算结果不符: %s" % key)
        return _ok("glyphs 与页 JSON chars 从源重算一致")

    # 5 highlight_level
    def check_highlight_level():
        entries = evidence_map_pack["entries"]
        for key, entry in entries.items():
            doc = page_docs[entry["page"]]
            line_id = entry["line_id"]
            recomputed_text = "".join(
                char["char"] for char in doc["chars"] if char["parent"] == line_id
            )
            expected_equal = recomputed_text == entry["text"]
            if entry["glyph_text_equal"] != expected_equal:
                return _fail("glyph_text_equal 与重算不一致: %s" % key)
            expected_level = "glyph" if expected_equal else "line_bbox"
            if entry["highlight_level"] != expected_level:
                return _fail("highlight_level 与重算不一致: %s" % key)
        return _ok("highlight_level 与字框/文本重算一致")

    # 6 ocr_page_binding
    def check_ocr_page_binding():
        entries = evidence_map_pack["entries"]
        for key, entry in entries.items():
            if entry["ocr_page_artifact_revision_id"] != ocr_page_revision_ids[entry["page"]]:
                return _fail("ocr_page 修订与登记不一致: %s" % key)
        return _ok("ocr_page 修订与登记一致")

    # 7 source_asset_binding
    def check_source_asset_binding():
        entries = evidence_map_pack["entries"]
        page_order = manifest["edition_part"]["pages"]
        assets = _manifest_assets(manifest)
        if source_asset_pack["content_level"] != manifest["release_policy"]:
            return _fail("source_asset_pack.content_level 与清单 release_policy 不符")
        if [page["page"] for page in source_asset_pack["pages"]] != page_order:
            return _fail("source_asset_pack 页序与清单页序不符")
        pack_pages = {page["page"]: page for page in source_asset_pack["pages"]}
        for page in page_order:
            manifest_asset = assets[page]
            pack_page = pack_pages[page]
            record = asset_records[page]
            if not (
                pack_page["sha256"] == manifest_asset["sha256"] == record["sha256"]
            ):
                return _fail("页 %s 资产哈希三方不一致" % page)
            if not (
                pack_page["width"] == manifest_asset["width"] == record["width"]
                and pack_page["height"] == manifest_asset["height"] == record["height"]
            ):
                return _fail("页 %s 尺寸三方不一致" % page)
            if pack_page["asset_artifact_revision_id"] != record["artifact_revision_id"]:
                return _fail("页 %s 资产修订号与记录不一致" % page)
        for key, entry in entries.items():
            page = entry["page"]
            if entry["image_sha256"] != assets[page]["sha256"]:
                return _fail("entry.image_sha256 与清单资产不符: %s" % key)
            if (
                entry["source_asset_artifact_revision_id"]
                != asset_records[page]["artifact_revision_id"]
            ):
                return _fail("entry.source_asset 修订号与记录不符: %s" % key)
        return _ok("资产包、清单、记录与 entry 三方绑定一致")

    # 8 coordinate_frame
    def check_coordinate_frame():
        entries = evidence_map_pack["entries"]
        assets = _manifest_assets(manifest)
        for key, entry in entries.items():
            page = entry["page"]
            doc = page_docs[page]
            frame = entry["frame"]
            if frame != {"width": doc["width"], "height": doc["height"]}:
                return _fail("entry.frame 与页 JSON 宽高不符: %s" % key)
            if (frame["width"], frame["height"]) != (
                assets[page]["width"],
                assets[page]["height"],
            ):
                return _fail("entry.frame 与清单宽高不符: %s" % key)
            boxes = [entry["bbox"]] + [glyph["box"] for glyph in entry["glyphs"]]
            for box in boxes:
                if (
                    box["x"] < 0
                    or box["y"] < 0
                    or box["x"] + box["w"] > frame["width"]
                    or box["y"] + box["h"] > frame["height"]
                ):
                    return _fail("框越出坐标系: %s" % key)
        return _ok("frame 与页 JSON/清单同源，框均在框内")

    # 9 reverse_index
    def check_reverse_index():
        page_order = manifest["edition_part"]["pages"]
        page_index = evidence_map_pack["page_index"]
        if list(page_index.keys()) != page_order:
            return _fail("page_index 键顺序与清单页序不符")
        by_page = {}
        for span in spans_doc["spans"]:
            by_page.setdefault(span["page"], []).append(span["span_id"])
        for page in page_order:
            if page_index[page] != by_page.get(page, []):
                return _fail("page_index[%s] 与 spans_doc 顺序不符" % page)
            if page in excluded_pages and page_index[page] != []:
                return _fail("排除页 %s 的反向索引非空" % page)
        if evidence_map_pack["excluded_pages"] != excluded_pages:
            return _fail("excluded_pages 与冻结值不符")
        return _ok("反向索引覆盖清单全部页，排除页为空")

    # 10 release_manifest_hashes
    def check_release_manifest_hashes():
        manifest_packs = {item["pack_type"]: item for item in release_manifest["packs"]}
        expected_types = {"evidence_map_pack", "source_asset_pack"}
        if set(manifest_packs.keys()) != expected_types:
            return _fail("release_manifest.packs 的 pack_type 集合不符")
        if set(pack_bytes.keys()) != expected_types:
            return _fail("pack_bytes 键集合不符")
        pack_dicts = {
            "evidence_map_pack": evidence_map_pack,
            "source_asset_pack": source_asset_pack,
        }
        for pack_type, item in manifest_packs.items():
            data = pack_bytes[pack_type]
            if item["sha256"] != _sha256(data):
                return _fail("%s 的 sha256 与字节不符" % pack_type)
            if item["size"] != len(data):
                return _fail("%s 的 size 与字节长度不符" % pack_type)
            if json.loads(data.decode("utf-8")) != pack_dicts[pack_type]:
                return _fail("%s 的字节内容与 pack dict 不符" % pack_type)
        expected_canonical = _sha256(
            _canonical_bytes(
                [
                    [pack_type, manifest_packs[pack_type]["sha256"]]
                    for pack_type in sorted(manifest_packs)
                ]
            )
        )
        if release_manifest["canonical_hash"] != expected_canonical:
            return _fail("canonical_hash 与子包哈希列表重算不符")
        return _ok("子包哈希、字节与 canonical_hash 均可重算")

    # 11 input_reconciliation
    def check_input_reconciliation():
        given = {
            (
                item["artifact_revision_id"],
                item["artifact_type"],
                item["sha256"],
            )
            for item in release_manifest["input_reconciliation"]
        }
        expected = {
            (
                item["artifact_revision_id"],
                item["artifact_type"],
                item["sha256"],
            )
            for item in frozen_inputs
        }
        if given != expected:
            return _fail("input_reconciliation 与冻结输入不一致")
        return _ok("input_reconciliation 与冻结输入逐项一致")

    # 12 consumption_level
    def check_consumption_level():
        if consumption_level != release_manifest["consumption_level"]:
            return _fail("consumption_level 与 release_manifest 不符")
        if release_manifest["consumption_level"] != "INTERNAL_DEMO":
            return _fail("首切片只签发 INTERNAL_DEMO")
        if release_manifest["isolation"] != "internal_only":
            return _fail("isolation 必须为 internal_only")
        if release_manifest["authoritative"] is not False:
            return _fail("authoritative 必须为 False")
        if release_manifest["completeness_claim"] != "partial":
            return _fail("completeness_claim 必须为 partial")
        expected_release = (
            "release" if spans_doc["content_status"] == "expert_verified" else "dev"
        )
        if release_manifest["source_release"] != expected_release:
            return _fail("source_release 推导不符（D9：source_verified 不算 release 级）")
        return _ok("消费级别、隔离、权威性与来源发布级别一致")

    # 13 watermark_disclosure
    def check_watermark_disclosure():
        if spans_doc["content_status"].startswith("machine_"):
            for key, entry in evidence_map_pack["entries"].items():
                if entry["watermark"] is not True:
                    return _fail("entry.watermark 未置真: %s" % key)
            watermark = release_manifest["watermark"]
            if watermark["required"] is not True:
                return _fail("watermark.required 未置真")
            if not watermark["text"]:
                return _fail("watermark.text 为空")
        required = set()
        if evidence_map_pack["excluded_pages"]:
            required.add("excluded_page")
        if any(
            entry["highlight_level"] == "line_bbox"
            for entry in evidence_map_pack["entries"].values()
        ):
            required.add("glyph_text_mismatch")
        if evidence_map_pack["knowledge_chain"] != "compiled":
            required.add("knowledge_chain_not_compiled")
        if spans_doc["content_status"].startswith("machine_"):
            required.add("machine_content")
        if isinstance(manifest["rights_status"], str) and "unconfirmed" in manifest[
            "rights_status"
        ]:
            required.add("rights_unconfirmed")
        if m3_gate_profile == "structural_only":
            required.add("semantic_not_evaluated")
        given = {item["code"] for item in release_manifest["known_defects"]}
        if not required.issubset(given):
            return _fail(
                "known_defects 少了必需代码: %s" % ",".join(sorted(required - given))
            )
        return _ok("水印与已知缺陷披露完整")

    # 14 knowledge_chain
    def check_knowledge_chain():
        value = evidence_map_pack["knowledge_chain"]
        if value == "not_compiled":
            return {
                "ok": None,
                "status": "not_evaluated",
                "detail": "KnowledgeEntry→Assertion→EvidenceLink 未编译",
            }
        return {
            "ok": False,
            "status": "evaluated",
            "detail": "knowledge_chain 声称非 not_compiled: %r" % (value,),
        }

    run("span_identity", check_span_identity)
    run("span_page_binding", check_span_page_binding)
    run("text_offsets", check_text_offsets)
    run("glyph_anchor_closure", check_glyph_anchor_closure)
    run("highlight_level", check_highlight_level)
    run("ocr_page_binding", check_ocr_page_binding)
    run("source_asset_binding", check_source_asset_binding)
    run("coordinate_frame", check_coordinate_frame)
    run("reverse_index", check_reverse_index)
    run("release_manifest_hashes", check_release_manifest_hashes)
    run("input_reconciliation", check_input_reconciliation)
    run("consumption_level", check_consumption_level)
    run("watermark_disclosure", check_watermark_disclosure)
    run("knowledge_chain", check_knowledge_chain)

    passed = all(
        checks[name]["ok"] is True
        for name in _CHECK_NAMES
        if checks[name]["ok"] is not None
    )
    failed_checks = [
        name for name in _CHECK_NAMES if checks[name]["ok"] is False
    ]
    return {
        "passed": passed,
        "checks": checks,
        "failed_checks": failed_checks,
        "knowledge_chain": "not_evaluated",
    }
