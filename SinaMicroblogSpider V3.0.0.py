# -*- coding: UTF-8 -*-
'''
*SinaMicroblogSpider  
*微博爬虫
*2019/09/19苏州
*Author: Syrah (dw313@126.com)
* 版本：V3.0.0
'''

import requests
import pymysql
from pyquery import PyQuery
from urllib.parse import urlencode
import queue
import sys

userId='1823887605'      #自定义首个用户的id
userNum=50              #爬几个账号
nextNum=10               #从每个用户获取几个粉丝url
Ids=queue.Queue()       #广度优先使用队列
pageNum=2                #更新次数，微博一次更新的数量为10，共更新pageNum-1次
idUsed={}
Ids.put(userId)

base_url = 'https://m.weibo.cn/api/container/getIndex?'      #url及header初始化
headers = {
    'Host': 'm.weibo.cn',
    'Referer': 'https://m.weibo.cn/u/'+userId,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='test', charset='utf8')    #数据库连接初始化，参数自定义
cur = conn.cursor()

def getNextId():                                         #下一个用户ID出列
    global userId
    if Ids.empty():
        return 0
    userId=Ids.get()
    headers['Referer']='https://m.weibo.cn/u/'+str(userId)
    return 1

def putNextId(thisId):                                     #检测是否爬过，没爬过则放到队列里，return1表示放入列表，0表示爬过了跳过
    global idUsed
    isUsed=idUsed.get(thisId)
    if isUsed is None:
        Ids.put(thisId)
        idUsed[userId] = userId
        return 1
    return 0

def saveToMysql(result,count):                                   # 保存result至数据库
    try:
        sql1="insert into weibo(id,text,attitudes,comments,reposts,datetime,userId,userName) value (%s,%s,%s,%s,%s,%s,%s,%s);"
        cur.execute(sql1,(result['id'],result['text'],result['attitudes_count'],result['comments_count'],result['reposts_count'],result['datetime'],result['userId'],result['userName']))
        count+=1
        print("第%d条数据已保存"%count)
        conn.commit()
        return count
    except:
        print(result,userId)
        return count

def getPage(page):                                             #url->response
    params = {
        'type':'uid',
        'value':userId,
        'containerid':'107603'+str(userId),
        'page':page
    }
    url = base_url + urlencode(params)
    try:
        response = requests.get(url,headers=headers)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError as e:
        print('Error',e.args)

def parsePage(json):                                            #提取信息
    global userName
    if json:
        items = json.get('data').get('cards')
        try:
            userName = json.get('data').get('cards')[1].get('mblog').get('user').get('screen_name')
        except:
            return
        if items != None:
            for index,item in enumerate(items):
                try:
                    item = item.get('mblog', {})
                    weibo = {}
                    weibo['id'] = item.get('id')
                    weibo['text'] = PyQuery(item.get('text')).text()
                    weibo['attitudes_count'] = item.get('attitudes_count')
                    weibo['comments_count'] = item.get('comments_count')
                    weibo['datetime'] = item.get('created_at')
                    weibo['reposts_count'] = item.get('reposts_count')
                    weibo['userName'] = userName
                    weibo['userId'] = userId
                    yield weibo
                except:
                    continue

def getPageFollow(page2):                                #获取关注列表
    params = {

        'containerid': '231051_-_followers_-_'+str(userId),
        'luicode': '10000011',
        'lfid': '1005051823887605',
        'page': page2
    }
    url = base_url + urlencode(params)
    try:
        response = requests.get(url,headers=headers)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError as e:
        print('Error',e.args)

def putFollow():                                       #把关注列表的用户信息提取并加入队列
    pageN=nextNum//20+1
    amount=0
    for page2 in range(2,sys.maxsize):
        json = getPageFollow(page2)
        if json:
            try:
                items = json.get('data').get('cards')[0].get('card_group')
            except:
                return
            if items != None:
                for index, item in enumerate(items):
                    oid=item.get('user').get('id')
                    amount+=putNextId(oid)
                    if amount>=nextNum:
                        return

def main():
    count=0
    for i in range(userNum):              #每个用户循环一次
        flag = getNextId()
        putFollow()
        if flag==0:
            print("相关用户已爬取完")      #如果没到指定数量但队列为空
            break
        for page in range(1,pageNum):     #进行pageNum次更新
            json = getPage(page)
            results = parsePage(json)
            for result in results:
                count = saveToMysql(result,count)
                #print(result)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()