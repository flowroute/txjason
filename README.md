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
from twisted.internet import deferred
from txjason import handler
from txjason.netstring import protocol


class Example(handler.Handler):
    #export the echo2 method as 'echo'
    @handler.exportRPC('echo')
    def echo2(self, param):
        return param

    #exported methods may return a deferred
    @handler.exportRPC()
    def deferred_echo(self, param):
        return defer.succeed(param)

factory = protocol.ServerFactory()
factory.addHandler(Example(), namespace='main')
```

The factory can then be used in a .tac, twistd plugin, or anywhere else a server factory
is normally found. The rpc methods will be exported as 'main.echo' and 'main.deferred_echo'.


Client Usage
------------

Assuming the reactor is running:

```python
from txjason.netstring.protocol import Proxy


proxy = Proxy('127.0.0.1', 7080)

d = proxy.callRemote('main.echo', 'foo')
d.addBoth(someFunction)
```

Running the Examples
--------------------

To run the provided examples:

	* Run 'make' from the main project directory.
    * In one shell run ./bin/twistd -noy examples/server.tac
    * In another shell run ./bin/python examples/client.py
