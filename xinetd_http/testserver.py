import socketserver
import traceback
import typing as t
from xinetd_http import HttpRequest, HttpResponse, CRITICAL_ERROR_RESPONSE, BEFORE_REQUEST, AFTER_REQUEST

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
        req.remote_host = self.client_address[0]
        res = HttpResponse(200)
        proceed = True
        for m in self.server.middlewares:
            proceed = m(req, res, BEFORE_REQUEST)
            if proceed is False:
                break
        if not proceed is False:
            self.server.handler_func(req, res)
            for m in reversed(self.server.middlewares):
                m(req, res, AFTER_REQUEST)
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
  def __init__(self, host, port, func, middlewares=None):
    super().__init__((host, port), TestStreamHandler)
    self.handler_func = func
    self.middlewares = [] if middlewares is None else middlewares

def run(handler, middlewares):
  srv = TestServer('localhost', 3000, handler, middlewares)
  print('Starting server at localhost:3000')
  srv.serve_forever()
