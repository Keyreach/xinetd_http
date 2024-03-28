import socketserver
import traceback
import typing as t
from xinetd_http import HttpRequest, HttpResponse, CRITICAL_ERROR_RESPONSE, BEFORE_REQUEST, AFTER_REQUEST

class IOWrapper():
  def __init__(self, buffer: t.BinaryIO) -> None:
    self.buffer = buffer

  def readline(self) -> bytes:
    return self.buffer.readline()

  def read(self, n: t.Optional[int]=None) -> bytes:
    return self.buffer.read(n)

  def write(self, data: bytes) -> int:
    return self.buffer.write(data)

  def flush(self) -> None:
    return self.buffer.flush()

class TestStreamHandler(socketserver.StreamRequestHandler):
  server: 'TestServer'
  def handle(self) -> None:
    try:
        req = HttpRequest.parse(reader=IOWrapper(self.rfile))
        req.remote_host = self.client_address[0]
        res = HttpResponse(200)
        proceed = True # type: t.Optional[bool]
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
  def __init__(
    self,
    host: str, port: int,
    func: t.Callable[[HttpRequest, HttpResponse], None],
    middlewares: t.Optional[t.List[t.Callable[[HttpRequest, HttpResponse, int], t.Optional[bool]]]]=None
  ):
    super().__init__((host, port), TestStreamHandler)
    self.handler_func = func
    self.middlewares = [] if middlewares is None else middlewares

def run(
  handler: t.Callable[[HttpRequest, HttpResponse], None],
  middlewares: t.Optional[t.List[t.Callable[[HttpRequest, HttpResponse, int], t.Optional[bool]]]],
  options: t.Dict[str, t.Any]={}
) -> None:
  host = options.get('host', 'localhost')
  port = options.get('port', 3000)
  srv = TestServer(
      host,
      port,
      handler,
      middlewares
  )
  print('Starting server at {}:{}'.format(host, port))
  srv.serve_forever()
