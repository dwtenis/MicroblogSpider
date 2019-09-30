# -*- coding: UTF-8 -*-
'''
*SinaMicroblogSpider  
*΢������
*2019/09/19����
*Author: Syrah (dw313@126.com)
* �汾��V3.0.0
'''

import requests
import pymysql
from pyquery import PyQuery
from urllib.parse import urlencode
import queue
import sys

userId='1823887605'      #�Զ����׸��û���id
userNum=50              #�������˺�
nextNum=10               #��ÿ���û���ȡ������˿url
Ids=queue.Queue()       #�������ʹ�ö���
pageNum=2                #���´�����΢��һ�θ��µ�����Ϊ10��������pageNum-1��
idUsed={}
Ids.put(userId)

base_url = 'https://m.weibo.cn/api/container/getIndex?'      #url��header��ʼ��
headers = {
    'Host': 'm.weibo.cn',
    'Referer': 'https://m.weibo.cn/u/'+userId,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='test', charset='utf8')    #���ݿ����ӳ�ʼ���������Զ���
cur = conn.cursor()

def getNextId():                                         #��һ���û�ID����
    global userId
    if Ids.empty():
        return 0
    userId=Ids.get()
    headers['Referer']='https://m.weibo.cn/u/'+str(userId)
    return 1

def putNextId(thisId):                                     #����Ƿ�������û������ŵ������return1��ʾ�����б�0��ʾ����������
    global idUsed
    isUsed=idUsed.get(thisId)
    if isUsed is None:
        Ids.put(thisId)
        idUsed[userId] = userId
        return 1
    return 0

def saveToMysql(result,count):                                   # ����result�����ݿ�
    try:
        sql1="insert into weibo(id,text,attitudes,comments,reposts,datetime,userId,userName) value (%s,%s,%s,%s,%s,%s,%s,%s);"
        cur.execute(sql1,(result['id'],result['text'],result['attitudes_count'],result['comments_count'],result['reposts_count'],result['datetime'],result['userId'],result['userName']))
        count+=1
        print("��%d�������ѱ���"%count)
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

def parsePage(json):                                            #��ȡ��Ϣ
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

def getPageFollow(page2):                                #��ȡ��ע�б�
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

def putFollow():                                       #�ѹ�ע�б���û���Ϣ��ȡ���������
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
    for i in range(userNum):              #ÿ���û�ѭ��һ��
        flag = getNextId()
        putFollow()
        if flag==0:
            print("����û�����ȡ��")      #���û��ָ������������Ϊ��
            break
        for page in range(1,pageNum):     #����pageNum�θ���
            json = getPage(page)
            results = parsePage(json)
            for result in results:
                count = saveToMysql(result,count)
                #print(result)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()