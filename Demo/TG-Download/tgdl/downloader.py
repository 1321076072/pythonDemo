"""单文件续传下载 + 链接级（含媒体组）编排。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

from tgdl.config import ensure_disk_space, history_ok, now_iso, record_result, save_config
from tgdl.control import Cancelled, DownloadControl
from tgdl.links import parse_message_link, resolve_chat
from tgdl.media import album_messages, doc_size, file_complete, is_video_message, suggested_name
from tgdl.progress import make_progress

# 匹配这些关键字才自动重试（用户取消绝不重试）
_RETRY_HINTS = (
    "timeout",
    "timed out",
    "connection",
    "reset",
    "server closed",
    "temporary",
    "flood",
    "wait of",
    "bytes read",
    "network",
)


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, Cancelled):
        return False
    msg = str(exc).lower()
    return any(h in msg for h in _RETRY_HINTS)


async def download_one_document(
    client: TelegramClient,
    message,
    download_dir: Path,
    cfg: dict,
    *,
    url: str,
    chat,
    progress_callback=None,
    log=print,
    control: DownloadControl | None = None,
) -> tuple[Path, bool]:
    """
    单条视频 → *.part（支持 offset 续传）→ size 校验 → rename。
    返回 (最终路径, 是否跳过)。
    """
    if control:
        control.check()
    if not is_video_message(message):
        raise RuntimeError(f"消息 {message.id} 不是视频")

    opts = cfg.get("options") or {}
    skip_existing = bool(opts.get("skip_existing", True))
    req_kb = int(opts.get("request_size_kb") or 512)

    name = suggested_name(message)
    final = download_dir / name
    part = Path(str(final) + ".part")
    expected = doc_size(message)
    doc = message.document
    if doc is None:
        raise RuntimeError(f"消息 {message.id} 无 document")

    hit = history_ok(url, msg_id=message.id)
    if skip_existing and hit:
        p = Path(hit["file"])
        if file_complete(p, hit.get("size") or expected):
            log(f"SKIP 历史: {p}")
            return p, True

    if skip_existing and file_complete(final, expected):
        log(f"SKIP 本地: {final}")
        record_result(
            cfg,
            url=url,
            chat=chat,
            msg_id=message.id,
            path=final,
            size=final.stat().st_size,
            status="ok",
            note="skip_existing",
        )
        return final, True

    if file_complete(part, expected):
        os.replace(part, final)
        log(f"part 已完整 → {final}")
        record_result(
            cfg,
            url=url,
            chat=chat,
            msg_id=message.id,
            path=final,
            size=final.stat().st_size,
            status="ok",
            note="part_rename",
        )
        return final, False

    if part.exists() and expected is not None and part.stat().st_size > expected:
        part.unlink(missing_ok=True)

    ensure_disk_space(
        download_dir,
        (expected or 0) - (part.stat().st_size if part.exists() else 0),
    )

    # MTProto 支持按 offset 拉后续分片 = 真断点续传
    offset = part.stat().st_size if part.exists() else 0
    report = make_progress(progress_callback, control)
    if expected:
        report(offset, expected)

    cfg["last_run"] = {
        "at": now_iso(),
        "current_url": url,
        "chat": chat,
        "msg_id": message.id,
        "status": "downloading",
        "expected_size": expected,
        "offset": offset,
        "part": str(part),
    }
    # 下载中不反复写盘；取消/结束再 save

    if offset > 0:
        log(f"断点续传 msg={message.id} offset={offset}/{expected}")
    else:
        log(f"开始下载 msg={message.id} size={expected}")

    mode = "ab" if offset > 0 else "wb"
    downloaded = offset
    try:
        with part.open(mode) as f:
            async for chunk in client.iter_download(
                doc,
                offset=offset,
                request_size=req_kb * 1024,
            ):
                if control:
                    control.check()
                f.write(chunk)
                downloaded += len(chunk)
                report(downloaded, expected or downloaded)
    except Cancelled:
        log(f"已取消，保留断点: {part} ({downloaded} bytes)")
        cfg["last_run"] = {
            "at": now_iso(),
            "current_url": url,
            "status": "cancelled",
            "part": str(part),
            "size": downloaded,
        }
        save_config(cfg)
        raise

    if expected is not None and part.stat().st_size != expected:
        raise RuntimeError(
            f"大小校验失败 msg={message.id}: got={part.stat().st_size} expected={expected}"
        )

    os.replace(part, final)
    record_result(
        cfg,
        url=url,
        chat=chat,
        msg_id=message.id,
        path=final,
        size=final.stat().st_size,
        status="ok",
    )
    return final, False


async def download_video_from_link(
    client: TelegramClient,
    url: str,
    download_dir: Path,
    cfg: dict,
    *,
    progress_callback=None,
    log=print,
    control: DownloadControl | None = None,
) -> tuple[list[Path], bool]:
    """一条链接 → 解析实体 →（可选）媒体组全视频。返回 (paths, 是否全部跳过)。"""
    if control:
        control.check()
    chat, msg_id = parse_message_link(url)
    opts = cfg.get("options") or {}
    download_group = bool(opts.get("download_group", True))
    max_retries = max(1, int(opts.get("max_retries") or 3))

    entity = await resolve_chat(client, chat)
    message = await client.get_messages(entity, ids=msg_id)
    if control:
        control.check()
    if message is None:
        raise RuntimeError(
            f"消息不存在或无权访问: chat={chat} id={msg_id}。"
            f"若含 ?thread=，请确认话题仍可见。"
        )

    targets = await album_messages(client, entity, message) if download_group else [message]
    videos = [m for m in targets if is_video_message(m)]
    if not videos:
        if isinstance(message.media, MessageMediaPhoto):
            raise RuntimeError("该消息是图片，不是视频")
        raise RuntimeError("该消息/媒体组不包含视频")

    if len(videos) > 1:
        log(f"媒体组: {len(videos)} 个视频")

    download_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    skip_n = 0

    for m in videos:
        last_err: BaseException | None = None
        for attempt in range(max_retries):
            if control:
                control.check()
            try:
                path, skipped = await download_one_document(
                    client,
                    m,
                    download_dir,
                    cfg,
                    url=url,
                    chat=chat,
                    progress_callback=progress_callback,
                    log=log,
                    control=control,
                )
                paths.append(path)
                if skipped:
                    skip_n += 1
                last_err = None
                break
            except Cancelled:
                raise
            except Exception as e:
                last_err = e
                if attempt + 1 >= max_retries or not _retryable(e):
                    break
                wait = 2**attempt
                log(f"瞬时错误，{wait}s 后重试 ({attempt+1}/{max_retries-1}): {e}")
                await asyncio.sleep(wait)
        if last_err is not None:
            record_result(
                cfg,
                url=url,
                chat=chat,
                msg_id=m.id,
                path=None,
                size=None,
                status="fail",
                error=str(last_err),
            )
            raise last_err

    return paths, skip_n == len(paths) and len(paths) > 0
