from twisted.application import service
from twisted.internet import defer, endpoints, reactor
from txjason.netstring import JSONRPCClientFactory
from txjason.client import JSONRPCClientError
from txjason.service import JSONRPCClientService


@defer.inlineCallbacks
def main():
    try:
        r = yield clientService.callRemote('bar.foo')
    except JSONRPCClientError as e:
        print e

    r = yield clientService.callRemote('bar.add', 1, 2)
    print "add result: %s" % str(r)

    r = yield clientService.callRemote('bar.whoami')
    print "whoami result: %s" % str(r)


application = service.Application('example JSON-RPC client')
endpoint = endpoints.clientFromString(reactor, 'tcp:127.0.0.1:7080')
client = JSONRPCClientFactory(endpoint, reactor=reactor)
clientService = JSONRPCClientService(client)
clientService.setServiceParent(application)
reactor.callLater(1, main)
