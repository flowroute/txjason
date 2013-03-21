from twisted.internet import protocol
import service, client


class BaseServerFactory(protocol.ServerFactory):
    def __init__(self, seperator='.', timeout=None):
        self.service = service.JSONRPCService(timeout)
        self.seperator = seperator

    def buildProtocol(self, addr):
        return self.protocol(self.service)

    def addHandler(self, handler, namespace=None):
        handler.addToService(self.service, namespace=namespace, seperator=self.seperator)


class BaseClientFactory(protocol.ClientFactory):
    pass
