# -*- coding: UTF-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append("..")

from pprint import pprint

from pymysqlrpc.utils import genACLmap

import demofunc
import demofunc1
import democlass

# develop mode , auto generate all function into ACL
aclmap = genACLmap(demofunc, demofunc1)

# sometiems, we well be map the method of instance into ACL
afoo = democlass.foo(7)
bfoo = democlass.foo(9)

aclmap['pymysqlrpc'][1]['afoomult'] = afoo.mult
aclmap['pymysqlrpc'][1]['bfoomult'] = bfoo.mult

pprint(aclmap)

'''
# to deploy for production, you should manual define access user, password and function dict ACL
aclmap = {  # username   #(password, (funcdict))
    'pymysqlrpc':    ('rpcpass',   {
        'add': demofunc.add,
        'testsleep': demofunc.testsleep,
        'testre': demofunc.raiseerror,
        'testcale': demofunc.cale,
        'afoomult': afoo.mult
    }),
}

# when too many conect , root can always login system to view pymysqlrpc server status
# when webview is open, root can view server status throgh web
# 0: login password, 1: view password
aclmap['root'] = ('juruntang', 'viewpass')
'''
