# hdf
Hui Distributed Framework

BSCTS分布式框架

总体技术框架(BSCTS)
Client前端：WebClient(Tornado/Flask+EasyUi)/RpcClient/SoapClient/SocketClient
Service：HttpService/JsonRpcService/SoapService/SocketService
缓存服务器：Redis
后台交易：Java/Python
后台数据库：Oracle/Mysql

交易请求处理流程：
1、Client前端发起交易请求至Service。
2、Service将交易请求信息封装成JSON格式数据，提交到Redis缓存服务器，然后同步或异步等待交易返回结果。
3、Redis服务器将请求交易信息发布给后台交易组件。
4、后台交易组件接收到交易请求后，执行业务交易，将执行结果写入Redis服务器。
5、Redis服务器通知Service接收交易执行结果。
6、Service接收交易执行结果，返还给Client前端。
可以建立多个不同Service ，接收不同格式的前端请求。
如：HttpService,JsonRpcService,SoapService,SocketService


本框架在传统的BSS基础上进行了扩展，将原三层架构变为五层的BSCTS，即在传统的BSS三层架构中插入了缓存服务和交易服务。相对于BSS三层架构，BSCTS有如下优点：

(1)分布式逻辑业务交易处理，实现高性能、高并发。可以将各逻辑业务交易打散，分布在各个后台交易程序中执行。可以针对不同业务交易的繁忙程度，增加调整对应的后台交易模块数量，加快处理速度。
(2)通过缓存服务器，耦合了前端与后端之间的关系。将MVC中的业务逻辑交易模块剥离出来，大大减轻Web服务器的负荷，增强了Web服务器吞吐量。
(3)以数据接口方式揉合前端、后台以及数据库之间的关系，使系统流程设计更加清晰和规范。前端，后台、数据库开发人员可以分别用不同的程序设计语言来开发相关模块，可以充分利用各种程序设计语言的优点来完成系统功能。如Service和业务交易后台，可以用java，python，c等语言相互协作实现系统功能。
