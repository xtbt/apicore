from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from controllers.MoodController import MoodController

class HTTPHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        self.wfile.write(json_data.encode('utf-8'))

    def dispatch(self, method):
        uri = urllib.parse.urlparse(self.path).path
        resource_id = uri.split('/')[-1] if len(uri.split('/')) > 2 else None
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        mood = None
        try:
            if method == 'GET' and uri == '/healthcheck':
                self.send_json_response({
                    'status': 'ok',
                    'message': 'Server is running',
                    'debug': body
                })
            elif uri == '/moods' or uri.startswith('/moods/'):
                # One controller (and DB connection) per request
                mood = MoodController()
                self.dispatch_moods(mood, method, uri, resource_id, body)
            else:
                self.send_json_response({'error': 'Not found'}, status=404)
        except ValueError as e:
            self.send_json_response({'error': str(e)}, status=400)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)
        finally:
            if mood is not None:
                mood.close()

    def dispatch_moods(self, mood, method, uri, resource_id, body):
        if method == 'GET' and uri == '/moods':
            self.send_json_response({'status': 'ok', 'data': mood.get_all()})
        elif method == 'GET':
            element = mood.get_by_id(resource_id)
            if element:
                self.send_json_response({'status': 'ok', 'data': element})
            else:
                self.send_json_response({'error': 'Mood not found'}, status=404)
        elif method == 'POST' and uri == '/moods':
            result = mood.create(json.loads(body))
            self.send_json_response({'status': 'ok', 'ID': result})
        elif method == 'PUT' and uri != '/moods':
            result = mood.update(resource_id, json.loads(body))
            if result == mood.model.NOT_FOUND:
                self.send_json_response({'error': 'Mood not found'}, status=404)
            elif result == mood.model.UNCHANGED:
                self.send_json_response({'status': 'ok', 'message': 'No changes to apply'})
            else:
                self.send_json_response({'status': 'ok', 'message': 'Mood updated'})
        elif method == 'DELETE' and uri != '/moods':
            if mood.delete(resource_id):
                self.send_json_response({'status': 'ok', 'message': 'Mood deleted'})
            else:
                self.send_json_response({'error': 'Mood not found'}, status=404)
        else:
            self.send_json_response({'error': 'Method not allowed'}, status=405)

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