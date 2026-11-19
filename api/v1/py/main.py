import json
import logging
import signal
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from utils.date_utils import LOCAL_TZ
from core.exceptions import AppError, PayloadTooLargeError
from core.router import Router
from core.settings import settings
from routers import register_all
from services.token_service import decode_token
from middlewares import default_pipeline
from middlewares.base import RequestContext

MAX_BODY_BYTES = 1024 * 1024  # 1 MB cap for request bodies

_log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# Log timestamps in APP_TIMEZONE (America/Tijuana) instead of the machine clock.
# Set on the instance: a class-level function would receive `self` as first argument.
_log_formatter.converter = lambda seconds: datetime.fromtimestamp(seconds, LOCAL_TZ).timetuple()
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(_log_formatter)
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
# The connector logs every plugin detail at INFO: keep it at warnings only
logging.getLogger('mysql.connector').setLevel(logging.WARNING)

# Route table shared by all requests; routers are discovered from the package.
# decode_token is injected here so the Router stays free of model imports: it
# checks signature, expiration, revocation and that the user is Active.
router = Router(authenticator=decode_token)
register_all(router)


def dispatch_request(request):
    """Handle protocol-specific routes and delegate application routes to Router."""
    method = request.method
    if method == 'OPTIONS':
        allowed = router.allowed_methods(request.path)
        if not allowed:
            raise AppError('Not found', 404)
        request.extra_headers['Allow'] = ', '.join(sorted(set(allowed) | {'HEAD', 'OPTIONS'}))
        return 204, None

    # HEAD uses GET's route and headers, but HTTPHandler suppresses its body.
    route_method = 'GET' if method == 'HEAD' else method
    request.body = request.read_body()
    return router.dispatch(
        route_method, request.path, request.body, request.headers, request.query,
        auth_context=(request.token, request.user),
    )


request_pipeline = default_pipeline(router, dispatch_request)


class HTTPHandler(BaseHTTPRequestHandler):
    # Keep-alive: one TCP connection can serve several requests (send_json_response
    # always sends Content-Length, as HTTP/1.1 requires)
    protocol_version = 'HTTP/1.1'

    def send_json_response(self, data, status=200, send_body=True, extra_headers=None):
        body = b''
        if status != 204 and data is not None:
            body = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if send_body and body:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # The client hung up before reading the response: nothing to send
                self.close_connection = True
                logging.info('Client disconnected before reading the response')

    def read_body(self):
        """Read the request body, rejecting an invalid or oversized Content-Length."""
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
        except ValueError:
            raise AppError('Invalid Content-Length header', 400)
        if length < 0:
            # A negative length would make read() block until the client closes
            self.close_connection = True
            raise AppError('Invalid Content-Length header', 400)
        if length > MAX_BODY_BYTES:
            # The oversized body is not read, so the connection cannot be reused
            self.close_connection = True
            raise PayloadTooLargeError('Request body too large')
        try:
            return self.rfile.read(length).decode('utf-8')
        except UnicodeDecodeError:
            raise AppError('Request body must be UTF-8', 400)

    def dispatch(self, method):
        parsed = urllib.parse.urlparse(self.path)
        uri = parsed.path
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        request = RequestContext(
            method, uri, query, self.headers, self.client_address[0], self.read_body)
        status, payload = request_pipeline(request)
        self.send_json_response(payload, status, send_body=method != 'HEAD',
                                extra_headers=request.extra_headers)

    def log_message(self, format, *args):
        pass  # the default per-request stderr log is replaced by the structured one above

    def do_GET(self):
        self.dispatch('GET')

    def do_HEAD(self):
        self.dispatch('HEAD')

    def do_OPTIONS(self):
        self.dispatch('OPTIONS')

    def do_POST(self):
        self.dispatch('POST')

    def do_PUT(self):
        self.dispatch('PUT')

    def do_PATCH(self):
        self.dispatch('PATCH')

    def do_DELETE(self):
        self.dispatch('DELETE')


if __name__ == "__main__":
    try:
        settings.validate()
    except ValueError as error:
        sys.exit(str(error))
    server = ThreadingHTTPServer((settings.APP_HOST, settings.APP_PORT), HTTPHandler)
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
