# encoding: utf-8
"""
@author: xsren 
@contact: bestrenxs@gmail.com
@site: xsren.me

@version: 1.0
@license: Apache Licence
@file: alimama.py
@time: 2017/5/27 下午9:55

"""
import json
import os.path
import platform
import re
import sys
import time
import traceback
import utils

if sys.version_info[0] < 3:
    import urllib
else:
    import urllib.parse as urllib

from io import BytesIO
from threading import Thread

import pyqrcode
import requests

from PIL import Image

from selenium import webdriver

sysstr = platform.system()
if (sysstr == "Linux") or (sysstr == "Darwin"):
    pass
cookie_fname = 'cookies.txt'


class Alimama:
    def __init__(self, logger):
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6',
            'cache-control': 'max-age=0',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36',
            'Proxy-Connection': 'Keep-Alive'
        }
        self.se = requests.Session()
        self.cookies = {}
        self.myip = '127.0.0.1'
        self.token = ''

        self.load_cookies()
        self.start_keep_cookie_thread()
        self.logger = logger
        self.driver = webdriver.Chrome()

    # 启动一个线程，定时访问淘宝联盟主页，防止cookie失效 - visit_main_url()
    def start_keep_cookie_thread(self):
        t = Thread(target=self.visit_main_url, args=())
        t.setDaemon(True)
        t.start()

    def visit_main_url(self):
        while True:
            time.sleep(60 * 5)
            try:
                self.logger.debug(
                    "visit_main_url......,time:{}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
                self.logger.debug(self.check_login())
                self.se.get('http://pub.alimama.com/myunion.htm')


            except Exception as e:
                trace = traceback.format_exc()
                self.logger.warning("error:{},trace:{}".format(str(e), trace))

    def get_url(self, url, headers):
        res = self.se.get(url, headers=headers, allow_redirects=True)
        return res

    def post_url(self, url, headers, data):
        res = self.se.post(url, headers=headers, data=data)
        return res

    def load_cookies(self):
        if os.path.isfile(cookie_fname):
            with open(cookie_fname, 'r') as f:
                c_str = f.read().strip()
                self.set_cookies(c_str)

    def set_cookies(self, c_str):
        try:
            cookies = json.loads(c_str)
        except:
            return
        for c in cookies:
            self.se.cookies.set(c[0], c[1])

    # check login
    def check_login(self):
        url = 'https://pub.alimama.com/common/getUnionPubContextInfo.json'
        web_data = self.se.get(url, headers=self.headers)
        data = json.loads(web_data.text)
        self.myip = data['data']['ip']
        print(data)

    def login(self):
        self.driver.get(
            'https://login.taobao.com/member/login.jhtml?style=mini&newMini2=true&css_style=alimama&from=alimama&redirectURL=http%3A%2F%2Fwww.alimama.com&full_redirect=true&disableQuickLogin=true')
        i = raw_input('请确认是否已登录？[y/n]:')
        if (i.replace('\r', '').replace('\n', '') != 'y'):
            return

        self.driver.get('http://pub.alimama.com/myunion.htm')
        '''cookie = ''
        for elem in self.driver.get_cookies():
            cookie += elem["name"] + "=" + elem["value"] + ";"
            if elem["name"] == '_tb_token_':
                self.token = elem["value"]
        self.cookies = cookie'''
        for elem in self.driver.get_cookies():
            self.cookies[elem["name"]] = elem["value"]
            if elem["name"] == '_tb_token_':
                self.token = elem["value"]
        self.se.cookies = requests.utils.cookiejar_from_dict(self.cookies, cookiejar=None, overwrite=True)
        # self.headers['Cookie'] = self.cookies
        #self.driver.quit()
        self.check_login()

    # 获取商品详情
    def get_detail(self, q):
        try:
            t = int(time.time() * 1000)
            tb_token = self.token
            pvid = '10_%s_1686_%s' % (self.myip, t)
            url = 'http://pub.alimama.com/items/search.json?q=%s&_t=%s&auctionTag=&perPageSize=40&shopTag=&t=%s&_tb_token_=%s&pvid=%s' % (
            urllib.quote(q.encode('utf8')), t, t, tb_token, pvid)
            res = self.get_url(url, self.headers)
            rj = res.json()
            if rj['data']['pageList'] is not None:
                return rj['data']['pageList'][0]
            else:
                return None
        except Exception as e:
            trace = traceback.format_exc()
            self.logger.warning("error:{},trace:{}".format(str(e), trace))

    # 获取淘宝客链接
    def get_tk_link(self, auctionid):
        t = int(time.time() * 1000)
        tb_token = self.token
        pvid = '10_%s_1686_%s' % (self.myip, t)
        try:
            gcid, siteid, adzoneid = self.__get_tk_link_s1(auctionid, tb_token, pvid)
            self.__get_tk_link_s2(gcid, siteid, adzoneid, auctionid, tb_token, pvid)
            res = self.__get_tk_link_s3(auctionid, adzoneid, siteid, tb_token, pvid)
            return res
        except Exception as e:
            trace = traceback.format_exc()
            self.logger.warning("error:{},trace:{}".format(str(e), trace))

    # 第一步，获取推广位相关信息
    def __get_tk_link_s1(self, auctionid, tb_token, pvid):
        url = 'http://pub.alimama.com/common/adzone/newSelfAdzone2.json?tag=29&itemId=%s&blockId=&t=%s&_tb_token_=%s&pvid=%s' % (
        auctionid, int(time.time() * 1000), tb_token, pvid)
        res = self.get_url(url, self.headers)
        self.logger.debug(res.text)
        rj = res.json()
        gcid = rj['data']['otherList'][0]['gcid']
        siteid = rj['data']['otherList'][0]['siteid']
        adzoneid = rj['data']['otherAdzones'][0]['sub'][0]['id']
        return gcid, siteid, adzoneid

    # post数据
    def __get_tk_link_s2(self, gcid, siteid, adzoneid, auctionid, tb_token, pvid):
        url = 'http://pub.alimama.com/common/adzone/selfAdzoneCreate.json'
        data = {
            'tag': '29',
            'gcid': gcid,
            'siteid': siteid,
            'selectact': 'sel',
            'adzoneid': adzoneid,
            't': int(time.time() * 1000),
            '_tb_token_': tb_token,
            'pvid': pvid,
        }
        headers = {
            'Host': 'pub.alimama.com',
            'Content-Length': str(len(json.dumps(data))),
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'http://pub.alimama.com',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'http://pub.alimama.com/promo/search/index.htm',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
            'Proxy-Connection': 'Keep-Alive',
        }
        res = self.post_url(url, headers, data)
        return res

    # 获取口令
    def __get_tk_link_s3(self, auctionid, adzoneid, siteid, tb_token, pvid):
        url = 'http://pub.alimama.com/common/code/getAuctionCode.json?auctionid=%s&adzoneid=%s&siteid=%s&scenes=1&t=%s&_tb_token_=%s&pvid=%s' % (
        auctionid, adzoneid, siteid, int(time.time() * 1000), tb_token, pvid)
        res = self.get_url(url, self.headers)
        rj = json.loads(res.text)
        return rj['data']

    def get_real_url(self, url):
        # return "https://detail.tmall.com/item.htm?id=548726815314"
        try:
            headers = {
                'Host': url.split('http://')[-1].split('/')[0],
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, sdch',
                'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
                'Proxy-Connection': 'Keep-Alive',
            }
            # headers = {'content-type':'application/octet-stream'}
            res = self.get_url(url, headers)
            if re.search(r'itemId\":\d+', res.text):
                item_id = re.search(r'itemId\":\d+', res.text).group().replace('itemId":', '').replace('https://',
                                                                                                       'http://')
                r_url = "https://detail.tmall.com/item.htm?id=%s" % item_id
            elif re.search(r"var url = '.*';", res.text):
                r_url = re.search(r"var url = '.*';", res.text).group().replace("var url = '", "").replace("';",
                                                                                                           "").replace(
                    'https://', 'http://')
            elif re.search(r'uland\.taobao\.com\\coupon', res.text):
                pass  # 优惠券链接的JS算法复杂，尚未解析sign
            else:
                r_url = res.url
            if 's.click.taobao.com' in r_url:
                r_url = self.handle_click_type_url(r_url)
            else:
                while ('tmall.com' not in r_url) and ('taobao.com' not in r_url):
                    headers1 = {
                        'Host': r_url.split('http://')[-1].split('/')[0],
                        'Upgrade-Insecure-Requests': '1',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, sdch',
                        'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
                        'Proxy-Connection': 'Keep-Alive',
                    }
                    # headers = {'content-type': 'application/octet-stream'}
                    res2 = self.get_url(r_url, headers)
                    self.logger.debug("{},{},{}".format(res2.url, res2.status_code, res2.history))
                    r_url = res2.url

            self.logger.debug(r_url)
            return r_url
        except Exception as e:
            self.logger.warning(str(e))
            return url

    def handle_click_type_url(self, url):
        # step 1
        headers = {
            'method': 'GET',
            'authority': 's.click.taobao.com',
            'path': '/t?%s' % url.split('/t?')[-1],
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
            'Proxy-Connection': 'Keep-Alive',
        }
        res = self.get_url(url, headers)
        self.logger.debug("{},{},{}".format(res.url, res.status_code, res.history))
        url2 = res.url

        # step 2
        headers2 = {
            'referer': url,
            'method': 'GET',
            'authority': 's.click.taobao.com',
            'path': '/t?%s' % url2.split('/t?')[-1],
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
            'Proxy-Connection': 'Keep-Alive',
        }
        res2 = self.get_url(url2, headers2)
        self.logger.debug("{},{},{}".format(res2.url, res2.status_code, res2.history))
        url3 = urllib.unquote(res2.url.split('t_js?tu=')[-1])

        # step 3
        headers3 = {
            'referer': url2,
            'method': 'GET',
            'authority': 's.click.taobao.com',
            'path': '/t?%s' % url3.split('/t?')[-1],
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh,en-US;q=0.8,en;q=0.6,zh-CN;q=0.4,zh-TW;q=0.2',
            'Proxy-Connection': 'Keep-Alive',
        }
        res3 = self.get_url(url3, headers3)
        self.logger.debug("{},{},{}".format(res3.url, res3.status_code, res3.history))
        r_url = res3.url

        return r_url

    # 根据名称获取优惠券商品
    def get_yhq(self, wpname):
        url = 'https://pub.alimama.com/items/search.json?q='+ urllib.quote(wpname.encode('utf8'))
        t = int(time.time() * 1000)
        tb_token = self.token
        pvid = '10_%s_1686_%s' % (self.myip, t)
        url = url + '&toPage=1&dpyhq=1&queryType=0&sortType=9&auctionTag=&perPageSize=3&shopTag=dpyhq&t=%s&_tb_token_=%s&pvid=%s' %(t, tb_token, pvid)
        try:
            urlList = []
            res = self.get_url(url, headers=self.headers)
            for auctionUrl in res.json()['data']['pageList']:
                urlList.append(auctionUrl['auctionUrl'])
            return urlList
        except Exception as e:
            print(e)



if __name__ == '__main__':
    logger = utils.init_logger()
    al = Alimama(logger)
    al.login()
    q = u'https://item.taobao.com/item.htm?id=524515653641'
    # q = u'蔻斯汀玫瑰身体护理套装沐浴露身体乳爽肤水滋润全身保湿补水正品'
    # q = u'DIY个性定制T恤 定做工作服短袖 男女夏季纯棉广告文化衫Polo印制'
    # q = u'防晒衣女2017女装夏装新款印花沙滩防晒服薄中长款大码白色短外套'
    res = al.get_detail(q)
    auctionid = res['auctionId']
    al.get_tk_link(auctionid)
    # url = 'http://c.b1wt.com/h.SQwr1X?cv=kzU8ZvbiEa8&sm=796feb'
    # al.get_real_url(url)
    # url = 'http://c.b1wt.com/h.S9fQZb?cv=zcNtZvbH4ak&sm=79e4be'
    # al.get_real_url(url)
    # url = 'http://c.b1wt.com/h.S9gdyy?cv=RW5EZvbuYBw&sm=231894'
    # al.get_real_url(url)
    # url = 'http://c.b1wt.com/h.S8ppn7?cv=ObUrZvZ3oH9&sm=1b02f8'
    # al.get_real_url(url)
    # url = 'http://c.b1wt.com/h.SQ70kv?cv=L5HpZv0w4hJ'
    # url = 'http://c.b1wt.com/h.S9A0pK?cv=8grnZvYkU14&sm=efb5b7'
    url = 'http://zmnxbc.com/s/nlO3j?tm=95b078'
    al.get_real_url(url)
