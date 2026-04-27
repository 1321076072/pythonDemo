import json

import requests

if __name__ == '__main__':
    url = 'http://192.168.100.222:9309/test/judgment/encrypt'
    registerUrl = 'https://bjjfuat.hzbxhd.com/prod-api/judgment/register/Vc8eQAU6h9M1XG2iIRyrtz1Ehs4JEFvzOF4smBYwLY'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }

    params = {

            'phone': '15448361119',
            'deviceType': 'ANDROID',
            'realNameOrNot': 1,
            'idCard': '332623197803121904',
            'actualName': '叶杨飞',
            'carProduction': 1,
            'creditCard': 1,
            'professionalIdentity': 1,
            'monthlyIncome': 1000,
            'formOfPayroll': 1,
            'currentWorkingAge': 1,
            'personalInsurance': 1,
            'age': 1,
            'sex': 1,
            'city': '杭州',
            'highestEducation': 1,
            'socialSecurity': 1,
            'accumulationFund': 1,
            'estate': 1,
            'sesame': 1,
            'huaBeiQuota': 1,
            'baiTiaoQuota': 1

    }

    request = requests.post(url, json=params,headers=headers)
    html_text = request.text
    print(html_text)

    requestTest = json.loads(html_text)

    print(requestTest)
    requestRegister = requests.post(registerUrl, json=requestTest)
    html_requestRegister = requestRegister.text
    print(html_requestRegister)