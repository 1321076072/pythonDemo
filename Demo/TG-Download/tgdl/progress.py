"""进度回调：节流 + 速度/ETA；windowed 打包时 stdout 可能为 None。"""

from __future__ import annotations

import sys
import time

from tgdl.control import DownloadControl


def make_progress(extra=None, control: DownloadControl | None = None):
    last = {"t": 0.0, "bytes": 0, "speed": 0.0}

    def progress(current: int, total: int) -> None:
        if control:
            control.check()
        if total <= 0:
            return
        now = time.monotonic()
        if last["t"] == 0.0:
            last["t"] = now
            last["bytes"] = current
        dt = now - last["t"]
        if current < total and dt < 0.4:
            return
        if dt > 0:
            last["speed"] = max((current - last["bytes"]) / dt, 0.0)
        last["t"] = now
        last["bytes"] = current
        speed = last["speed"]
        eta = (max(total - current, 0) / speed) if speed > 1 else None
        if extra:
            try:
                extra(current, total, speed, eta)
            except TypeError:
                try:
                    extra(current, total)
                except Exception:
                    pass
            except Exception:
                pass
        out = sys.stdout
        if out is None:
            return
        pct = current * 100 / total
        filled = min(30, int(30 * current / total))
        bar = "#" * filled + "-" * (30 - filled)
        spd = f"{speed/1024/1024:.2f}MB/s" if speed else "-"
        eta_s = f"{int(eta)}s" if eta is not None else "-"
        try:
            out.write(f"\r[{bar}] {pct:5.1f}%  {spd}  ETA {eta_s}  {current}/{total}")
            out.flush()
            if current >= total:
                out.write("\n")
        except Exception:
            pass

    return progress
