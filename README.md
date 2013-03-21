txjason
============


Description
-----------

An interface for writing jsonrpc 2.0 servers and clients in Twisted.


Features
--------

* jsonrpc 2.0 compliant (including batch operations for the server).

* Support for TCP/netstring transport.

* Easily extensible for other transports.


Server Usage
------------

Define a factory and handler, and add the handler to the factory:

```python
from twisted.internet import defer
from txjason import handler
from txjason.netstring import JSONRPCServerFactory


class Example(handler.Handler):
    # export the echo2 method as 'echo'
    @handler.exportRPC('echo')
    def echo2(self, param):
        return param

    # exported methods may return a deferred
    @handler.exportRPC()
    def deferred_echo(self, param):
        return defer.succeed(param)

factory = JSONRPCServerFactory()
factory.addHandler(Example(), namespace='main')
```

The factory can then be used in a .tac, twistd plugin, or anywhere else a server factory
is normally found. The rpc methods will be exported as 'main.echo' and 'main.deferred_echo'.

The server can be forced to serve a predefined exception by invoking the service's
``stopServing`` method, with the exception class to serve:

```python
from txjason.service import JSONRPCError


class CustomError(JSONRPCError):
    code = -32099
    message = 'Custom Error'

...

factory.service.stopServing(CustomError)
```

Requests to all methods will now receive an error response.

If the ``timeout`` parameter is passed to the Factory, a "Timeout Error" will be returned to the
client after the specified number of seconds have elapsed:

```python
factory = JSONRPCServerFactory(timeout=2)
```

At any time, all pending requests may be cancelled:

```python
factory.service.cancelPending()
```

Client Usage
------------

Assuming the reactor is running:

```python
from txjason.netstring import JSONRPCClientFactory


client = JSONRPCClientFactory('127.0.0.1', 7080)

d = client.callRemote('main.echo', 'foo')
d.addBoth(someFunction)
```

Running the Examples
--------------------

To run the provided examples:

    * Run 'make' from the main project directory.
    * In one shell run ./bin/twistd -noy examples/server.tac
    * In another shell run ./bin/python examples/client.py
