#pymysqlrpc#

----------

###简介###

pymysqlrpc是一个非常有趣，非常简单的rpc框架。实现了 **mysql服务端协议**，基于 **gevent**开发，将对mysql存储过程的调用映射到python的一个函数或者一个实例的某个方法。

目前pymysqlrpc的版本为 0.1.0，并且使用MIT协议。

为什么基于mysql协议？mysql已经具有：

- 用户
- 密码认证
- 权限控制
- 协议规范
- 各种语言都有client lib

mysql的存储过程更加具有：

- 方法名
- 入参规范
- 返回规范
- 序列化和反序列化

只要调用者曾经使用过mysql DB开发，那么在向他发布 pymysqlrpc 服务时候，不用协商网络协议，参数规范，只要告诉他象调用一个mysql的存储过程就可以了。这样大大降低了沟通，使用成本。

为什么使用gevent？这是个问题吗？

###使用入门###

首先从pypi上安装pymysqlrpc 或者从 [pymysqlrpc on github](http://www.github.com/feihuroger/pymysqlrpc) clone源码:

	easy_install pymysqlrpc

然后我们来写一个最简单的例子：

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


运行服务端：

	$python runmain.py

然后可以使用mysql的命令客户端连接：

	$mysql -utestuser -ptestpass -P3308

连接成功后，可以象调用mysql存储过程一样来调用刚才定义的方法：**mysql> call myadd(3,4);**

可以得到结果：

	mysql> call myadd(3,4);
	+------+
	| sum  |
	+------+
	|    7 |
	+------+
	1 row in set (0.00 sec)

pymysqlrpc 提供了web，命令行两种查看系统状态的方式，如果你在aclmap中设置了root用户的登录密码，web查看密码。

在浏览器地址栏访问这个地址：[http://localhost:8308/pymysqlrpc/info/root/viewpass](http://localhost:8308/pymysqlrpc/info/root/viewpass)

可以看到：

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


还可以root 用户 mysql命令行登录：

	$mysql -uroot -prootpass -P3308

执行 **call pymysqlrpcinfo;**

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

###项目站点###

请访问 [github上的pymysqlrpc](http://www.github.com/feihuroger/pymysqlrpc "http://www.github.com/feihuroger/pymysqlrpc")，更加全面的例子，注释在example目录下。

感谢当时参与过开发的前同事：gashero, kilnt, bob.ning. rpc的版本从 twisted, socket&flup, ioloop 一路走过来，现在由我把它改写成gevent并开源。

feihu.roger@2013年5月1日
