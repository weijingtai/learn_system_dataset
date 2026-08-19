"""gujiorc.core.progress — 进度汇报（本地 + Colab 远程监控）。

对应 PLANS.md M9_：识别进度按百分比隔段汇报，每 ≥5% 输出一次。

- 本地：print 输出百分比 + 进度条
- Colab/远程：写 progress.json 心跳，供本地监控页读取
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import get_root


def _default_posix():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProgressReporter:
    """进度汇报器。

    维护一个 progress.json（原子写入），记录 total/done/current/errors/status，
    并每隔 report_every（默认 5%）打印一次进度条。
    """

    def __init__(
        self,
        total: int,
        report_every: float = 5.0,     # 每 ≥5% 输出一次
        progress_path: str | None = None,  # 绝对或相对路径；默认 root/logs/progress.json
    ):
        self.total = max(total, 1)
        self.report_every = report_every
        self.done = 0
        self.current = ""
        self.errors: list[str] = []
        self.start_time = time.time()
        self.last_reported_pct = -1.0   # 保证第一个就报
        self._progress_path = progress_path
        self._status = "running"

    @property
    def progress_path(self) -> Path:
        if self._progress_path:
            return Path(self._progress_path)
        return Path(get_root()) / "logs" / "progress.json"

    def _write_progress(self):
        """原子写入 progress.json（临时文件 + rename）。"""
        data = {
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "errors": self.errors[-20:],
            "status": self._status,
            "start_time": self.start_time,
            "last_update": _default_timestamp(),
            "pct": round(self.done / self.total * 100, 1),
        }
        path = self.progress_path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)   # 原子

    def tick(self, current: str = ""):
        """完成一项，报告进度."""
        self.done += 1
        self.current = current
        pct = self.done / self.total * 100

        # 每 report_every 输出一次
        if pct >= self.last_reported_pct + self.report_every or self.done == self.total:
            self.last_reported_pct = pct
            bar = _progress_bar(pct, width=30)
            elapsed = time.time() - self.start_time
            print(f"\r识别进度 {bar} {pct:5.1f}%  ({self.done}/{self.total})  "
                  f"当前: {current}  已耗时: {elapsed:.0f}s", flush=True)
            # 写 progress.json（心跳）
            self._write_progress()

    def add_error(self, page: str, msg: str):
        self.errors.append(f"[{page}] {msg}")

    def finish(self):
        self._status = "done"
        self._write_progress()
        print(f"\n✅ 完成 {self.done}/{self.total} 页，耗时 {time.time()-self.start_time:.0f}s", flush=True)


def _default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _progress_bar(pct: float, width: int = 30) -> str:
    filled = int(width * pct / 100)
    bars = "█" * filled + "░" * (width - filled)
    return f"[{bars}]"