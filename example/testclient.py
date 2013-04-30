#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import pymysql
from pprint import pprint


conn = pymysql.connect(host='127.0.0.1', port=3308, user='pymysqlrpc', passwd='rpcpass')
cur = conn.cursor()

cur.execute("call hello('roger')")
for r in cur.fetchall():
    for k in r:
        print(k)

cur.execute("call alltype();")
for r in cur.fetchall():
    for k in r:
        print k, type(k)

try:
    cur.execute("call myerror;")
except Exception, e:
    print e
    print e.args[0], e.args[1]

cur.close()
conn.close()
