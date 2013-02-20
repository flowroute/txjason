from twisted.internet import defer
from twisted.application import service, internet
from txjason.netstring import JSONRPCServerFactory
from txjason import handler


class Example(handler.Handler):
    def __init__(self, who):
        self.who = who

    @handler.exportRPC("add")
    @defer.inlineCallbacks
    def _add(self, x, y):
        yield
        defer.returnValue(x+y)

    @handler.exportRPC()
    def whoami(self):
        return self.who


factory = JSONRPCServerFactory()
factory.addHandler(Example('foo'), namespace='bar')

application = service.Application("Example JSON-RPC Server")
jsonrpcServer = internet.TCPServer(7080, factory)
jsonrpcServer.setServiceParent(application)
