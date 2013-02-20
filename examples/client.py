from twisted.internet import reactor, defer
from txjason.netstring import JSONRPCClientFactory
from txjason.client import JSONRPCClientError


client = JSONRPCClientFactory('127.0.0.1', 7080)


@defer.inlineCallbacks
def stuff():
    try:
        r = yield client.callRemote('bar.foo')
    except JSONRPCClientError as e:
        print e

    r = yield client.callRemote('bar.add', 1, 2)
    print "add result: %s" % str(r)

    r = yield client.callRemote('bar.whoami')
    print "whaomi result: %s" % str(r)


reactor.callWhenRunning(stuff)
reactor.run()
