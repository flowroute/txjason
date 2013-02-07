import os
import sys
from twisted.internet import reactor, defer
from txjsonrpc2.netstring.protocol import Proxy
from txjsonrpc2.client import JSONRPCClientError


proxy = Proxy('127.0.0.1', 7080)


@defer.inlineCallbacks
def stuff():
    try:
        r = yield proxy.callRemote('bar.add2', z=1, y=2)
        print "add result: %s" % str(r)
    except JSONRPCClientError as e:
        print e

    r = yield proxy.callRemote('bar.whoami')
    print "whaomi result: %s" % str(r)


reactor.callWhenRunning(stuff)
reactor.run()
