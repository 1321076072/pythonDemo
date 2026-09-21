#!/usr/bin/env python3
"""安易借进件安全报文，对照 AypCodecUtil.verifyAndDecrypt 的逆过程。

正式进件 POST /ayj/req/apply 才需要加密签名。
撞库 / 跳转 / 查单 / 协议走明文；/ayj/test/req/apply 也是明文。

流程：
  1. AES/CBC/PKCS5Padding 加密明文 JSON，输出 Base64 → data
  2. timestamp = 13 位毫秒
  3. sign = Base64(SHA256withRSA(data + timestamp))，用平台私钥签
服务端用 thirdPublicKey 验签，再用 aesKey/aesIv 解密。

依赖: pip install pycryptodome
"""
from __future__ import annotations

import base64
import json
import time

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# 与 ayj_channel_config 对齐。签名必须用平台私钥 thirdPrivateKey（配置中心没有这个字段）。
CFG = {
    "aesKey": "LLgkJFC1wF8W2zissTq4eg==",
    "aesIv": "R+mUMkzbthubrdv9KF0Wzg==",
    "thirdPublicKey": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDETdWWTh9oCD4m6EO0/XZu00Sj3rRvmjP45mhd8QSVH7gCdVKCeG+fNjaVSZw8ZQ8g0f+aZcA20k7zDsPVlIwD1uf2ihDuFwEuqQK2O+3HLg7Sc8NrWqOR7bP2s6b3v5pRcAeBFrqQZ5l2UIs4CGphg9j9R7Vv04RRq8F8nUPiZwIDAQAB",
    "thirdPrivateKey": "MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAMRN1ZZOH2gIPiboQ7T9dm7TRKPetG+aM/jmaF3xBJUfuAJ1UoJ4b582NpVJnDxlDyDR/5plwDbSTvMOw9WUjAPW5/aKEO4XAS6pArY77ccuDtJzw2tao5Hts/azpve/mlFwB4EWupBnmXZQizgIamGD2P1HtW/ThFGrwXydQ+JnAgMBAAECgYA1qsXS0sbZTS+YuXURPR4szEt+tXsE69Z7nJo53JORJVvMKEEHdF+n2k1v4PD6vfI12dOUZW74TeTRpF67vGHOjDvxlnXKQnEPZpXjF5/Pb9niSALtHErUKfsHoG6Vh+50fRpDbvqZ4jSa1ep2YCyHmBhHTXxAxaWjxHhJo5vpcQJBAOmNWwTxP49SxtwfaZ0X5Zzoz7l/pnLZcCHgprKqoM/NBrSFFj6DrE9E3wEoRsRJRPacCgXBaIvdabBUwGryuA8CQQDXK/lCLbd4lqWHr7z15PCeANEbQ4KeqfaFLql4KOecWGUZr5a0ovQzU/Y38yJD5u8FWIGdCC9uT0kccZsXrRgpAkBie2O9Esl9cyc9nNVZE8GTx6wICWazmTKqZmOEhWSoG0lPh6sYk0duaZkrkMM+c7Lr1mJ3iNW/3I57d1FoB49LAkAXK2wGvUeBW69tYfYWAFYMnYfmyKk7DpA2HSUwhC8Ufcw9LNQslVN4Z3Ue5zZsW2SnjbU/RI9e8Hit8GnD7eapAkBNsd2sZQDKSTpA7UR+2JGeVIINCc9ePKGX3kp3DS+8VT0FfrAm9+l+S20PsCpTuUss56Ybcadz/IEtbc9Zuyh9",
}

TS_SKEW_MS = 5 * 60 * 1000


def _b64key(pem_or_b64: str) -> bytes:
    t = (
        pem_or_b64.replace("-----BEGIN PUBLIC KEY-----", "")
        .replace("-----END PUBLIC KEY-----", "")
        .replace("-----BEGIN PRIVATE KEY-----", "")
        .replace("-----END PRIVATE KEY-----", "")
    )
    return base64.b64decode("".join(t.split()))


def _aes_bytes(v: str) -> bytes:
    try:
        raw = base64.b64decode(v)
        if len(raw) in (16, 24, 32):
            return raw
    except Exception:
        pass
    return v.encode("utf-8")


def encrypt(plain: str, aes_key: str, aes_iv: str) -> str:
    key, iv = _aes_bytes(aes_key), _aes_bytes(aes_iv)
    if len(iv) != 16:
        raise ValueError("AES IV长度错误")
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plain.encode("utf-8"), 16))
    return base64.b64encode(ct).decode()


def decrypt(data: str, aes_key: str, aes_iv: str) -> str:
    key, iv = _aes_bytes(aes_key), _aes_bytes(aes_iv)
    if len(iv) != 16:
        raise ValueError("AES IV长度错误")
    pt = AES.new(key, AES.MODE_CBC, iv).decrypt(base64.b64decode(data))
    return unpad(pt, 16).decode("utf-8")


def sign(raw: str, private_key_b64: str) -> str:
    key = RSA.import_key(_b64key(private_key_b64))
    sig = pkcs1_15.new(key).sign(SHA256.new(raw.encode("utf-8")))
    return base64.b64encode(sig).decode()


def verify(raw: str, public_key_b64: str, sign_b64: str) -> bool:
    key = RSA.import_key(_b64key(public_key_b64))
    try:
        pkcs1_15.new(key).verify(SHA256.new(raw.encode("utf-8")), base64.b64decode(sign_b64))
        return True
    except ValueError:
        return False


def seal(plain, cfg: dict | None = None) -> dict:
    """明文 → {data, timestamp, sign}，给 POST /ayj/req/apply。"""
    cfg = cfg or CFG
    if not isinstance(plain, str):
        plain = json.dumps(plain, ensure_ascii=False, separators=(",", ":"))
    data = encrypt(plain, cfg["aesKey"], cfg["aesIv"])
    ts = str(int(time.time() * 1000))
    return {"data": data, "timestamp": ts, "sign": sign(data + ts, cfg["thirdPrivateKey"])}


def open_secure(req: dict, cfg: dict | None = None, check_timestamp: bool = True) -> str:
    """对照 verifyAndDecrypt。"""
    cfg = cfg or CFG
    data, ts, sig = req.get("data") or "", req.get("timestamp") or "", req.get("sign") or ""
    if not data or not ts or not sig:
        raise ValueError("安全报文不完整")
    if check_timestamp:
        try:
            if abs(int(time.time() * 1000) - int(ts)) > TS_SKEW_MS:
                raise ValueError("时间戳过期")
        except ValueError as e:
            if str(e) == "时间戳过期":
                raise
            raise ValueError("时间戳过期") from e
    if not verify(data + ts, cfg["thirdPublicKey"], sig):
        raise ValueError("验签失败")
    return decrypt(data, cfg["aesKey"], cfg["aesIv"])


if __name__ == "__main__":
    sample = {
        "orderNo": "AYJ" + str(int(time.time() * 1000)),
        "phone": "13800138000",
        "name": "张三",
        "idCard": "110101199003078888",
        "relations": [
            {"name": "李四", "phone": "13900139000", "relation": 1},
            {"name": "王五", "phone": "13700137000", "relation": 3},
        ],
    }
    body = seal(sample)
    back = json.loads(open_secure(body))
    assert back["orderNo"] == sample["orderNo"]
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print("roundtrip ok, POST /ayj/req/apply")
