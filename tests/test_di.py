import unittest

from configstream.di import Container


# Define some dummy classes for testing
class ServiceA:
    pass


class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a


class ServiceC:
    def __init__(self, service_b: ServiceB):
        self.service_b = service_b


class TestContainer(unittest.TestCase):

    def setUp(self):
        self.container = Container()

    def test_register_and_resolve(self):
        self.container.register(ServiceA)
        instance = self.container.resolve(ServiceA)
        self.assertIsInstance(instance, ServiceA)

    def test_resolve_with_dependencies(self):
        self.container.register(ServiceA)
        self.container.register(ServiceB)
        instance = self.container.resolve(ServiceB)
        self.assertIsInstance(instance, ServiceB)
        self.assertIsInstance(instance.service_a, ServiceA)

    def test_resolve_with_nested_dependencies(self):
        self.container.register(ServiceA)
        self.container.register(ServiceB)
        self.container.register(ServiceC)
        instance = self.container.resolve(ServiceC)
        self.assertIsInstance(instance, ServiceC)
        self.assertIsInstance(instance.service_b, ServiceB)
        self.assertIsInstance(instance.service_b.service_a, ServiceA)

    def test_register_singleton(self):
        service_a_instance = ServiceA()
        self.container.register_singleton(ServiceA, service_a_instance)
        resolved_instance = self.container.resolve(ServiceA)
        self.assertIs(resolved_instance, service_a_instance)

    def test_register_factory(self):
        self.container.register(ServiceA)
        self.container.register_factory(ServiceB, lambda c: ServiceB(c.resolve(ServiceA)))
        instance = self.container.resolve(ServiceB)
        self.assertIsInstance(instance, ServiceB)
        self.assertIsInstance(instance.service_a, ServiceA)

    def test_resolve_unregistered_service(self):
        with self.assertRaises(ValueError):
            self.container.resolve(ServiceA)


if __name__ == "__main__":
    unittest.main()
