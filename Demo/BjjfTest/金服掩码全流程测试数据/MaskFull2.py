import random
import requests
import json
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass


class EnvironmentType(Enum):
    """环境类型枚举"""
    TEST = 1
    UAT = 2
    DEV = 3
    API = 4


@dataclass
class ApiConfig:
    """API配置数据类"""
    domain: str
    channel_signature: str


class EnvironmentConfig:
    """环境配置类"""
    CONFIG_MAP = {
        EnvironmentType.TEST: ApiConfig(
            domain='https://bjjftest.hzbxhd.com/prod-api',
            channel_signature='GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
        ),
        EnvironmentType.UAT: ApiConfig(
            domain='https://bjjfuat.hzbxhd.com/prod-api',
            channel_signature='GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
        ),
        EnvironmentType.DEV: ApiConfig(
            domain='https://bjjfdev.hzbxhd.com/prod-api',
            channel_signature='GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
        ),
        EnvironmentType.PROD: ApiConfig(
            domain='https://bjjfapi.hzbxhd.com/prod-api',
            channel_signature='PAFju5UC1Gw9j5KW2bHwiHlYTcfOiocYL51S3DciJF'
        )
    }


class MaskFull:
    """掩码全流程测试类"""

    # 常量定义
    IP = 'http://192.168.100.222:9309'
    ENCRYPTION_PATH = '/test/common/mask/api/encrypt/b81281e4813a174a'
    CHECK_PATH = '/app/openapi/full/check/v2'
    PUSH_PATH = '/app/openapi/full/push/v2'

    def __init__(self, phone: str, city: str = "杭州", city_code: str = "3301"):
        self.phone = phone
        self.city = city
        self.city_code = city_code

        # 默认配置
        self._config = EnvironmentConfig.CONFIG_MAP[EnvironmentType.UAT]

        # 请求参数模板
        self._base_params = {
            'baiTiaoQuota': 2,
            'accumulationFund': 2,
            'city': self.city,
            'huaBeiQuota': 2,
            'cityCode': self.city_code,
            'highestEducation': 2,
            'carProduction': 2,
            'nameMd5': 'd8f2d743cfe2036ac013119945b0cfcc',
            'name': '张胜男',
            'customerFormOfPayroll': 2,
            'loanPurpose': 1,
            'socialSecurity': 2,
            'customerChildChannel': '',
            'professionalIdentity': 2,
            'monthlyIncome': 2.00,
            'deviceType': 0,
            'sex': 1,
            'ip': '183.134.143.168',
            'estate': 2,
            'channelSignature': self._config.channel_signature,
            'customerCreditCard': 2,
            'idCardMd5': '3b67c1725afed81ce793d342a929186e',
            'unitSocialSecurity': 2,
            'phone': self._mask_phone(phone),
            'lengthOfService': 2,
            'sesame': 1,
            'age': 52
        }

    def _mask_phone(self, phone: str) -> str:
        """手机号脱敏处理"""
        return phone[:-3] + '***'

    def set_environment(self, env_type: EnvironmentType) -> None:
        """设置运行环境"""
        self._config = EnvironmentConfig.CONFIG_MAP[env_type]
        self._base_params['channelSignature'] = self._config.channel_signature

    def _request_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """统一的API请求方法"""
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'code': 500, 'msg': f'请求失败: {str(e)}'}

    def _get_encryption_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取加密数据"""
        return self._request_api(f"{self.IP}{self.ENCRYPTION_PATH}", params)

    def _get_check_data(self) -> Dict[str, Any]:
        """获取检查数据"""
        check_params = self._base_params.copy()
        check_encry = self._get_encryption_data(check_params)
        return self._request_api(f"{self._config.domain}{self.CHECK_PATH}", check_encry)

    def _get_push_data(self, serial_no: str) -> Dict[str, Any]:
        """获取推送数据"""
        push_params = self._base_params.copy()
        push_encry = self._get_encryption_data(push_params)
        push_encry['serialNo'] = serial_no
        return self._request_api(f"{self._config.domain}{self.PUSH_PATH}", push_encry)

    def run_test(self) -> bool:
        """执行完整测试流程"""
        print(f"开始测试手机号: {self.phone}")

        # 撞库检查
        check_data = self._get_check_data()

        if check_data.get('code') == 200:
            print(f"撞库成功 - 手机号: {self.phone}, 响应: {check_data['msg']}")

            # 进件推送
            serial_no = check_data['data'][0]['serialNo']
            push_data = self._get_push_data(serial_no)
            print(f"进件结果 - 手机号: {self.phone}, 响应: {push_data['msg']}")

            return push_data.get('code') == 200
        else:
            print(f"撞库失败 - 手机号: {self.phone}, 响应: {check_data['msg']}")
            return False


def main():
    """主函数"""
    # 生成随机手机号
    phone = f'154{random.randint(10000000, 99999999)}'

    # 创建测试实例
    mask_test = MaskFull(phone, '杭州', '3301')
    mask_test.set_environment(EnvironmentType.TEST)

    # 执行测试
    success = mask_test.run_test()
    print(f"测试结果: {'成功' if success else '失败'}")


if __name__ == '__main__':
    main()