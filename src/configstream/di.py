from collections.abc import Callable
from inspect import signature
from typing import Any, TypeVar

T = TypeVar("T")


class Container:
    """Dependency injection container"""

    def __init__(self):
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}
        self._singletons: dict[type, Any] = {}

    def register(self,
                 interface: type[T],
                 implementation: type[T] = None) -> None:
        """Register a service"""
        if implementation is None:
            implementation = interface
        self._services[interface] = implementation

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """Register a singleton instance"""
        self._singletons[interface] = instance

    def register_factory(self, interface: type[T],
                         factory: Callable[..., T]) -> None:
        """Register a factory function"""
        self._factories[interface] = factory

    def resolve(self, interface: type[T]) -> T:
        """Resolve a dependency"""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factories
        if interface in self._factories:
            return self._factories[interface](self)

        # Resolve from registered services
        if interface not in self._services:
            raise ValueError(f"Service {interface} not registered")

        implementation = self._services[interface]

        # Auto-wire dependencies
        sig = signature(implementation.__init__)
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.annotation != param.empty:
                params[param_name] = self.resolve(param.annotation)

        return implementation(**params)
