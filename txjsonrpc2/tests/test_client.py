import json
from twisted.internet import defer, task
from twisted.trial import unittest
from txjsonrpc2 import client


clock = task.Clock()


class ClientTestCase(unittest.TestCase):
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
        clock.advance(self.client.timeout)
        self.assertIsInstance(called[0], defer.CancelledError)

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

    def test_args_and_kwargs(self):
        self.assertRaises(client.JSONRPCClientError, self.client.getRequest, 'foo', 1, bar='bar')

    def test_positional_params(self):
        payload, d = self.client.getRequest('foo', 1, 2, 3)
        expected = {'id': 1, 'jsonrpc': '2.0', 'method': 'foo', 'params': [1, 2, 3]}
        self.checkPayload(payload, expected, d)

    def test_named_params(self):
        payload, d = self.client.getRequest('foo', a=1, b=2)
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

    def test_no_id(self):
        response = {'jsonrpc': '2.0', 'result': 'bar'}
        self.assertRaises(client.JSONRPCClientError, self.client.handleResponse, json.dumps(response))

    def test_bad_version(self):
        response = {'jsonrpc': '3.0', 'id': 1, 'result': 'bar'}
        self.assertRaises(client.JSONRPCClientError, self.client.handleResponse, json.dumps(response))

    def test_no_version(self):
        response = {'id': 1, 'result': 'bar'}
        self.assertRaises(client.JSONRPCClientError, self.client.handleResponse, json.dumps(response))

    def test_no_result(self):
        response = {'jsonrpc': '2.0', 'id': 1}
        self.assertRaises(client.JSONRPCClientError, self.client.handleResponse, json.dumps(response))
