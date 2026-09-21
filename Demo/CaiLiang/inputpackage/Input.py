import time
from datetime import datetime
import copy
import json

import requests

from AesEncryptUtil import aescbc

from encryptutil import EncryptUtil
md5 = EncryptUtil.md5_encrypt

from json import JSONDecodeError

from util.loggin_util import LoggingUtil


import random


class Input:
    
    BAJIE_JIGOU_CHECK = (True,("data","check"))
    BAJIE_JIGOU_PUSH = (True,("data","success"))
    
    XIN_YONG_MIAO_JIE_CHECK = ('"check":true,"message":"撞库成功"',("data",))
    XIN_YONG_MIAO_JIE_PUSH =  ('"success":true',("data",))
    
    
    
    CHECK_RESULT = (BAJIE_JIGOU_CHECK,XIN_YONG_MIAO_JIE_CHECK)
    PUSH_RESULT = (BAJIE_JIGOU_PUSH,XIN_YONG_MIAO_JIE_PUSH)
    
    
    
    
    def __init__(self,channelSignature,name,city,idcard="",child_channel="",phone=None,*,domain):
        
        self.action_result = None
        
        self.logging_util = LoggingUtil(__name__)
        self.logging_util.init_logger()
        
        self.domain = domain
        self.check_url = "https://" + domain + ""
        self.push_url = "https://" + domain + ""
        self.key = ""
        
        self.channelSignature = channelSignature
        self.child_channel = child_channel
        
        self.name = name
        self.city = city
        self.child_channel = child_channel
        self.idcard = idcard
        
        if phone:
            self.phone = phone
        else:
            #self.phone = "154" + (str(datetime.now().timestamp()).replace(".",""))[-8:]
            #self.phone = "154" + str(int(datetime.now().timestamp()))[-8:][::-1]
            self.phone = "154" + ''.join(random.choices('0123456789', k=8))

        self.logging_util.info(self.phone)
        self.logging_util.info(md5(self.phone))
        
        
    def _check(self,body=None):
        ...
    def _push(self,body=None):
        ...
        
    def action(self,body=None):
        self.action_result = None
        self._check(body)
        self.action_result = "md5" + self.phone
        
        temp = self._push(body)
        
        if temp:
            self.action_result = self.phone
        else:
            self.action_result = "0" + self.phone
        
        return temp
    
    def reset(self,channelSignature=None,name=None,city=None,idcard="",child_channel="",*,phone=None,domain=None):
        if channelSignature:
            self.channelSignature = channelSignature
            
        if child_channel:
            self.child_channel = child_channel
            
        if name:
            self.name = name
        if city:
            self.city = city
        if idcard:
            self.idcard = idcard
        
        if domain:
            self.check_url.replace(self.domain,domain)
            self.push_url.replace(self.domain,domain)
            
            self.domain = domain
            
        if phone:
            self.phone = phone
        else:
            #self.phone = "154" + (str(datetime.now().timestamp()).replace(".",""))[-8:]
            #self.phone = "154" + str(int(datetime.now().timestamp()))[-8:][::-1]
            self.phone = "154" + ''.join(random.choices('0123456789', k=8))

        self.logging_util.info(self.phone)
        self.logging_util.info(md5(self.phone))
        print(self.phone)
        
        
    def _check_result(self,response_json:dict, checkTuple:tuple) -> bool:
    
        struct_config = {
            1: "response_json[argsc[0]]",
            2: "response_json[argsc[0]][argsc[1]]",
            3: "response_json[argsc[0]][argsc[1]][argsc[2]]",
            4: "response_json[argsc[0]][argsc[1]][argsc[2]][argsc[3]]"}

        for t in checkTuple:
        
            result = t[0]
            argsc = t[1]
            
            # 层级计算
            struct = len(argsc)
            
            if struct:
                try:
                    if result:
                        return (result == eval(struct_config[struct])) or (result in eval(struct_config[struct]))
                    else:
                        return eval(struct_config[struct])
                except Exception:
                    print("\n\n***未查找到对应层级***")
                    print("入参:{},判断:{},层级:{}\n\n".format(str(response_json), str(result), str(args)))
            else:
                return result in response_json.values()
