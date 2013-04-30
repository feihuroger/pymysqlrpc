# -*- coding: UTF-8 -*-


class foo(object):

    def __init__(self, arg):
        self.a = arg

    def mult(self, arg):
        return arg * self.a, # must hava a comma, return shuold be standard of pymysqlrpc
