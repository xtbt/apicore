"""Discover and register route modules without editing the application entry point.

Convention: each ``*Router.py`` module exports ``register_routes(router)``.
Adding an entity router then requires only adding that module to this package.
"""
from importlib import import_module
from pkgutil import iter_modules


def register_all(router):
    """Import route modules in stable alphabetical order and register their routes."""
    modules = sorted(
        module.name
        for module in iter_modules(__path__)
        if module.name.endswith('Router')
    )
    for module_name in modules:
        module = import_module(f'{__name__}.{module_name}')
        register_routes = getattr(module, 'register_routes', None)
        if not callable(register_routes):
            raise ImportError(f'{module.__name__} must define register_routes(router)')
        register_routes(router)
