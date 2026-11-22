"""HTTP server adapter: turns stdlib http.server events into pipeline calls.

Layer: server (entry-point side). It is the only module that knows about
sockets, headers and status codes on the request side; the pipeline and the
router stay transport-agnostic.
"""
import json
import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler

from core.exceptions import AppError, PayloadTooLargeError
from middlewares.base import RequestContext

MAX_BODY_BYTES = 1024 * 1024  # 1 MB cap for request bodies

# Injected by main.py via set_request_pipeline(); read at call time so the
# pipeline (which needs the route table) can be built after importing this module.
request_pipeline = None


def set_request_pipeline(pipeline):
    """Inject the shared request pipeline (error -> logging -> auth -> dispatch)."""
    global request_pipeline
    request_pipeline = pipeline


class HTTPHandler(BaseHTTPRequestHandler):
    """Parses the raw request, runs the pipeline (see set_request_pipeline)
    and writes the JSON response."""

    # Keep-alive: one TCP connection can serve several requests (send_json_response
    # always sends Content-Length, as HTTP/1.1 requires)
    protocol_version = 'HTTP/1.1'

    def send_json_response(self, response, send_body=True):
        body = b''
        if response.status != 204 and response.payload is not None:
            body = json.dumps(response.payload, ensure_ascii=False, default=str).encode('utf-8')
        try:
            self.send_response(response.status)
            if response.status != 204:
                # A 204 carries no body, so RFC 7230 forbids Content-Length and Content-Type
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.end_headers()
            if send_body and body:
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
        """Build the RequestContext for one request and run the shared pipeline."""
        parsed = urllib.parse.urlparse(self.path)
        uri = parsed.path
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        request = RequestContext(
            method, uri, query, self.headers, self.client_address[0], self.read_body)
        response = request_pipeline(request)
        self.send_json_response(response, send_body=method != 'HEAD')

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
