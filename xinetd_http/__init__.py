import os
import sys
import json
from urllib.parse import parse_qs
from http.client import responses
import typing as t

BEFORE_REQUEST = 0
AFTER_REQUEST = 1
CRITICAL_ERROR_RESPONSE = 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error\r\n'

class HttpRequest(object):

    def __init__(self, method: str, uri: str, headers: t.Dict[str, str], environ: t.Dict[str, str], body: t.Optional[str]):
        self.method = method
        self.uri = uri
        self.headers = headers
        self.remote_host = environ.get('REMOTE_HOST', '')
        self.path = uri.split('?', 1)[0]
        self.query = parse_qs(uri.split('?', 1)[1]) if uri.find('?') != -1 else {}
        self.body = body

    @classmethod
    def parse(cls: t.Type['HttpRequest'], reader: t.Optional[t.BinaryIO]=None) -> 'HttpRequest':
        HTTP_START_LINE = 0
        HTTP_HEADERS = 1
        HTTP_BODY = 2

        if reader is None:
            reader = sys.stdin.buffer

        parser_mode = HTTP_START_LINE
        request_headers = {} # type: t.Dict[str, str]
        uri = '/'
        version = 'HTTP/0.9'
        method = 'GET'
        body_size = 0
        body = None
        while True:
            if parser_mode == HTTP_START_LINE:
                line = reader.readline().strip()
                method, uri, version = line.decode('ascii').split(' ')
                parser_mode = HTTP_HEADERS
            elif parser_mode == HTTP_HEADERS:
                line = reader.readline().strip()
                if line == b'':
                    body_size = int(request_headers.get('content-length', 0))
                    if body_size > 0:
                        parser_mode = HTTP_BODY
                        continue
                    else:
                        break
                parts = line.decode('utf-8').split(':', 1)
                header_name = parts[0].lower()
                header_value = parts[1].strip()
                request_headers[header_name] = header_value
            elif parser_mode == HTTP_BODY:
                body = reader.read(body_size)
                break

        return cls(method, uri, request_headers, dict(os.environ), body)

class HttpResponse(object):
    def __init__(self, status_code: int, headers: t.Optional[t.Dict[str, str]]=None, body: t.Union[str, bytes, None]=None):
        self.status = status_code
        self.headers = {} if headers is None else headers
        self.body = body
        self.is_binary = False

    def copy_from(self, response: 'HttpResponse') -> None:
        self.status = response.status
        self.headers = response.headers
        self.body = response.body
        self.is_binary = response.is_binary

    def set_status(self, status_code: int) -> None:
        self.status = status_code

    def set_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def set_body(self, body: t.Union[str, bytes]) -> None:
        self.body = body
        self.is_binary = isinstance(body, bytes)

    def set_json(self, data: t.Any) -> None:
        self.headers['content-type'] = 'application/json';
        self.body = json.dumps(data)
        self.is_binary = False

    def set_content_type(self, content_type: str) -> None:
        self.headers['content-type'] = content_type

    def set_text(self, text: str) -> None:
        self.headers['content-type'] = 'text/plain; charset=utf-8'
        self.body = text
        self.is_binary = False

    def redirect(self, location: str, status_code: int=303) -> None:
        self.status = status_code
        self.headers['location'] = location
        self.body = None

    def output(self, writer: t.Optional[t.BinaryIO]=None) -> None:
        if writer is None:
            writer = sys.stdout.buffer
        writer.write('HTTP/1.1 {} {}\r\n'.format(self.status, responses[self.status]).encode('utf-8'))
        body = None # type: t.Optional[bytes]
        if not self.is_binary and isinstance(self.body, str):
            body = self.body.encode('utf-8')
        elif isinstance(self.body, bytes):
            body = self.body
        self.headers['content-length'] = '0' if body is None else str(len(body))
        for k, v in self.headers.items():
            writer.write('{}: {}\r\n'.format(k, v).encode('utf-8'))
        writer.write(b'\r\n')
        writer.flush()
        if body is not None:
            writer.write(body)
            writer.flush()

def run(handler: t.Callable[[HttpRequest, HttpResponse], None], middlewares: t.Optional[t.List[t.Callable[[HttpRequest, HttpResponse, int], t.Optional[bool]]]]=None) -> None:
    try:
        req = HttpRequest.parse()
        res = HttpResponse(200)
        proceed = True
        if middlewares is None:
            middlewares = []
        for m in middlewares:
            proceed = m(req, res, BEFORE_REQUEST)
            if proceed is False:
                break
        if not proceed is False:
            handler(req, res)
            for m in reversed(middlewares):
                m(req, res, AFTER_REQUEST)
        res.output()
    except:
        sys.stdout.write(CRITICAL_ERROR_RESPONSE + traceback.format_exc())
