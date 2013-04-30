#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import signal
import gevent

try:
    from pymysqlrpc import RPCServer
except:
    pass
    sys.path.append("..")
    from pymysqlrpc import RPCServer

from demoapp import aclmap

# spawn = 30，最多30个链接，否则会报 too many connections
# spawn = 30, max connction is 30, if greater than this, error is too many connections
# activetimeout  = 30 ,just for test, common default is 1800s
server = RPCServer(('0.0.0.0', 3308), aclmap, log=None, spawn=30, webport=8308, querytimeout=20, interval=3, activetimeout=30)
gevent.signal(signal.SIGTERM, server.close)
gevent.signal(signal.SIGINT, server.close)
server.serve_forever()
