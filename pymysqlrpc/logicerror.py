# -*- coding: utf-8 -*-


class LogicError(Exception):

    """
        在逻辑处理中，可以把逻辑错误做为例外返回，客户端捕捉 mysql的 errno 和 errmsg
        while logic error, return a Exception , client will deal with the MYSQL Exception or  errno and errmsg
    """
    def __init__(self, errno, errmsg):
        self.errno = errno
        self.errmsg = errmsg
        self.args = (errno, errmsg)
        return

    def __str__(self):
        return 'LogicError: errno=%d errmsg=%s' % self.args

    def __repr__(self):
        return "LogicError(%d,'%s')" % self.args
