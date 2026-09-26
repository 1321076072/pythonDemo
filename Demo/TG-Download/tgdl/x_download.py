"""X / Twitter 状态视频下载。

主路径：fxtwitter 解析直链（多视频全下 + .part 断点）。
失败再回退 yt-dlp 状态页解析。
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from tgdl.config import ensure_disk_space, history_ok, now_iso, record_result, save_config
from tgdl.control import Cancelled, DownloadControl
from tgdl.links import normalize_x_url, parse_x_status_link
from tgdl.media import file_complete, safe_filename
from tgdl.progress import make_progress
from tgdl.proxy import proxy_url

_CHUNK = 256 * 1024

_RETRY_HINTS = (
    "timeout",
    "timed out",
    "connection",
    "reset",
    "temporary",
    "http error 429",
    "http error 5",
    "network",
    "unable to download",
)


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, Cancelled):
        return False
    msg = str(exc).lower()
    return any(h in msg for h in _RETRY_HINTS)


def _target_path(
    download_dir: Path,
    user: str,
    status_id: str,
    *,
    index: int = 0,
    total: int = 1,
    ext: str = "mp4",
) -> Path:
    if total <= 1:
        name = f"x_{user}_{status_id}.{ext.lstrip('.')}"
    else:
        name = f"x_{user}_{status_id}_{index + 1:02d}.{ext.lstrip('.')}"
    return download_dir / safe_filename(name)


def _best_mp4_from_entry(v: dict) -> str | None:
    best_url = None
    best_br = -1
    for fmt in v.get("formats") or v.get("variants") or []:
        u = fmt.get("url") or ""
        path = u.split("?", 1)[0].lower()
        if "m3u8" in path or not path.endswith(".mp4"):
            continue
        br = int(fmt.get("bitrate") or 0)
        if br >= best_br:
            best_br, best_url = br, u
    if best_url:
        return best_url
    top = v.get("url") or ""
    if top and top.split("?", 1)[0].lower().endswith(".mp4"):
        return top
    return None


def _pick_all_mp4s(tweet: dict) -> list[str]:
    """一条推文里所有视频的最高清 mp4（去重保序）。"""
    media = tweet.get("media") or {}
    videos = list(media.get("videos") or [])
    if not videos:
        videos = [m for m in (media.get("all") or []) if (m.get("type") or "") == "video"]
    if not videos:
        raise RuntimeError("该推文无视频媒体")

    out: list[str] = []
    seen: set[str] = set()
    for v in videos:
        u = _best_mp4_from_entry(v)
        if not u:
            continue
        key = u.split("?", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(u)
    if not out:
        raise RuntimeError("fxtwitter 未返回可用 mp4 直链")
    return out


def _resolve_fx_mp4s(user: str, status_id: str, proxy: str | None, log=print) -> list[str]:
    import yt_dlp

    api = f"https://api.fxtwitter.com/{user}/status/{status_id}"
    log(f"fxtwitter: {api}")
    opts: dict = {"quiet": True, "no_warnings": True}
    if proxy:
        opts["proxy"] = proxy
    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = ydl.urlopen(api).read()
    data = json.loads(raw.decode("utf-8", "replace"))
    if not isinstance(data, dict):
        raise RuntimeError(f"fxtwitter 响应异常: {type(data)}")
    if data.get("code") not in (None, 200, "200") and not data.get("tweet"):
        raise RuntimeError(f"fxtwitter 失败: {data.get('message') or data.get('code')}")
    tweet = data.get("tweet")
    if not tweet:
        raise RuntimeError(f"fxtwitter 无 tweet 字段: {data.get('message') or data}")
    return _pick_all_mp4s(tweet)


def _resp_headers(resp) -> dict:
    h = getattr(resp, "headers", None) or {}
    if hasattr(h, "items"):
        return {str(k).lower(): v for k, v in h.items()}
    return {}


def _resp_status(resp) -> int:
    for attr in ("status", "code", "status_code"):
        v = getattr(resp, attr, None)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 200


def _total_size(headers: dict, offset: int, status: int) -> int | None:
    cr = headers.get("content-range") or ""
    if "/" in cr:
        total_s = cr.rsplit("/", 1)[-1].strip()
        if total_s.isdigit():
            return int(total_s)
    cl = headers.get("content-length")
    if cl is not None and str(cl).isdigit():
        n = int(cl)
        return offset + n if status == 206 else n
    return None


def _http_download_resumable(
    url: str,
    final: Path,
    *,
    proxy: str | None,
    progress_callback=None,
    control: DownloadControl | None = None,
    log=print,
) -> Path:
    """直链 HTTP 下载，支持 Range + .part 续传。"""
    import yt_dlp

    try:
        from yt_dlp.networking.common import Request
    except ImportError:  # 极老版本
        Request = None  # type: ignore

    part = Path(str(final) + ".part")
    report = make_progress(progress_callback, control)
    opts: dict = {"quiet": True, "no_warnings": True, "retries": 3}
    if proxy:
        opts["proxy"] = proxy

    offset = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if offset > 0:
        headers["Range"] = f"bytes={offset}-"
        log(f"断点续传 {final.name} offset={offset}")

    with yt_dlp.YoutubeDL(opts) as ydl:
        req = Request(url, headers=headers) if Request is not None else url
        if Request is None and offset > 0:
            # 无法设 Range：删 part 重来
            part.unlink(missing_ok=True)
            offset = 0
            req = url
        resp = ydl.urlopen(req)
        status = _resp_status(resp)
        hdrs = _resp_headers(resp)

        if offset > 0 and status == 200:
            log(f"服务器忽略 Range，重新下载 {final.name}")
            try:
                resp.close()
            except Exception:
                pass
            part.unlink(missing_ok=True)
            offset = 0
            headers.pop("Range", None)
            resp = ydl.urlopen(Request(url, headers=headers) if Request else url)
            status = _resp_status(resp)
            hdrs = _resp_headers(resp)

        total = _total_size(hdrs, offset, status)
        need = (total - offset) if total else 8 * 1024 * 1024
        ensure_disk_space(final.parent, max(need, 0))

        if total:
            report(offset, total)

        mode = "ab" if offset > 0 and status == 206 else "wb"
        if mode == "wb":
            offset = 0
            if part.exists():
                part.unlink()

        downloaded = offset
        try:
            with part.open(mode) as f:
                while True:
                    if control:
                        control.check()
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        report(downloaded, total)
        except Cancelled:
            log(f"已取消，保留断点: {part} ({downloaded} bytes)")
            raise
        finally:
            try:
                resp.close()
            except Exception:
                pass

        if total is not None and part.stat().st_size != total:
            raise RuntimeError(
                f"大小校验失败 {final.name}: got={part.stat().st_size} expected={total}"
            )

    os.replace(part, final)
    if total:
        report(final.stat().st_size, final.stat().st_size)
    return final


def _ydl_download(
    source: str,
    *,
    out_tmpl: str,
    proxy: str | None,
    progress_callback=None,
    control: DownloadControl | None = None,
) -> list[Path]:
    """yt-dlp 状态页兜底。"""
    import yt_dlp

    report = make_progress(progress_callback, control)
    finished: list[Path] = []

    def hook(d: dict) -> None:
        if control:
            control.check()
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            current = d.get("downloaded_bytes") or 0
            if total:
                report(int(current), int(total))
        elif status == "finished":
            name = d.get("filename")
            if name:
                finished.append(Path(name))
            total = d.get("total_bytes") or d.get("downloaded_bytes") or 0
            if total:
                report(int(total), int(total))

    opts: dict = {
        "outtmpl": out_tmpl,
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio/best",
        "merge_output_format": "mp4",
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "progress_hooks": [hook],
        "noplaylist": False,
    }
    if proxy:
        opts["proxy"] = proxy

    def _existing(p: Path) -> Path | None:
        if p.is_file():
            return p
        alt = p.with_suffix(".mp4")
        return alt if alt.is_file() else None

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source, download=True)
        if info is None:
            raise RuntimeError("yt-dlp 未返回媒体信息")
        paths: list[Path] = []
        if "entries" in info and info["entries"]:
            for e in info["entries"]:
                if not e:
                    continue
                got = _existing(Path(ydl.prepare_filename(e)))
                if got:
                    paths.append(got)
        else:
            got = _existing(Path(ydl.prepare_filename(info)))
            if got:
                paths.append(got)
        if not paths and finished:
            paths = [p for p in finished if p.is_file()]
        if not paths:
            raise RuntimeError("下载完成但找不到输出文件")
        return paths


def _download_urls_resumable(
    mp4s: list[str],
    download_dir: Path,
    *,
    user: str,
    status_id: str,
    proxy: str | None,
    progress_callback=None,
    log=print,
    control: DownloadControl | None = None,
    skip_existing: bool = True,
) -> tuple[list[Path], int]:
    """下载多个直链。返回 (paths, skip_count)。"""
    n = len(mp4s)
    if n > 1:
        log(f"媒体组: {n} 个视频")
    paths: list[Path] = []
    skip_n = 0
    for i, mp4 in enumerate(mp4s):
        if control:
            control.check()
        final = _target_path(download_dir, user, status_id, index=i, total=n)
        if skip_existing and file_complete(final, None):
            log(f"SKIP 本地: {final}")
            paths.append(final)
            skip_n += 1
            continue
        log(f"直链[{i + 1}/{n}]: {mp4.split('?')[0]}")
        path = _http_download_resumable(
            mp4,
            final,
            proxy=proxy,
            progress_callback=progress_callback,
            control=control,
            log=log,
        )
        paths.append(path)
    return paths, skip_n


def _download_sync(
    url: str,
    download_dir: Path,
    cfg: dict,
    *,
    user: str,
    status_id: str,
    out_tmpl: str,
    progress_callback=None,
    log=print,
    control: DownloadControl | None = None,
) -> tuple[list[Path], int]:
    try:
        import yt_dlp  # noqa: F401
    except ImportError as e:
        raise RuntimeError("缺少 yt-dlp：pip install yt-dlp") from e

    proxy = proxy_url(cfg)
    opts = cfg.get("options") or {}
    skip_existing = bool(opts.get("skip_existing", True))
    if proxy:
        log(f"X 下载走代理: {proxy.split('@')[-1] if '@' in proxy else proxy}")

    # 1) fxtwitter 优先
    try:
        mp4s = _resolve_fx_mp4s(user, status_id, proxy, log=log)
        return _download_urls_resumable(
            mp4s,
            download_dir,
            user=user,
            status_id=status_id,
            proxy=proxy,
            progress_callback=progress_callback,
            log=log,
            control=control,
            skip_existing=skip_existing,
        )
    except Cancelled:
        raise
    except Exception as e:
        log(f"fxtwitter 失败，回退 yt-dlp: {e}")

    # 2) yt-dlp 兜底
    paths = _ydl_download(
        url,
        out_tmpl=out_tmpl,
        proxy=proxy,
        progress_callback=progress_callback,
        control=control,
    )
    return paths, 0


async def download_x_video(
    url: str,
    download_dir: Path,
    cfg: dict,
    *,
    progress_callback=None,
    log=print,
    control: DownloadControl | None = None,
) -> tuple[list[Path], bool]:
    """一条 X 链接 → 一个或多个视频。返回 (paths, 是否全部跳过)。"""
    if control:
        control.check()

    user, status_id = parse_x_status_link(url)
    clean = normalize_x_url(url)
    opts = cfg.get("options") or {}
    skip_existing = bool(opts.get("skip_existing", True))
    max_retries = max(1, int(opts.get("max_retries") or 3))
    chat = f"x:{user}"
    msg_id = int(status_id)

    download_dir.mkdir(parents=True, exist_ok=True)

    # 单文件历史快路径（兼容旧命名）
    single = _target_path(download_dir, user, status_id, index=0, total=1)
    hit = history_ok(url, msg_id=msg_id) or history_ok(clean, msg_id=msg_id)
    if skip_existing and hit:
        p = Path(hit["file"])
        if file_complete(p, hit.get("size")):
            # 若已有 _02 等兄弟文件，交给后面完整扫描；仅当单文件场景才早退
            sibling = _target_path(download_dir, user, status_id, index=1, total=2)
            if not sibling.exists() and not Path(str(single) + ".part").exists():
                log(f"SKIP 历史: {p}")
                return [p], True

    ensure_disk_space(download_dir, 8 * 1024 * 1024)

    out_tmpl = str(download_dir / f"x_{user}_{status_id}_%(autonumber)02d.%(ext)s")
    cfg["last_run"] = {
        "at": now_iso(),
        "current_url": url,
        "chat": chat,
        "msg_id": msg_id,
        "status": "downloading",
    }
    log(f"开始下载 X @{user} status={status_id}")

    last_err: BaseException | None = None
    paths: list[Path] | None = None
    skip_n = 0
    for attempt in range(max_retries):
        if control:
            control.check()
        try:
            paths, skip_n = await asyncio.to_thread(
                _download_sync,
                clean,
                download_dir,
                cfg,
                user=user,
                status_id=status_id,
                out_tmpl=out_tmpl,
                progress_callback=progress_callback,
                log=log,
                control=control,
            )
            last_err = None
            break
        except Cancelled:
            cfg["last_run"] = {
                "at": now_iso(),
                "current_url": url,
                "status": "cancelled",
            }
            save_config(cfg)
            raise
        except Exception as e:
            last_err = e
            if attempt + 1 >= max_retries or not _retryable(e):
                break
            wait = 2**attempt
            log(f"瞬时错误，{wait}s 后重试 ({attempt+1}/{max_retries-1}): {e}")
            await asyncio.sleep(wait)

    if last_err is not None or not paths:
        err = last_err or RuntimeError("未知错误")
        record_result(
            cfg,
            url=url,
            chat=chat,
            msg_id=msg_id,
            path=None,
            size=None,
            status="fail",
            error=str(err),
        )
        raise err

    # 统一命名：yt-dlp 兜底可能写出 autonumber 文件
    normalized: list[Path] = []
    n = len(paths)
    for i, path in enumerate(paths):
        want = _target_path(download_dir, user, status_id, index=i, total=n)
        if path.resolve() != want.resolve() and path.suffix.lower() == ".mp4":
            try:
                if want.exists() and want.resolve() != path.resolve():
                    want.unlink()
                path.replace(want)
                path = want
            except OSError:
                pass
        normalized.append(path)
        size = path.stat().st_size
        record_result(
            cfg,
            url=url,
            chat=chat,
            msg_id=msg_id,
            path=path,
            size=size,
            status="ok",
            note=None if n == 1 else f"index={i + 1}/{n}",
        )
        log(f"X 完成[{i + 1}/{n}]: {path} ({size} bytes)")

    all_skipped = skip_n == len(normalized) and len(normalized) > 0
    return normalized, all_skipped
