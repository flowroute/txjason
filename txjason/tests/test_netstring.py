import json

from twisted.internet import defer, task
from twisted.test import proto_helpers
from txjason.netstring import JSONRPCClientFactory, JSONRPCServerFactory
from txjason import client, handler

from common import TXJasonTestCase


def readNetstring(string):
    prefix, sep, rest = string.partition(':')
    if not sep or len(rest) != int(prefix) + 1:
        raise ValueError('not a valid netstring')
    return rest[:-1]


def makeNetstring(string):
    return '%d:%s,' % (len(string), string)


class TestHandler(handler.Handler):
    @handler.exportRPC()
    def add(self, x, y):
        return x + y


class FakeReactor(object):
    def connectTCP(self, host, port, factory):
        proto = factory.buildProtocol(host)
        proto.makeConnection(proto_helpers.StringTransport())


class FakeError(Exception):
    pass


class FakeDisconnectedError(Exception):
    pass


class FakeEndpoint(object):
    def __init__(self, deferred=None, fail=False):
        self.deferred = deferred
        self.fail = fail
        self.connected = False

    def connect(self, fac):
        if self.deferred:
            return self.deferred
        if self.fail:
            return defer.fail(FakeError())
        self.proto = fac.buildProtocol(None)
        self.transport = proto_helpers.StringTransport()
        self.transport.abortConnection = self.transport.loseConnection = (
            lambda: self.disconnect(FakeDisconnectedError()))
        self.proto.makeConnection(self.transport)
        self.connected = True
        return defer.succeed(self.proto)

    def disconnect(self, reason):
        self.connected = False
        self.proto.connectionLost(reason)
        self.proto = self.transport = None


class ServerTestCase(TXJasonTestCase):
    def setUp(self):
        self.factory = JSONRPCServerFactory()
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


class ClientTestCase(TXJasonTestCase):
    """
    Tests for JSONRPCClientFactory.
    """

    def setUp(self):
        self.reactor = task.Clock()
        self.endpoint = FakeEndpoint()
        self.factory = JSONRPCClientFactory(
            self.endpoint, reactor=self.reactor)

    def test_callRemote(self):
        """
        callRemote sends data and returns a Deferred that fires with the result
        from over the wire.
        """
        self.assertFalse(self.endpoint.connected)
        d = self.factory.callRemote('spam')
        self.assert_(self.endpoint.connected)
        self.assertEqual(
            json.loads(readNetstring(self.endpoint.transport.value())),
            {'params': [], 'jsonrpc': '2.0', 'method': 'spam', 'id': 1})
        self.endpoint.proto.stringReceived(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'result': 'eggs'}))
        self.assertEqual(self.successResultOf(d), 'eggs')

    def test_callRemote_error_response(self):
        """
        callRemote's Deferred can also errback if an error comes over the wire.
        """
        d = self.factory.callRemote('spam')
        self.endpoint.proto.stringReceived(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'error': {
                'message': 'error', 'code': -19}}))
        self.failureResultOf(d, client.JSONRPCClientError)

    def test_notifyRemote(self):
        """
        notifyRemote sends data but and returns a Deferred, but does not expect
        a response.
        """
        self.assertFalse(self.endpoint.connected)
        d = self.factory.notifyRemote('spam')
        self.assert_(self.endpoint.connected)
        self.assertEqual(
            json.loads(readNetstring(self.endpoint.transport.value())),
            {'params': [], 'jsonrpc': '2.0', 'method': 'spam'})
        self.successResultOf(d)

    def test_callRemote_connection_failure(self):
        """
        Connection failures get propagated as an errback on callRemote's
        Deferred.
        """
        self.assertFalse(self.endpoint.connected)
        self.endpoint.fail = True
        d = self.factory.callRemote('spam')
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 1)
        self.failureResultOf(d, FakeError)

    def test_notifyRemote_connection_failure(self):
        """
        Connection failures get propagated as an errback on notifyRemote's
        Deferred.
        """
        self.assertFalse(self.endpoint.connected)
        self.endpoint.fail = True
        d = self.factory.notifyRemote('spam')
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 1)
        self.failureResultOf(d, FakeError)

    def test_notifyRemote_two_connection_failures(self):
        """
        In the case of two synchronous connection failures, both notifyRemote
        calls errback with the connection failure.
        """
        self.assertFalse(self.endpoint.connected)
        self.endpoint.fail = True
        d1 = self.factory.notifyRemote('spam')
        d2 = self.factory.notifyRemote('spam')
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 2)
        self.successResultOf(defer.gatherResults([
            self.assertFailure(d1, FakeError),
            self.assertFailure(d2, FakeError),
        ]))

    def test_notifyRemote_two_pending_connection_failures(self):
        """
        In the case of two notifyRemotes both waiting on the same connection,
        and the connection fails, both Deferreds returned by notifyRemote will
        errback.
        """
        self.assertFalse(self.endpoint.connected)
        self.endpoint.deferred = defer.Deferred()
        d1 = self.factory.notifyRemote('spam')
        d2 = self.factory.notifyRemote('spam')
        self.endpoint.deferred.errback(FakeError())
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 1)
        self.successResultOf(defer.gatherResults([
            self.assertFailure(d1, FakeError),
            self.assertFailure(d2, FakeError),
        ]))

    def test_callRemote_cancellation_during_connection(self):
        """
        The Deferred returned by callRemote can be cancelled during the
        connection attempt.
        """
        self.assertFalse(self.endpoint.connected)
        canceled = []
        self.endpoint.deferred = defer.Deferred(canceled.append)
        d = self.factory.callRemote('spam')
        d.cancel()
        self.assert_(canceled)
        self.assertEqual(len(self.flushLoggedErrors(defer.CancelledError)), 1)
        self.failureResultOf(d, defer.CancelledError)

    def test_callRemote_cancellation_during_request(self):
        """
        The Deferred returned by callRemote can be cancelled while waiting on a
        response.
        """
        self.assertFalse(self.endpoint.connected)
        d = self.factory.callRemote('spam')
        d.cancel()
        self.failureResultOf(d, defer.CancelledError)

    def test_notifyRemote_cancellation_during_connection(self):
        """
        The Deferred returned by notifyRemote can be cancelled during the
        connection attempt.
        """
        self.assertFalse(self.endpoint.connected)
        canceled = []
        self.endpoint.deferred = defer.Deferred(canceled.append)
        d = self.factory.notifyRemote('spam')
        d.cancel()
        self.assert_(canceled)
        self.assertEqual(len(self.flushLoggedErrors(defer.CancelledError)), 1)
        self.failureResultOf(d, defer.CancelledError)

    def test_reconnection(self):
        """
        A new connection is established if the connection is lost between
        notifyRemote calls.
        """
        self.assertFalse(self.endpoint.connected)
        self.factory.notifyRemote('spam')
        self.assert_(self.endpoint.connected)
        self.endpoint.disconnect(FakeDisconnectedError())
        self.assertFalse(self.endpoint.connected)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 1)
        self.factory.notifyRemote('eggs')
        self.assert_(self.endpoint.connected)
        self.assertEqual(
            json.loads(readNetstring(self.endpoint.transport.value())),
            {'params': [], 'jsonrpc': '2.0', 'method': 'eggs'})

    def test_callRemote_timeout(self):
        """
        A timeout causes the Deferred returned by callRemote to errback with
        CancelledError.
        """
        self.assertFalse(self.endpoint.connected)
        d = self.factory.callRemote('spam')
        self.reactor.advance(10)
        self.failureResultOf(d, defer.CancelledError)

    def test_disconnect(self):
        """
        The disconnect method drops the current connection.
        """
        d = self.factory.notifyRemote('spam')
        self.successResultOf(d)
        self.assertIsNot(self.endpoint.transport, None)
        self.factory.disconnect()
        self.assertIs(self.endpoint.transport, None)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 1)

    def test_disconnect_connection_cancellation(self):
        """
        The disconnect method cancels pending connections.
        """
        canceled = []
        self.endpoint.deferred = defer.Deferred(canceled.append)
        d = self.factory.notifyRemote('spam')
        self.factory.disconnect()
        self.assert_(canceled)
        self.assertEqual(len(self.flushLoggedErrors(defer.CancelledError)), 1)
        self.failureResultOf(d, defer.CancelledError)

    def test_disconnect_callRemote_cancellation(self):
        """
        The disconnect method cancels pending callRemote Deferreds.
        """
        d = self.factory.callRemote('spam')
        self.assertIsNot(self.endpoint.transport, None)
        self.factory.disconnect()
        self.assertIs(self.endpoint.transport, None)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 1)
        self.failureResultOf(d, defer.CancelledError)

    def test_connect(self):
        """
        The connect method returns a Deferred that fires when the connection is
        established.
        """
        self.endpoint.deferred = defer.Deferred()
        d = self.factory.connect()
        self.assertNoResult(d)
        self.endpoint.deferred.callback(self.factory.buildProtocol(None))
        self.successResultOf(d)

    def test_connect_cancellation(self):
        """
        Cancelling the connect method's Deferred cancels the connection's
        Deferred.
        """
        canceled = []
        self.endpoint.deferred = defer.Deferred(canceled.append)
        d = self.factory.connect()
        self.assertNoResult(d)
        d.cancel()
        self.assert_(canceled)
        self.failureResultOf(d, defer.CancelledError)
        self.assertEqual(len(self.flushLoggedErrors(defer.CancelledError)), 1)

    def test_connect_failure(self):
        """
        The connect method's Deferred errbacks if the connection itself
        errbacks.
        """
        self.endpoint.deferred = defer.Deferred()
        d = self.factory.connect()
        self.assertNoResult(d)
        self.endpoint.deferred.errback(FakeError())
        self.failureResultOf(d, FakeError)
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 1)

    def test_notifyDisconnect(self):
        """
        The notifyDisconnect method returns a Deferred that fires when the
        client has disconnected.
        """
        d = self.factory.notifyDisconnect()
        self.successResultOf(self.factory.connect())
        self.assertNoResult(d)
        self.endpoint.disconnect(FakeDisconnectedError())
        self.failureResultOf(d, FakeDisconnectedError)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 1)

    def test_notifyDisconnect_after_connection(self):
        """
        The notifyDisconnect method returns a Deferred that fires when the
        client has disconnected even if it's called after a connection is
        established.
        """
        self.successResultOf(self.factory.connect())
        d = self.factory.notifyDisconnect()
        self.assertNoResult(d)
        self.endpoint.disconnect(FakeDisconnectedError())
        self.failureResultOf(d, FakeDisconnectedError)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 1)

    def test_notifyDisconnect_after_disconnection(self):
        """
        notifyDisconnect doesn't return a fired Deferred if it's called after
        disconnection but instead returns a Deferred that fires after the next
        disconnection.
        """
        self.successResultOf(self.factory.connect())
        self.endpoint.disconnect(FakeDisconnectedError())
        d = self.factory.notifyDisconnect()
        self.assertNoResult(d)
        self.successResultOf(self.factory.connect())
        self.endpoint.disconnect(FakeDisconnectedError())
        self.failureResultOf(d, FakeDisconnectedError)
        self.assertEqual(len(self.flushLoggedErrors(FakeDisconnectedError)), 2)
