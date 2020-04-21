from __future__ import with_statement
import os
import pickle
from contextlib import closing
try:
    from redis import Redis
except ImportError:
    Redis = None


class Cache(object):
    def __init__(self):
        self._cache = {}

    def get(self, k):
        return self._cache.get(k)

    def set(self, k, v):
        self._cache[k] = v


class PickleCache(Cache):
    def __init__(self, filename='cache.db'):
        self.filename = filename
        self._cache = self.load()
    
    def load(self):
        if os.path.exists(self.filename):
            with closing(open(self.filename, 'rb')) as fh:
                return pickle.load(fh)
        return {}

    def save(self):
        with closing(open(self.filename, 'wb')) as fh:
            pickle.dump(self._cache, fh)


if Redis:
    class RedisCache(Cache):
        def __init__(self, namespace='micawber', **conn):
            self.namespace = namespace
            self.key_fn = lambda self, k: '%s.%s' % (self.namespace, k)
            self.conn = Redis(**conn)
        
        def get(self, k):
            cached = self.conn.get(self.key_fn(k))
            if cached:
                return pickle.loads(cached)
        
        def set(self, k, v):
            self.conn.set(self.key_fn(k), pickle.dumps(v))
