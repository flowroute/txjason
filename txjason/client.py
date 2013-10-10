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
        _id = self.id
        if _id > 1000000:
            _id = 1
        else:
            _id += 1
        self.id = _id
        return _id

    def cancelRequests(self):
        for id, d in self.requests.items():
            d.cancel()
            del self.requests[id]

    def getRequest(self, __method, *args, **kwargs):
        timeout = kwargs.pop('timeout', self.timeout)
        if kwargs:
            raise TypeError('got extra keyword arguments', kwargs)
        def cancel(r, t):
            try:
                t.cancel()
            except error.AlreadyCalled:
                pass
            return r
        id = self._next_id()
        payload = self._getPayload(__method, id, *args)
        d = defer.Deferred()
        self.requests[id] = d
        t = self.reactor.callLater(timeout, d.cancel)
        d.addBoth(cancel, t)
        return (payload, d)

    def getNotification(self, __method, *args):
        return self._getPayload(__method, None, *args)

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

    def _getPayload(self, __method, id, *args):
        if len(args) == 1 and isinstance(args[0], dict):
            params = args[0]
        else:
            params = args

        payload = {'jsonrpc': '2.0',
                   'method': __method,
                   'params': params}
        if id:
            payload['id'] = id
        return json.dumps(payload)
