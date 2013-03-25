import collections
import inspect


class exportRPC(object):
    """
    Decorator to indicate a method should be exported via RPC.
    To export with the method's name, use as @exportRPC().
    Optionally, provde an argument to indicate the name to export as:
    @exportRPC("foo").
    """
    def __init__(self, name=None):
        self.name=name

    def __call__(self, f):
        if self.name:
            f.export_rpc = self.name
        else:
            f.export_rpc = f.__name__
        return f


class Handler(object):
    """
    Define RPC methods in subclasses of Handler. @exportRPC decorator indicates
    that a method should be exported. Call .addHandler on a subclass of txjason's
    BaseClientFactory (e.g., netstring.JSONRPCServerFactory) and pass an instance
    of a Handler subclass to expose the RPC methods via that factory.

    Example:

    class Example(handler.Handler):
        # export the echo2 method as 'echo'
        @handler.exportRPC('echo')
        def echo2(self, param):
            return param

        # exported methods may return a deferred
        @handler.exportRPC()
        def deferred_echo(self, param):
            return defer.succeed(param)
    """

    def addToService(self, service, namespace=None, seperator='.'):
        """
        Add this Handler's exported methods to an RPC Service instance.
        """
        if namespace is None:
            namespace = []
        if isinstance(namespace, basestring):
            namespace = [namespace]

        for n, m in inspect.getmembers(self, inspect.ismethod):
            if hasattr(m, 'export_rpc'):
                try:
                    name = seperator.join(namespace + m.export_rpc)
                except TypeError:
                    name = seperator.join(namespace + [m.export_rpc])
                service.add(m, name)
