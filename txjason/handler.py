import collections
import inspect


class exportRPC(object):
    def __init__(self, name=None):
        self.name=name

    def __call__(self, f):
        if self.name:
            f.export_rpc = self.name
        else:
            f.export_rpc = f.__name__
        return f


class Handler(object):
    def addToService(self, service, namespace=None, seperator='.'):
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
