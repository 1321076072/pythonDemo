#!/usr/bin/env python3
"""对照 YshAesUtil.java / 半流程通用渠道加解密。

aesKey = MD5(channelNo[5:15]) 的 32 位小写 hex（ASCII 32 字节 → AES-256）
算法 AES/CBC/PKCS5Padding，密钥和 IV 按 US-ASCII，密文小写 hex。
依赖: pip install pycryptodome
"""
from __future__ import annotations

import hashlib
import json
import random
import string
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_IV_CHARS = string.ascii_letters + string.digits  # 对齐 Hutool RandomUtil.randomString


class YshAesUtil:
    @staticmethod
    def get_aes_key(channel_no: str) -> str:
        if channel_no is None or len(channel_no) < 15:
            raise ValueError("channelNo 长度必须 >= 15")
        return hashlib.md5(channel_no[5:15].encode("utf-8")).hexdigest()

    @staticmethod
    def get_iv() -> str:
        return "".join(random.choices(_IV_CHARS, k=16))

    @staticmethod
    def encrypt_text(text: str, aes_key: str, aes_iv: str) -> str:
        cipher = AES.new(aes_key.encode("ascii"), AES.MODE_CBC, aes_iv.encode("ascii"))
        return cipher.encrypt(pad(text.encode("utf-8"), AES.block_size)).hex()

    @staticmethod
    def decrypt_text(encrypted_hex: str, aes_key: str, aes_iv: str) -> str:
        cipher = AES.new(aes_key.encode("ascii"), AES.MODE_CBC, aes_iv.encode("ascii"))
        return unpad(cipher.decrypt(bytes.fromhex(encrypted_hex)), AES.block_size).decode("utf-8")

    @classmethod
    def wrap(cls, channel_no: str, payload: dict | str) -> dict:
        """组装 ApiChannelCommonReq：data / channelNo / iv / timestamp。"""
        iv = cls.get_iv()
        key = cls.get_aes_key(channel_no)
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return {
            "data": cls.encrypt_text(payload, key, iv),
            "channelNo": channel_no,
            "iv": iv,
            "timestamp": str(int(time.time() * 1000)),
        }

    @classmethod
    def unwrap(cls, req: dict) -> str:
        """解密 ApiChannelCommonReq.data。"""
        key = cls.get_aes_key(req["channelNo"])
        return cls.decrypt_text(req["data"], key, req["iv"])


if __name__ == "__main__":
    channel_no = "OtJawdVXbTdERrJvTGF6BRlJgjz4F6jCfjrFWgzs4d"
    payload = {"phoneMd5": "7945bd83237335e5376ff44d62e4f0ae", "idCardMd5": "2a87cdc3aa49b9bfbd68a4eeee91cba1"}
    req = YshAesUtil.wrap(channel_no, payload)
    print("aesKey:", YshAesUtil.get_aes_key(channel_no))
    print("req:", json.dumps(req, ensure_ascii=False, indent=2))
    print("plain:", YshAesUtil.unwrap(req))
    assert json.loads(YshAesUtil.unwrap(req)) == payload
    print("roundtrip ok")
