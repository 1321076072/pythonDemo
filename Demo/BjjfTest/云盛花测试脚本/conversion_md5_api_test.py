#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 MD5 转掩码 — 撞库 / 进件 联调脚本

对应接口:
  POST {base}/openapi/conversion/md5/check
  POST {base}/openapi/conversion/md5/push

请求体字段对齐 ApiFullCheckReq / ApiFullPushReq:
  撞库: phoneMd5 / nameMd5 / idCardMd5
  进件: phone / name / idCard（其余业务字段与撞库一致）

加密约定 (与 SecureUtils.AesUtil 一致):
  key = md5("XIAO_AN_FEN_QI")[8:24]   # 16 字节 ASCII
  AES/CBC/PKCS5Padding
  请求体: {"iv": "<16字符明文IV>", "data": "<Base64密文>"}

用法示例:
  python conversion_md5_api_test.py --mode both
  python conversion_md5_api_test.py --mode check --phone 13800138000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import string
import sys
from typing import Any, Dict

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ======================== 可改配置 ========================
BASE_URL = "https://yshwcf.hzbxhd.com/prod-api/app"
CHANNEL_SIGNATURE = "wwX04QoJjfjnLMZSIIJgpoasYemKJUSKZM3xbHFltI"

PHONE = None  # None=每次随机；可用 --phone 指定
NAME = "张三"  # 须过中文姓名校验
ID_CARD = "110101199001011234"
CITY = "杭州"
CITY_CODE = "330100"
IP = "183.134.143.168"

TIMEOUT = 30
# ========================================================

CHANNEL_KEYWORD = "XIAO_AN_FEN_QI"


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def generate_aes_key(keyword: str = CHANNEL_KEYWORD) -> str:
    """SecureUtils.AesUtil.generateDdfqKey"""
    return md5_hex(keyword)[8:24]


def random_iv(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def random_phone() -> str:
    prefix = secrets.choice(
        ("130", "131", "132", "135", "136", "137", "138", "139",
         "150", "151", "152", "158", "159", "186", "188")
    )
    return prefix + f"{secrets.randbelow(100_000_000):08d}"


def encrypt_cbc(plain: str, key: str, iv: str) -> str:
    import base64

    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    encrypted = cipher.encrypt(pad(plain.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_cbc(cipher_b64: str, key: str, iv: str) -> str:
    import base64

    raw = base64.b64decode(cipher_b64)
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    return unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8")


def wrap_encrypted(payload: Dict[str, Any]) -> Dict[str, str]:
    key = generate_aes_key()
    iv = random_iv(16)
    plain = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    data = encrypt_cbc(plain, key, iv)
    assert decrypt_cbc(data, key, iv) == plain, "本地加解密自检失败"
    return {"iv": iv, "data": data}


def build_common_fields(channel: str) -> Dict[str, Any]:
    """
    ApiFullCheckReq 公共业务字段（撞库/进件共用）。
    约束对齐实体校验:
      age ∈ [23, 55], sesame ∈ [350, 950]
    枚举取值与掩码全流程一致。
    """
    return {
        # 性别: 0女 1男  @NotNull
        "sex": secrets.choice([0, 1]),
        # 年龄 @NotNull @Min(23) @Max(55)
        "age": secrets.randbelow(55 - 23 + 1) + 23,
        # 城市 @NotBlank
        "city": CITY,
        "cityCode": CITY_CODE,
        # 学历 @NotNull  1初中及以下…6研究生及以上
        "highestEducation": secrets.choice([1, 2, 3, 4, 5, 6]),
        # 房产 @NotNull  1无房产 2有房产按揭 3全款房
        "estate": secrets.choice([1, 2, 3]),
        # 社保 @NotNull  1无 2未满6月 3满6月以上
        "socialSecurity": secrets.choice([1, 2, 3]),
        # 公积金 @NotNull
        "accumulationFund": secrets.choice([1, 2, 3]),
        # 芝麻分 @NotNull @Min(350) @Max(950)
        "sesame": secrets.randbelow(950 - 350 + 1) + 350,
        # 职业身份 @NotNull  1上班族…5其他
        "professionalIdentity": secrets.choice([1, 2, 3, 4, 5]),
        # 月收入 @NotNull BigDecimal
        "monthlyIncome": round(secrets.randbelow(47001) + 3000 + secrets.randbelow(100) / 100, 2),
        # 贷款用途 @NotNull  1~10
        "loanPurpose": secrets.choice(list(range(1, 11))),
        # 车产 @NotNull  1无 2有
        "carProduction": secrets.choice([1, 2]),
        # ip 可选
        "ip": IP,
        # 信用卡 @NotNull  1无 2有
        "customerCreditCard": secrets.choice([1, 2]),
        # 保单 @NotNull  1无保单…4缴纳2年以上
        "unitSocialSecurity": secrets.choice([1, 2, 3, 4]),
        # 工资发放形式 @NotNull  1银行卡 2现金 3自存
        "customerFormOfPayroll": secrets.choice([1, 2, 3]),
        # 工作年限 @NotNull  1:0~6月 2:6~12月 3:12月以上
        "lengthOfService": secrets.choice([1, 2, 3]),
        # 设备 0安卓 1ios（可选）
        "deviceType": secrets.choice([0, 1]),
        # 渠道标识 @NotBlank
        "channelSignature": channel,
        # 花呗/白条额度  1无 2:5000以下 3:5000-10000 4:>10000
        "huaBeiQuota": secrets.choice([1, 2, 3, 4]),
        "baiTiaoQuota": secrets.choice([1, 2, 3, 4]),
    }


def build_check_body(phone: str, channel: str, common: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """ApiFullCheckReq — 撞库：手机号/姓名/身份证走 MD5。"""
    body = dict(common or build_common_fields(channel))
    body.update(
        {
            "phoneMd5": md5_hex(phone),
            "nameMd5": md5_hex(NAME),
            "idCardMd5": md5_hex(ID_CARD),
            "channelSignature": channel,
            "city": CITY,
            "cityCode": CITY_CODE,
        }
    )
    return body


def build_push_body(phone: str, channel: str, common: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """ApiFullPushReq — 进件：手机号/姓名/身份证明文，其余与撞库一致。"""
    body = dict(common or build_common_fields(channel))
    body.pop("phoneMd5", None)
    body.pop("nameMd5", None)
    body.pop("idCardMd5", None)
    body.update(
        {
            "phone": phone,
            "name": NAME,
            "idCard": ID_CARD,
            "channelSignature": channel,
            "city": CITY,
            "cityCode": CITY_CODE,
        }
    )
    return body


def post_json(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    print(f"\n>>> POST {url}")
    print(f">>> encrypted body keys: {list(body.keys())}, iv={body.get('iv')}")
    resp = requests.post(url, json=body, timeout=TIMEOUT, headers={"Content-Type": "application/json"})
    print(f"<<< http={resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        raise
    print(f"<<< resp={json.dumps(data, ensure_ascii=False, indent=2)}")
    return data


def do_check(base: str, phone: str, channel: str, common: Dict[str, Any]) -> Dict[str, Any]:
    plain = build_check_body(phone, channel, common)
    print("\n[CHECK] 明文业务参数 (ApiFullCheckReq):")
    print(json.dumps(plain, ensure_ascii=False, indent=2))
    print(f"[CHECK] phoneMd5={plain['phoneMd5']} (from {phone})")
    return post_json(f"{base.rstrip('/')}/openapi/conversion/md5/check", wrap_encrypted(plain))


def do_push(base: str, phone: str, channel: str, common: Dict[str, Any]) -> Dict[str, Any]:
    plain = build_push_body(phone, channel, common)
    print("\n[PUSH] 明文业务参数 (ApiFullPushReq):")
    print(json.dumps(plain, ensure_ascii=False, indent=2))
    print(f"[PUSH] phoneMd5={md5_hex(phone)} (must match check)")
    return post_json(f"{base.rstrip('/')}/openapi/conversion/md5/push", wrap_encrypted(plain))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MD5转掩码 撞库/进件测试")
    p.add_argument("--base", default=BASE_URL, help="服务根地址")
    p.add_argument("--channel", default=CHANNEL_SIGNATURE, help="渠道标识 channelSignature")
    p.add_argument("--phone", default=None, help="手机号明文；不传则每次随机")
    p.add_argument("--city", default=CITY, help="城市名，撞库/进件须一致")
    p.add_argument("--city-code", default=CITY_CODE, help="城市编码")
    p.add_argument("--mode", choices=["check", "push", "both"], default="both")
    p.add_argument("--dry-run", action="store_true", help="只打印加密包，不发请求")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    global CITY, CITY_CODE
    CITY = args.city
    CITY_CODE = args.city_code
    phone = args.phone or PHONE or random_phone()
    common = build_common_fields(args.channel)

    print("=== MD5转掩码 API 测试 ===")
    print(f"AES key (XIAO_AN_FEN_QI) = {generate_aes_key()}")
    print(f"base={args.base}")
    print(f"channel={args.channel}")
    print(f"phone={phone} md5={md5_hex(phone)}")
    print(f"city={CITY} cityCode={CITY_CODE}")
    print(f"common: age={common['age']} sex={common['sex']} sesame={common['sesame']} "
          f"edu={common['highestEducation']} income={common['monthlyIncome']}")

    if args.channel.startswith("替换"):
        print("\n[WARN] 请先改 CHANNEL_SIGNATURE / --channel 为真实渠道标识", file=sys.stderr)

    if args.dry_run:
        if args.mode in ("check", "both"):
            print("\n[DRY] check body:", json.dumps(wrap_encrypted(build_check_body(phone, args.channel, common)), ensure_ascii=False))
        if args.mode in ("push", "both"):
            print("\n[DRY] push body:", json.dumps(wrap_encrypted(build_push_body(phone, args.channel, common)), ensure_ascii=False))
        return 0

    if args.mode in ("check", "both"):
        r = do_check(args.base, phone, args.channel, common)
        if str(r.get("code")) != "200" and args.mode == "both":
            print("\n[ABORT] 撞库未成功，跳过进件")
            return 1

    if args.mode in ("push", "both"):
        do_push(args.base, phone, args.channel, common)

    return 0


if __name__ == "__main__":
    BASE_URL = os.environ.get("YSH_BASE_URL", BASE_URL)
    CHANNEL_SIGNATURE = os.environ.get("YSH_CHANNEL", CHANNEL_SIGNATURE)
    sys.exit(main())
