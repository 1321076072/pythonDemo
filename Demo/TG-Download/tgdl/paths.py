"""路径与版本。打包后所有可写文件落在 exe 旁。"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import cryptg  # noqa: F401

    HAS_CRYPTG = True
except ImportError:
    HAS_CRYPTG = False

VERSION = "1.4.0"
HISTORY_MAX = 200


def app_dir() -> Path:
    """开发：项目根；冻结：exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # tgdl/paths.py → 上一级为项目根
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = app_dir() / "config.json"
HISTORY_PATH = app_dir() / "history.jsonl"
LOCK_PATH = app_dir() / ".instance.lock"
