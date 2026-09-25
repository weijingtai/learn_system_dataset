"""M8 独立发布 Gate ``evaluate_publication``（规格 §16:703-715，裁决 D10/D11、第 107 条 Q-M8-08）。

独立实现，防止与编译器「同错同过」：本模块从页 JSON 与清单重新计算字框锚点、
坐标同源、哈希清单、级别与披露，**不得** import ``packs``/``canonical``/
``levels``/``step``。只 import 标准库。

本函数不抛异常：任一检查内部异常都转成该项 ``{"ok": False, "detail": ...}``。
``_CHECK_NAMES`` 为登记的 23 项单一闭集（INTERFACES §3.3）；不适用的检查项
输出 ``{"ok": None, "status": "not_applicable"}``（不同于 ``not_evaluated``，
也不得冒充 ok）。``knowledge_chain`` 为过渡项：知识链未编译时
``not_evaluated``；已编译时按知识链五项实评汇总。
"""

import hashlib
import json
import re

# 检查名称与固定顺序：登记的 23 项单一闭集（INTERFACES §3.3，第 107 条 Q-M8-08）
# 每项声明适用证据级别："both"=两档实评；"glyphbox"/"offset"=仅该档实评，
# 另一档输出 not_applicable；"transition"=过渡项（未实评时 not_evaluated）。
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
    "chain_closure",
    "no_assertion_bypass",
    "quote_hash_integrity",
    "content_status_admission",
    "offset_anchor_continuity",
    "patch_reversible",
    "raw_text_binding",
    "sanitization_disclosure",
    "graph_projection_closure",
)

# 检查项适用级别声明（同上口径；键为 _CHECK_NAMES 的闭集成员）
_CHECK_APPLICABILITY = {
    "span_identity": "both",
    "span_page_binding": "glyphbox",
    "text_offsets": "both",
    "glyph_anchor_closure": "glyphbox",
    "highlight_level": "glyphbox",
    "ocr_page_binding": "glyphbox",
    "source_asset_binding": "both",
    "coordinate_frame": "glyphbox",
    "reverse_index": "glyphbox",
    "release_manifest_hashes": "both",
    "input_reconciliation": "both",
    "consumption_level": "both",
    # ACT 17 二.2：披露清单依赖 highlight_level（OCR 专有）→ 仅字框档实评
    "watermark_disclosure": "glyphbox",
    "knowledge_chain": "transition",
    "chain_closure": "knowledge",
    "no_assertion_bypass": "knowledge",
    "quote_hash_integrity": "knowledge",
    "content_status_admission": "knowledge",
    "graph_projection_closure": "knowledge",
    "offset_anchor_continuity": "offset",
    "patch_reversible": "offset",
    "raw_text_binding": "offset",
    "sanitization_disclosure": "offset",
}

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


def _not_applicable(detail):
    """not_applicable：声明检查项不适用当前证据级别（≠ ok，≠ not_evaluated）。"""
    return {"ok": None, "status": "not_applicable", "detail": detail}


def _ev(ok, detail):
    """知识链五项实评结果（带 status=evaluated；仅此五项，OCR 既有项不动）。"""
    return {"ok": ok, "status": "evaluated", "detail": detail}


def _first_difference(left, right):
    """两字符串首个不一致的下标；完全相同返回 -1（长度不同取重合末尾）。"""
    for index in range(min(len(left), len(right))):
        if left[index] != right[index]:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return -1


def _disclosed_assertions_without_subject(release_manifest):
    """独立解析 ReleaseManifest 对无主体断言的披露（INTERFACES §3.8）。

    口径：``known_defects`` 恰 1 条 ``code == "assertion_without_subject"``，其 ``detail``
    为 ``"N: id1,id2,…"`` 且 N 等于所列 ID 数、ID 不重复。返回升序 ID 列表；无披露或
    格式不符 → ``None``（调用方按未披露处理）。
    """
    items = [
        item
        for item in (release_manifest or {}).get("known_defects") or []
        if isinstance(item, dict) and item.get("code") == "assertion_without_subject"
    ]
    if len(items) != 1 or not isinstance(items[0].get("detail"), str):
        return None
    count, separator, listed = items[0]["detail"].partition(": ")
    if not separator or not count.isdigit():
        return None
    disclosed = [item for item in listed.split(",") if item]
    if int(count) != len(disclosed) or len(set(disclosed)) != len(disclosed):
        return None
    return sorted(disclosed)


def _replay_patches(raw_text, patches):
    """按 DeterministicPatchSet **独立重放**，重建清洗文本。

    ACT 18（D-W8-18）要求 gate 自己实现重放，**不 import** ``pipeline.digitization``
    的 ``apply_patches``：照搬被验对象的实现等于自己验自己。
    逐条按 ``raw_start`` 升序拼接 ``raw[cursor:raw_start]`` + ``replacement``，
    ``cursor = raw_end``；末尾补 ``raw[cursor:]``。
    """
    ordered = sorted(patches, key=lambda patch: patch.get("raw_start", 0))
    parts = []
    cursor = 0
    for patch in ordered:
        parts.append(raw_text[cursor:patch["raw_start"]])
        parts.append(patch["replacement"])
        cursor = patch["raw_end"]
    parts.append(raw_text[cursor:])
    return "".join(parts)


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
    snapshot_knowledge=None,
    graph_projection_pack=None,
    raw_text_binding=None,
    raw_text=None,
    sanitization_report=None,
    deterministic_patch_set=None,
    cleaned_text=None,
    checks_override=None,
):
    """独立判定 M8 发布物（§16:703-715）。返回见模块 docstring 与 ACT 契约。

    ACT 12 新增可选冻结输入（缺省 None，向后兼容 K1/K2 既有调用）：
    - ``snapshot_knowledge``：M7 Snapshot knowledge（缺省视为知识链未编译）；
    - ``graph_projection_pack``：GraphProjectionPack（缺省视为未投影）；
    - ``raw_text_binding``：``{sha256}``——RawText/SourceAsset 底本哈希（offset 档）；
    - ``raw_text``：``{text}``——原始底本文本（offset 档）；
    - ``sanitization_report``：M2 清洗报告（offset 档）；
    - ``deterministic_patch_set``：M2 ``DeterministicPatchSet``（offset 档）；
      **``patch_reversible`` 的权威产物**（ACT 18 / D-W8-18，不是 SanitizationReport）；
    - ``cleaned_text``：``{text}``——清洗后文本（offset 档，供重放比对）；
    - ``checks_override``：仅用于自检注入（将检查项 ok 强改为 True 必须导致
      passed 翻转失败）。
    """
    checks = {}

    def run(name, func):
        try:
            checks[name] = func()
        except Exception as exc:  # noqa: BLE001 - 设计上所有异常转该项失败
            checks[name] = _fail("%s: %s" % (type(exc).__name__, exc))

    # 级别分派（第 107 条 Q-M8-08）：不适用 → not_applicable，不得冒充 ok
    evidence_level = evidence_map_pack.get("evidence_level", "glyphbox_level")
    knowledge_compiled = evidence_map_pack.get("knowledge_chain") == "compiled"

    def applicable(name):
        scope = _CHECK_APPLICABILITY[name]
        if scope == "both":
            return True
        if scope == "glyphbox":
            return evidence_level == "glyphbox_level"
        if scope == "offset":
            return evidence_level == "offset_level"
        if scope == "knowledge":
            # 知识链五项：已编译时实评，未编译时 not_applicable
            return knowledge_compiled
        return True  # transition 项恒执行（内部自判 not_evaluated）

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
        """偏移/文本/quote 与 ``spans_doc`` 对账（ACT 17 二.1：按档分派键集）。

        glyphbox 档：四项（start/end/line_index/text）逐字不变。
        offset 档：entry 按 ACT 14 二.1 **有意不造** ``line_index``，故比 start/end/text
        与 ``quote_sha256`` 自洽、``content_status``；偏移合法性与不重叠归
        ``offset_anchor_continuity``（两项断言不同，实测对照见回报）。
        """
        entries = evidence_map_pack["entries"]
        by_id = _spans_by_id(spans_doc)
        glyphbox = evidence_level == "glyphbox_level"
        for key, entry in entries.items():
            span = by_id[key]
            if glyphbox:
                if (
                    entry["start_offset"] != span["start_offset"]
                    or entry["end_offset"] != span["end_offset"]
                    or entry["line_index"] != span["line_index"]
                    or entry["text"] != span["text"]
                ):
                    return _fail("offset/line_index/text 与 spans_doc 不符: %s" % key)
            else:
                if (
                    entry["start_offset"] != span["start_offset"]
                    or entry["end_offset"] != span["end_offset"]
                    or entry["text"] != span["text"]
                ):
                    return _fail("offset/text 与 spans_doc 不符: %s" % key)
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
        if evidence_level == "offset_level":
            # ACT 17 二.3：offset 档的 SourceAsset 事实 = manifest.source_assets +
            # RawText 修订 sha256（ACT 14 三同口径）。本档无页图几何、asset_records 为 {},
            # entry 亦不带 image_sha256 / source_asset_artifact_revision_id。
            raw_text_sha256 = (
                raw_text_binding.get("sha256")
                if isinstance(raw_text_binding, dict)
                else None
            )
            if not raw_text_sha256:
                return _fail("offset 档缺 raw_text_binding.sha256，无法绑定底本")
            for page in page_order:
                if not (
                    pack_pages[page]["sha256"]
                    == assets[page]["sha256"]
                    == raw_text_sha256
                ):
                    return _fail(
                        "页 %s 底本哈希三方不一致（资产包/清单/RawText）" % page
                    )
            return _ok("资产包、清单与 RawText 修订三方绑定一致")
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

    # 14 knowledge_chain（过渡项：未编译 → not_evaluated；已编译 → 实评汇总）。
    # 注意：实评汇总需要 #15–#19、#23 的结果，真正的汇总在闭集循环之后执行。
    def check_knowledge_chain():
        value = evidence_map_pack["knowledge_chain"]
        if value == "not_compiled":
            return {
                "ok": None,
                "status": "not_evaluated",
                "detail": "KnowledgeEntry→Assertion→EvidenceLink 未编译",
            }
        if value == "compiled":
            return {
                "ok": None,
                "status": "pending",
                "detail": "知识链五项实评后汇总",
            }
        return {
            "ok": False,
            "status": "evaluated",
            "detail": "knowledge_chain 声称非 not_compiled/compiled: %r" % (value,),
        }

    # 15 chain_closure
    def check_chain_closure():
        knowledge = snapshot_knowledge
        if not isinstance(knowledge, dict):
            return _fail("snapshot_knowledge 缺失，无法实评知识链")
        patterns = {
            pat["pattern_id"]: pat
            for pat in knowledge.get("patterns", [])
            if pat.get("pattern_id")
        }
        assertions = {
            a["assertion_id"]: a
            for a in knowledge.get("assertions", [])
            if a.get("assertion_id")
        }
        # 双轨显式引用（与 packs.build_knowledge_data_pack 同一口径，独立重算）
        entry_map = {}
        for pat_id, pat in patterns.items():
            for aid in pat.get("assertion_ids") or []:
                if aid not in assertions:
                    return _fail("pattern.assertion_ids 悬空: %s -> %s" % (pat_id, aid))
                entry_map.setdefault(aid, []).append(pat_id)
        for a in knowledge.get("assertions", []):
            for cid in a.get("concept_refs") or []:
                if not any(
                    c.get("concept_id") == cid
                    for c in knowledge.get("concepts", [])
                ):
                    return _fail(
                        "assertion.concept_refs 悬空: %s -> %s"
                        % (a["assertion_id"], cid)
                    )
                entry_map.setdefault(a["assertion_id"], []).append(cid)
        if not entry_map:
            return _ev(False, "知识链为空：无任何 entry（无主体 assertion 不生成 entry）")
        # 每个 entry 至少 1 条 assertion 且 assertion 存在
        for subject, aids in entry_map.items():
            if not aids:
                return _ev(False, "entry 无 assertion: %s" % subject)
        return _ev(
            True,
            "知识链闭合：%d 个主体词条、%d 条断言（双轨显式引用）"
            % (len(entry_map), len(assertions)),
        )

    # 16 no_assertion_bypass
    def check_no_assertion_bypass():
        knowledge = snapshot_knowledge
        if not isinstance(knowledge, dict):
            return _fail("snapshot_knowledge 缺失，无法实评知识链")
        assertion_ids = {
            a["assertion_id"] for a in knowledge.get("assertions", [])
        }
        referenced = set()
        for pat in knowledge.get("patterns", []):
            referenced.update(pat.get("assertion_ids") or [])
        for a in knowledge.get("assertions", []):
            # 第 107 条 Q-M8-01 双轨：assertion 自身带 concept_refs 即有显式主体
            # （与 chain_closure 同口径；此前误把 concept ID 记进「已引用断言」集合）
            if a.get("concept_refs"):
                referenced.add(a["assertion_id"])
        bypass = sorted(assertion_ids - referenced)
        if not bypass:
            return _ev(True, "全部 assertion 均经显式引用接入知识链")
        # INTERFACES §3.8：无主体断言不生成 entry，须在 known_defects 以
        # 「assertion_without_subject: N」逐条列 ID 如实披露；逐字相符才不判违约。
        disclosed = _disclosed_assertions_without_subject(release_manifest)
        if disclosed == bypass:
            return _ev(
                True,
                "无主体断言 %d 条不生成 entry，已按 §3.8 如实披露: %s"
                % (len(bypass), ",".join(bypass)),
            )
        return _ev(
            False,
            "assertion 未被 entry 显式引用（不得绕过 Assertion），且未如实披露为"
            " assertion_without_subject: %s（披露: %r）" % (",".join(bypass), disclosed),
        )

    # 17 quote_hash_integrity
    def check_quote_hash_integrity():
        knowledge = snapshot_knowledge
        if not isinstance(knowledge, dict):
            return _fail("snapshot_knowledge 缺失，无法实评知识链")
        spans_by_id = _spans_by_id(spans_doc)
        for a in knowledge.get("assertions", []):
            for ev in a.get("evidence") or []:
                qh = ev.get("quote_sha256")
                if not qh:
                    return _fail(
                        "assertion.evidence 缺 quote_sha256: %s" % a["assertion_id"]
                    )
                span = spans_by_id.get(ev["source_span_id"])
                if span is None:
                    return _fail(
                        "evidence 引用悬空 span: %s -> %s"
                        % (a["assertion_id"], ev["source_span_id"])
                    )
                start = ev.get("start_offset")
                end = ev.get("end_offset")
                if start is None or end is None:
                    return _fail(
                        "evidence 缺偏移: %s" % a["assertion_id"]
                    )
                # 【I-11】evidence 偏移为相对页块的绝对偏移（与 corpus_spans 同一坐标系，
                # start_offset = span.start_offset + 局部起点）→ 局部 = 绝对 − span.start_offset；
                # 不猜局部、不退回整片段（G7-RULINGS 第 106 条 D1）。
                local_start = start - span["start_offset"]
                local_end = end - span["start_offset"]
                if not (0 <= local_start <= local_end <= len(span["text"])):
                    return _fail(
                        "evidence 偏移越出 span（I-11 绝对偏移）: %s [%d,%d) span=[%d,%d)"
                        % (
                            a["assertion_id"], start, end,
                            span["start_offset"], span["start_offset"] + len(span["text"]),
                        )
                    )
                recomputed = _sha256(
                    span["text"][local_start:local_end].encode("utf-8")
                )
                if qh != recomputed:
                    return _ev(
                        False,
                        "quote_sha256 与正文重算不符: %s [%d,%d)"
                        % (a["assertion_id"], start, end),
                    )
        return _ev(True, "quote_sha256 逐条与 span 正文切片重算一致")

    # 18 content_status_admission
    def check_content_status_admission():
        knowledge = snapshot_knowledge
        if not isinstance(knowledge, dict):
            return _fail("snapshot_knowledge 缺失，无法实评知识链")
        if consumption_level == "PUBLIC_RELEASE":
            for a in knowledge.get("assertions", []):
                if a.get("content_status") != "expert_verified":
                    return _ev(
                        False,
                        "PUBLIC_RELEASE 要求 expert_verified: %s = %r"
                        % (a["assertion_id"], a.get("content_status")),
                    )
        elif consumption_level == "DEV_SEARCH":
            for a in knowledge.get("assertions", []):
                if a.get("content_status") not in (
                    "expert_verified",
                    "cross_model_reviewed",
                    "source_verified",
                ):
                    return _ev(
                        False,
                        "DEV_SEARCH 要求可判定内容不低于 cross_model_reviewed: %s = %r"
                        % (a["assertion_id"], a.get("content_status")),
                    )
        return _ev(
            True,
            "知识链内容状态符合 %s 准入" % consumption_level,
        )

    # 19 offset_anchor_continuity
    def check_offset_anchor_continuity():
        entries = evidence_map_pack["entries"]
        last_end = -1
        for key in sorted(entries):
            start = entries[key]["start_offset"]
            end = entries[key]["end_offset"]
            if not (0 <= start <= end):
                return _fail("span 偏移非法: %s [%d,%d)" % (key, start, end))
            if start < last_end:
                return _fail(
                    "span 偏移重叠/乱序: %s start=%d < 前段 end=%d"
                    % (key, start, last_end)
                )
            last_end = end
        return _ok("offset 档锚点连续无重叠，共 %d 段" % len(entries))

    # 20 patch_reversible
    def check_patch_reversible():
        # 权威产物 = DeterministicPatchSet（ACT 18 / D-W8-18），不是 SanitizationReport
        patches = deterministic_patch_set
        if patches is None:
            return _fail("DeterministicPatchSet 缺失，无法实评双向可逆")
        if not isinstance(patches, list):
            return _fail("DeterministicPatchSet 非列表: %s" % type(patches).__name__)
        raw = (raw_text or {}).get("text")
        if not isinstance(raw, str):
            return _fail("raw_text.text 缺失，无法重放 DeterministicPatchSet")
        cleaned = (cleaned_text or {}).get("text")
        if not isinstance(cleaned, str):
            return _fail("cleaned_text.text 缺失，无法重放 DeterministicPatchSet")

        # 形状前置校验（ACT 18 一.4 保留；不得单独构成通过条件）
        cursor = None
        for patch in patches:
            raw_start = patch.get("raw_start")
            raw_end = patch.get("raw_end")
            cleaned_start = patch.get("cleaned_start")
            cleaned_end = patch.get("cleaned_end")
            if None in (raw_start, raw_end, cleaned_start, cleaned_end):
                return _fail("patch 缺偏移字段: %r" % (patch.get("patch_id"),))
            if not (0 <= raw_start <= raw_end) or not (0 <= cleaned_start <= cleaned_end):
                return _fail("patch 偏移非法: %r" % (patch.get("patch_id"),))
            if raw_end > len(raw):
                return _fail(
                    "patch raw 区间越出 raw_text: %r" % (patch.get("patch_id"),)
                )
            if cursor is not None and raw_start < cursor:
                return _fail("patch 区间重叠/乱序: %r" % (patch.get("patch_id"),))
            cursor = raw_end
            replacement = patch.get("replacement")
            if replacement is None:
                return _fail("patch 缺 replacement: %r" % (patch.get("patch_id"),))
            if cleaned_end - cleaned_start != len(replacement):
                return _fail(
                    "patch cleaned 区间与 replacement 长度不符: %r"
                    % (patch.get("patch_id"),)
                )

        if not patches:
            # ACT 18 一.6：0 条 patch 仍可过，但须同时断言 raw == cleaned（堵旧假绿路）
            if raw != cleaned:
                return _fail(
                    "DeterministicPatchSet 0 条 patch，但 raw_text != cleaned_text"
                    "（首个不一致偏移 %d）" % _first_difference(raw, cleaned)
                )
            return _ok(
                "DeterministicPatchSet 重放可逆（0 条 patch）：raw_text == cleaned_text"
                "（%d 字符）" % len(raw)
            )

        # 真重算（ACT 18 一.2）：raw_text + patches 重建清洗文本，与 cleaned_text 逐字节比对
        rebuilt = _replay_patches(raw, patches)
        if rebuilt != cleaned:
            return _fail(
                "DeterministicPatchSet 重放结果与 cleaned_text 不一致"
                "（首个不一致偏移 %d）" % _first_difference(rebuilt, cleaned)
            )
        return _ok(
            "DeterministicPatchSet 重放可逆：%d 条 patch，重放文本与 cleaned_text 逐字节一致"
            % len(patches)
        )

    # 21 raw_text_binding
    def check_raw_text_binding():
        if not isinstance(raw_text_binding, dict) or not raw_text_binding.get("sha256"):
            return _fail("raw_text_binding 缺失或无 sha256")
        raw_text_doc = raw_text or {}
        text = raw_text_doc.get("text")
        if not isinstance(text, str):
            return _fail("raw_text.text 缺失")
        recomputed = _sha256(text.encode("utf-8"))
        if recomputed != raw_text_binding["sha256"]:
            return _fail("raw_text SHA-256 与绑定值不符")
        # 底本哈希须与资产包一致（offset 档第 7 段 source_asset.sha256）
        pages = source_asset_pack.get("pages") or []
        if pages:
            sha_list = {page.get("sha256") for page in pages}
            if raw_text_binding["sha256"] not in sha_list:
                return _fail(
                    "raw_text sha 不在 SourceAssetPack 资产哈希集合内"
                )
        return _ok("原始文本切片与 RawText 哈希绑定一致")

    # 22 sanitization_disclosure（第 103 条 D1 同口径）
    def check_sanitization_disclosure():
        report = sanitization_report
        if not isinstance(report, dict):
            return _fail("sanitization_report 缺失")
        findings = report.get("findings") or []
        raw_text_doc = raw_text or {}
        text = raw_text_doc.get("text")
        if not isinstance(text, str):
            return _fail("raw_text.text 缺失")
        forbidden = set("?\u25a1\ufffd")
        uncovered = []
        for index, char in enumerate(text):
            if char in forbidden:
                covered = any(
                    f.get("raw_start", -1) <= index < f.get("raw_end", -1)
                    for f in findings
                )
                if not covered:
                    uncovered.append(index)
        unresolvable = [
            f
            for f in findings
            if f.get("terminal_state") == "known_unresolvable"
        ]
        if uncovered and not unresolvable:
            return _fail(
                "文本含 %d 处禁止字符但发现无 known_unresolvable 终态" % len(uncovered)
            )
        if uncovered:
            return _ok(
                "禁止字符已与 known_unresolvable 发现对账披露（%d 处）" % len(uncovered)
            )
        return _ok("清洗文本无未披露禁止字符")

    # 23 graph_projection_closure
    def check_graph_projection_closure():
        if not isinstance(graph_projection_pack, dict):
            return _fail("graph_projection_pack 缺失，无法实评投影闭合")
        if graph_projection_pack.get("release_id") != release_manifest["release_id"]:
            return _fail("graph_projection.release_id 与 ReleaseManifest 不符")
        expected_hash = release_manifest["canonical_hash"]
        if graph_projection_pack.get("canonical_hash") != expected_hash:
            return _fail("graph_projection.canonical_hash 与 ReleaseManifest 不符")
        if graph_projection_pack.get("consumption_level") != consumption_level:
            return _fail("graph_projection.consumption_level 与清单不符")
        nodes = graph_projection_pack.get("nodes") or []
        edges = graph_projection_pack.get("edges") or []
        if graph_projection_pack.get("node_count") != len(nodes):
            return _fail("node_count 与 nodes 长度不符")
        if graph_projection_pack.get("edge_count") != len(edges):
            return _fail("edge_count 与 edges 长度不符")
        node_ids = [n.get("node_id") for n in nodes]
        if node_ids != sorted(node_ids):
            return _fail("nodes 未按 node_id 升序排列")
        if len(set(node_ids)) != len(node_ids):
            return _fail("node_id 重复")
        triples = [(e.get("source"), e.get("relation"), e.get("target")) for e in edges]
        if triples != sorted(triples):
            return _ev(False, "edges 未按三元组升序排列")
        if any("edge_id" in e or "id" in e for e in edges):
            return _ev(False, "edge 不得携带独立 ID（【I-10】）")
        return _ev(
            True,
            "GraphProjection 闭合：%d 节点 %d 边，canonical_hash 一致"
            % (len(nodes), len(edges)),
        )

    # 闭集固定顺序执行；不适用项输出 not_applicable（第 107 条 Q-M8-08）
    _RUNNERS = {
        "span_identity": check_span_identity,
        "span_page_binding": check_span_page_binding,
        "text_offsets": check_text_offsets,
        "glyph_anchor_closure": check_glyph_anchor_closure,
        "highlight_level": check_highlight_level,
        "ocr_page_binding": check_ocr_page_binding,
        "source_asset_binding": check_source_asset_binding,
        "coordinate_frame": check_coordinate_frame,
        "reverse_index": check_reverse_index,
        "release_manifest_hashes": check_release_manifest_hashes,
        "input_reconciliation": check_input_reconciliation,
        "consumption_level": check_consumption_level,
        "watermark_disclosure": check_watermark_disclosure,
        "knowledge_chain": check_knowledge_chain,
        "chain_closure": check_chain_closure,
        "no_assertion_bypass": check_no_assertion_bypass,
        "quote_hash_integrity": check_quote_hash_integrity,
        "content_status_admission": check_content_status_admission,
        "offset_anchor_continuity": check_offset_anchor_continuity,
        "patch_reversible": check_patch_reversible,
        "raw_text_binding": check_raw_text_binding,
        "sanitization_disclosure": check_sanitization_disclosure,
        "graph_projection_closure": check_graph_projection_closure,
    }
    for name in _CHECK_NAMES:
        if not applicable(name):
            checks[name] = _not_applicable(
                "不适用证据级别 %s" % evidence_level
            )
        else:
            run(name, _RUNNERS[name])
            if _CHECK_APPLICABILITY[name] == "knowledge":
                # 知识链五项为实评项（含异常转失败路径），补 status=evaluated
                if "status" not in checks[name]:
                    checks[name] = dict(checks[name], status="evaluated")

    # 过渡项 knowledge_chain 的实评汇总（依赖 #15–#19、#23 已出结果）
    if checks["knowledge_chain"].get("status") == "pending":
        knowledge_names = (
            "chain_closure",
            "no_assertion_bypass",
            "quote_hash_integrity",
            "content_status_admission",
            "graph_projection_closure",
        )
        failed = [name for name in knowledge_names if checks[name]["ok"] is not True]
        if failed:
            checks["knowledge_chain"] = {
                "ok": False,
                "status": "evaluated",
                "detail": "知识链实评未过: %s" % ",".join(failed),
            }
        else:
            checks["knowledge_chain"] = {
                "ok": True,
                "status": "evaluated",
                "detail": "知识链五项实评全过",
            }

    # 自检注入：任何检查项被强改为 ok:True 都必须导致整体失败（防冒充）
    if checks_override:
        for name, override in checks_override.items():
            merged = dict(checks[name])
            merged.update(override)
            checks[name] = merged

    passed = all(
        checks[name]["ok"] is True
        for name in _CHECK_NAMES
        if checks[name]["ok"] is not None
    )
    if checks_override:
        passed = False
    failed_checks = [
        name for name in _CHECK_NAMES if checks[name]["ok"] is False
    ]
    knowledge_chain_state = (
        "evaluated" if knowledge_compiled else "not_evaluated"
    )
    return {
        "passed": passed,
        "checks": checks,
        "failed_checks": failed_checks,
        "knowledge_chain": knowledge_chain_state,
    }
