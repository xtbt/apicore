import signal
import sys
from http.server import ThreadingHTTPServer

from core.exceptions import AppError
from core.http import Response, route_method
from core.logger import configure_logging
from core.router import Router
from core.settings import settings
from middlewares import default_pipeline
from routers import register_all
from services.token_service import decode_token
from server import HTTPHandler, set_request_pipeline

configure_logging()


class ApiServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with a listen backlog that survives request bursts.

    socketserver defaults request_queue_size to 5, so a handful of simultaneous
    connections can overflow the queue and the client sees a broken pipe.
    """

    request_queue_size = 128


# Route table shared by all requests; routers are discovered from the package.
# decode_token is injected into the auth middleware, which validates every token
# before dispatch and keeps the Router focused on route resolution.
router = Router()
register_all(router)


def dispatch_request(request):
    """Handle protocol-specific routes and delegate application routes to Router."""
    method = request.method
    if method == 'OPTIONS':
        allow = router.allow_header(request.path)
        if allow is None:
            raise AppError('Not found', 404)
        return Response(204, headers={'Allow': allow})

    # HEAD uses GET's route and headers, but HTTPHandler suppresses its body.
    result = router.dispatch(
        route_method(method), request.path, request.read_body(), request.query,
        token=request.token, user=request.user,
    )
    # Handlers return (status, payload); POST returns a Response to add Location
    return result if isinstance(result, Response) else Response(*result)


request_pipeline = default_pipeline(router, dispatch_request, decode_token)
set_request_pipeline(request_pipeline)

if __name__ == "__main__":
    try:
        settings.validate()
    except ValueError as error:
        sys.exit(str(error))
    server = ApiServer((settings.APP_HOST, settings.APP_PORT), HTTPHandler)
    # Treat SIGTERM (kill, IDE stop button) like Ctrl+C so the port is always released
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"Server started on http://{settings.APP_HOST}:{settings.APP_PORT}")
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down server")
    finally:
        # Close the listening socket so the port is freed
        server.server_close()
