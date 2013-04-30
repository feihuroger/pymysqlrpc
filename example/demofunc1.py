# -*- coding: UTF-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import time
from datetime import datetime
import gevent

try:
    from pymysqlrpc import LogicError
except:
    sys.path.append("..")
    from pymysqlrpc import LogicError


# system sleep() will block the app until sleep time end
def timesleep(args):
    time.sleep(args)
    return ('count', "total"), [(args, 3856000.1), ]


# never block,
def geventsleep(args):
    gevent.sleep(args)
    return ('count', "total"), [(args, 3856000.1), ]


# some time, when programm have a logic error, can raise a mysql Exception
# client recive the mysql Exception, read error no, erron message
def myerror():
    raise LogicError(99, "some message")


# test return of UTF-8
def hello(a):
    return ('language', 'var', 'hello(var)'), [('English', str(a), "Hello, " + str(a)), ('Chinese', str(a), "嗨, " + str(a))]


# simple return the dataset onlye has one line, you can return a tuple.
# the colname will be auto gen like '0', '1', '2',....
def onlytuple():
    return ("this", "is", 1, "tuple")


# simple return the dataset has multi lines, you ca return a list
# one item of list is a tuple, is a line
def onlylist():
    return [('aa', 1111), ('cc', 2222), ]


def errorretval():
    return ('af', 'bb', (1, 2, 3), 'adfa')


# return all the type where pymysqlrpc supported
# all support type :float, int, str, datetime, buffer, None
def alltype():
    return [(123, 45.67, "ab89", None, bytearray("xy\17\2\3"), datetime.fromtimestamp(time.time())), ]

# rerun empty set
def noline():
    return ('a', 'b', 'noline'), []
