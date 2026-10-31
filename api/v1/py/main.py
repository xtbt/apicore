from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import urllib
from models import Mood

mood = Mood.Mood()

class HTTPHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False)
        self.wfile.write(json_data.encode('utf-8'))

    def dispatch(self, method):
        uri = urllib.parse.urlparse(self.path).path
        resource_id = uri.split('/')[-1] if len(uri.split('/')) > 2 else None
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        try:
            if method == 'GET' and uri == '/healthcheck':
                self.send_json_response({
                    'status': 'ok',
                    'message': 'Server is running',
                    'debug': body
                })
            elif method == 'GET' and uri == '/moods':
                elements = mood.get_moods()
                self.send_json_response({
                    'status': 'ok',
                    'data': elements
                    })
            elif method == 'GET' and uri.startswith('/moods/'):
                element = mood.get_mood_by_id(resource_id)
                if element:
                    self.send_json_response({
                        'status': 'ok',
                        'data': element
                    })
                else:
                    self.send_json_response({'error': 'Mood not found'}, status=404)
            elif method == 'POST' and uri == '/moods':
                data = json.loads(body)
                result = mood.create_mood(data)
                self.send_json_response({
                    'status': 'ok',
                    'ID': result
                })
            elif method == 'PUT' and uri.startswith('/moods/'):
                data = json.loads(body)
                mood.modify_mood(resource_id, data)
                self.send_json_response({
                    'status': 'ok',
                    'message': 'Mood updated'
                })
            elif method == 'DELETE' and uri.startswith('/moods/'):
                mood.delete_mood(resource_id)
                self.send_json_response({
                    'status': 'ok',
                    'message': 'Mood deleted'
                })
            else:
                self.send_json_response({'error': 'Method not allowed'}, status=405)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

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