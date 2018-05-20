# encoding: utf-8
"""
@author: xsren 
@contact: bestrenxs@gmail.com
@site: xsren.me

@version: 1.0
@license: Apache Licence
@file: wx_bot.py
@time: 2017/5/28 上午10:40

"""
from __future__ import unicode_literals

import platform
import re
import threading
import traceback

import itchat
import requests
from itchat.content import *

from libs import utils
from libs.alimama import Alimama

logger = utils.init_logger()

al = Alimama(logger)
al.login()


# 检查是否是淘宝链接
def check_if_is_tb_link(msg):
    real_url = ""
    if (re.search(r'￥.*￥', msg.text)) and (u'淘宝APP' in msg.text or u'天猫APP' in msg.text or u'手淘' in msg.text):
        logger.debug(msg.text)
        # q = re.search(r'【.*】', msg.text).group().replace(u'【', '').replace(u'】', '')
        if u'打开👉天猫APP👈' in msg.text:
            try:
                url = re.search(r'http://.* \)', msg.text).group().replace(u' )', '')
            except:
                url = None

        else:
            try:
                url = re.search(r'http://.* ，', msg.text).group().replace(u' ，', '')
            except:
                url = None
            # 20170909新版淘宝分享中没有链接， 感谢网友jindx0713（https://github.com/jindx0713）提供代码和思路，现在使用第三方网站 http://www.taokouling.com 根据淘口令获取url
        if url is None:
            taokoulingurl = 'http://www.taokouling.com/index.php?m=api&a=taokoulingjm'
            taokouling = re.search(r'￥.*￥', msg.text).group()
            parms = {'username': 'tinysxing', 'password': '123569', 'text': taokouling}
            res = requests.post(taokoulingurl, data=parms)
            url = res.json()['url'].replace('https://', 'http://')
            info = "tkl url: {}".format(url)
            logger.debug(info)
            # get real url
            real_url = al.get_real_url(url)
            info = "real_url: {}".format(real_url)
            logger.debug(info)

    elif (re.search(r'taobao\.com', msg.text) or re.search(r'tmall\.com', msg.text)) and (re.search(r'id=', msg.text)):
        real_url = msg.text

    elif re.search(r'买.*', msg.text):
        real_url_list = al.get_yhq(re.search(r'买.*', msg.text).group().replace('买',''))
        for real_url in real_url_list:
            geturl_tk(msg, real_url)
        return
    else:
        return

    try:
        geturl_tk(msg, real_url)
    except Exception as e:
        trace = traceback.format_exc()
        logger.warning("error:{},trace:{}".format(str(e), trace))
        res_text = u'''-----------------
❤该宝贝暂时没有找到内部优惠券！亲可以直接复制宝贝链接查询，或者“买XXX”查询优惠券！ '''
        msg.user.send(res_text)


def geturl_tk(msg, real_url):
    if real_url == "":
        return
    # get detail
    res = al.get_detail(real_url)
    if res is None:
        res_text = u'''❤该宝贝非常特殊，居然在内部找不到，亲可以输入“买XXX”查询优惠券！ '''
        msg.user.send(res_text)
        return
    q = '【' + res['title'] + '】'
    auctionid = res['auctionId']
    coupon_amount = res['couponAmount']
    tk_rate = res['tkRate']
    price = res['zkPrice']
    fx = (price - coupon_amount) * tk_rate / 100
    yhprice = str(float(price) - float(coupon_amount))

    # get tk link
    res1 = al.get_tk_link(auctionid)
    tao_token = res1['taoToken']
    short_link = res1['shortLinkUrl']
    coupon_link = res1['couponLink']

    if coupon_link != "":
        coupon_token = res1['couponLinkTaoToken']
        res_text = '''%s
        【价格】 %s元
        【优惠券】%s元
        【优惠后】%s元
    ★复制本条信息、打开手淘可直接跳转至原商家下单、%s淘口令
    ❤如果没有优惠券，您复制本消息购物将为公益捐款1元，谢谢！
        ''' % (q, price, coupon_amount, yhprice, coupon_token)
        # res_text = u'''%s
        # 【优惠券】%s元
        # 请复制%s淘口令、打开淘宝APP下单
        # -----------------
        # 【下单地址】%s
        #             ''' % (q, coupon_amount, coupon_token, short_link)
    else:
        #                 res_text = u'''%s
        # 【优惠券】%s元
        # 请复制%s淘口令、打开淘宝APP下单
        # -----------------
        # 【下单地址】%s
        #                                 ''' % (q, coupon_amount, tao_token, short_link)
        res_text = '''%s
        【价格】 %s元
        【优惠券】%s元
        【优惠后】%s元
    ★复制本条信息、打开手淘可直接跳转至原商家下单、%s淘口令
    ❤如果没有优惠券，您复制本消息购物将为公益捐款1元，谢谢！
        ''' % (q, price, coupon_amount, yhprice, tao_token)
    msg.user.send(res_text)


class WxBot(object):
    @itchat.msg_register([TEXT])
    def text_reply(msg):
        check_if_is_tb_link(msg)
        # msg.user.send('%s: %s' % (msg.type, msg.text))

    @itchat.msg_register(TEXT, isGroupChat=True)
    def text_reply(msg):
        check_if_is_tb_link(msg)
        # if msg.isAt:
        #     msg.user.send(u'@%s\u2005I received: %s' % (
        #         msg.actualNickName, msg.text))

    def run(self):
        sysstr = platform.system()
        if (sysstr == "Linux") or (sysstr == "Darwin"):
            itchat.auto_login(enableCmdQR=2, hotReload=True)
        else:
            itchat.auto_login(hotReload=True)
        itchat.run(True)


if __name__ == '__main__':
    mi = WxBot()
    t = threading.Thread(target=mi.run, args=())
    t.start()
