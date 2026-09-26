"""
兼容入口：旧代码 `from tg_download import ...` / `python tg_download.py` 仍可用。
实现已迁到 tgdl/ 包。
"""

from __future__ import annotations

from tgdl import *  # noqa: F401,F403
from tgdl import __all__  # noqa: F401
from tgdl.runner import main

if __name__ == "__main__":
    main()
