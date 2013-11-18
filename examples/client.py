from twisted.internet import defer, endpoints, task
from txjason.netstring import JSONRPCClientFactory
from txjason.client import JSONRPCClientError


@defer.inlineCallbacks
def main(reactor, description):
    endpoint = endpoints.clientFromString(reactor, description)
    client = JSONRPCClientFactory(endpoint, reactor=reactor)

    try:
        r = yield client.callRemote('bar.foo')
    except JSONRPCClientError as e:
        print e

    r = yield client.callRemote('bar.add', 1, 2)
    print "add result: %s" % str(r)

    r = yield client.callRemote('bar.whoami')
    print "whoami result: %s" % str(r)


task.react(main, ['tcp:127.0.0.1:7080'])
