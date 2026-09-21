"""
云盛花掩码采量：撞库 + 进件
支持单发 / 并发。加密对齐 AesUtil CBC（key=b81281e4813a174a）。
"""

import argparse
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy

import requests
from SecureUtils import AesUtil

AES_KEY = "66fa4d17fc49e0f2"
CHECK_PATH = "/app/openapi/mask/check/COMMON"
PUSH_PATH = "/app/openapi/mask/push/COMMON"

ENV = {
    1: ("https://yshwcf.hzbxhd.com/prod-api", "wwX04QoJjfjnLMZSIIJgpoasYemKJUSKZM3xbHFltI"),
    2: ("https://api.bxysh.com/prod-api", "wqxhjDJSSk9HtMF9mJGLTtPhBqPzFppgwy4WOg0y2z"),
    3: ("https://bjjfdev.hzbxhd.com/prod-api", "GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU"),
    4: ("https://bjjfapi.hzbxhd.com/prod-api", "PAFju5UC1Gw9j5KW2bHwiHlYTcfOiocYL51S3DciJF"),
}

BASE_PARAMS = {
    "baiTiaoQuota": 2,
    "accumulationFund": 2,
    "city": "杭州",
    "huaBeiQuota": 2,
    "cityCode": "3301",
    "highestEducation": 4,
    "carProduction": 1,
    "nameMd5": "d8f2d743cfe2036ac013119945b0cfcc",
    "name": "测试",
    "customerFormOfPayroll": 1,
    "loanPurpose": 1,
    "socialSecurity": 1,
    "customerChildChannel": "",
    "professionalIdentity": 1,
    "monthlyIncome": 10000.00,
    "deviceType": 0,
    "sex": 0,
    "ip": "183.134.143.168",
    "estate": 2,
    "customerCreditCard": 1,
    "idCardMd5": "140221********0011",
    "idCard": "132924197405098011",
    "unitSocialSecurity": 1,
    "lengthOfService": 3,
    "sesame": 2,
    "age": 52,
}

_print_lock = threading.Lock()
_thread_local = threading.local()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def http() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        _thread_local.session = sess
    return sess


def random_phone() -> str:
    return "154" + f"{random.randint(10000000, 99999999)}"


def mask_phone(phone: str) -> str:
    return phone[:-3] + "***"


class MaskFull:
    def __init__(self, phone: str, city: str = "杭州", city_code: str = "3101", env: int = 1):
        self.phone = phone
        self.city = city
        self.city_code = city_code
        self.domain, self.channel_signature = ENV[env]
        self.params = deepcopy(BASE_PARAMS)
        self.params["city"] = city
        self.params["cityCode"] = city_code
        self.params["channelSignature"] = self.channel_signature

    def randomize_enum_values(self) -> None:
        p = self.params
        p["sex"] = random.choice([0, 1])
        p["socialSecurity"] = random.choice([1, 2, 3])
        p["accumulationFund"] = random.choice([1, 2, 3])
        p["carProduction"] = random.choice([1, 2])
        p["estate"] = random.choice([1, 2, 3])
        p["unitSocialSecurity"] = random.choice([1, 2, 3, 4])
        p["professionalIdentity"] = random.choice([1, 2, 3, 4, 5])
        p["highestEducation"] = 6
        p["customerFormOfPayroll"] = random.choice([1, 2, 3])
        p["lengthOfService"] = random.choice([1, 2, 3])
        p["loanPurpose"] = random.choice(list(range(1, 11)))
        p["huaBeiQuota"] = random.choice([1, 2, 3, 4])
        p["baiTiaoQuota"] = random.choice([1, 2, 3, 4])
        p["customerCreditCard"] = random.choice([1, 2])
        p["deviceType"] = random.choice([0, 1])
        p["monthlyIncome"] = round(random.uniform(3000, 50000), 2)
        p["age"] = random.randint(22, 60)
        p["sesame"] = random.randint(350, 750)

    def encrypt_body(self) -> dict:
        iv = AesUtil.get_iv()
        data = AesUtil.encrypt_cbc(json.dumps(self.params, ensure_ascii=False), AES_KEY, iv)
        return {"iv": iv, "data": data}

    def check(self) -> dict:
        self.params["phone"] = mask_phone(self.phone)
        self.params["channelSignature"] = self.channel_signature
        resp = http().post(self.domain + CHECK_PATH, json=self.encrypt_body(), timeout=30)
        return resp.json()

    def push(self, serial_no: str) -> dict:
        self.params["phone"] = self.phone
        self.params["channelSignature"] = self.channel_signature
        self.params["serialNo"] = serial_no
        resp = http().post(self.domain + PUSH_PATH, json=self.encrypt_body(), timeout=30)
        return resp.json()

    def run(self, do_push: bool = True) -> dict:
        """单条：撞库成功后可选进件。"""
        result = {"phone": self.phone, "ok": False}
        try:
            check_resp = self.check()
            result["check"] = check_resp
            log(f"[撞库] 手机明文={self.phone} 响应={json.dumps(check_resp, ensure_ascii=False)}")
            if check_resp.get("code") != 200:
                result["msg"] = check_resp.get("msg")
                return result

            if not do_push:
                result["ok"] = True
                result["msg"] = check_resp.get("msg")
                return result

            serial_no = check_resp["data"][0]["serialNo"]
            push_resp = self.push(serial_no)
            result["push"] = push_resp
            result["ok"] = push_resp.get("code") == 200
            result["msg"] = push_resp.get("msg")
            log(f"[进件] 手机明文={self.phone} 响应={json.dumps(push_resp, ensure_ascii=False)}")
        except Exception as e:
            result["msg"] = str(e)
            log(f"[异常] phone={self.phone} err={e}")
        return result


def run_one(task_id: int, env: int, city: str, city_code: str, do_push: bool) -> dict:
    client = MaskFull(random_phone(), city, city_code, env)
    client.randomize_enum_values()
    result = client.run(do_push=do_push)
    result["task_id"] = task_id
    return result


def run_concurrent(
    total: int = 1,
    workers: int = 1,
    env: int = 1,
    city: str = "杭州",
    city_code: str = "3101",
    do_push: bool = True,
) -> list[dict]:
    workers = max(1, min(workers, total))
    mode = "并发" if total > 1 else "单发"
    log(f"{mode}启动: total={total} workers={workers} env={env} push={do_push}")
    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_one, i, env, city, city_code, do_push)
            for i in range(total)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    ok = sum(1 for r in results if r.get("ok"))
    log(f"完成: ok={ok}/{total} 耗时={time.perf_counter() - t0:.2f}s")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="金服掩码撞库+进件（单发/并发）")
    parser.add_argument("-n", "--total", type=int, default=1, help="总请求条数，默认单发")
    parser.add_argument("-w", "--workers", type=int, default=1, help="并发线程数")
    parser.add_argument("-e", "--env", type=int, default=2, choices=list(ENV.keys()), help="1=test 2=uat 3=dev 4=prod")
    parser.add_argument("--city", default="杭州")
    parser.add_argument("--city-code", default="3101")
    parser.add_argument("--no-push", action="store_true", help="仅撞库，不进件")
    args = parser.parse_args()
    run_concurrent(
        total=args.total,
        workers=args.workers,
        env=args.env,
        city=args.city,
        city_code=args.city_code,
        do_push=not args.no_push,
    )
