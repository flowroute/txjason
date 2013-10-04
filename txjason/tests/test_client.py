import json
from twisted.internet import defer, task
from txjason import client

from common import TXJasonTestCase

clock = task.Clock()


class ClientTestCase(TXJasonTestCase):
    def setUp(self):
        self.client = client.JSONRPCClient(reactor=clock)

    def checkPayload(self, payload, expected, d=None):
        payload = json.loads(payload)
        self.assertEqual(payload, expected)
        if d:
            d.callback(None)

    def test_timeout(self):
        called = []

        def eb(r):
            called.append(r.value)
        payload, d = self.client.getRequest('foo')
        d.addErrback(eb)
        clock.advance(self.client.timeout - 1)
        self.assertFalse(called)
        clock.advance(1)
        self.assertIsInstance(called[0], defer.CancelledError)

    def test_timeout_argument(self):
        called = []
        payload, d = self.client.getRequest('foo', timeout=4)
        d.addErrback(called.append)
        clock.advance(3)
        self.assertFalse(called)
        clock.advance(1)
        self.assertIsInstance(called[0].value, defer.CancelledError)

    def test_response(self):
        called = []

        def cb(r):
            called.append(r)
        payload, d = self.client.getRequest('foo')
        d.addCallback(cb)
        response = {'id': 1, 'jsonrpc': '2.0', 'result': 'bar'}
        self.client.handleResponse(json.dumps(response))
        self.assertEqual(called, ['bar'])

    def test_error(self):
        called = []

        def eb(r):
            called.append(r.value)
        payload, d = self.client.getRequest('foo')
        d.addErrback(eb)
        response = {'id': 1, 'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found'}}
        self.client.handleResponse(json.dumps(response))
        self.assertIsInstance(called[0], client.JSONRPCClientError)

    def test_unrecognized_kwargs(self):
        self.assertRaises(TypeError, self.client.getRequest, bar='bar')

    def test_positional_params(self):
        payload, d = self.client.getRequest('foo', 1, 2, 3)
        expected = {'id': 1, 'jsonrpc': '2.0', 'method': 'foo', 'params': [1, 2, 3]}
        self.checkPayload(payload, expected, d)

    def test_named_params(self):
        payload, d = self.client.getRequest('foo', dict(a=1, b=2))
        expected = {'id': 1, 'jsonrpc': '2.0', 'method': 'foo', 'params': {'a': 1, 'b': 2}}
        self.checkPayload(payload, expected, d)

    def test_no_params(self):
        payload, d = self.client.getRequest('foo')
        expected = {'id': 1, 'jsonrpc': '2.0', 'method': 'foo', 'params': []}
        self.checkPayload(payload, expected, d)

    def test_notification(self):
        payload = self.client.getNotification('foo', 1)
        expected = {'jsonrpc': '2.0', 'method': 'foo', 'params': [1]}
        self.checkPayload(payload, expected)

    def test_id_increment(self):
        payload, d = self.client.getRequest('foo')
        expected = {'id': 1, 'jsonrpc': '2.0', 'method': 'foo', 'params': []}
        self.checkPayload(payload, expected)
        payload, d = self.client.getRequest('foo')
        expected['id'] = 2
        self.checkPayload(payload, expected)

    def test_no_id(self):
        response = {'jsonrpc': '2.0', 'result': 'bar'}
        self.assertRaises(client.JSONRPCProtocolError, self.client.handleResponse, json.dumps(response))

    def test_bad_version(self):
        response = {'jsonrpc': '3.0', 'id': 1, 'result': 'bar'}
        self.assertRaises(client.JSONRPCProtocolError, self.client.handleResponse, json.dumps(response))

    def test_no_version(self):
        response = {'id': 1, 'result': 'bar'}
        self.assertRaises(client.JSONRPCProtocolError, self.client.handleResponse, json.dumps(response))

    def test_request_not_found(self):
        response = {'jsonrpc': '2.0', 'id': 999, 'result': 'bar'}
        self.assertRaises(client.JSONRPCClientError, self.client.handleResponse, json.dumps(response))

    def test_no_result(self):
        payload, d = self.client.getRequest('foo')
        response = {'jsonrpc': '2.0', 'id': 1}
        self.assertRaises(client.JSONRPCProtocolError, self.client.handleResponse, json.dumps(response))
