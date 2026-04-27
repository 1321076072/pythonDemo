import random
import requests
import json


class MaskFull(object):

    def __init__(self,phone,city,cityCode):
        self.IP = 'http://192.168.100.222:9309'
        self.Domain_name = 'https://bjjfuat.hzbxhd.com/prod-api'
        self.phone = phone
        self.city = city
        self.cityCode = cityCode
        self.channelSignature = 'GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
        self.encryption = '/test/common/mask/api/encrypt/b81281e4813a174a'
        self.check = '/app/openapi/full/check/v2'
        self.push = '/app/openapi/full/push/v2'
        self.params = {
            
            'baiTiaoQuota': 2,
            'accumulationFund': 2,
            'city': '杭州',
            'huaBeiQuota': 2,
            'cityCode': '3301',
            'highestEducation': 4,
            'carProduction': 1,
            'nameMd5': 'd8f2d743cfe2036ac013119945b0cfcc',
            'name': '测试',
            'customerFormOfPayroll': 1,
            'loanPurpose': 1,
            'socialSecurity': 1,
            'customerChildChannel': '',
            'professionalIdentity': 1,
            'monthlyIncome': 10000.00,
            'deviceType': 0,
            'sex': 0,
            'ip': '183.134.143.168',
            'estate': 2,
            'channelSignature': 'GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU',
            'customerCreditCard': 1,
            'idCardMd5': '140221********0011',
            'idCard': '140221********0011',
            'unitSocialSecurity': 1,
            'phone': '15456012***',
            'lengthOfService': 3,
            'sesame': 2,
            'age': 52

    }

    def randomize_enum_values(self):
        """随机生成params中的枚举值"""

        # 性别: 0.女 1.男
        self.params['sex'] = random.choice([0, 1])

        # 本地社保: 1.无社保 2.缴纳未满6个月 3.缴纳6个月以上
        self.params['socialSecurity'] = random.choice([1, 2, 3])

        # 本地公积金: 1.无公积金 2.缴纳未满6个月 3.缴纳6个月以上
        self.params['accumulationFund'] = random.choice([1, 2, 3])

        # 名下车产: 1.无车产 2.有车产
        self.params['carProduction'] = random.choice([1, 2])

        # 名下房产: 1.无房产 2.有房产按揭 3.全款房
        self.params['estate'] = random.choice([1, 2, 3])

        # 个人保险: 1.无保单 2.缴纳不足一年 3.缴纳1年以上 4.缴纳2年以上
        self.params['unitSocialSecurity'] = random.choice([1, 2, 3, 4])

        # 职业身份: 1.上班族 2.公务员或事业单位 3.私营业主 4.个体户 5.其他职业
        self.params['professionalIdentity'] = random.choice([1, 2, 3, 4, 5])

        # 学历: 1.初中及以下 2.高中 3.中专 4.大专 5.本科 6.研究生及以上
        self.params['highestEducation'] = random.choice([1, 2, 3, 4, 5, 6])

        # 工资发放形式: 1.银行卡 2.现金 3.自存
        self.params['customerFormOfPayroll'] = random.choice([1, 2, 3])

        # 当前单位工龄: 1.0~6个月 2.6~12个月 3.12个月以上
        self.params['lengthOfService'] = random.choice([1, 2, 3])

        # 贷款用途: 1-10
        self.params['loanPurpose'] = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # 花呗额度: 1.无额度 2.5000以下 3.5000-10000 4.大于10000
        self.params['huaBeiQuota'] = random.choice([1, 2, 3, 4])

        # 京东白条额度: 1.无额度 2.5000以下 3.5000-10000 4.大于10000
        self.params['baiTiaoQuota'] = random.choice([1, 2, 3, 4])

        # 是否有信用卡: 1.无 2.有
        self.params['customerCreditCard'] = random.choice([1, 2])

        # 设备类型: 0.安卓 1.iOS
        self.params['deviceType'] = random.choice([0, 1])

        # 月收入: 随机生成3000-50000之间的值
        self.params['monthlyIncome'] = round(random.uniform(3000, 50000), 2)

        # 年龄: 随机生成22-60之间
        self.params['age'] = random.randint(22, 60)

        # 芝麻分: 随机生成350-750之间（实际芝麻分范围）
        self.params['sesame'] = random.randint(350, 750)

    def InitializationRequest(self,ctype):
        match ctype:
            case 1:
                self.Domain_name = 'https://bjjftest.hzbxhd.com/prod-api'
                self.channelSignature = 'GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
            case 2:
                self.Domain_name = 'https://bjjfuat.hzbxhd.com/prod-api'
                self.channelSignature = 'GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
            case 3:
                self.Domain_name = 'https://bjjfdev.hzbxhd.com/prod-api'
                self.channelSignature = 'GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU'
            case 4:
                self.Domain_name = 'https://bjjfapi.hzbxhd.com/prod-api'
                self.channelSignature = 'PAFju5UC1Gw9j5KW2bHwiHlYTcfOiocYL51S3DciJF'


    def startTest(self):
        checkData = self.getCheckData()
        if checkData['code'] == 200:
            print("撞库手机号:" + self.phone + " 响应: " + checkData['msg'])
            pushData = self.getPushData(checkData['data'][0]['serialNo'])
            print("进件手机号:" + self.phone + " 响应: " + pushData['msg'])
        else:
            print("撞库手机号:" + self.phone + " 响应: " + checkData['msg'])


    def getEncryptionData(self):
        request = requests.post(self.IP + self.encryption , json = self.params)
        return json.loads(request.text)

    def getCheckData(self):
        self.params['phone'] = self.phone
        self.params['phone'] = self.params['phone'][:-3] + '***'
        self.params['channelSignature'] = self.channelSignature
        if self.city is not None:
            self.params['city'] = self.city
        if self.cityCode is not None:
            self.params['cityCode'] = self.cityCode
        checkEncry = self.getEncryptionData()
        request = requests.post(self.Domain_name + self.check , json = checkEncry)
        return json.loads(request.text)

    def getPushData(self,serialNo):
        self.params['phone'] = self.phone
        self.params['channelSignature'] = self.channelSignature
        if self.city is not None:
            self.params['city'] = self.city
        if self.cityCode is not None:
            self.params['cityCode'] = self.cityCode
        pushEncry = self.getEncryptionData()
        pushEncry['serialNo'] = serialNo
        request = requests.post(self.Domain_name + self.push , json = pushEncry)
        return json.loads(request.text)

    def print_params_description(self):
        """打印params中参数的中文释义"""

        # 性别映射
        sex_map = {0: '女', 1: '男'}

        # 本地社保映射
        social_security_map = {1: '无社保', 2: '缴纳未满6个月', 3: '缴纳6个月以上'}

        # 本地公积金映射
        accumulation_fund_map = {1: '无公积金', 2: '缴纳未满6个月', 3: '缴纳6个月以上'}

        # 名下车产映射
        car_production_map = {1: '无车产', 2: '有车产'}

        # 名下房产映射
        estate_map = {1: '无房产', 2: '有房产按揭', 3: '全款房'}

        # 个人保险映射
        unit_social_security_map = {1: '无保单', 2: '缴纳不足一年', 3: '缴纳1年以上', 4: '缴纳2年以上'}

        # 职业身份映射
        professional_identity_map = {
            1: '上班族',
            2: '公务员或事业单位',
            3: '私营业主（有营业执照）',
            4: '个体户（无营业执照）',
            5: '其他职业'
        }

        # 学历映射
        highest_education_map = {
            1: '初中及以下',
            2: '高中',
            3: '中专',
            4: '大专',
            5: '本科',
            6: '研究生及以上'
        }

        # 工资发放形式映射
        customer_form_of_payroll_map = {1: '银行卡', 2: '现金', 3: '自存'}

        # 当前单位工龄映射
        length_of_service_map = {1: '0~6个月', 2: '6~12个月', 3: '12个月以上'}

        # 贷款用途映射
        loan_purpose_map = {
            1: '个人日常消费',
            2: '装修',
            3: '旅游',
            4: '教育',
            5: '医疗',
            6: '婚庆开销',
            7: '购置车',
            8: '购置家具家电',
            9: '购置货物生产设备',
            10: '创业经营'
        }

        # 花呗额度映射
        hua_bei_quota_map = {1: '无额度', 2: '5000以下', 3: '5000-10000', 4: '大于10000'}

        # 京东白条额度映射
        bai_tiao_quota_map = {1: '无额度', 2: '5000以下', 3: '5000-10000', 4: '大于10000'}

        # 是否有信用卡映射
        customer_credit_card_map = {1: '无', 2: '有'}

        # 设备类型映射
        device_type_map = {0: '安卓', 1: 'iOS'}

        print("=" * 60)
        print("参数中文释义")
        print("=" * 60)

        # 基本信息
        if 'phone' in self.params:
            print(f"手机号码: {self.params['phone']}")
        if 'name' in self.params:
            print(f"真实姓名: {self.params['name']}")
        if 'nameMd5' in self.params:
            print(f"姓名MD5: {self.params['nameMd5']}")
        if 'idCardMd5' in self.params:
            print(f"身份证MD5: {self.params['idCardMd5']}")
        if 'age' in self.params:
            print(f"年龄: {self.params['age']}")
        if 'sex' in self.params:
            sex_value = self.params['sex']
            print(f"性别: {sex_value} ({sex_map.get(sex_value, '未知')})")
        if 'city' in self.params:
            print(f"所在城市: {self.params['city']}")

        print("-" * 60)

        # 资产信息
        if 'socialSecurity' in self.params:
            ss_value = self.params['socialSecurity']
            print(f"本地社保: {ss_value} ({social_security_map.get(ss_value, '未知')})")
        if 'accumulationFund' in self.params:
            af_value = self.params['accumulationFund']
            print(f"本地公积金: {af_value} ({accumulation_fund_map.get(af_value, '未知')})")
        if 'carProduction' in self.params:
            cp_value = self.params['carProduction']
            print(f"名下车产: {cp_value} ({car_production_map.get(cp_value, '未知')})")
        if 'estate' in self.params:
            es_value = self.params['estate']
            print(f"名下房产: {es_value} ({estate_map.get(es_value, '未知')})")

        print("-" * 60)

        # 职业与收入
        if 'professionalIdentity' in self.params:
            pi_value = self.params['professionalIdentity']
            print(f"职业身份: {pi_value} ({professional_identity_map.get(pi_value, '未知')})")
        if 'highestEducation' in self.params:
            he_value = self.params['highestEducation']
            print(f"学历: {he_value} ({highest_education_map.get(he_value, '未知')})")
        if 'monthlyIncome' in self.params:
            print(f"月收入: {self.params['monthlyIncome']}")
        if 'customerFormOfPayroll' in self.params:
            cfp_value = self.params['customerFormOfPayroll']
            print(f"工资发放形式: {cfp_value} ({customer_form_of_payroll_map.get(cfp_value, '未知')})")
        if 'lengthOfService' in self.params:
            los_value = self.params['lengthOfService']
            print(f"当前单位工龄: {los_value} ({length_of_service_map.get(los_value, '未知')})")

        print("-" * 60)

        # 保险与信用
        if 'unitSocialSecurity' in self.params:
            uss_value = self.params['unitSocialSecurity']
            print(f"个人保险: {uss_value} ({unit_social_security_map.get(uss_value, '未知')})")
        if 'customerCreditCard' in self.params:
            cc_value = self.params['customerCreditCard']
            print(f"是否有信用卡: {cc_value} ({customer_credit_card_map.get(cc_value, '未知')})")
        if 'sesame' in self.params:
            print(f"芝麻分: {self.params['sesame']}")

        print("-" * 60)

        # 额度信息
        if 'huaBeiQuota' in self.params:
            hbq_value = self.params['huaBeiQuota']
            print(f"花呗额度: {hbq_value} ({hua_bei_quota_map.get(hbq_value, '未知')})")
        if 'baiTiaoQuota' in self.params:
            btq_value = self.params['baiTiaoQuota']
            print(f"京东白条额度: {btq_value} ({bai_tiao_quota_map.get(btq_value, '未知')})")

        print("-" * 60)

        # 贷款与其他
        if 'loanPurpose' in self.params:
            lp_value = self.params['loanPurpose']
            print(f"贷款用途: {lp_value} ({loan_purpose_map.get(lp_value, '未知')})")
        if 'deviceType' in self.params:
            dt_value = self.params['deviceType']
            print(f"设备类型: {dt_value} ({device_type_map.get(dt_value, '未知')})")
        if 'ip' in self.params:
            print(f"IP地址: {self.params['ip']}")
        if 'channelSignature' in self.params:
            print(f"渠道标识: {self.params['channelSignature']}")

        print("=" * 60)

if __name__ == '__main__':
    maskFull = MaskFull('154' + str(random.randint(10000000, 99999999)),'深圳','4403')
    maskFull.InitializationRequest(4)
    maskFull.randomize_enum_values()  # 随机生成枚举值
    maskFull.print_params_description()  # 打印参数中文释义
    maskFull.startTest()