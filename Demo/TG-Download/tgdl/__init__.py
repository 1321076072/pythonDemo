"""
TG 视频下载核心包。

模块划分（按数据流）：
  paths/control → config/history → links/proxy → media/progress → downloader/x_download → runner
"""

from __future__ import annotations

from tgdl.paths import (
    CONFIG_PATH,
    HAS_CRYPTG,
    HISTORY_PATH,
    LOCK_PATH,
    VERSION,
    app_dir,
)
from tgdl.control import Cancelled, DownloadControl, acquire_instance_lock, release_instance_lock
from tgdl.config import (
    append_history,
    clear_history,
    disk_free_gb,
    history_ok,
    load_config,
    load_history,
    save_config,
)
from tgdl.links import link_kind, normalize_x_url, parse_message_link, parse_x_status_link, resolve_chat
from tgdl.proxy import build_proxy, probe_proxy, proxy_url
from tgdl.downloader import download_video_from_link
from tgdl.x_download import download_x_video
from tgdl.runner import collect_urls, main, run

__all__ = [
    "VERSION",
    "HAS_CRYPTG",
    "CONFIG_PATH",
    "HISTORY_PATH",
    "LOCK_PATH",
    "app_dir",
    "Cancelled",
    "DownloadControl",
    "acquire_instance_lock",
    "release_instance_lock",
    "load_config",
    "save_config",
    "load_history",
    "append_history",
    "clear_history",
    "history_ok",
    "disk_free_gb",
    "link_kind",
    "normalize_x_url",
    "parse_message_link",
    "parse_x_status_link",
    "resolve_chat",
    "build_proxy",
    "probe_proxy",
    "proxy_url",
    "download_video_from_link",
    "download_x_video",
    "run",
    "collect_urls",
    "main",
]
