import typing as t
from http.client import responses
from . import HttpRequest, HttpResponse, BEFORE_REQUEST, AFTER_REQUEST

class Adapter(object):
    def __init__(self, handler: t.Callable[[HttpRequest, HttpResponse], None], middlewares=None):
        self.handler = handler
        self.middlewares = [] if middlewares is None else middlewares

    def transform_request(self, environ: t.Dict[str, t.Any]) -> HttpRequest:
        headers = {}
        for k in environ:
            if k.startswith('HTTP_'):
                headers[k[5:].replace('_', '-').lower()] = environ[k]
        headers['content-type'] = environ.get('CONTENT_TYPE', 'application/octet-stream')
        headers['content-length'] = environ.get('CONTENT_LENGTH', 0)
        body = b''
        if 'CONTENT_LENGTH' in environ:
            body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        return HttpRequest(
            environ['REQUEST_METHOD'].upper(),
            environ['REQUEST_URI'],
            headers,
            { 'REMOTE_HOST': environ['REMOTE_HOST'] },
            body
        )

    def __call__(self, environ, start_response):
        req = self.transform_request(environ)
        res = HttpResponse(200)

        proceed = True # type: t.Optional[bool]
        for m in self.middlewares:
            proceed = m(req, res, BEFORE_REQUEST)
            if proceed is False:
                break
        if proceed is not False:
            self.handler(req, res)
            for m in reversed(self.middlewares):
                m(req, res, AFTER_REQUEST)

        start_response(
            '{} {}'.format(res.status, responses[res.status]),
            list(res.headers.items())
        )
        if not res.is_binary and isinstance(res.body, str):
            yield res.body.encode('utf-8')
        elif isinstance(res.body, bytes):
            yield res.body
        else:
            yield b''
