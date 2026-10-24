from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import urllib
from core import Database
from models import moodsselect


class HTTPHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))
    
    def dispatch(self, method):
        uri = urllib.parse.urlparse(self.path).path
        # resource_id = uri.split('/')[-1] if len(uri.split('/')) > 2 else None
        # body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        dbconn = Database.get_db_connection()
        try:
            if method == 'GET' and uri == '/healthcheck':
                self.send_json_response(
                    '{"status": "ok",' \
                    '"message": "Server is running"}'
                    )
            elif method == 'GET' and uri == '/moods':
                elements = moodsselect.get_moods(dbconn)
                self.send_json_response(
                    '{"status": "ok", ' \
                    '"message": "GET request received for resource"}'
                    )
            else:
                self.send_json_response('{"error": "Method not allowed"}', status=405)
        except Exception as e:
            self.send_json_response(f'{{"error": "{str(e)}"}}', status=500)

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
    print("Server started on http://localhost:65000" )
    server.serve_forever()