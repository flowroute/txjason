from twisted.trial import unittest
import types


class ReturnedAGeneratorError(Exception):
    pass


class TXJasonTestCase(unittest.TestCase):
    def _run(self, methodName, result):
        """
        Ensure that test cases don't return generators, as that basically
        always means someone forgot an @inlineCallbacks.
        """
        d = unittest.TestCase._run(self, methodName, result)

        def ensureNoGenerators(result):
            if isinstance(result, types.GeneratorType):
                raise ReturnedAGeneratorError(
                    'method %r returned a generator' % methodName)
            return result
        d.addCallback(ensureNoGenerators)
        return d
