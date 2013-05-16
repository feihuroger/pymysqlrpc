# pymysqlrpc#

----------

BTW: after writing readme in chinese, I used Youdao Dict translate it into english, and modify something. I hope you can understand those, if feel uncertain, reading the source and example. The language of programmer is code.

###Introduction###

pymysqlrpc is a very interesting, very simple RPC framework, implement **mysql server protocol**,  on top of **gevent**,  map one call of mysql stored procedures to python's a function or a method of an instance.

At present, pymysqlrpc version is 0.1.0, and MIT license.

Why implement the mysql server protocol? Mysql already have:

- the user
- password authentication
- access control
- protocol specifications
- all languages have mysql client lib.

Mysql stored procedures have more:

- the method name
- the parameter specification
- the return specification
- serialization and deserialization

As long as the developer used mysql DB, when release the pymysqlrpc service, need not consultation network protocol, parameter specification, just tell developer like calling a mysql stored procedures. This greatly reduces the communication.

Why use gevent? Why not?

###How to use###

First of all， install pymysqlrpc from pypi or clone from [pymysqlrpc on github](http://www.github.com/feihuroger/pymysqlrpc):

	easy_install pymysqlrpc

And then to write one of the most simple example, know about the use pymysqlrpc

runmain.py

	from pymysqlrpc import RPCServer

	def add(a, b):
	    return('sum',), [(a+b,), ]

	aclmap = {"testuser": ["testpass",
						{"myadd": add}
						],
			"root":("rootpass", "viewpass")
			}

	server = RPCServer(('0.0.0.0', 3308), aclmap)
	server.serve_forever()


Run the server:

	$python runmain.py

Use the mysql command client connection:

	$mysql --port 3308 -h 127.0.0.1 -utestuser -ptestpass
After the connection is successful, rpc can be invoked just like invoke mysql stored procedures defined in the method:

	mysql>call myadd(3,4);

the result:

	mysql> call myadd(3,4);
	+------+
	| sum  |
	+------+
	|    7 |
	+------+
	1 row in set (0.00 sec)

You can view pymysqlrpc server status throght web or mysql command line，if you set user "root" and root's login password and webview password

Access this address in your browser's address bar:[http://localhost:8308/pymysqlrpc/info/root/webviewpass](http://localhost:8308/pymysqlrpc/info/root/webviewpass)

then can see:

	python_version : 2.7.4
	gevent_version : 1.0b2
	pymysqlrpc_ver : 1.0.0
	server listen  : ('0.0.0.0', 3308)
	webviewer port : 8308
	monitor        : interval:  1s; querytimeout:  3s; activetimeout:  1800s
	begin   time   : 2013-04-29 12:41:14
	running time   : 0 days 0 hours 791 seconds
	pool  stat     : using:      2; size:      100;
	conn  stat     : active:     2; total:       5; normal close:     3; error close:     0;
	auth  stat     : good:       4; total:       5; error:     1;
	query stat     : good:       4; total:      10; error:     6;
	online client  : online:     2
	client 1       : testuser@('127.0.0.1', 5078) authBEG: 04-29 12:54:08 lastqueryBEG: 04-29 12:54:22  totalquery:4
	client 2       : root@('127.0.0.1', 4997) authBEG: 04-29 12:48:26 lastqueryBEG: 04-29 12:49:40  totalquery:3


and you can login pymysqlrpc server throght mysql command line:

	$mysql --prot 3308 -h 127.0.0.1 -uroot -prootpass

type  **call pymysqlrpcinfo;**

	mysql> call pymysqlrpcinfo;
	+----------------+--------------------------------------------------------------------------------------------------+
	| Variable_name  | Value                                                                                            |
	+----------------+--------------------------------------------------------------------------------------------------+
	| python_version | 2.7.4                                                                                            |
	| gevent_version | 1.0b2                                                                                            |
	| pymysqlrpc_ver | 1.0.0                                                                                            |
	| server listen  | ('0.0.0.0', 3308)                                                                                |
	| webviewer port | 8308                                                                                             |
	| monitor        | interval:  1s; querytimeout:  3s; activetimeout:  1800s                                          |
	| begin   time   | 2013-04-29 12:41:14                                                                              |
	| running time   | 0 days 0 hours 990 seconds                                                                       |
	| pool  stat     | using:      2; size:      100;                                                                   |
	| conn  stat     | active:     2; total:       9; normal close:     7; error close:     0;                          |
	| auth  stat     | good:       7; total:       9; error:     2;                                                     |
	| query stat     | good:       4; total:      10; error:     6;                                                     |
	| online client  | online:     2                                                                                    |
	| client 1       | testuser@('127.0.0.1', 5078) authBEG: 04-29 12:54:08 lastqueryBEG: 04-29 12:54:22  totalquery:4  |
	| client 2       | root@('127.0.0.1', 4997) authBEG: 04-29 12:48:26 lastqueryBEG: 04-29 12:49:40  totalquery:3      |
	+----------------+--------------------------------------------------------------------------------------------------+
	15 rows in set (0.00 sec)

###project site###

Please visit the [pymysqlrpc on github](http://www.github.com/feihuroger/pymysqlrpc "http://www.github.com/feihuroger/pymysqlrpc"), a more comprehensive demo in example directory.

Thanks of my co-worker at that time: gashero, kilnt, bob.ning. The rpc framework evolution from twisted, socket&flup, ioloop of tornado 1.x, now I rewrite it by gevent.

by feihu.roger@2013/5/1
