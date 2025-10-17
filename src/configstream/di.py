from inspect import signature
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class Container:
    """Dependency injection container"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(self, interface: Type[T], implementation: Type[T] = None) -> None:
        """Register a service"""
        if implementation is None:
            implementation = interface
        self._services[interface] = implementation

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Register a singleton instance"""
        self._singletons[interface] = instance

    def register_factory(self, interface: Type[T], factory: Callable[..., T]) -> None:
        """Register a factory function"""
        self._factories[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
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
