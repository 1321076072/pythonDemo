import time
from datetime import datetime
import copy
import json

import requests

from AesEncryptUtil import aescbc

from encryptutil import EncryptUtil
md5 = EncryptUtil.md5_encrypt

from json import JSONDecodeError

from inputpackage.Input import Input

import random




class FullMarkInput(Input):
    
    """
    通用掩码采量-全流程
    """
    
    
    headers = {
       'Content-Type': 'application/json',
       'Connection': 'close',
       "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
    
    
    body = {
                "sex": 1,
                "age": 44,
                "socialSecurity": 3,
                "accumulationFund": 3,
                "carProduction": 1,
                "estate": 2,
                "unitSocialSecurity": 1,
                "sesame": 601,
                "professionalIdentity":1,
                "customerCreditCard": 1,
                "highestEducation": 1,
                "monthlyIncome": 2000,
                "customerFormOfPayroll": 1,
                "lengthOfService": 1,
                "deviceType": 1,
                "huaBeiQuota": 1,
                "baiTiaoQuota": 1,
                "price": 11.11,
                "loanPurpose":1,
                "channelSignature": "",
                "ip":"192.168.100.154"
                    }
    

    
      
    def __init__(self,channelSignature,name,city,idcard="",child_channel="",phone=None,*,domain,mode=True):
        #self.logging_util.info(city)
        
        self.domain = domain
        self.check_url = "https://" + self.domain + "/prod-api/app/openapi/full/check/v2"
        self.push_url =  "https://" + self.domain + "/prod-api/app/openapi/full/push/v2"
        
        
        self.key = "b81281e4813a174a"
        #self.key = "66fa4d17fc49e0f2"
        
        self.channelSignature = channelSignature
        self.child_channel = child_channel
        
        self.name = name
        self.city = city
        
        self.child_channel = child_channel
        self.idcard = idcard
        
        if phone:
            self.phone = phone
            self.markphone = phone[:8]
        else:
            #self.phone = "154" + (str(datetime.now().timestamp()).replace(".",""))[-8:]
            #self.phone = "154" + str(int(datetime.now().timestamp()))[-8:][::-1]
            self.phone = "154" + ''.join(random.choices('0123456789', k=8))
            self.markphone = self.phone[:8]

        
        
    def _check(self,body=None):
        
        
        if body is None:
            
            check_body = copy.deepcopy(FullMarkInput.body)
            check_body["phone"] = self.markphone
            check_body["nameMd5"] = md5(self.name)
            check_body["city"] = self.city
            check_body["channelSignature"] = self.channelSignature
            
            if self.child_channel == "":
                check_body.pop("customerChannel",None)
            else:
                check_body["customerChannel"] = self.child_channel
                
            if self.idcard == "":
                check_body.pop("idCardMd5",None)
            else:
                check_body["idCardMd5"] = md5(self.idcard)
        else:
            check_body = copy.deepcopy(body)
            
            if not ("phone" in check_body):
                check_body["phone"] = "154" + ''.join(random.choices('0123456789', k=8))[:8]
                check_body["nameMd5"] = md5(self.name)
                check_body["city"] = self.city
                check_body["channelSignature"] = self.channelSignature
                
                if self.idcard == "":
                    check_body.pop("idCardMd5",None)
                else:
                    check_body["idCardMd5"] = md5(self.idcard)
        

        #加密入参
        ##############################################################################################################
        
        encrypt_data = aescbc()(json.dumps(check_body),self.key,self.key)
        #encrypt_data = aescbc()(json.dumps(check_body),self.key,self.key)
        
        encrypt_body = {"data":encrypt_data,
                        "iv":self.key}
            
        
        ##############################################################################################################
        with requests.session() as session:

            ################################
            # 设置重连次数
            requests.adapters.DEFAULT_RETRIES = 2
            # 设置连接活跃状态为False
            session.keep_alive = False
            ################################
            response = session.request("POST", self.check_url, headers=FullMarkInput.headers, json=encrypt_body)
        
        
        try:
            
            result = response.json()
            #print(result)
            #self.logging_util.info(result)
            print(result)
            
            self.serialNo = result["data"][0]['serialNo']
            self.check_result = True
            
            return True
            
            #check_result = self._check_result(result,Input.CHECK_RESULT)
            """
            if result["data"]["check"] is True:
                self.logging_util.info("撞库成功 - 响应：",result,"\n")
                self.check_result = True
                return True
            else:
                self.logging_util.info("撞库失败 - 响应：",result,"\n")
                self.check_result = False
                return False
            """
            
        except (JSONDecodeError,KeyError) as e:
            self.check_result = False
            return False
    
    
    def _push(self,body=None):
        
        if self.check_result:
        
            if body is None:
                push_body = copy.deepcopy(FullMarkInput.body)
                push_body["channelSignature"] = self.channelSignature
            
                push_body["phone"] = self.phone
                
                push_body["name"] = self.name
                push_body["city"] = self.city
                if self.child_channel == "":
                    push_body.pop("customerChannel",None)
                else:
                    push_body["customerChannel"] = self.child_channel
                    
                if self.idcard == "":
                    push_body.pop("idCard",None)
                else:
                    push_body["idCard"] = self.idcard
                
            else:
                push_body = copy.deepcopy(body)
                
                if not ("phone" in push_body):
                    push_body["phone"] = "154" + ''.join(random.choices('0123456789', k=8))
                    push_body["name"] = self.name
                    push_body["city"] = self.city
                    push_body["channelSignature"] = self.channelSignature
                
                    if self.idcard == "":
                        push_body.pop("idCardMd5",None)
                    else:
                        push_body["idCardMd5"] = self.idcard
                
            
            
            
                
            
            
            # 加密入参
            ##############################################################################################################
            encrypt_data = aescbc()(json.dumps(push_body),self.key,self.key)
            
            encrypt_body = {"data":encrypt_data,
                            "iv":self.key,
                            "serialNo":self.serialNo}
            

            
            
            ##############################################################################################################
            with requests.session() as session:

                ################################
                # 设置重连次数
                requests.adapters.DEFAULT_RETRIES = 15
                # 设置连接活跃状态为False
                session.keep_alive = False
                ################################
                response = session.request("POST", self.push_url, headers=FullMarkInput.headers, json=encrypt_body)
            
            
            try:
                result = response.json()
                self.logging_util.info(result)
                
                if result["msg"] == "进件成功":
                    return True
                else:
                    return False
                
                """
                #push_result = self._check_result(result,Input.PUSH_RESULT)
                if result["data"]["success"] is True:
                    self.logging_util.info("进件成功 - 响应：",result,"\n")
                    return True
                else:
                    self.logging_util.info("进件失败 - 响应：",result,"\n")
                    return False
                
                """
                
            except (JSONDecodeError,KeyError) as e:
                return False
                
        else:
            return False
        
    
        
    @classmethod
    def encrypt_body(cls,body,key,iv):
        encrypt_data = aescbc()(json.dumps(body),key,iv)
        encrypt_body = {"data":encrypt_data,
                        "iv":iv}
        
        return encrypt_body
