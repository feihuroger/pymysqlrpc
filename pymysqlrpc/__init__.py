#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: roger.luo feihu.roger@gmail.com
# http://github.com/feihuroger/pymysqlrpc
# 2013/05/01

""""
    采用gevent实现的基于 mysql 协议的 rpc 框架
    rpc 服务端是很多python实现的函数，rpc 客户端调用那个这些远程接口，就像调用mysql的存储过程。
    this is a rpc framework by gevent using the protocol of mysql.
    rpc server have many python functions, rpc client call those remote functions like call mysql stored procedure
"""

__all__ = ["RPCServer", "LogicError"]

from .rpcserver import RPCServer
from .logicerror import LogicError

RPCServer.FRAME_VERSION = '0.1.4'
