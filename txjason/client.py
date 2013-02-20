import json
from twisted.internet import defer, reactor, error


class JSONRPCClientError(Exception):
    pass


class JSONRPCProtocolError(Exception):
    pass


class JSONRPCClient(object):
    def __init__(self, timeout=5, reactor=reactor):
        self.requests = {}
        self.id = 0
        self.timeout = timeout
        self.reactor = reactor

    def _next_id(self):
        if self.id > 1000000:
            self.id = 1
        else:
            self.id = self.id +1
        return self.id

    def cancelRequests(self):
        for id, d in self.requests.items():
            d.cancel()
            del self.requests[id]

    def getRequest(self, method, *args, **kwargs):
        def cancel(r, t):
            try:
                t.cancel()
            except error.AlreadyCalled:
                pass
            return r
        id = self._next_id()
        payload = self._getPayload(method, id, *args, **kwargs)
        d = defer.Deferred()
        self.requests[id] = d
        t = self.reactor.callLater(self.timeout, d.cancel)
        d.addBoth(cancel, t)
        return (payload, d)

    def getNotification(self, method, *args, **kwargs):
        return self._getPayload(method, None, *args, **kwargs)

    def handleResponse(self, payload):
        try:
            response = json.loads(payload)
        except ValueError:
            raise JSONRPCProtocolError('server response is not valid json:\n%s' % payload)
        if 'jsonrpc' not in response or response['jsonrpc'] != '2.0':
            raise JSONRPCProtocolError('not a valid jsonrpc response (no version):\n%s' % payload)
        try:
            id = response['id']
        except KeyError:
            raise JSONRPCProtocolError('not a valid jsonrpc response (no id):\n%s' % payload)
        try:
            deferred = self.requests[id]
        except KeyError:
            raise JSONRPCClientError('invalid id in response:\n%s' % payload)
        if 'result' in response:
            deferred.callback(response['result'])
        elif 'error' in response:
            deferred.errback(JSONRPCClientError(response['error']))
        else:
            raise JSONRPCProtocolError('No result or error in response:\n%s' % payload)
        del self.requests[id]

    def _getPayload(self, method, id, *args, **kwargs):
        if args and kwargs:
            raise JSONRPCClientError('call accepts positional or named arguments, but not both')
        elif kwargs:
            params = kwargs
        else:
            params = args

        payload = {
                    'jsonrpc': '2.0',
                    'method': method,
                    'params': params,
                  }
        if id:
            payload['id'] = id
        return json.dumps(payload)
