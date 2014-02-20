# -*- coding: utf-8 -*-

import time
import platform
import logging
from functools import partial

import gevent
from gevent.server import StreamServer
from gevent import pywsgi

from .rpchandler import RPCHandler
from .utils import sectodhs


class RPCServer(StreamServer):
    """
        主程序的类一定要有 handle()方法
        main class must have the method of handler()
    """

    FRAME_VERSION = -1
    frameworklog = False

    def __init__(self, listener, aclmap, spawn=100, log=None, webport=8308, interval=1, querytimeout=3, conntimeout=3, activetimeout=1800):
        StreamServer.__init__(self, listener, spawn=spawn)
        self.listener = listener
        self.webport = webport
        self.interval = interval
        self.querytimeout = querytimeout
        self.activetimeout = activetimeout
        self.aclmap = aclmap

        if log is None:
            self.log = logging.getLogger('framework')
            logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level='DEBUG')
        else:
            self.log = log
        # 默认logging是没有write的，在pywsgi里输出log用了write，会报错
        # default loggins have not  method of write(), buy pywsgi need it
        self.log.write = self.log.info
        setattr(self.log, "critical", partial(self.log.critical, exc_info=True))
        setattr(self.log, "error", partial(self.log.error, exc_info=True))
        # 非常重要handlers={} ，每有一个客户端连接，就添加个新 item < handler:greenlet >，便于通过 handler 去处理对应的greenlet
        # handlers={} is very import struct, when a new client to connect, append it with new item < handler: greenlet>, we can process some greenlet throght the handler
        self.handlers = {}
        """
            sbT:server begin time
            tcC:total connect count, 总链接次数
            ncC:normal close connect count,链接正常断开数
            ecC:error close connect count, 链接非正常断开
            taC:total auth count, auth 总次数
            eaC:error auth count, auth 失败次数
            tqC:total query count, query 总次数
            eqC:error qurey count, 错误query 总次数
        """
        self.state = {'sbT': time.time(), 'tcC': 0, 'ncC': 0, 'ecC': 0, 'taC': 0, 'eaC': 0, 'tqC': 0, 'eqC': 0}
        self.log.info("%-8s: %s" % ('svrstart', repr(listener)))
        self.webviewer(webport)
        if interval > 0:
            if querytimeout <= 0:
                querytimeout = 3
            self.gm = gevent.spawn(self.monitor, interval, conntimeout, querytimeout, activetimeout)

    def webviewer(self, webport):
        '''
             webport>0 和 有root用户 启动 webserver 去查看状态
             when webport>0 an have user 'root', launche webserver to view system status
        '''
        self.pathinfo = ''
        if 'root' in self.aclmap:
            self.pathinfo = '/pymysqlrpc/info/root/'+self.aclmap['root'][1]

        if webport > 0 and self.pathinfo:
            # maybe log=self.log
            pywsgi.WSGIServer(('', webport), self.pymsqlrpcinfo, log=self.log).start()
            self.log.info("%-8s: webport = %s" % ('webstart', repr(webport)))

    def monitor(self, interval=1, conntimeout=3, querytimeout=3, activetimeout=1800):
        '''
            监控socket链接情况，比如长时间不query，长时间不auth等,默认 1s 监控一次
            conntimeout: 连接后，不 auth 步骤
            querytimeout： 超时执行的query，
            activetimeout: 链接成功后，或者 距离上次最有一次 query，1800s没有发信息 (只对非root用户)
            monitor check every socket,
            conntimeout: after connecting, not to auth
            querytimeout: overtime query
            activetimeout: not active for a long time (just for NOT 'root' user)
        '''
        self.log.info("%-8s: interl= %ds; querTout= %ds;  actiTout= %ds; connTout= %ds;" % (
            'monitor', interval, querytimeout, activetimeout, conntimeout))

        while True:
            gevent.sleep(interval)
            closehandlers = {'conn': [], 'active': [], 'query': []}
            toclose = 0
            nowtime = time.time()

            for i, j in self.handlers.items():
                # 连接上来但是不auth的链接
                # connecting but to auth
                if (nowtime - i.beginconntime > conntimeout) and (i.beginauthtime == 0):
                    toclose = 1
                    closehandlers['conn'].append((i, j))

                # 长时间不 query的链接
                # not active for a long time
                activetime = max(i.beginauthtime, i.lastqueryBEGtime)
                if activetime > 0:
                    if (nowtime - activetime > activetimeout) and (i.username != 'root'):
                        toclose = 1
                        closehandlers['active'].append((i, j))

                # 超时的query
                # one overtime qurey
                if (nowtime - i.lastqueryBEGtime > querytimeout) and (i.lastqueryBEGtime > i.lastqueryENDtime):
                    toclose = 1
                    closehandlers['query'].append((i, j))

            if toclose == 1:
                self.closereq(closehandlers)

    def closereq(self, handlers):
        for i, j in handlers['conn']:
            gevent.kill(j)
            i.socket.close()
            self.log.warning("%-8s: %s@%s: conn timeout" % ('connTout', i.username, i.client_address))

        for i, j in handlers['active']:
            i.socket.close()
            gevent.kill(j)
            self.log.warning("%-8s: %s@%s: active timeout" % ('actiTout', i.username, i.client_address))

        for i, j in handlers['query']:
            # 发一个超时消息，客户端收到友好提示，优雅结束，kill 某个超时query，从设计来说，已经是非常严重的问题了
            # send client a timeout Exception, close socket. kill a overtime qurey ,it should be a serious case
            i.structError(500, "HY103", "func call 3: timeout : %s " % i.cmdarg[1:100])
            i.packetheader = False
            i._sendall(''.join(i.datalist))
            self.state['eq'] += 1
            gevent.kill(j)
            i.socket.close()
            self.log.error("%-8s: %s@%s:%s" % ('querTout', i.username, i.client_address, i.cmdarg))

    def handle(self, socket, address):
        '''
            请求入口，重写了StreamServer的handle()
            每来一个客户端，生成一个 RPCHandler 的实例 handler
            这里最重要的是要自己来管理 handler和greenlet的对应关系，在新生成的时候，循环处理结束时删除
            entrance of clie connecting , override the method handle() of super class StreamServer
            when a client connect,an instance of RPCHandler is created
            This dict is very import to manage item of <handler, greenlet>
        '''
        handler = RPCHandler(socket, address, self)
        self.handlers[handler] = self.getgreenlet(handler)
        try:
            handler.work()
        finally:
            del self.handlers[handler]

    def getgreenlet(self, handler):
        '''
            根据handler的socket ，从gevent pool中找到是对应的greenlet
            因为是基于 BaseServer的， greenlet的第一个参数 argr[0] ,是 gevent.socket.socket类型
            depend socket of handler, find the corrent greenlet from gevent pool
            from sourc of super super class BaseServer, the type of first arg from greenlet is gevet.socket.socket
        '''
        for i in self.pool.greenlets:
            if id(i.args[0]) == id(handler.socket):
                return i
        return None

    def close(self):
        self.log.info("%-8s: %s" % ('svrCLOSE', repr(self.listener)))
        StreamServer.close(self)

    def serverinfo(self):
        """
            返回服务器的基本状态，结果集形式，通过handler输出
            returun the result set of RPCServer status， will be delived by handler
        """
        dataset = [('python_version', platform.python_version())]
        dataset.append(('gevent_version', gevent.__version__))
        dataset.append(('pymysqlrpc_ver', self.FRAME_VERSION))
        dataset.append(('server listen', str(self.listener)))
        dataset.append(('webviewer port', self.webport))
        if self.interval > 0:
            dataset.append(('monitor', 'interval:%3ds; querytimeout:%3ds; activetimeout:%6ds' % (
                self.interval, self.querytimeout, self.activetimeout)))
        else:
            dataset.append(('monitor', '0'))
        dataset.append(('frameworklog', str(self.frameworklog)))
        dataset.append(('begin   time', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.state['sbT']))))
        dataset.append(('running time', '%d days %d hours %d seconds' % sectodhs(time.time()-self.state['sbT'])))
        dataset.append(('pool  stat', 'using:%7d; size:%9d;' % (len(self.pool), self.pool.size)))
        dataset.append(('conn  stat', 'active:%6d; total:%8d; normal close:%6d; error close:%6d;' % (
            self.state['tcC']-self.state['ncC']-self.state['ecC'], self.state['tcC'], self.state['ncC'], self.state['ecC'],)))
        dataset.append(('auth  stat', 'good:%8d; total:%8d; error:%6d;' % (
            self.state['taC']-self.state['eaC'], self.state['taC'], self.state['eaC'],)))
        dataset.append(('query stat', 'good:%8d; total:%8d; error:%6d;' % (
            self.state['tqC']-self.state['eqC'], self.state['tqC'], self.state['eqC'],)))
        dataset.append(('online client', 'online:%6d' % len(self.handlers)))
        retvar = self.detailsofhandlers(self.handlers)
        for i in xrange(len(retvar)):
            dataset.append(('client %d' % (i+1), retvar[i]))
        return (('Variable_name', 'Value'), dataset)

    def detailsofhandlers(self, handlers):
        retvar = []
        for i, _ in handlers.items():
            retvar.append("%s@%s authBEG: %s lastqueryBEG: %s  totalquery:%d" % (
                i.username,
                i.client_address,
                time.strftime("%m-%d %H:%M:%S", time.localtime(i.beginauthtime)),
                time.strftime("%m-%d %H:%M:%S", time.localtime(i.lastqueryBEGtime)),
                i.totalquery,)
            )
        return retvar

    def pymsqlrpcinfo(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        if env['PATH_INFO'] == self.pathinfo:
            retvar = self.serverinfo()
            infostr = ''
            for i in xrange(0, len(retvar[1])):
                infostr += "%-14s : %s \r\n" % retvar[1][i]
            return ["<pre>\r\n%s</pre>" % infostr]
        else:
            return ["this is one pymysqlrpc"]

    def turnonlog(self):
        self.frameworklog = True

    def turnofflog(self):
        self.frameworklog = False
