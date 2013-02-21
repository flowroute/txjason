from twisted.internet import defer, reactor
from twisted.protocols.basic import NetstringReceiver
from twisted.python import log
from txjason import protocol, client


class JSONRPCClientProtocol(NetstringReceiver):
    def __init__(self, factory):
        self.factory = factory

    def stringReceived(self, string):
        try:
            self.factory.client.handleResponse(string)
        except client.JSONRPCProtocolError as e:
            log.err()
            self.transport.loseConnection()
        except:
            log.err()

    def connectionMade(self):
        self.factory.connectionMade()

    def connectionLost(self, reason):
        if self.brokenPeer:
            log.msg('Disconencted from server because of a broken peer.')
        else:
            log.msg('Lost server connection.')
        self.factory.connectionLost()


class JSONRPCServerProtocol(NetstringReceiver):
    def __init__(self, service):
         self.service = service

    @defer.inlineCallbacks
    def stringReceived(self, string):
        result = yield self.service.call(string)
        if result is not None:
             self.sendString(result)


class JSONRPCClientFactory(protocol.BaseClientFactory):
    def __init__(self, host, port, timeout=5, _reactor=reactor):
        self.client = client.JSONRPCClient(timeout=timeout)
        self.host = host
        self.port = port
        self.connecting = False
        self.connected = False
        self.closing = False
        self.reactor = _reactor

    def buildProtocol(self, addr):
        self.connection = JSONRPCClientProtocol(self)
        return self.connection

    def connect(self):
        if self.connected:
            return defer.succeed(None)
        elif self.connecting:
            return self.connecting
        if self.closing:
            return self.closing.addCallback(lambda x: self.connect())
        self.connecting = defer.Deferred()
        self.reactor.connectTCP(self.host, self.port, self)
        return self.connecting

    def connectionMade(self):
        self.connecting.callback(None)
        self.connecting = False
        self.connected = True

    def connectionLost(self):
        d = self.closing = defer.Deferred()
        self.connected = False
        self.client.cancelRequests()
        self.closing = False
        d.callback(None)

    @defer.inlineCallbacks
    def callRemote(self, method, *args, **kwargs):
        payload, d = self.client.getRequest(method, *args, **kwargs)
        yield self.connect()
        self.connection.sendString(payload)
        result = yield d
        defer.returnValue(result)

    @defer.inlineCallbacks
    def notifyRemote(self, method, *args, **kwargs):
        payload = self.client.getNotification(method, *args, **kwargs)
        yield self.connect()
        self.connection.sendString(payload)


class JSONRPCServerFactory(protocol.BaseServerFactory):
    protocol = JSONRPCServerProtocol
