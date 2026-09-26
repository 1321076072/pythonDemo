"""视频判定、文件名、媒体组拉取。"""

from __future__ import annotations

import re

from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    MessageMediaDocument,
)


def is_video_message(message) -> bool:
    if getattr(message, "video", None) is not None:
        return True
    media = message.media
    if not isinstance(media, MessageMediaDocument):
        return False
    doc = media.document
    if not doc:
        return False
    if getattr(doc, "mime_type", "").startswith("video/"):
        return True
    return any(isinstance(a, DocumentAttributeVideo) for a in (doc.attributes or []))


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "video.mp4"


def suggested_name(message) -> str:
    """最终文件名带 msg{id}_ 前缀，避免同名覆盖/误 skip。"""
    doc = getattr(message, "document", None)
    base = None
    if doc:
        for attr in doc.attributes or []:
            if isinstance(attr, DocumentAttributeFilename) and attr.file_name:
                base = attr.file_name
                break
    if not base:
        mime = getattr(doc, "mime_type", "") if doc else ""
        ext = ".mp4" if (mime or "").startswith("video/") else ".bin"
        base = f"msg_{message.id}{ext}"
    safe = safe_filename(base)
    if not safe.startswith(f"msg{message.id}_"):
        safe = f"msg{message.id}_{safe}"
    return safe


def doc_size(message) -> int | None:
    doc = getattr(message, "document", None)
    return int(doc.size) if doc and getattr(doc, "size", None) is not None else None


def file_complete(path, expected: int | None) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    if expected is None:
        return True
    return path.stat().st_size == expected


async def album_messages(client: TelegramClient, chat, message) -> list:
    """同 grouped_id 的相册；无则仅自身。附近 ±12 条足够覆盖常见相册。"""
    gid = getattr(message, "grouped_id", None)
    if not gid:
        return [message]
    lo = max(1, message.id - 12)
    hi = message.id + 12
    msgs = await client.get_messages(chat, ids=list(range(lo, hi + 1)))
    album = [m for m in msgs if m and getattr(m, "grouped_id", None) == gid]
    album.sort(key=lambda m: m.id)
    return album or [message]
