import socketserver
import traceback
from xinetd_http import HttpRequest, HttpResponse, CRITICAL_ERROR_RESPONSE

class IOWrapper():
  def __init__(self, buffer):
    self.buffer = buffer

  def readline(self):
    return self.buffer.readline().decode('utf-8')

  def read(self, n):
    return self.buffer.read(n).decode('utf-8')

  def write(self, data):
    return self.buffer.write(data.encode('utf-8'))

  def flush(self):
    return self.buffer.flush()

class TestStreamHandler(socketserver.StreamRequestHandler):
  def handle(self):
    try:
        req = HttpRequest.parse(reader=IOWrapper(self.rfile))
        res = HttpResponse(200)
        self.server.handler_func(req, res)
        res.output(writer=IOWrapper(self.wfile))
    except:
        traceback.print_exc()
        self.wfile.write(CRITICAL_ERROR_RESPONSE.encode('utf-8'))

class TestServer(socketserver.TCPServer):
  allow_reuse_address = True
  def __init__(self, host, port, func):
    super().__init__((host, port), TestStreamHandler)
    self.handler_func = func

def run(handler):
  srv = TestServer('localhost', 3000, handler)
  srv.serve_forever()
