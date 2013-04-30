#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import gevent.monkey
gevent.monkey.patch_all() # if not gevent patch, the socket of pymysql will block until query execute end

import signal
import gevent

import pymysql
# db connecting pool
# https://github.com/CMGS/pool
from pool import pool

try:
    from pymysqlrpc import LogicError
except:
    sys.path.append("..")
    from pymysqlrpc import LogicError


def dbcreator():
    return pymysql.connect(host='127.0.0.1', port=3308, user='pymysqlrpc', passwd='rpcpass')

# recycle must less the remote MYSQL server activetime out, then pool can initiative close connection
# recycle=20 just for test, runmain.py, activetime is 30s
dbpool = pool.QueuePool(dbcreator, recycle=20, max_overflow=10)

try:
    from pymysqlrpc import RPCServer
except:
    pass
    sys.path.append("..")
    from pymysqlrpc import RPCServer


def routertimesleep(arg):
    global dbpool
    conn = dbpool.connect()
    cur = conn.cursor()
    cur.execute("call timesleep(%f)" % arg)
    cur.close()
    conn.close()
    return (str(arg)+'s',)


def routergeventsleep(arg):
    global dbpool
    conn = dbpool.connect()
    cur = conn.cursor()
    cur.execute("call geventsleep(%f)" % arg)
    cur.close()
    conn.close()
    return (str(arg)+'s',)


def routercale(a, b):
    global dbpool
    conn = dbpool.connect()
    cur = conn.cursor()
    cur.execute("call cale(%d, %d)" % (a, b))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(rows)


def commquery(arg):
    global dbpool
    conn = dbpool.connect()
    cur = conn.cursor()
    try:
        cur.execute("call " + arg)
    except Exception, e:
        print e
        raise LogicError(e.args[0], str(e.args[1]))
    desc = cur.description
    rows = cur.fetchall()
    print desc
    print rows
    cur.close()
    conn.close()
    newcolname = []
    for i in desc:
        newcolname.append(i[0])
    return tuple(newcolname), list(rows)


aclmap = {
        "testuser": ["testpass",
            {"routertimesleep": routertimesleep,
             "routergeventsleep": routergeventsleep,
             "rcale": routercale,
             "cq": commquery,
            }],
        "root":("rootpass", "viewpass")
    }

server = RPCServer(('0.0.0.0', 3309), aclmap, log=None, spawn=6, webport=8309, querytimeout=30, interval=3)
gevent.signal(signal.SIGTERM, server.close)
gevent.signal(signal.SIGINT, server.close)
server.serve_forever()
