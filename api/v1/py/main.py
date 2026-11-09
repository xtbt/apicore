from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import signal
import sys
import urllib.parse
from core.Router import Router
from routers.MoodRouter import register_mood_routes

# Route table shared by all requests
router = Router()
register_mood_routes(router)

class HTTPHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        self.wfile.write(json_data.encode('utf-8'))

    def dispatch(self, method):
        uri = urllib.parse.urlparse(self.path).path
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        try:
            if method == 'GET' and uri == '/healthcheck':
                status, payload = 200, {
                    'status': 'ok',
                    'message': 'Server is running',
                    'debug': body
                }
            else:
                status, payload = router.dispatch(method, uri, body)
        except ValueError as e:
            status, payload = 400, {'error': str(e)}
        except Exception as e:
            status, payload = 500, {'error': str(e)}
        self.send_json_response(payload, status)

    def do_GET(self):
        self.dispatch('GET')
    
    def do_POST(self):
        self.dispatch('POST')
    
    def do_PUT(self):
        self.dispatch('PUT')

    def do_DELETE(self):
        self.dispatch('DELETE')

if __name__ == "__main__":
    server = ThreadingHTTPServer(('localhost', 65000), HTTPHandler)
    # Treat SIGTERM (kill, IDE stop button) like Ctrl+C so the port is always released
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    print("Server started on http://localhost:65000" )
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down server")
    finally:
        # Close the listening socket so the port is freed
        server.server_close()