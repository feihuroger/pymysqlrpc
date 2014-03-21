# -*- coding: utf-8 -*-

import time
import hashlib
import types
import random
import struct
import errno
import ast

from gevent import socket

from .logicerror import LogicError

SERVER_VERSION = '\n5.1.23-feihuroger\x00'

TYPENO = {
    'decimal':  0x00,  # FIELD_TYPE_DECIMAL
    'int':      0x03,  # FIELD_TYPE_LONG
    'long':     0x03,  # FIELD_TYPE_LONG
    'float':    0x05,  # FIELD_TYPE_DOUBLE
    'none':     0x06,  # FIELD_TYPE_NULL
    'str':      0xfe,  # FIELD_TYPE_STRING
    'buffer':   0xfc,  # FIELD_TYPE_BLOB
    'datetime': 0x0c,  # FIELD_TYPE_DATETIME
}


class RPCHandler(object):
    """
        docstring for RPCHandler, when one new client connected, an instance of handler is created like raw socket mysqlrpc
    """

    def __init__(self, socket, address, server):
        self.socket = socket
        self.client_address = address
        self.username = '--null--'
        self.server = server
        self.aclmap = server.aclmap

        self.buf = ""
        self.packetfull = False
        self.authed = False
        self.sid = -1
        self.datalist = []
        self.gdict = {}  # 该用户可执行函数列表, dict of can be called functions
        self.cmdarg = "command"

        self.beginconntime = time.time()  # 链接开始时间
        self.beginauthtime = 0  # 客户端开始auth 时间
        self.lastqueryBEGtime = 0  # 最后一个query开始时间
        self.lastqueryENDtime = 0  # 最有一个query结束时间
        self.totalquery = 0

        self.log = self.server.log
        self.state = self.server.state

    def work(self):
        """
            处理socket的所有请求，一直执行,直到断掉连接
            deal with all requests of one socket, run forever until the socket be breaked
        """
        self._structpacket(self._handshake())
        self._sendall(''.join(self.datalist))
        # client socket is connecting
        #self.log.info('%-8s: %s ' % ('conBEGIN',  self.client_address))
        self.state['tcC'] += 1
        connclose = 0
        try:
            while self.socket is not None:
                data = self.socket.recv(16777216)
                if not len(data):
                    self.log.warning('%-8s: %s ' % ('conERR',  self.client_address))
                    break
                self._data_received(data)
        except socket.error, e:
            if e[0] == errno.EBADF:
                # 客户端socket 关闭
                # client socket closed
                # self.log.info('%-8s: %s ' % ('conCLOS1',  self.client_address))
                self.state['ncC'] += 1
                connclose = 1
        except ValueError:
            raise EOFError
        finally:
            if self.socket is not None:
                try:
                    self.socket.close()
                except socket.error:
                    pass
            self.__dict__.pop('socket', None)
            if connclose == 0:
                # 链接非正常中断
                # the socket connection unusually closed
                self.log.warning('%-8s: %s ' % ('conCLOS2',  self.client_address))
                self.state['ecC'] += 1

    def _sendall(self, data):
        # 分包发送(不知什么愿意,有时在某些操作系统环境下,如果data超长,某些平台客户端会接收不全数据,卡在那里)
        # splite long data to some buffs, if data to long, some OS client can't receive all, will be hang up.
        ## self.socket.send(data)
        buffsize = 10240
        datalen = len(data)
        countbuff = int(datalen/buffsize)
        modbuff = datalen%buffsize
        if( countbuff > 0):
            for x in xrange(0,countbuff):
                self.socket.send(data[x*buffsize: (x+1)*buffsize])
        if(modbuff > 0):
            self.socket.send(data[countbuff*buffsize:])
        self.datalist = []

    def _structpacket(self, pkt):
        self.sid += 1
        if(self.sid>255):
            self.sid=0
        len2, len1 = divmod(len(pkt), 65536)
        header = struct.pack("<HBB", len1, len2, self.sid)
        self.datalist.append(header+pkt)
        return

    def _struct_simpleok(self):
        OK_PACKET = '\x00\x00\x00\x02\x00\x00\x00'
        self._structpacket(OK_PACKET)
        return

    def _struct_eof(self):
        EOF_PACKET = '\xfe\x00\x00' + struct.pack("<H", 0)
        self._structpacket(EOF_PACKET)
        return

    def _struct_ok(self, arows, insertid, server_status, warning_count, message):
        packet = '\x00'+self._encode_int(arows) + self._encode_int(insertid) + \
            struct.pack("<H", server_status) + struct.pack("<H", warning_count)
        if message:
            packet += self._encode_str(message)
        self._structpacket(packet)
        return

    def _struct_error(self, errno, sqlstatus, message):
        assert len(sqlstatus) == 5, 'length of sqlstatus must be 5'
        packet = '\xff'+struct.pack("<H", errno)+'#'+sqlstatus[:5]+message
        self._structpacket(packet)
        return

    def _struct_resultset(self, column_list, dataset, database_name = '', table_name = '', origin_table_name = '', server_status = 0, charset = 8):
        self._structpacket(struct.pack("B", len(column_list)))
        dbname = self._encode_str(database_name)
        tablename = self._encode_str(table_name)
        origintablename = self._encode_str(origin_table_name)
        serverstatus = struct.pack("<H", server_status)
        charset = struct.pack("<H", charset)
        typelist = []
        for (colname, pytype) in column_list:
            columnname = self._encode_str(str(colname))
            typeno = TYPENO[pytype]
            packet = self._encode_str('def')+dbname+tablename+origintablename+columnname+columnname + \
                '\x0c\x08\x00\x00\x00\x00\x00'+struct.pack("B", typeno)+'\x00\x00\x00\x00\x00\x00'
            self._structpacket(packet)
            typelist.append(pytype)
        eofpacket = '\xfe\x00\x00'+serverstatus
        self._structpacket(eofpacket)
        try:
            if len(dataset) :
                for record in dataset:
                    packet = ''
                    assert len(record) == len(typelist), "Dataset's column count not equal title column count"
                    for pytype, cell in zip(typelist, record):
                        if cell is None:
                            packet += '\xfb'
                        else:
                            if pytype == 'datetime':
                                packet += self._encode_str(cell.strftime('%Y-%m-%d %H:%M:%S'))
                            else:
                                packet += self._encode_str(str(cell))
                    self._structpacket(packet)
        finally:
            self._structpacket(eofpacket)
        return

    def _encode_str(self, astr):
        if astr is None:
            return self._encode_int(None)
        else:
            astrlen = len(astr)
            header = self._encode_int(astrlen)
            return header + astr

    def _encode_int(self, aint):
        if aint is None:
            return '\xfb'  # ascii=251 NULL
        elif aint <= 250:
            return struct.pack("B", aint)
        elif aint >= 251 and aint < 65536:
            return '\xfc'+struct.pack("<H", aint)
        elif aint >= 65536 and aint < 4294967296L:
            return '\xfd'+struct.pack("<I", aint)
        else:
            aint1, aint2 = divmod(aint, 4294967296L)
            return '\xfe'+struct.pack("<II", aint2, aint1)
        return

    def scramble(self, message, password):
        stage1 = hashlib.sha1(password).digest()
        stage2 = hashlib.sha1(stage1).digest()
        stage3 = hashlib.sha1(message+stage2).digest()
        stage4 = map(lambda (x, y): chr(ord(x) ^ ord(y)), zip(stage1, stage3))
        stage4 = ''.join(stage4)
        return stage4

    def _handshake(self):
        """
            mysql 客户端刚连接上来，服务器发送握手协议包
            mysql client connect, server send handshake
        """
        version = SERVER_VERSION
        thread_id = struct.pack("<I", random.randint(1, 65535))
        self.sbuffer = ''.join(map(lambda _: chr(random.randint(33, 127)), range(20)))
        buffer_0 = self.sbuffer[:8]
        buffer_1 = self.sbuffer[8:]
        server_option = struct.pack("<H", 33288)
        server_language = '\x08'
        server_status = '\x02\x00'
        packet = version+thread_id+buffer_0+'\x00'+server_option+server_language+server_status+'\x00'*13+buffer_1+'\x00'
        return packet

    def _data_received(self, data):
        """
            传统的读包，解包，先读4字节的包头，得到body的长度，再读取body
            read 4 byte head or request , then read body the request
        """
        self.buf += data
        if len(self.buf) >= 16777216:  # mysql 规范长度 16777216
            self.socket.close()
        if not self.authed and len(self.buf) >= 16777216:
            self.socket.close()
        if not self.packetfull:
            if len(self.buf) >= 4:
                len1, len2, self.sid = struct.unpack("<HBB", self.buf[:4])
                length = (len2 << 16) + len1
            else:
                return

        body = self.buf[4:]
        if len(body) >= length:
            self.packetfull = True
            cmdarg = body[:length]
            self.cmdarg = cmdarg
            self.buf = body[length:]
            try:
                if self.authed:
                    # normal query
                    self._query(cmdarg)
                else:
                    self.auth(cmdarg)
                self.packetfull = False
                self._sendall(''.join(self.datalist))
            except:
                self._struct_error(9999, "HY000", "Internal server error. Close connection.")
                self._sendall(''.join(self.datalist))
                self.socket.close()
                self.log.error('%-8s: ip:%s' % ('dataRECV', self.client_address))
        return

    def _auth(self, password, sbuffer, cbuffer, dbname, client_option, max_packet_size):
        try:
            if self.scramble(sbuffer, password) == cbuffer:
                return True
            else:
                return False
        except KeyError:
            return False

    def auth(self, data):
        """
            mysql 登录认证
            mysql auth
        """
        client_option = struct.unpack("<I", data[:4])[0]
        max_packet_size = struct.unpack("<I", data[4:8])[0]
        charset = data[8]
        assert data[9:32] == '\x00'*23
        zeropos = data[32:].find('\x00')
        zeropos += 32
        username = data[32:zeropos]
        # 预留了三个链接给root用户
        if self.server.pool is not None and \
           self.server.pool.free_count() <= 2 and \
           username != 'root':
            self._struct_error(1040, "08004", "pymysqlrpc Too many connections(TMC)")
            self._sendall(''.join(self.datalist))
            self.socket.close()
            self.log.warning('%-8s: %s@%s ' % ('con2many',  username, self.client_address))
            return

        if data[zeropos+1] == '\x14':
            cbuffer = data[zeropos+2:zeropos+22]
            if len(data) > zeropos+22:
                dbname = data[zeropos+22:-1]
            else:
                dbname = 'pymysqlrpc'
        elif data[zeropos+1] == '\x00':
            cbuffer = None
            dbname = None
        else:
            raise ValueError("Auth packet error, %s" % repr(data))

        try:
            self.state['taC'] += 1
            self.beginauthtime = time.time()  # this greenlet ,auth begin time
            # 先判断用户名是否存在，然后再判断密码是否错
            if username in self.aclmap:
                password, _ = self.aclmap[username]
                if self._auth(password, self.sbuffer, cbuffer, dbname, client_option, max_packet_size):
                    self._struct_ok(0, 0, 2, 0, '')
                    self.authed = True
                    self.username = username
                    (_, self.gdict) = self.aclmap[username]
                    #self.log.info('%-8s: %s@%s ' % ('authOK', username, self.client_address))
                else:
                    self._structpacket('\xfe')
                    self.sid += 1
                    self._structpacket('''\xff\x15\x04#28000Access denied (password is ERROR)''')
                    self._sendall(''.join(self.datalist))
                    self.socket.close()
                    self.log.warning('%-8s: %s@%s ' % ('authERR', username, self.client_address))
                    self.state['eaC'] += 1
            else:
                self._structpacket('\xfe')
                self.sid += 1
                self._structpacket('''\xff\x15\x04#28000Access denied (username is ERROR)''')
                self._sendall(''.join(self.datalist))
                self.socket.close()
                self.log.warning('%-8s: %s@%s ' % ('authERR', username, self.client_address))
                self.state['eaC'] += 1
        except KeyError:
            self.state['eaC'] += 1
            self._struct_error(500, "HY101", "Access denied: ")
            self.socket.close()
            raise ValueError("Auth error, %s" % repr(data))
        return

    def _toresultset(self, retvar):
        """
            将函数返回retvar，按照mysql返回结果集的协议，处理成mysql结果集
            reorganize the return of user function into mysql reslt of mysql
        """
        collist = []
        if type(retvar) == tuple and len(retvar) == 2 and type(retvar[0]) == tuple and type(retvar[1]) == list:
            # 最标准，最全面的返回
            # the standardest return
            colname, dataset = retvar
        elif type(retvar) == list:
            # only dataset, autogen colname
            # simple return mulit rows, use list, each one item is a tuple
            dataset = retvar
            colname = tuple(map(str, range(len(dataset[0]))))
        elif type(retvar) == tuple:
            #retun one row, can use a tuple
            dataset = [retvar]
            colname = tuple(map(str, range(len(dataset[0]))))
        else:
            colname = ("error")
            dataset = [(0, ), ]
        if dataset:
            assert len(colname) == len(dataset[0]), "Column count must equal record"
            for colname, cell in zip(colname, dataset[0]):
                celltype = type(cell)
                if celltype in (types.IntType, types.LongType):
                    collist.append((colname, 'long'))
                elif celltype in (types.StringType, types.UnicodeType):
                    collist.append((colname, 'str'))
                elif celltype in (types.FloatType,):
                    collist.append((colname, 'float'))
                elif celltype in (types.NoneType,):
                    collist.append((colname, 'none'))
                elif celltype.__name__ == "datetime":
                    collist.append((colname, 'datetime'))
                elif celltype.__name__ == "bytearray":
                    collist.append((colname, 'buffer'))
                elif cell.__class__.__name__ == 'Decimal':
                    collist.append((colname, 'decimal'))
                else:
                    raise ValueError("cell type can not turn into mysql: %s" % repr(cell))
        else:
            collist = zip(colname, map(lambda _: 'str', range(len(colname))))
        return collist, dataset

    def _query(self, cmdarg):
        """
            整个方法的核心处理程序，处理 call xxxx()形式请求
            core method, process the request of "call foo()"
        """
        cmd = cmdarg[0]
        arg = cmdarg[1:]
        if cmd == '\x03':
            arg = arg.strip()
            offset = arg.find(' ')
            if offset != -1:
                query, param = arg.split(' ', 1)
                query = query.strip()
                param = param.strip()
                if param[-1] == ';':
                    param = param[:-1]
            else:
                self._struct_simpleok()
                if arg.lower() != "commit" and arg.lower() != "rollback":  # bypass commit
                    self.log.warning('%-8s: %s@%s:%s' % ('cmdBAD1', self.username, self.client_address, repr(cmdarg)))
                return

            query = query.lower()
            if query == 'call':  # 存储过程调用
                if param != 'pymysqlrpcinfo' and param != 'turnonlog' and param != 'turnofflog':
                    try:
                        self.state['tqC'] += 1
                        self.lastqueryBEGtime = time.time()
                        self.totalquery += 1
                        # not use eval , but dispatch call request to correct function
                        # retvar = eval(param, self.gdict.copy())
                        reterror, retvar = self.callfunc(param, self.gdict)
                        if reterror:
                            self.lastqueryENDtime = time.time()
                            self._struct_error(500, "HY101", "func call 1: "+str(retvar)+":" + param[:100])
                            self.log.warning('%-8s: %s@%s:%s' % ('callBAD1', self.username, self.client_address, param))
                            self.state['eqC'] += 1
                            return

                        self.lastqueryENDtime = time.time()
                        request_time = 1000.0 * (self.lastqueryENDtime - self.lastqueryBEGtime)
                        if self.server.frameworklog:
                            self.log.info("%-8s: %s@%s:%10.03f s:%8.03fms:%s" % ('callOK1', self.username, self.client_address, self.lastqueryBEGtime, request_time, param))
                        if not retvar:
                            self._struct_ok(1, 0, 0, 0, "")
                        else:
                            collist, dataset = self._toresultset(retvar)
                            self._struct_resultset(collist, dataset)
                    except LogicError, ex:
                        # 逻辑错误，也是我们主程序用在正确执行了过程，只是返回了错误结果中，所以也要记录 info
                        self.lastqueryENDtime = time.time()
                        request_time = 1000.0 * (self.lastqueryENDtime - self.lastqueryBEGtime)
                        if self.server.frameworklog:
                            self.log.info("%-8s: %s@%s:%10.03f s:%8.03fms:%s" % ('callOK2', self.username, self.client_address, self.lastqueryBEGtime, request_time, param))
                        self._struct_error(ex.errno, "HY100", ex.errmsg)
                    except Exception, ex:
                        self.lastqueryENDtime = time.time()
                        self._struct_error(500, "HY102", "func call 2: --"+str(ex)+"--:" + param[:100])
                        self.log.error('%-8s: %s@%s:%10.03f s:%s' % ('callBAD2', self.username, self.client_address, self.lastqueryBEGtime, param))
                        self.state['eqC'] += 1
                    finally:
                        pass
                    return

                elif self.username == 'root':
                    # only root can "call pymysqlrpcinfo;"  to get server infomation
                    # logon: turn on log of info
                    # logoff: turn off log fo info
                    # get pymysqlrpc server running status
                    if param == 'pymysqlrpcinfo':
                        collist, dataset = self._toresultset(self.server.serverinfo())
                    else:
                        if param == 'turnonlog':
                            self.server.turnonlog()
                        elif param == 'turnofflog':
                            self.server.turnofflog()
                        collist, dataset =self._toresultset((('frameworklog',),[(str(self.server.frameworklog),)]))
                    self._struct_resultset(collist, dataset)
                    return
                else:
                    self._struct_simpleok()
                    return

            elif query == 'set' or query == "show" or query == "select":
                # bypass like command as "SET xxx ", "SHOW yyyyy" ,"select zzz"
                self._struct_simpleok()
                return
            else:
                self.log.warning('%-8s: %s@%s:%s' % ('cmdBAD2', self.username, self.client_address, repr(cmdarg)))
                self._struct_simpleok()
                return

        elif cmd == '\x01':  # mysql cmd quit;
            self.socket.close()
            #self.log.info('%-8s: %s@%s ' % ('authCLOS', self.username, self.client_address))
            return
        elif cmd == '\x02':  # use somedb;
            self._struct_simpleok()
            return
        elif cmd == '\x1b':  # COM_SET_OPTION;
            self._struct_eof()
            return
        elif cmd == '\x0e':  # mysql client ping
            self._struct_simpleok()
            self.lastqueryBEGtime = self.lastqueryENDtime = time.time()
            return
        else:
            self.log.warning('%-8s: %s@%s:%s' % ('cmdBAD3', self.username, self.client_address, repr(cmdarg)))
            self._struct_simpleok()
            return

    def callfunc(self, req, funcdict):
        offset = req.find('(')
        if offset == -1:
            return 1, "--'(' NOT exist--"
        paramlist = []
        try:
            paramast = ast.literal_eval(req[offset:])
            if type(paramast) == tuple:
                paramlist = paramast
            else:
                paramlist.append(paramast)
        except Exception, ex:
            return 2, '--'+str(ex)+'--'
        if req[:offset] in funcdict:
            return 0, funcdict[req[:offset]](*paramlist)
        else:
            return 3, "--function NOT exist--"
