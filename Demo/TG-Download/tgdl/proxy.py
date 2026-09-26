"""代理构造与 TCP 预检。"""

from __future__ import annotations

import socket
from urllib.parse import quote


def build_proxy(cfg: dict):
    proxy = cfg.get("proxy") or {}
    if not proxy.get("enabled"):
        return None
    addr = proxy.get("addr") or "127.0.0.1"
    port = int(proxy.get("port") or 1080)
    ptype = (proxy.get("type") or "socks5").lower()
    username = proxy.get("username") or None
    password = proxy.get("password") or None
    if username or password:
        return {
            "proxy_type": ptype,
            "addr": addr,
            "port": port,
            "username": username,
            "password": password,
        }
    return (ptype, addr, port)


def proxy_url(cfg: dict) -> str | None:
    """yt-dlp / httpx 用的代理 URL，未启用返回 None。"""
    proxy = cfg.get("proxy") or {}
    if not proxy.get("enabled"):
        return None
    addr = proxy.get("addr") or "127.0.0.1"
    port = int(proxy.get("port") or 1080)
    ptype = (proxy.get("type") or "socks5").lower()
    # yt-dlp 对 socks5h 做远程 DNS，国内更稳
    if ptype in ("socks5", "socks5h"):
        scheme = "socks5h"
    elif ptype in ("socks4", "socks4a"):
        scheme = "socks4a"
    else:
        scheme = "http"
    user = proxy.get("username") or ""
    pwd = proxy.get("password") or ""
    if user or pwd:
        auth = f"{quote(str(user), safe='')}:{quote(str(pwd), safe='')}@"
    else:
        auth = ""
    return f"{scheme}://{auth}{addr}:{port}"


def probe_proxy(cfg: dict, timeout: float = 3.0) -> None:
    """启用代理时先探端口，避免干等 Telethon 超时。"""
    proxy = cfg.get("proxy") or {}
    if not proxy.get("enabled"):
        return
    addr = proxy.get("addr") or "127.0.0.1"
    port = int(proxy.get("port") or 1080)
    try:
        with socket.create_connection((addr, port), timeout=timeout):
            pass
    except OSError as e:
        raise RuntimeError(f"代理不可达 {addr}:{port} — {e}") from e
