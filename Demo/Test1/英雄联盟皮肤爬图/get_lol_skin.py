"""

抓取英雄联盟皮肤

"""
import json
from urllib import parse

import requests

class GetLolSkin(object):
    def __init__(self):
        """初始化变量"""
        self.hero_url = 'https://lol.qq.com/biz/hero/champion.js'
        self.hero_name = 'http://lol.qq.com/biz/hero/'
        self.skin_folder = 'skin'
        self.shin_url = 'https://ossweb-img.qq.com/images/lol/web201310/skin/big'


    @staticmethod
    def get_html(url):
        """下载html"""
        request = requests.get(url)
        request.encoding = 'gbk'
        if request.status_code == 200:
            return request.text
        else:
            return "{}"

    def get_hero_list(self):
        """获取英雄的完整信息列表"""
        hero_js = self.get_html(self.hero_url)
        # 删除左右的多余信息，得到json数据
        out_left = "if(!LOLherojs)var LOLherojs={};LOLherojs.champion="
        out_right = ';'
        hero_list = hero_js.replace(out_left, '').rstrip(out_right)
        return json.loads(hero_list)

    def get_hero_info(self, hero_id):
        """获取英雄的详细信息"""
        # 获取js详情
        detail_url = parse.urljoin(self.hero_detail_url, hero_id + '.js')
        detail_js = self.get_html(detail_url)
        # 删除左右的多余信息，得到json数据
        out_left = "if(!herojs)var herojs={champion:{}};herojs['champion'][%s]=" % hero_id
        out_right = ';'
        hero_info = detail_js.replace(out_left, '').rstrip(out_right)
        return json.loads(hero_info)


    def run(self):
        hero_json = self.get_hero_list()
        print(hero_json)

#程序执行入口
if __name__ == '__main__':
    lol_skin = GetLolSkin()
    lol_skin.run()