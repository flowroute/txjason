import json
from twisted.internet import defer
from twisted.trial import unittest
from txjsonrpc2 import service


def subtract(minuend, subtrahend):
    return minuend-subtrahend


def update(*args):
    pass


def deferred_echo(x):
    return defer.succeed(x)


class ServiceTestCase(unittest.TestCase): 
    def setUp(self):
        self.service = service.JSONRPCService()
        self.service.add(subtract)
        self.service.add(update)
        self.service.add(deferred_echo)

    @defer.inlineCallbacks
    def makeRequest(self, request, expected):
        if not isinstance(request, basestring):
            request = json.dumps(request)
        response = yield self.service.call(request)
        if response is not None:
            response = json.loads(response)
        self.assertEqual(response, expected)

    @defer.inlineCallbacks
    def test_positonal_params(self):
        request = {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
        expected = {"jsonrpc": "2.0", "result": 19, "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_named_params(self):
        request = {"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 1}
        expected = {"jsonrpc": "2.0", "result": 19, "id": 1}
        yield self.makeRequest(request, expected)
        request = {"jsonrpc": "2.0", "method": "subtract", "params": {"minuend": 42, "subtrahend": 23}, "id": 1}
        expected = {"jsonrpc": "2.0", "result": 19, "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_notification(self):
        request = {"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]}
        expected = None
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_bad_method(self):
        request = {"jsonrpc": "2.0", "method": "foobar", "id": "1"}
        expected = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "1"}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_invalid_json(self):
        request = '{"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]'
        expected = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_bad_request(self):
        request = {"jsonrpc": "2.0", "method": 1, "id": "1"}
        expected = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request"}, "id": "1"}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_empty_batch(self):
        request = []
        expected = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request"}, "id": None}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_invalid_batch(self):
        request = [1,2,3]
        expected = [
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request"}, "id": None},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request"}, "id": None},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request"}, "id": None}
                  ]
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_batch(self):
        request = [
                    {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1},
                    {"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]},
                    {"foo": "bar"},
                    {"jsonrpc": "2.0", "method": "subtract.foo", "params": {"subtrahend": 23, "minuend": 42}, "id": 2},
                    {"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 3}
                  ]
        expected = [
                     {'error': {'code': -32600, 'message': 'Invalid request'}, 'id': None, 'jsonrpc': '2.0'},
                     {'error': {'code': -32601, 'message': 'Method not found'}, 'id': 2, 'jsonrpc': '2.0'},
                     {'id': 1, 'jsonrpc': '2.0', 'result': 19},
                     {'id': 3, 'jsonrpc': '2.0', 'result': 19}
                   ]
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_batch_notification(self):
        request = [
                    {"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]},
                    {"jsonrpc": "2.0", "method": "update", "params": ['x', 'y', 'z']},
                  ]
        expected = None
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_deferred(self):
        request = {"jsonrpc": "2.0", "method": "deferred_echo", "params": ["x"], "id": 1}
        expected = {"jsonrpc": "2.0", "result": "x", "id": 1}
        yield self.makeRequest(request, expected)

    @defer.inlineCallbacks
    def test_deferred_batch(self):
        request = [
                    {"jsonrpc": "2.0", "method": "deferred_echo", "params": ["x"], "id": 1},
                    {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 2}
                  ]
        expected = [
                     {"jsonrpc": "2.0", "result": "x", "id": 1},
                     {"jsonrpc": "2.0", "result": 19, "id": 2}
                   ]

        yield self.makeRequest(request, expected)
