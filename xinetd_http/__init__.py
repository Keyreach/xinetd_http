import os
import sys
import json
from urllib.parse import parse_qs
from http.client import responses
import typing as t

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
    def parse(cls: t.Type['HttpRequest'], reader: t.Optional[t.TextIO]=None) -> 'HttpRequest':
        HTTP_START_LINE = 0
        HTTP_HEADERS = 1
        HTTP_BODY = 2

        if reader is None:
            reader = sys.stdin

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
                method, uri, version = line.split(' ')
                parser_mode = HTTP_HEADERS
            elif parser_mode == HTTP_HEADERS:
                line = reader.readline().strip()
                if line == '':
                    body_size = int(request_headers.get('content-length', 0))
                    if body_size > 0:
                        parser_mode = HTTP_BODY
                        continue
                    else:
                        break
                parts = line.split(':', 1)
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
    
    def output(self, writer: t.Optional[t.TextIO]=None) -> None:
        if writer is None:
            writer = sys.stdout
        writer.write('HTTP/1.1 {} {}\r\n'.format(self.status, responses[self.status]))
        if self.body is not None:
            self.headers['content-length'] = str(len(self.body))
        for k, v in self.headers.items():
            writer.write('{}: {}\r\n'.format(k, v))
        writer.write('\r\n')
        writer.flush()
        if self.is_binary and isinstance(self.body, bytes):
            writer.buffer.write(self.body)
        elif isinstance(self.body, str):
            writer.write(self.body)

def run(handler: t.Callable[[HttpRequest, HttpResponse], None]) -> None:
    try:
        req = HttpRequest.parse()
        res = HttpResponse(200)
        handler(req, res)
        res.output()
    except:
        sys.stdout.write(CRITICAL_ERROR_RESPONSE)
