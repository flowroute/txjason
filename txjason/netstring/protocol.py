import traceback
from twisted.internet import defer, reactor
from twisted.protocols.basic import NetstringReceiver
from twisted.python import log
from txjason import protocol, client
import netstring


class BaseProtocol(NetstringReceiver):
    def write(self, string):
         self.transport.write(netstring.dumps(string))


class ClientProtocol(BaseProtocol):
    def __init__(self, factory):
        self.factory = factory

    def stringReceived(self, string):
        try:
            self.factory.proxy.client.handleResponse(string)
        except client.JSONRPCProtocolError as e:
            traceback.format_exc()
            self.transport.loseConnection()
        except:
            traceback.format_exc()

    def connectionMade(self):
        self.factory.proxy.connectionMade()

    def connectionLost(self, reason): 
        if self.brokenPeer:
            log.msg('Disconencted from server because of a broken peer.')
        else:
            log.msg('Lost server connection.')
        self.factory.proxy.connectionLost()


class ServerProtocol(BaseProtocol):
    def __init__(self, service):
         self.service = service

    @defer.inlineCallbacks
    def stringReceived(self, string):
        result = yield self.service.call(string)
        if result is not None:
             self.write(result)


class ClientFactory(protocol.BaseClientFactory):
    def __init__(self, proxy):
        self.proxy = proxy

    def buildProtocol(self, addr):
        self.connection = ClientProtocol(self)
        return self.connection


class ServerFactory(protocol.BaseServerFactory):
    protocol = ServerProtocol


class Proxy(object):
    def __init__(self, host, port, timeout=5):
        self.client = client.JSONRPCClient(timeout=timeout)
        self.host = host
        self.port = port
        self.connecting = False
        self.connected = False
        self.closing = False
        self.factory = None

    def connect(self):
        if self.connected:
            return defer.succeed(None)
        elif self.connecting:
            return self.connecting
        if self.closing:
            return self.closing.addCallback(lambda x: self.connect())
        self.connecting = defer.Deferred()
        self.factory = ClientFactory(self)
        reactor.connectTCP(self.host, self.port, self.factory)
        return self.connecting

    def connectionMade(self):
        self.connecting.callback(None)
        self.connecting = False
        self.connected = True

    def connectionLost(self):
        d = self.closing = defer.Deferred()
        self.connected = False
        self.factory = None
        self.client.cancelRequests()
        self.closing = False
        d.callback(None)

    @defer.inlineCallbacks
    def callRemote(self, method, *args, **kwargs):
        payload, d = self.client.getRequest(method, *args, **kwargs)
        yield self.connect()
        self.factory.connection.write(payload)
        result = yield d
        defer.returnValue(result)

    @defer.inlineCallbacks
    def notifyRemote(self, method, *args, **kwargs):
        payload = self.client.getNotification(method, *args, **kwargs)
        yield self.connect()
        self.factory.connection.write(payload)
