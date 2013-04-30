# -*- coding: utf-8 -*-
import types


def sectodhs(sec):
    """
        秒数换成(天，时，秒)的tuple，方便查看
        trans second to a tuple of (day, hour, second)
    """
    d = sec/86400
    h = (sec-d)/3600
    s = sec % 3600
    return (d, h, s)


def genACLmap(*args):
    funclist = {}
    for k in args:
        if type(k).__name__ == 'module':
            for v in dir(k):
                if not v.startswith('_') and type(getattr(k, v)) == types.FunctionType and callable(getattr(k, v)):
                    funclist[v] = getattr(k, v)

    aclmap = {'pymysqlrpc': ('rpcpass', funclist), 'root': ('rootpass', 'webviewpass'), }
    return aclmap
