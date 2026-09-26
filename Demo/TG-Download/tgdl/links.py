"""链接解析：Telegram 消息 + X/Twitter 状态；私有频道实体解析。"""

from __future__ import annotations

import re

from telethon import TelegramClient

# 私有: t.me/c/<id>/<msg> 或 t.me/c/<id>/<topic>/<msg>
# 公开: t.me/<user>/<msg> 或带 topic；允许 ?thread= / ?single
LINK_RE = re.compile(
    r"""
    (?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/
    (?:
        c/(?P<channel_id>\d+)/(?P<c_tail>\d+(?:/\d+)*)
      | (?P<username>[A-Za-z0-9_]+)/(?P<u_tail>\d+(?:/\d+)*)
    )
    (?:[?#][^\s]*)?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# x.com|twitter.com/<user>/status/<id>[/video/N]
X_LINK_RE = re.compile(
    r"""
    (?:https?://)?(?:(?:www|mobile|m)\.)?(?:twitter\.com|x\.com)/
    (?P<user>[A-Za-z0-9_]+)/status/(?P<status_id>\d+)
    (?:/(?:video|photo)/\d+)?
    (?:[?#][^\s]*)?
    """,
    re.VERBOSE | re.IGNORECASE,
)


def link_kind(url: str) -> str:
    """返回 'tg' | 'x' | 'unknown'。"""
    u = (url or "").strip()
    if not u:
        return "unknown"
    if X_LINK_RE.search(u):
        return "x"
    if LINK_RE.search(u):
        return "tg"
    return "unknown"


def parse_message_link(url: str) -> tuple[str | int, int]:
    """返回 (chat, message_id)。论坛多段路径取最后一段为 msg_id。"""
    m = LINK_RE.search(url.strip())
    if not m:
        raise ValueError(f"无法解析消息链接: {url}")
    if m.group("channel_id"):
        # Telegram 内部超级群/频道 id = -100 + 公开链接里的数字
        chat = int(f"-100{m.group('channel_id')}")
        msg_id = int(m.group("c_tail").rsplit("/", 1)[-1])
        return chat, msg_id
    msg_id = int(m.group("u_tail").rsplit("/", 1)[-1])
    return m.group("username"), msg_id


def parse_x_status_link(url: str) -> tuple[str, str]:
    """返回 (username, status_id)。"""
    m = X_LINK_RE.search(url.strip())
    if not m:
        raise ValueError(f"无法解析 X/Twitter 链接: {url}")
    return m.group("user"), m.group("status_id")


def normalize_x_url(url: str) -> str:
    """去掉 /video/N，统一成 https://x.com/user/status/id 供 yt-dlp。"""
    user, sid = parse_x_status_link(url)
    return f"https://x.com/{user}/status/{sid}"


async def resolve_chat(client: TelegramClient, chat):
    """
    私有 t.me/c/ID 需要 access_hash。
    会话缓存没有 → 扫 dialogs；仍没有 = 账号未加入该群。
    """
    try:
        return await client.get_input_entity(chat)
    except (ValueError, TypeError):
        pass

    async for d in client.iter_dialogs():
        if d.id == chat:
            return await client.get_input_entity(d.entity)

    raise RuntimeError(
        f"无法访问对话 {chat}：当前登录账号的会话里找不到该群/频道。"
        f"常见原因：1) 账号未加入；2) 已退出/被踢；3) 用了另一个账号登录。"
        f"请用本程序同一账号在 Telegram 客户端打开该群后再试。"
        f"（?thread= 只是话题标记，不是失败根因）"
    )
