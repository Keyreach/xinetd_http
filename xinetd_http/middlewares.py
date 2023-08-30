import time
import gzip
import redis
import pickle
import typing as t
from xinetd_http import HttpRequest, HttpResponse, HttpResponse, BEFORE_REQUEST, AFTER_REQUEST

def timer_middleware(req: HttpRequest, res: HttpResponse, stage: int) -> None:
    if stage == BEFORE_REQUEST:
        now = time.time()
        req.headers['x-timer-middleware'] = now
    elif stage == AFTER_REQUEST:
        start_at = req.headers['x-timer-middleware'] # type: float
        res.headers['x-request-time'] = str(time.time() - start_at)
    else:
        raise ValueError('Something went wrong')

def gzip_middleware(req: HttpRequest, res: HttpResponse, stage: int) -> None:
    """Useless in production, only as PoC
    """
    if stage == AFTER_REQUEST:
        if res.body is not None:
            res.set_header('content-encoding', 'gzip')
            body = res.body.encode('utf-8') if not res.is_binary else res.body # type: bytes
            res.set_body(gzip.compress(body))

class RedisLimiter():
    def __init__(self, prefix: str, redis_url: str, limit: int, period: int):
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.limit = limit
        self.period = period
    
    def __call__(self, req: HttpRequest, res: HttpResponse, stage: int) -> t.Optional[bool]:
        if stage == BEFORE_REQUEST:
            key = self.prefix + ':' + req.remote_host
            if self.redis.exists(key):
                visits = int(self.redis.get(key))
                if visits >= self.limit:
                    res.set_status(429)
                    res.set_text('Please retry later')
                    return False
                self.redis.incr(key, 1)
            else:
                self.redis.set(key, 1, ex=self.period)

class RedisCache():
    def __init__(self, prefix: str, redis_url: str, max_age: int=600):
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.max_age = max_age
    
    def __call__(self, req: HttpRequest, res: HttpResponse, stage: int) -> t.Optional[bool]:
        if req.method not in ('GET', 'OPTIONS'):
            return
        key = self.prefix + ':' + req.uri
        if stage == BEFORE_REQUEST:
            if self.redis.exists(key):
                record = pickle.loads(self.redis.get(key))
                res.copy_from(record)
                res.set_header('x-cache', 'hit')
                return False
            else:
                res.set_header('x-cache', 'miss')
        elif stage == AFTER_REQUEST:
            if res.status < 300:
                record = pickle.dumps(res)
                self.redis.set(key, record, ex=self.max_age)
