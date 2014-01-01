import json
from twisted.internet import defer, task
from twisted.python.failure import Failure
from txjason import service

from common import TXJasonTestCase

clock = task.Clock()


class FooException(service.JSONRPCError):
    message = "Foo"
    code = -32099


class ApplicationError(service.JSONRPCError):
    code = -32099
    message = "Fake Error"


def subtract(minuend, subtrahend):
    return minuend-subtrahend


def error():
    raise ApplicationError()


def update(*args):
    pass


def deferred_echo(x):
    return defer.succeed(x)


def bad_handler(x):
    return "foo" + 2 + x


def delay(d):
    return task.deferLater(clock, d, lambda: 'x')


class ServiceTestCase(TXJasonTestCase):
    def setUp(self):
        self.service = service.JSONRPCService(reactor=clock)
        self.service.add(subtract)
        self.service.add(update)
        self.service.add(error)
        self.service.add(delay)
        self.service.add(deferred_echo)
        self.service.add(bad_handler)

    @defer.inlineCallbacks
    def makeRequest(self, request, expected, advance=None):
        if not isinstance(request, basestring):
            request = json.dumps(request)
        d = self.service.call(request)
        if advance:
            clock.advance(advance)
        response = yield d
        if response is not None:
            response = json.loads(response)
        self.assertEqual(response, expected)

    @defer.inlineCallbacks
    def test_positonal_params(self):
        request = {"jsonrpc": "2.0",
                   "method": "subtract",
                   "params": [42, 23],
                   "id": 1}
        expected = {"jsonrpc": "2.0",
                    "result": 19,
                    "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_named_params(self):
        request = {"jsonrpc": "2.0",
                   "method": "subtract",
                   "params": {"subtrahend": 23, "minuend": 42},
                   "id": 1}
        expected = {"jsonrpc": "2.0", "result": 19, "id": 1}
        yield self.makeRequest(request, expected)
        request = {"jsonrpc": "2.0",
                   "method": "subtract",
                   "params": {"minuend": 42,
                              "subtrahend": 23},
                   "id": 1}
        expected = {"jsonrpc": "2.0", "result": 19, "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_notification(self):
        request = {"jsonrpc": "2.0",
                   "method": "update",
                   "params": [1, 2, 3, 4, 5]}
        expected = None
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_bad_method(self):
        request = {"jsonrpc": "2.0", "method": "foobar", "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found"},
                    "id": "1"}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_applicationError(self):
        request = {"jsonrpc": "2.0", "method": "error", "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32099, "message": "Fake Error"},
                    "id": "1"}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_out_of_service(self):
        called = []

        def cb(r):
            called.append(r)
        request = {"jsonrpc": "2.0",
                   "method": "delay",
                   "params": [1],
                   "id": "1"}
        d = self.service.call(json.dumps(request))
        d = self.service.stopServing(FooException)
        d.addBoth(cb)
        request = {"jsonrpc": "2.0", "method": "error", "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32099, "message": "Foo"},
                    "id": "1"}
        yield self.makeRequest(request, expected)
        clock.advance(2)
        yield d
        self.assertEqual(len(called), 1)

    @defer.inlineCallbacks
    def test_invalid_json(self):
        request = \
            '{"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]'
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_bad_request(self):
        request = {"jsonrpc": "2.0", "method": 1, "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid request"},
                    "id": "1"}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_empty_batch(self):
        request = []
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid request"},
                    "id": None}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_invalid_batch(self):
        request = [1, 2, 3]
        expected = [
            {"jsonrpc": "2.0",
             "error": {"code": -32600, "message": "Invalid request"},
             "id": None},
            {"jsonrpc": "2.0",
             "error": {"code": -32600, "message": "Invalid request"},
             "id": None},
            {"jsonrpc": "2.0",
             "error": {"code": -32600, "message": "Invalid request"},
             "id": None}
        ]
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_batch(self):
        request = [
            {"jsonrpc": "2.0",
             "method": "subtract",
             "params": [42, 23],
             "id": 1},
            {"jsonrpc": "2.0",
             "method": "update",
             "params": [1, 2, 3, 4, 5]},
            {"foo": "bar"},
            {"jsonrpc": "2.0",
             "method": "subtract.foo",
             "params": {"subtrahend": 23, "minuend": 42},
             "id": 2},
            {"jsonrpc": "2.0",
             "method": "subtract",
             "params": {"subtrahend": 23, "minuend": 42},
             "id": 3}
        ]
        expected = [
            {'error': {'code': -32600, 'message': 'Invalid request'},
             'id': None,
             'jsonrpc': '2.0'},
            {'error': {'code': -32601, 'message': 'Method not found'},
             'id': 2,
             'jsonrpc': '2.0'},
            {'id': 1, 'jsonrpc': '2.0', 'result': 19},
            {'id': 3, 'jsonrpc': '2.0', 'result': 19}
        ]
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_batch2(self):
        self.service.stopServing(FooException)
        request = [
            {"jsonrpc": "2.0",
             "method": "update",
             "params": [1, 2, 3, 4, 5]},
            {"jsonrpc": "2.0",
             "method": "subtract",
             "params": {"subtrahend": 23,
                        "minuend": 42},
             "id": 3}
        ]
        expected = [
            {'error': {'code': -32099, 'message': 'Foo'},
             'id': 3,
             'jsonrpc': '2.0'},
        ]
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_batch_notification(self):
        request = [
            {"jsonrpc": "2.0", "method": "update", "params": [1, 2, 3, 4, 5]},
            {"jsonrpc": "2.0", "method": "update", "params": ['x', 'y', 'z']},
        ]
        expected = None
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_deferred(self):
        request = {"jsonrpc": "2.0",
                   "method": "deferred_echo",
                   "params": ["x"],
                   "id": 1}
        expected = {"jsonrpc": "2.0", "result": "x", "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_deferred_batch(self):
        request = [
            {"jsonrpc": "2.0",
             "method": "deferred_echo",
             "params": ["x"],
             "id": 1},
            {"jsonrpc": "2.0",
             "method": "subtract",
             "params": [42, 23],
             "id": 2}
        ]
        expected = [
            {"jsonrpc": "2.0", "result": "x", "id": 1},
            {"jsonrpc": "2.0", "result": 19, "id": 2}
        ]

        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_timeout(self):
        request = {"jsonrpc": "2.0",
                   "method": "delay",
                   "params": [10],
                   "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32098, "message": "Server Timeout"},
                    "id": "1"}
        self.service.timeout = 1
        yield self.makeRequest(request, expected, 5)

    @defer.inlineCallbacks
    def test_cancel_pending(self):
        d1 = self.service.call(json.dumps({"jsonrpc": "2.0",
                                           "method": "delay",
                                           "params": [10],
                                           "id": "1"}))
        d2 = self.service.call(json.dumps({"jsonrpc": "2.0",
                                           "method": "delay",
                                           "params": [10],
                                           "id": "2"}))
        self.service.cancelPending()
        r1 = yield d1
        r2 = yield d2
        e1 = {"jsonrpc": "2.0",
              "error": {"code": -32098, "message": "Server Timeout"},
              "id": "1"}
        e2 = {"jsonrpc": "2.0",
              "error": {"code": -32098, "message": "Server Timeout"},
              "id": "2"}
        self.assertEqual(json.loads(r1), e1)
        self.assertEqual(json.loads(r2), e2)

    @defer.inlineCallbacks
    def test_bad_handler(self):
        request = {"jsonrpc": "2.0",
                   "method": "bad_handler",
                   "params": [10],
                   "id": "1"}
        expected = {"jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "Server error"},
                    "id": "1"}
        yield self.makeRequest(request, expected)
        e = self.flushLoggedErrors(TypeError)
        self.assertTrue(e[0].check(TypeError))


class FakeJSONRPCClientFactory(object):
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []
        self.connected = False

    def connect(self):
        self.connected = True
        return defer.succeed(self.failure)

    def disconnect(self):
        self.connected = False

    def callRemote(self, *a, **kw):
        self.calls.append(('call', a, kw))
        return defer.succeed(None)

    def notifyRemote(self, *a, **kw):
        self.calls.append(('notify', a, kw))
        return defer.succeed(None)


class FakeError(Exception):
    pass


class ClientServiceTests(TXJasonTestCase):
    def setUp(self):
        self.clientFactory = FakeJSONRPCClientFactory()
        self.service = service.JSONRPCClientService(self.clientFactory)

    def test_basic_operation(self):
        self.service.startService()
        d1 = self.service.callRemote('spam', 'eggs', spam='eggs')
        d2 = self.service.notifyRemote('eggs', 'spam', eggs='spam')
        self.assertEqual(self.clientFactory.calls, [
            ('call', ('spam', 'eggs'), {'spam': 'eggs'}),
            ('notify', ('eggs', 'spam'), {'eggs': 'spam'}),
        ])
        self.successResultOf(d1)
        self.successResultOf(d2)

    def test_connection_failures_get_logged(self):
        self.clientFactory.failure = Failure(FakeError())
        self.service.startService()
        self.assertEqual(len(self.flushLoggedErrors(FakeError)), 1)

    def test_connection_and_disconnection(self):
        self.assertFalse(self.clientFactory.connected)
        self.service.startService()
        self.assertTrue(self.clientFactory.connected)
        self.service.stopService()
        self.assertFalse(self.clientFactory.connected)

    def test_connection_check_on_callRemote(self):
        d = self.service.callRemote('spam', 'eggs')
        self.failureResultOf(d, service.ServiceStopped)

    def test_connection_check_on_notifyRemote(self):
        d = self.service.notifyRemote('spam', 'eggs')
        self.failureResultOf(d, service.ServiceStopped)
