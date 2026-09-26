"""取消令牌 + 单实例锁（防多开抢 session）。"""

from __future__ import annotations

import atexit
import os
import sys
import threading

from tgdl.paths import LOCK_PATH


class Cancelled(Exception):
    """用户点了停止。"""


class DownloadControl:
    """跨线程取消：GUI 线程 set，下载回调里 check。"""

    def __init__(self) -> None:
        self._ev = threading.Event()

    def cancel(self) -> None:
        self._ev.set()

    def reset(self) -> None:
        self._ev.clear()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self._ev.is_set():
            raise Cancelled("用户取消")


_lock_fp = None


def acquire_instance_lock() -> bool:
    global _lock_fp
    if _lock_fp is not None:
        return True
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fp = open(LOCK_PATH, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fp.close()
        return False
    fp.seek(0)
    fp.truncate()
    fp.write(f"{os.getpid()}\n".encode())
    fp.flush()
    _lock_fp = fp
    atexit.register(release_instance_lock)
    return True


def release_instance_lock() -> None:
    global _lock_fp
    fp = _lock_fp
    _lock_fp = None
    if fp is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt

            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        fp.close()
    except OSError:
        pass
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass
