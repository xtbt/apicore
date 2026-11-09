"""User routes: wires the `users` URLs to UserController.

POST /users is public (self-registration); the rest require a token."""
from controllers.UserController import UserController


def register_user_routes(router):
    router.add_crud_routes('/users', UserController, 'User', public_methods=('POST',))
