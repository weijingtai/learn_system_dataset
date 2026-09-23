"""mini_release01 的人工决定集读取（夹具数据；用例**不得**手写提案或决定）。

夹具的第二版次（ed99）带一条**同名歧义**提案（R03b：另一个 `pat_` 号与基底格局同名），
第三轮（ed01r2 同书返工）带 R03d/R04/R06 三条人工提案。决定集由
`tools/build_fixture.py` 从**真实提案**推出并落盘（`manifest.yaml` 的 `decisions[]` 登记
轮次与文件），故用例直接读夹具数据即可，见 ACT 28 四与 CHARTER §19.3。
"""

import json
from pathlib import Path

import yaml

FIXTURE = Path(__file__).resolve().parents[2] / "corpus" / "_fixture" / "mini_release01"


def load_manifest() -> dict:
    return yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def decisions_for_round(round_no: int) -> list:
    """读夹具登记的第 `round_no` 轮决定集（`manifest.decisions[]` → 文件 → `decisions`）。"""
    rows = [row for row in load_manifest()["decisions"] if row["round"] == round_no]
    if not rows:
        raise KeyError("夹具未登记第 %d 轮的决定集" % round_no)
    doc = json.loads((FIXTURE / rows[0]["file"]).read_text(encoding="utf-8"))
    return doc["decisions"]


if __name__ == "__main__":  # pragma: no cover - 人工查看用（不进用例）
    for row in load_manifest()["decisions"]:
        print("round %d: %s" % (row["round"], json.dumps(decisions_for_round(row["round"]), ensure_ascii=False)))
