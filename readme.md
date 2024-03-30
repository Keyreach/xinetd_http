
# xinetd_http

Framework for creating Python web application working using xinetd

## Example app

```python
from xinetd_http import HttpRequest, HttpResponse, run
from xinetd_http.middlewares import CorsMiddleware

def app(req: HttpRequest, res: HttpResponse):
  if req.method == 'GET':
    res.set_json({
      'success': True
    })
  else:
    res.set_status(405)
    res.set_json({
      'success': False,
      'error': 'Method Not Allowed'
    })

if __name__ == '__main__':
  cors = CorsMiddleware(['GET'], origins=['example.com'])
  run(app, [cors])
```

## Interfaces

Web application is following parts:

* application handler - callable implementing main application logic and having ApplicationHandler interface described below
* middlewares - optional callables having Middleware interface described below, used for preprocessing or post-processing of request

### ApplicationHandler interface

`handler(req, res)`

_Parameters_

* __req__ - instance of `HttpRequest`
* __res__ - instance of `HttpResponse`

### Middleware interface

`middleware(req, res, stage)`

_Parameters_

* __req__ - instance of `HttpRequest`
* __res__ - instance of `HttpResponse`
* __stage__ - `0` if called before main handler, 1 if called after main handler

_Returns_

If `False` is returned, response is returned immediately without calling main handler and other middlewares

## API

### xinetd_http

#### `class HttpRequest(method, uri, headers, environ, body)`
_Parameters_
* __method__ - HTTP request method in upper case
* __uri__ - HTTP full request URI
* __headers__ - dictionary containing HTTP request headers
* __environ__ - dictionary containing other request data
* __body__ - HTTP request body as bytes

#### `HttpRequest.method`
HTTP request method

#### `HttpRequest.uri`
HTTP request URI

#### `HttpRequest.headers`
Dictionary containing HTTP request headers

#### `HttpRequest.remote_host`
IP address of client

#### `HttpRequest.path`
HTTP request URI path segment

#### `HttpRequest.query_string`
HTTP request URI query segment

#### `HttpRequest.query`
Parsed HTTP request query string

#### `HttpRequest.body`
HTTP request body

#### `HttpRequest.parse(reader=None)`

Parse HTTP request from file-like object or standard input

_Parameters_

* __reader__ - (optional) object implementing `BytesIO` interface, standard input is used if empty

_Return_

instance of `HttpRequest`

#### `class HttpResponse(status_code, headers=None, body=None)`

_Parameters_

* __status_code__ - HTTP status code
* __headers__ - HTTP response headers
* __body__ - HTTP response body

#### `HttpResponse.copy_from(response)`

Copy data from another `HttpResponse`

_Parameters_

* __response__ - instance of `HttpResponse`

#### `HttpResponse.set_status(status_code)`

Set status code

_Parameters_

* __status_code__ - HTTP status code

#### `HttpResponse.set_header(name, value)`

Set response header

_Parameters_

* __name__ - header name
* __value__ - header value

#### `HttpResponse.set_body(body)`

Set response body

_Parameters_

* __body__ - response body, `str` or `bytes`

#### `HttpResponse.set_json(data)`

Convert object to JSON, set as response body, adjust `Content-Type` header

_Parameters_

* __data__ - object, JSON serializable

#### `HttpResponse.set_text(text)`

Set text as response body, adjust `Content-Type` header

_Parameters_

* __text__ - text string

#### `HttpResponse.set_content_type(content_type)`

Set response `Content-Type`

_Parameters_

* __content_type__ - content type

#### `HttpResponse.redirect(location, status_code=None)`

Set HTTP redirect response

_Parameters_

* __location__ - redirect location
* __status_code__ - status code (optional, default - 303)

#### `HttpResponse.output(writer=None)`

Generate HTTP response, write to `BytesIO` object or standard output

_Parameters_

* __writer__ - (optional) object implementing `BytesIO` interface, standard output is used if empty

#### `run(handler, middlewares=None)`

Entry point for use with xinetd. Read HTTP request from standard input, run `handler` as web application, write HTTP response to standard output.

_Parameters_

* __handler__ - function/callable implementing web application having ApplicationHandler interface
* __middlewares__ - list of functions/callables having Middleware interface, called before/after `handler` callable

### xinetd_http.testserver

#### `run(handler, middlewares=None, options={})`
Run application using test server based on`socketserver.TCPServer`

_Parameters_

* __handler__ - function/callable implementing web application having ApplicationHandler interface
* __middlewares__ - list of functions/callables having Middleware interface, called before/after `handler` callable
* __options__ - dictionary, containing options for test server
  * `host` - host for binding (default: `localhost`)
  * `port` - port for binding (default: 3000)

### xinetd_http.wsgi_adapter

#### `class Adapter(handler, middlewares)`

Create WSGI application using application handler and middlewares

_Parameters_

* __handler__ - function/callable implementing web application having ApplicationHandler interface
* __middlewares__ - list of functions/callables having Middleware interface, called before/after `handler` callable

### xinetd_http.middlewares
Sample middlewares for framework

#### `timer_middleware(req, res, stage)`
Adds `x-request-time` header containing handler execution time

#### `gzip_middleware(req, res, stage)`
Compresses HTTP response using gzip

#### `CorsMiddleware(methods, origins=None, headers=None, handle_options=True)`

Adds CORS headers and handles preflight requests

_Parameters_

* __methods__ - allowed methods
* __origins__ - allowed origins (by default allows any)
* __headers__ - allowed headers
* __handle_options__ - handle `OPTIONS` request in middleware

#### `RedisLimiter(prefix, redis_url, limit, period)`

Limit request rate

_Parameters_

* __prefix__ - prefix used for used redis keys
* __redis_url__ - redis instance URL
* __limit__ - max. number of requests from same IP during `period`
* __period__ - period used for measuring (in seconds)

#### `RedisCache(prefix, redis_url, max_age)`

Cache GET and OPTIONS responses

_Parameters_

* __prefix__ - prefix used for used redis keys
* __redis_url__ - redis instance URL
* __max_age__ - max time of cache entry until expiry
