"""``ent_`` 词条身份发号（第 107 条 Q-M8-02，INTERFACES §3.16）。

``ent_`` 为 UUIDv4 家族（规格 §8.1:318）。确定性由「发号表作为冻结输入」保证：
M8 step 层读取前序 Release 的 ``subject_entity_id → entry_id`` 映射（首个 Release
为空）、为新主体分配 uuid4 并登记为 Artifact；纯函数打包层只接收该映射，
**不得**调用 uuid（``packs.py`` 的模块纯函数护栏亦禁止出现 uuid 字样）。

本模块是唯一允许调用 uuid 的地方（ACT 13 的 step 层从这里导入）。
"""

import uuid

from pipeline.ledger.errors import SchemaViolation

_ENTRY_ID_PREFIX = "ent_"


def allocate_entry_ids(previous_allocation, subject_entity_ids, *, release_id):
    """在 ``previous_allocation`` 基础上为主体集合分配 ``entry_id``。

    - 已有主体沿用旧号（跨 Release 保号）；
    - 新主体 ``uuid.uuid4().hex`` 补号（UUIDv4，版本位为 4）；
    - ``release_id`` 为本次分配发生的 Release（校验形态）；
    - 不修改入参，返回新映射（按 ``subject_entity_id`` 升序排序的字典，
      字典插入序即排序序，供 step 层直接登记发号表 Artifact）。
    """
    from pipeline.ledger import ids

    ids.validate("release_id", release_id)
    if not isinstance(previous_allocation, dict):
        raise SchemaViolation("previous_allocation 必须为字典", code="SCH_002")

    allocation = dict(previous_allocation)
    for subject in subject_entity_ids:
        existing = allocation.get(subject)
        if existing is not None:
            ids.validate("entry_id", existing)
            continue
        allocation[subject] = _ENTRY_ID_PREFIX + uuid.uuid4().hex
    # 稳定输出：按 subject_entity_id 升序重建
    return {subject: allocation[subject] for subject in sorted(allocation)}
