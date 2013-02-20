import json
from twisted.internet import defer
from twisted.trial import unittest
from twisted.test import proto_helpers
from txjason.netstring import protocol
from txjason import client, handler


def makeNetstring(string):
    return '%d:%s,' % (len(string), string)


class TestHandler(handler.Handler):
    @handler.exportRPC()
    def add(self, x, y):
        return x+y


class FakeReactor(object):
    def connectTCP(self, host, port, factory):
        proto = factory.buildProtocol(host)
        #proto.transport = proto_helpers.StringTransport()
        proto.makeConnection(proto_helpers.StringTransport())


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.factory = protocol.ServerFactory()
        self.factory.addHandler(TestHandler(), 'foo')
        self.proto = self.factory.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)
        self.client = client.JSONRPCClient()

    def _test(self, request, expected):
        request = makeNetstring(request)
        self.proto.dataReceived(request)
        self.assertEqual(self.tr.value(), expected)

    def test_request(self):
        request = self.client._getPayload('foo.add', 'X', 1, 2)
        self._test(request, '42:{"jsonrpc": "2.0", "result": 3, "id": "X"},')

    def test_notification(self):
        request = self.client._getPayload('foo.add', None, 1, 2)
        self._test(request, '')

    def test_error(self):
        request = self.client._getPayload('add', 'X', 1, 2)
        self._test(request, '87:{"jsonrpc": "2.0", "id": "X", "error": {"message": "Method not found", "code": -32601}},')


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        self.proxy = protocol.Proxy('localhost', 5050, _reactor=FakeReactor())

    def test_request(self):
        called = []
        def cb(r):
            called.append(r)
            self.assertEqual(r, 3)
        d = self.proxy.callRemote('foo', 1, 2).addBoth(cb)
        self.assertEqual(self.proxy.connection.transport.value(), '62:{"params": [1, 2], "jsonrpc": "2.0", "method": "foo", "id": 1},')
        self.proxy.connection.stringReceived('{"jsonrpc": "2.0", "result": 3, "id": 1}')
        return d

    def test_notification(self):
        self.proxy.notifyRemote('foo', 1, 2)
        self.assertEqual(self.proxy.connection.transport.value(), '53:{"params": [1, 2], "jsonrpc": "2.0", "method": "foo"},')

    def test_error_response(self):
        d = self.proxy.callRemote('foo', 1, 2)
        self.proxy.connection.stringReceived('{"jsonrpc": "2.0", "id": 1, "error": {"message": "Method not found", "code": -32601}}')
        self.failUnlessFailure(d, client.JSONRPCClientError)

    def test_lost_connection(self):
        d = self.proxy.callRemote('foo', 1, 2)
        self.proxy.connection.connectionLost(None)
        self.failUnlessFailure(d, defer.CancelledError)
