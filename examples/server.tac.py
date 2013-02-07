from twisted.internet import defer
from twisted.application import service, internet
from txjsonrpc2.netstring import protocol
from txjsonrpc2 import handler


class Example(handler.Handler):
    def __init__(self, who):
        self.who = who

    @handler.exportRPC("add2")
    @defer.inlineCallbacks
    def add(self, x, y):
        yield
        defer.returnValue(x+y)

    @handler.exportRPC("whoami")
    def whoami(self):
        return self.who


factory = protocol.ServerFactory()
factory.addHandler(Example('foo'), namespace='bar')

application = service.Application("Example JSON-RPC Server")
jsonrpcServer = internet.TCPServer(7080, factory)
jsonrpcServer.setServiceParent(application)
