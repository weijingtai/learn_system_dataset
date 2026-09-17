"""M5 Validator 注册表与错误码映射（规格 §13.1、§8.2 第 3 表）。

``VALIDATORS`` 为 14 项固定顺序元组 ``(validator_id, gate, func_name)``；
``CHECK_CODES`` 是检查名到 §8.2 九码（或 ``None``）的权威映射；``resolve``
按 ``validator_id`` 惰性导入所在模块并返回 ``(gate, func)``。

本模块不 import 任何 Validator 实现模块（避免注册表与实现循环依赖，也让
各 Validator 可独立实现）；``resolve`` 在调用时才导入。

权威「检查名 → 错误码 / None」表（与 ``CHECK_CODES`` 逐项一致）：
    G1：
        object_missing → SRC_001
        hash_mismatch → SRC_003
        page_set_mismatch → REF_001
        page_hash_mismatch → SRC_003
        terminal_state_mismatch → REF_001
        content_sha256_mismatch → SRC_003
        spans_revision_mismatch → REF_001
        source_asset_mismatch → SRC_003（R83：offset 档 SourceAsset 哈希与 raw_text 修订字节不符）
        forbidden_char_in_text → TXT_001
        unresolved_glyph → SRC_001
        unproofread_glyphs → None（§5.5 缺口：无语义吻合码）
        replay_tool_mismatch → None（§5.5 缺口）
        replay_bytes_mismatch → SRC_003
    G2：
        page_missing → REF_001
        page_unregistered → REF_001
        page_without_span → SRC_001
        page_deferred → REF_001
        excluded_page_no_evidence → SEM_001
        coverage_gap → TXT_001
        coverage_overlap → TXT_001
        span_text_mismatch → TXT_001
        span_boundary_mismatch → TXT_001
        batch_span_leak → REF_001
        batch_span_duplicate → ID_002
        batch_cross_page → ID_002
        batch_oversize → SCH_002
        count_mismatch → None（§5.5 缺口）
    G3：
        span_id_format → ID_001
        span_id_duplicate → ID_002
        page_line_mismatch → REF_001
        anchor_offset_mismatch → REF_001（R83：offset 档 span_id 起点偏移段与锚点 raw_start 不符）
        source_id_mismatch → REF_001
        content_status_invalid → SCH_002
        dangling_ref → REF_001
        not_consumable → REF_001
        ref_type_mismatch → REF_001
        offset_out_of_range → TXT_001
        offset_mismatch → TXT_001
        quote_hash_mismatch → TXT_001
        quote_hash_not_stored → SCH_001
        anchor_revision_mismatch → REF_001（R83：offset 档锚点修订号与冻结 M1/M2 修订不符）
        raw_anchor_mismatch → TXT_001（R83：offset 档 patch 映射回原始偏移不成立）
        page_image_hash_mismatch → SRC_003
        line_box_mismatch → TXT_001
        glyph_box_mismatch → TXT_001
        anchor_out_of_page → TXT_001
        anchor_field_missing → SCH_001
        glyph_text_misaligned → TXT_001
        evidence_level_insufficient → SEM_001
        glyphbox_incomplete → SCH_001
        evidence_level_invalid → SCH_002
"""

import importlib

# 14 项 Validator：顺序固定，禁止增删或调序（act/00.yaml contract）
VALIDATORS = (
    ("g1_frozen_bytes", "G1", "validate_frozen_bytes"),
    ("g1_page_registry", "G1", "validate_page_registry"),
    ("g1_content_hashes", "G1", "validate_content_hashes"),
    ("g1_unresolved_chars", "G1", "validate_unresolved_chars"),
    ("g1_replay", "G1", "validate_replay"),
    ("g2_page_accounting", "G2", "validate_page_accounting"),
    ("g2_contiguous_coverage", "G2", "validate_contiguous_coverage"),
    ("g2_batch_partition", "G2", "validate_batch_partition"),
    ("g2_count_reconciliation", "G2", "validate_count_reconciliation"),
    ("g3_span_identity", "G3", "validate_span_identity"),
    ("g3_references", "G3", "validate_references"),
    ("g3_strict_offset_quote", "G3", "validate_strict_offset_quote"),
    ("g3_glyphbox_anchor", "G3", "validate_glyphbox_anchor"),
    ("g3_evidence_level", "G3", "validate_evidence_level"),
)

# 每个 validator_id 的实现模块（resolve 惰性导入用）
_VALIDATOR_MODULES = {
    "g1_frozen_bytes": "pipeline.validation.g1_source",
    "g1_page_registry": "pipeline.validation.g1_source",
    "g1_content_hashes": "pipeline.validation.g1_source",
    "g1_unresolved_chars": "pipeline.validation.g1_source",
    "g1_replay": "pipeline.validation.replay",
    "g2_page_accounting": "pipeline.validation.g2_coverage",
    "g2_contiguous_coverage": "pipeline.validation.g2_coverage",
    "g2_batch_partition": "pipeline.validation.g2_coverage",
    "g2_count_reconciliation": "pipeline.validation.g2_coverage",
    "g3_span_identity": "pipeline.validation.g3_evidence",
    "g3_references": "pipeline.validation.g3_evidence",
    "g3_strict_offset_quote": "pipeline.validation.g3_evidence",
    "g3_glyphbox_anchor": "pipeline.validation.g3_evidence",
    "g3_evidence_level": "pipeline.validation.g3_evidence",
}

# 检查名 → §8.2 九码（或 None）。§5.5 缺口清单：count_mismatch、
# unproofread_glyphs、replay_tool_mismatch 无语义吻合码，取 None。
CHECK_CODES = {
    # ---- G1 来源与可重放性 ----
    "object_missing": "SRC_001",
    "hash_mismatch": "SRC_003",
    "page_set_mismatch": "REF_001",
    "page_hash_mismatch": "SRC_003",
    "terminal_state_mismatch": "REF_001",
    "content_sha256_mismatch": "SRC_003",
    "spans_revision_mismatch": "REF_001",
    "source_asset_mismatch": "SRC_003",
    "forbidden_char_in_text": "TXT_001",
    "unresolved_glyph": "SRC_001",
    "unproofread_glyphs": None,
    "replay_tool_mismatch": None,
    "replay_bytes_mismatch": "SRC_003",
    # ---- G2 全书覆盖 ----
    "page_missing": "REF_001",
    "page_unregistered": "REF_001",
    "page_without_span": "SRC_001",
    "page_deferred": "REF_001",
    "excluded_page_no_evidence": "SEM_001",
    "coverage_gap": "TXT_001",
    "coverage_overlap": "TXT_001",
    "span_text_mismatch": "TXT_001",
    "span_boundary_mismatch": "TXT_001",
    "batch_span_leak": "REF_001",
    "batch_span_duplicate": "ID_002",
    "batch_cross_page": "ID_002",
    "batch_oversize": "SCH_002",
    "count_mismatch": None,
    # ---- G3 身份、引用与证据锚点 ----
    "span_id_format": "ID_001",
    "span_id_duplicate": "ID_002",
    "page_line_mismatch": "REF_001",
    "anchor_offset_mismatch": "REF_001",
    "source_id_mismatch": "REF_001",
    "content_status_invalid": "SCH_002",
    "dangling_ref": "REF_001",
    "not_consumable": "REF_001",
    "ref_type_mismatch": "REF_001",
    "offset_out_of_range": "TXT_001",
    "offset_mismatch": "TXT_001",
    "quote_hash_mismatch": "TXT_001",
    "quote_hash_not_stored": "SCH_001",
    "anchor_revision_mismatch": "REF_001",
    "raw_anchor_mismatch": "TXT_001",
    "page_image_hash_mismatch": "SRC_003",
    "line_box_mismatch": "TXT_001",
    "glyph_box_mismatch": "TXT_001",
    "anchor_out_of_page": "TXT_001",
    "anchor_field_missing": "SCH_001",
    "glyph_text_misaligned": "TXT_001",
    "evidence_level_insufficient": "SEM_001",
    "glyphbox_incomplete": "SCH_001",
    "evidence_level_invalid": "SCH_002",
}


def resolve(validator_id):
    """按 ``validator_id`` 返回 ``(gate, func)``；未登记则抛 ``KeyError``。"""
    for vid, gate, func_name in VALIDATORS:
        if vid == validator_id:
            module = importlib.import_module(_VALIDATOR_MODULES[vid])
            return gate, getattr(module, func_name)
    raise KeyError("未登记的 validator_id: %r" % (validator_id,))
