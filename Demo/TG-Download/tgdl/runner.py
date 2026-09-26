"""登录、批量调度、CLI 入口。按链接类型分流：TG → Telethon，X → yt-dlp。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient

from tgdl.config import load_config, now_iso, record_result, save_config
from tgdl.control import Cancelled, DownloadControl, acquire_instance_lock
from tgdl.downloader import download_video_from_link
from tgdl.links import link_kind, parse_message_link, parse_x_status_link
from tgdl.paths import CONFIG_PATH, HAS_CRYPTG, app_dir
from tgdl.proxy import build_proxy, probe_proxy
from tgdl.x_download import download_x_video


def _require_tg(cfg: dict) -> None:
    for key in ("api_id", "api_hash"):
        if key not in cfg or not cfg[key] or str(cfg[key]).startswith("your_"):
            raise ValueError(f"下载 Telegram 链接需要 config.json 中配置 {key}")


async def run(
    urls: list[str],
    config_path: Path,
    *,
    progress_callback=None,
    log=print,
    phone_callback=None,
    code_callback=None,
    password_callback=None,
    cfg: dict | None = None,
    control: DownloadControl | None = None,
    status_callback=None,
) -> int:
    """
    status_callback(url, status, idx, total)
    status ∈ pending|running|ok|skip|fail|cancelled
    """
    cfg = cfg if cfg is not None else load_config(config_path)
    root = app_dir()
    download_dir = Path(cfg.get("download_dir") or "downloads")
    if not download_dir.is_absolute():
        download_dir = root / download_dir

    kinds = [link_kind(u) for u in urls]
    for u, k in zip(urls, kinds):
        if k == "unknown":
            raise ValueError(f"不支持的链接（仅 t.me / x.com / twitter.com）: {u}")

    need_tg = any(k == "tg" for k in kinds)
    need_x = any(k == "x" for k in kinds)
    if need_tg:
        _require_tg(cfg)

    log(f"cryptg={'ON' if HAS_CRYPTG else 'OFF（建议 pip install cryptg）'}")
    if need_x:
        try:
            import yt_dlp  # noqa: F401

            log("yt-dlp=ON（X/Twitter）")
        except ImportError:
            raise RuntimeError("下载 X 链接需要 yt-dlp：pip install yt-dlp") from None

    probe_proxy(cfg)
    if (cfg.get("proxy") or {}).get("enabled"):
        p = cfg["proxy"]
        log(f"代理预检通过: {p.get('type')} {p.get('addr')}:{p.get('port')}")

    client: TelegramClient | None = None
    if need_tg:
        session = str(root / cfg.get("session", "tg_download"))
        proxy = build_proxy(cfg)
        opts = cfg.get("options") or {}
        client = TelegramClient(
            session,
            int(cfg["api_id"]),
            cfg["api_hash"],
            proxy=proxy,
            connection_retries=int(opts.get("connection_retries") or 5),
            timeout=int(opts.get("timeout") or 30),
            request_retries=int(opts.get("max_retries") or 3),
            receive_updates=False,
        )
        phone = phone_callback or ((cfg.get("phone") or "").strip() or None)
        start_kwargs = {"phone": phone}
        if code_callback:
            start_kwargs["code_callback"] = code_callback
        if password_callback:
            start_kwargs["password"] = password_callback
        await client.start(**start_kwargs)

    try:
        if control:
            control.check()
        if client is not None:
            me = await client.get_me()
            cfg["account"] = {
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "phone": me.phone,
            }
            if me.phone and not (cfg.get("phone") or "").strip():
                cfg["phone"] = (
                    f"+{me.phone}" if not str(me.phone).startswith("+") else str(me.phone)
                )
            save_config(cfg, config_path)
            log(f"账号: id={me.id} @{me.username or '-'} phone={cfg.get('phone') or me.phone}")

        ok = fail = skip = cancelled = 0
        total = len(urls)
        for idx, url in enumerate(urls, 1):
            if control and control.cancelled:
                cancelled += 1
                if status_callback:
                    status_callback(url, "cancelled", idx, total)
                log(f"CANCEL 跳过剩余: {url}")
                break
            if status_callback:
                status_callback(url, "running", idx, total)
            kind = link_kind(url)
            try:
                if kind == "x":
                    paths, all_skipped = await download_x_video(
                        url,
                        download_dir,
                        cfg,
                        progress_callback=progress_callback,
                        log=log,
                        control=control,
                    )
                else:
                    assert client is not None
                    paths, all_skipped = await download_video_from_link(
                        client,
                        url,
                        download_dir,
                        cfg,
                        progress_callback=progress_callback,
                        log=log,
                        control=control,
                    )
                save_config(cfg, config_path)
                if all_skipped:
                    skip += 1
                    if status_callback:
                        status_callback(url, "skip", idx, total)
                    log(f"OK(skip) {url}\n -> " + "\n -> ".join(str(p.resolve()) for p in paths))
                else:
                    ok += 1
                    if status_callback:
                        status_callback(url, "ok", idx, total)
                    log(f"OK  {url}\n -> " + "\n -> ".join(str(p.resolve()) for p in paths))
            except Cancelled as e:
                cancelled += 1
                if status_callback:
                    status_callback(url, "cancelled", idx, total)
                log(f"CANCEL {url}\n -> {e}")
                break
            except Exception as e:
                fail += 1
                if status_callback:
                    status_callback(url, "fail", idx, total)
                chat, msg_id = None, 0
                try:
                    if kind == "x":
                        user, sid = parse_x_status_link(url)
                        chat, msg_id = f"x:{user}", int(sid)
                    else:
                        chat, msg_id = parse_message_link(url)
                except Exception:
                    pass
                record_result(
                    cfg,
                    url=url,
                    chat=chat,
                    msg_id=msg_id or 0,
                    path=None,
                    size=None,
                    status="fail",
                    error=str(e),
                )
                save_config(cfg, config_path)
                log(f"FAIL {url}\n -> {e}")

        cfg["last_run"] = {
            "at": now_iso(),
            "status": "done",
            "ok": ok,
            "fail": fail,
            "skip": skip,
            "cancelled": cancelled,
        }
        save_config(cfg, config_path)
        log(f"完成: ok={ok} skip={skip} fail={fail} cancelled={cancelled}")
        return 0 if fail == 0 and cancelled == 0 else 1
    finally:
        if client is not None:
            await client.disconnect()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="下载 Telegram / X(Twitter) 视频链接")
    p.add_argument("urls", nargs="*", help="t.me 或 x.com 链接，可多个")
    p.add_argument("-f", "--file", help="从文本文件读取链接，每行一个")
    p.add_argument("-c", "--config", default=str(CONFIG_PATH), help="配置文件路径")
    return p


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.urls or [])
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        urls.extend(
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main() -> None:
    if not acquire_instance_lock():
        print("已有实例在运行（.instance.lock）", file=sys.stderr)
        raise SystemExit(2)
    parser = build_parser()
    args = parser.parse_args()
    urls = collect_urls(args)
    if not urls:
        parser.error("请提供至少一个链接，或用 -f 指定链接文件")
    raise SystemExit(asyncio.run(run(urls, Path(args.config))))


if __name__ == "__main__":
    main()
