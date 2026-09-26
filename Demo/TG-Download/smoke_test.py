"""冒烟：链接解析 +（可选）TG 登录取消息。

默认只做离线解析断言；传 --online 才连 Telegram。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tg_download import (  # noqa: E402
    acquire_instance_lock,
    app_dir,
    build_proxy,
    link_kind,
    load_config,
    normalize_x_url,
    parse_message_link,
    parse_x_status_link,
    release_instance_lock,
    save_config,
)
from tgdl.x_download import _pick_all_mp4s, _target_path  # noqa: E402
from telethon import TelegramClient  # noqa: E402

TG_URL = "https://t.me/c/4453856621/6525"
X_URL = "https://x.com/manzhanchinv/status/2102602856993841486/video/1"


def test_parse() -> None:
    assert link_kind(TG_URL) == "tg"
    chat, msg_id = parse_message_link(TG_URL)
    assert chat == -1004453856621
    assert msg_id == 6525

    assert link_kind(X_URL) == "x"
    user, sid = parse_x_status_link(X_URL)
    assert user == "manzhanchinv"
    assert sid == "2102602856993841486"
    assert normalize_x_url(X_URL) == "https://x.com/manzhanchinv/status/2102602856993841486"

    assert link_kind("https://example.com/foo") == "unknown"

    # 多视频命名 + 选链
    from pathlib import Path

    p1 = _target_path(Path("."), "u", "1", index=0, total=1)
    p2 = _target_path(Path("."), "u", "1", index=0, total=2)
    p3 = _target_path(Path("."), "u", "1", index=1, total=2)
    assert p1.name == "x_u_1.mp4"
    assert p2.name == "x_u_1_01.mp4"
    assert p3.name == "x_u_1_02.mp4"
    urls = _pick_all_mp4s(
        {
            "media": {
                "videos": [
                    {
                        "type": "video",
                        "formats": [
                            {"url": "https://x/a-low.mp4", "bitrate": 1},
                            {"url": "https://x/a.mp4", "bitrate": 9},
                        ],
                    },
                    {"type": "video", "url": "https://x/b.mp4"},
                ]
            }
        }
    )
    assert urls == ["https://x/a.mp4", "https://x/b.mp4"]
    print("parse ok")


async def test_online() -> int:
    if not acquire_instance_lock():
        print("FAIL instance lock")
        return 2
    try:
        chat, msg_id = parse_message_link(TG_URL)
        print("parse", chat, msg_id)
        cfg = load_config()
        proxy = build_proxy(cfg)
        session = str(app_dir() / cfg.get("session", "tg_download"))
        client = TelegramClient(session, int(cfg["api_id"]), cfg["api_hash"], proxy=proxy, timeout=30)
        phone = (cfg.get("phone") or "").strip() or None
        await client.start(phone=phone)
        try:
            me = await client.get_me()
            cfg["account"] = {
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "phone": me.phone,
            }
            save_config(cfg)
            msg = await client.get_messages(chat, ids=msg_id)
            doc = getattr(msg, "document", None) if msg else None
            print("ok", me.id, getattr(doc, "size", None))
        finally:
            await client.disconnect()
        return 0
    finally:
        release_instance_lock()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true", help="连 Telegram 做登录冒烟")
    args = ap.parse_args()
    test_parse()
    if args.online:
        return asyncio.run(test_online())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
