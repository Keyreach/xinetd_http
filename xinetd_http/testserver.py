import socketserver
import traceback
import typing as t
from xinetd_http import HttpRequest, HttpResponse, CRITICAL_ERROR_RESPONSE

class IOWrapper():
  def __init__(self, buffer) -> None:
    self.buffer = buffer

  def readline(self) -> str:
    return self.buffer.readline().decode('utf-8')

  def read(self, n: t.Optional[int]=None) -> str:
    return self.buffer.read(n).decode('utf-8')

  def write(self, data: str) -> int:
    return self.buffer.write(data.encode('utf-8'))

  def flush(self) -> None:
    return self.buffer.flush()

class TestStreamHandler(socketserver.StreamRequestHandler):
  server: 'TestServer'
  def handle(self):
    try:
        req = HttpRequest.parse(reader=IOWrapper(self.rfile))
        res = HttpResponse(200)
        self.server.handler_func(req, res)
        print('[{}] {} {}'.format(
          res.status,
          req.method,
          req.uri
        ))
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
  print('Starting server at localhost:3000')
  srv.serve_forever()
