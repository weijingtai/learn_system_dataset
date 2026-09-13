"""纯函数候选装配：证据定位、逐条准入、双路差异、裁决应用、人工闭集 ID。

本模块不读文件、不访问 Ledger、不取时间；随机性只允许经 ``id_factory`` 注入。
坐标语义（README §6.3）：证据的 ``start_offset/end_offset`` 为**相对页块的绝对偏移**
（与 ``corpus_spans`` 同坐标系，``start_offset = span.start_offset + 局部起点``）。
"""

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier

from . import CANDIDATE_SCHEMA_VERSION, CATEGORIES
from .errors import ExtractionRefused
from .serialize import canonical_json, sha256_hex

# 裁决选择闭集（§6.4(a)）
RULING_CHOICES = ("a", "b", "both", "neither")


class _ItemRejected(Exception):
    """模块私有：单条候选被逐条拒收（``reason_code`` 取 §8.2 九码之一）。"""

    def __init__(self, reason_code, detail):
        super().__init__("%s: %s" % (reason_code, detail))
        self.reason_code = reason_code
        self.detail = detail


# ------------------------------------------------------------------ 页块 / 索引
def page_blocks(spans_doc):
    """按 Span 出现顺序，把同页 Span 的 ``text`` 以 ``"\\n"`` 连接。"""
    order = []
    grouped = {}
    for span in spans_doc["spans"]:
        page = span["page"]
        if page not in grouped:
            grouped[page] = []
            order.append(page)
        grouped[page].append(span["text"])
    return {page: "\n".join(grouped[page]) for page in order}


def span_index(spans_doc):
    """返回 ``{span_id: {"order": 全局序号, "span": span}}``；重复 span_id 抛 ID_002。"""
    index = {}
    for order, span in enumerate(spans_doc["spans"]):
        span_id = span["span_id"]
        if span_id in index:
            raise ExtractionRefused("span_id 重复: %s" % span_id, code="ID_002")
        index[span_id] = {"order": order, "span": span}
    return index


# ------------------------------------------------------------------ 证据定位
def locate_evidence(evidence, index):
    """定位一条证据；成功返回规范化证据，失败抛 ``_ItemRejected``（E1–E4）。"""
    span_id = evidence["source_span_id"]
    if span_id not in index:
        raise _ItemRejected("REF_001", "未知 Span: %s" % span_id)
    span = index[span_id]["span"]
    text = span["text"]
    if "span_char_start" in evidence:
        start = evidence["span_char_start"]
        end = evidence["span_char_end"]
        if not (0 <= start < end <= len(text)):
            raise _ItemRejected("TXT_001", "span_char 区间越界: [%d,%d)" % (start, end))
        quote = text[start:end]
        if "quote" in evidence and evidence["quote"] != quote:
            raise _ItemRejected("TXT_001", "区间与 quote 不一致: %r" % (evidence["quote"],))
    elif "quote" in evidence:
        quote = evidence["quote"]
        count = text.count(quote)
        if count == 0:
            raise _ItemRejected("TXT_001", "quote 不在 Span 内")
        if count > 1:
            raise _ItemRejected("TXT_001", "quote 在 Span 内不唯一")
        start = text.index(quote)
        end = start + len(quote)
    else:
        start = 0
        end = len(text)
        quote = text
    start_offset = span["start_offset"] + start
    end_offset = start_offset + (end - start)
    return {
        "source_span_id": span_id,
        "support_type": evidence["support_type"],
        "start_offset": start_offset,
        "end_offset": end_offset,
        "quote": quote,
        "quote_sha256": sha256_hex(quote.encode("utf-8")),
    }


# ------------------------------------------------------------------ 引用校验
def _concept_refs(values, profile):
    """校验概念引用（D-06：只校验不扫描）。"""
    canon = {row["concept_id"] for row in profile["canon"]["concepts"]}
    glossary = {row["concept_id"] for row in profile.get("glossary", [])}
    for value in values:
        kind = ids.kind_of(value)
        if kind == "shared_concept_id":
            if value not in canon:
                raise _ItemRejected("REF_001", "未登记共享概念: %s" % value)
        elif kind == "technique_concept_id":
            if value not in glossary:
                raise _ItemRejected("REF_001", "技法概念表未登记: %s" % value)
        else:
            try:
                ids.validate(kind, value)
            except InvalidIdentifier:
                raise _ItemRejected("ID_001", "概念引用标识非法: %r" % (value,))
            raise _ItemRejected("REF_001", "非概念引用: %s" % value)
    return list(values)


def _school_ids(values, profile):
    """校验流派引用；首切片流派闭集未冻结，任何 school_id 一律 REF_001。"""
    registry = {row["school_id"] for row in profile.get("schools", [])}
    for value in values:
        try:
            ids.validate("school_id", value)
        except InvalidIdentifier:
            raise _ItemRejected("ID_001", "school_id 非法: %r" % (value,))
        if value not in registry:
            raise _ItemRejected("REF_001", "未登记流派: %s" % value)
    return list(values)


def _check_mention_surface(concept_ref, surface, evidence, profile):
    """绑定 ``co_shared_*`` 的概念提及：surface 必须与 canon 字面及证据 quote 一致。"""
    concept = None
    for row in profile["canon"]["concepts"]:
        if row["concept_id"] == concept_ref:
            concept = row
            break
    allowed = set()
    if concept is not None:
        allowed = {concept["surface"]} | set(concept.get("aliases", []))
    if surface not in allowed:
        raise _ItemRejected("TXT_001", "surface 与共享概念字面不符: %s" % surface)
    if not evidence or evidence[0]["quote"] != surface:
        raise _ItemRejected("TXT_001", "surface 与证据 quote 不一致: %s" % surface)


def _homograph_guard(surface, profile):
    """未绑定概念提及不得使用同形字面（§12.1:550 禁止裸绑字面）。"""
    surfaces = set()
    for entry in profile.get("homographs", []):
        if isinstance(entry, dict):
            if "surface" in entry:
                surfaces.add(entry["surface"])
        else:
            surfaces.add(entry)
    if surface in surfaces:
        raise _ItemRejected("REF_001", "同形字面必须绑定技法义项: %s" % surface)


# ------------------------------------------------------------------ 逐条准入
def _normalize_item(category, item, index, profile, lane, item_index):
    """把一条已过形状校验的 item 准入为规范化条目；失败抛 ``_ItemRejected``。"""
    evidence_in = item["evidence"]
    if not evidence_in:
        raise _ItemRejected("SEM_001", "证据为空")
    located = [locate_evidence(row, index) for row in evidence_in]
    located.sort(
        key=lambda row: (
            index[row["source_span_id"]]["order"],
            row["start_offset"],
            row["end_offset"],
        )
    )
    evidence = []
    seen = set()
    for row in located:
        key = (row["source_span_id"], row["start_offset"], row["end_offset"])
        if key in seen:
            continue
        seen.add(key)
        evidence.append(row)
    origin = {"lane": lane, "item_index": item_index}

    if category == "assertion":
        if item.get("layer", "general") == "case":
            raise _ItemRejected("SCH_002", "G4 命例不得作为通则主张")
        concept_refs = _concept_refs(item.get("concept_refs", []), profile)
        school_ids = _school_ids(item.get("school_ids", []), profile)
        return {
            "proposition": item["proposition"],
            "relation": item["relation"],
            "evidence": evidence,
            "conditions": list(item.get("conditions", [])),
            "exceptions": list(item.get("exceptions", [])),
            "concept_refs": sorted(set(concept_refs)),
            "school_ids": sorted(set(school_ids)),
            "layer": item.get("layer", "general"),
            "origin": origin,
        }
    if category == "pattern":
        return {
            "name": item["name"],
            "assertion_propositions": sorted(set(item["assertion_propositions"])),
            "evidence": evidence,
            "interpretation": item.get("interpretation"),
            "origin": origin,
        }
    if category == "school_view":
        _school_ids([item["school_id"]], profile)
        return {
            "school_id": item["school_id"],
            "subject": item["subject"],
            "claim_propositions": sorted(set(item["claim_propositions"])),
            "conflict_key": item.get("conflict_key"),
            "changes_current_judgment": item["changes_current_judgment"],
            "evidence": evidence,
            "origin": origin,
        }
    concept_ref = item.get("concept_ref")
    if concept_ref is not None:
        _concept_refs([concept_ref], profile)
        _check_mention_surface(concept_ref, item["surface"], evidence, profile)
    else:
        _homograph_guard(item["surface"], profile)
    return {
        "surface": item["surface"],
        "concept_ref": concept_ref,
        "evidence": evidence,
        "origin": origin,
    }


def normalize_lane(submission, *, spans_doc, profile):
    """逐条准入一路提交件，返回 ``{category, lane, channel, accepted, rejected}``。"""
    index = span_index(spans_doc)
    category = submission["category"]
    lane = submission["lane"]
    accepted = []
    rejected = []
    for item_index, item in enumerate(submission["items"]):
        try:
            accepted.append(
                _normalize_item(category, item, index, profile, lane, item_index)
            )
        except _ItemRejected as exc:
            rejected.append(
                {
                    "category": category,
                    "lane": lane,
                    "item_index": item_index,
                    "disposition": "refused",
                    "reason_code": exc.reason_code,
                    "detail": exc.detail,
                }
            )
    return {
        "category": category,
        "lane": lane,
        "channel": submission["channel"],
        "accepted": accepted,
        "rejected": rejected,
    }


# ------------------------------------------------------------------ 双路差异
def _key_of(item):
    return tuple(
        (row["source_span_id"], row["start_offset"], row["end_offset"])
        for row in item["evidence"]
    )


def _strip_origin(item):
    return {key: value for key, value in item.items() if key != "origin"}


def _group_by_key(items):
    groups = {}
    for item in items:
        groups.setdefault(_key_of(item), []).append(item)
    return groups


def reconcile_lanes(lane_results, *, required_lanes):
    """检出双路差异：返回 ``{agreed, disputes, rejected}``。

    分歧编号跨 category 连续（category 按 ``CATEGORIES`` 顺序，category 内按
    证据键排序；证据键按 (首证据 Span 序, start, end) 排序，与页块坐标一致）。
    """
    agreed = {}
    disputes = []
    rejected = []
    counter = 0
    for category in CATEGORIES:
        if category not in lane_results:
            continue
        lanes = lane_results[category]
        required = list(required_lanes.get(category, []))
        for lane in required:
            if lane not in lanes:
                raise ExtractionRefused(
                    "缺必需路: %s/%s" % (category, lane), code="REF_001"
                )
        for lane in sorted(lanes):
            rejected.extend(lanes[lane]["rejected"])
        if len(required) <= 1:
            bucket = []
            for lane in sorted(lanes):
                bucket.extend(lanes[lane]["accepted"])
            agreed[category] = bucket
            continue
        a_lane, b_lane = required[0], required[1]
        groups_a = _group_by_key(lanes[a_lane]["accepted"])
        groups_b = _group_by_key(lanes[b_lane]["accepted"])
        bucket = []
        for key in sorted(set(groups_a) | set(groups_b)):
            a_items = groups_a.get(key, [])
            b_items = groups_b.get(key, [])
            a_bodies = sorted(canonical_json(_strip_origin(row)) for row in a_items)
            b_bodies = sorted(canonical_json(_strip_origin(row)) for row in b_items)
            if a_bodies and a_bodies == b_bodies:
                bucket.extend(a_items)
            else:
                counter += 1
                disputes.append(
                    {
                        "dispute_id": "m4_d%03d" % counter,
                        "category": category,
                        "key": [list(part) for part in key],
                        "a": list(a_items),
                        "b": list(b_items),
                    }
                )
        agreed[category] = bucket
    return {"agreed": agreed, "disputes": disputes, "rejected": rejected}


# ------------------------------------------------------------------ 裁决 + 装配
def _first_evidence_key(item, index):
    evidence = item["evidence"][0]
    return (
        index[evidence["source_span_id"]]["order"],
        evidence["start_offset"],
        evidence["end_offset"],
    )


def assemble_candidates(
    *,
    spans_doc,
    profile,
    lane_results,
    required_lanes,
    rulings,
    id_range,
    id_factory=None,
):
    """应用裁决并装配 ``candidate_set``（确定性；随机性只经 ``id_factory``）。"""
    for dispute_id, choice in rulings.items():
        if choice not in RULING_CHOICES:
            raise ExtractionRefused(
                "裁决 choice 非法: %r（%s）" % (choice, dispute_id), code="SCH_002"
            )
    rec = reconcile_lanes(lane_results, required_lanes=required_lanes)
    known = {row["dispute_id"] for row in rec["disputes"]}
    for row in rec["disputes"]:
        if row["dispute_id"] not in rulings:
            raise ExtractionRefused("存在未裁决分歧: %s" % row["dispute_id"])
    for dispute_id in rulings:
        if dispute_id not in known:
            raise ExtractionRefused("未知 dispute_id: %s" % dispute_id, code="REF_001")

    technique_id = profile["technique_id"]
    index = span_index(spans_doc)
    factory = id_factory or ids.new_id

    resolved = {category: [] for category in CATEGORIES}
    for category, items in rec["agreed"].items():
        for item in items:
            resolved[category].append(
                {"item": item, "content_status": "machine_extracted"}
            )
    rejected = list(rec["rejected"])
    for row in rec["disputes"]:
        choice = rulings[row["dispute_id"]]
        if choice == "a":
            for item in row["a"]:
                resolved[row["category"]].append(
                    {"item": item, "content_status": "machine_extracted"}
                )
        elif choice == "b":
            for item in row["b"]:
                resolved[row["category"]].append(
                    {"item": item, "content_status": "machine_extracted"}
                )
        elif choice == "both":
            for item in row["a"] + row["b"]:
                resolved[row["category"]].append(
                    {"item": item, "content_status": "disputed"}
                )
        else:  # neither
            for item in row["a"] + row["b"]:
                rejected.append(
                    {
                        "category": row["category"],
                        "lane": item["origin"]["lane"],
                        "item_index": item["origin"]["item_index"],
                        "disposition": "ruled_out",
                        "reason_code": None,
                        "detail": "裁决 neither：两路条目均排除",
                    }
                )

    # ---- assertions ----
    ranked = sorted(
        resolved["assertion"],
        key=lambda entry: _first_evidence_key(entry["item"], index)
        + (entry["item"]["proposition"], entry["item"]["relation"]),
    )
    assertions = []
    assertion_ids_by_proposition = {}
    number = id_range["assertion"][0]
    for entry in ranked:
        if number > id_range["assertion"][1]:
            raise ExtractionRefused(
                "assertion 号段耗尽: %r" % (id_range["assertion"],), code="ID_001"
            )
        item = entry["item"]
        assertion_id = "as_%s_%06d" % (technique_id, number)
        assertions.append(
            {
                "assertion_id": assertion_id,
                "proposition_id": "pr_%s_%06d" % (technique_id, number),
                "proposition": item["proposition"],
                "relation": item["relation"],
                "evidence": item["evidence"],
                "conditions": item["conditions"],
                "exceptions": item["exceptions"],
                "concept_refs": item["concept_refs"],
                "school_ids": item["school_ids"],
                "layer": item["layer"],
                "content_status": entry["content_status"],
                "origin": item["origin"],
            }
        )
        assertion_ids_by_proposition.setdefault(item["proposition"], []).append(
            assertion_id
        )
        number += 1

    # ---- patterns ----
    ranked = sorted(
        resolved["pattern"],
        key=lambda entry: (entry["item"]["name"],)
        + _first_evidence_key(entry["item"], index),
    )
    patterns = []
    pattern_ids_by_name = {}
    number = id_range["pattern"][0]
    for entry in ranked:
        item = entry["item"]
        assertion_ids = []
        missing = None
        for proposition in item["assertion_propositions"]:
            matched = assertion_ids_by_proposition.get(proposition)
            if not matched:
                missing = proposition
                break
            assertion_ids.extend(matched)
        if missing is not None:
            rejected.append(
                {
                    "category": "pattern",
                    "lane": item["origin"]["lane"],
                    "item_index": item["origin"]["item_index"],
                    "disposition": "refused",
                    "reason_code": "REF_001",
                    "detail": "主张未解析到 assertion: %s" % missing,
                }
            )
            continue
        if number > id_range["pattern"][1]:
            raise ExtractionRefused(
                "pattern 号段耗尽: %r" % (id_range["pattern"],), code="ID_001"
            )
        pattern_id = "pat_%s_%06d" % (technique_id, number)
        patterns.append(
            {
                "pattern_id": pattern_id,
                "name": item["name"],
                "assertion_ids": sorted(set(assertion_ids)),
                "evidence": item["evidence"],
                "interpretation": item["interpretation"],
                "interpretation_status": (
                    "not_captured" if item["interpretation"] is None else "captured"
                ),
                "recognition_rule_status": "not_captured",
                "content_status": entry["content_status"],
                "origin": item["origin"],
            }
        )
        pattern_ids_by_name[item["name"]] = pattern_id
        number += 1

    # ---- school_views ----
    ranked = sorted(
        resolved["school_view"],
        key=lambda entry: (
            entry["item"]["school_id"],
            entry["item"]["subject"]["kind"],
            entry["item"]["subject"]["key"],
        )
        + _first_evidence_key(entry["item"], index),
    )
    school_views = []
    conflict_groups = {}
    for entry in ranked:
        item = entry["item"]
        subject = item["subject"]
        if subject["kind"] == "assertion":
            target = (assertion_ids_by_proposition.get(subject["key"]) or [None])[0]
        else:
            target = pattern_ids_by_name.get(subject["key"])
        claim_refs = []
        resolvable = target is not None
        if resolvable:
            for proposition in item["claim_propositions"]:
                matched = assertion_ids_by_proposition.get(proposition)
                if not matched:
                    resolvable = False
                    break
                claim_refs.extend(matched)
        if not resolvable:
            rejected.append(
                {
                    "category": "school_view",
                    "lane": item["origin"]["lane"],
                    "item_index": item["origin"]["item_index"],
                    "disposition": "refused",
                    "reason_code": "REF_001",
                    "detail": "subject / claim 未能解析到已装配对象",
                }
            )
            continue
        conflict_key = item["conflict_key"]
        if conflict_key is None:
            conflict_group_id = None
        else:
            if conflict_key not in conflict_groups:
                conflict_groups[conflict_key] = factory("conflict_group_id")
            conflict_group_id = conflict_groups[conflict_key]
        source_refs = []
        seen_refs = set()
        for evidence in item["evidence"]:
            span_id = evidence["source_span_id"]
            if span_id in seen_refs:
                continue
            seen_refs.add(span_id)
            source_refs.append(
                {"source_id": spans_doc["source_id"], "source_span_id": span_id}
            )
        school_views.append(
            {
                "school_view_id": factory("school_view_id"),
                "school_id": item["school_id"],
                "subject_entity_id": target,
                "claim_refs": sorted(set(claim_refs)),
                "conflict_group_id": conflict_group_id,
                "changes_current_judgment": item["changes_current_judgment"],
                "source_refs": source_refs,
                "evidence": item["evidence"],
                "content_status": entry["content_status"],
                "origin": item["origin"],
            }
        )

    # ---- concept_mentions / new_concept_candidates ----
    ranked = sorted(
        resolved["concept_mention"],
        key=lambda entry: _first_evidence_key(entry["item"], index)
        + (entry["item"]["surface"],),
    )
    concept_mentions = []
    new_concept_candidates = []
    for entry in ranked:
        item = entry["item"]
        if item["concept_ref"] is not None:
            concept_mentions.append(
                {
                    "surface": item["surface"],
                    "concept_ref": item["concept_ref"],
                    "evidence": item["evidence"],
                    "content_status": entry["content_status"],
                    "origin": item["origin"],
                }
            )
        else:
            new_concept_candidates.append(
                {
                    "surface": item["surface"],
                    "technique_id": technique_id,
                    "evidence": item["evidence"],
                    "content_status": entry["content_status"],
                    "origin": item["origin"],
                }
            )

    rejected.sort(
        key=lambda row: (
            CATEGORIES.index(row["category"]),
            row["lane"],
            row["item_index"],
        )
    )
    disputes = [
        {
            "dispute_id": row["dispute_id"],
            "category": row["category"],
            "key": row["key"],
            "choice": rulings[row["dispute_id"]],
        }
        for row in rec["disputes"]
    ]
    counts = {
        "assertions": len(assertions),
        "patterns": len(patterns),
        "school_views": len(school_views),
        "concept_mentions": len(concept_mentions),
        "new_concept_candidates": len(new_concept_candidates),
        "rejected": len(rejected),
        "disputes": len(disputes),
        "human_decisions": len(rulings),
    }
    source_channels = {}
    for category, lanes in lane_results.items():
        source_channels[category] = {
            lane: lanes[lane]["channel"] for lane in sorted(lanes)
        }
    candidate_set = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "technique_id": technique_id,
        "source_id": spans_doc["source_id"],
        "edition_part_artifact_id": spans_doc["edition_part_artifact_id"],
        "evidence_level": spans_doc["evidence_level"],
        "span_layer": "structural",
        "source_channels": source_channels,
        "assertions": assertions,
        "patterns": patterns,
        "school_views": school_views,
        "concept_mentions": concept_mentions,
        "new_concept_candidates": new_concept_candidates,
        "rejected": rejected,
        "disputes": disputes,
        "counts": counts,
    }
    candidate_bytes = canonical_json(candidate_set)
    lane_bytes = {
        "%s/%s" % (category, lane): canonical_json(lane_results[category][lane])
        for category in lane_results
        for lane in sorted(lane_results[category])
    }
    content_status_counts = {}
    for row in (
        assertions
        + patterns
        + school_views
        + concept_mentions
        + new_concept_candidates
    ):
        status = row["content_status"]
        content_status_counts[status] = content_status_counts.get(status, 0) + 1
    return {
        "candidate_set": candidate_set,
        "candidate_bytes": candidate_bytes,
        "candidate_sha256": sha256_hex(candidate_bytes),
        "lane_bytes": lane_bytes,
        "content_status_counts": content_status_counts,
    }
