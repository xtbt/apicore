"""Example routes: only wires the `examples` URLs to ExampleController (all protected)."""
from controllers.example_controller import ExampleController


def register_routes(router):
    router.add_crud_routes('/examples', ExampleController, 'Example')
