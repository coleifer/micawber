from collections import OrderedDict
import pickle
import time
try:
    from redis import Redis
except ImportError:
    Redis = None


class Cache(object):
    def __init__(self, timeout=None, max_size=1024):
        self.max_size = max_size
        self.timeout = timeout
        self._cache = OrderedDict()

    def get(self, k):
        if k not in self._cache:
            return None

        v = self._cache[k]
        if isinstance(v, tuple):
            v, ttl = v
            if ttl is not None and time.time() > ttl:
                del self._cache[k]
                return None
        self._cache.move_to_end(k)
        return v

    def set(self, k, v, timeout=None):
        timeout = timeout or self.timeout
        if timeout:
            ttl = time.time() + timeout
        else:
            ttl = None
        self._cache[k] = (v, ttl)
        self._cache.move_to_end(k)
        while self.max_size and len(self._cache) > self.max_size:
            self._cache.popitem(last=False)


class PickleCache(Cache):
    def __init__(self, filename='cache.db', timeout=None, max_size=None):
        super(PickleCache, self).__init__(timeout, max_size)
        self.filename = filename
        self._cache.update(self.load())

    def load(self):
        try:
            with open(self.filename, 'rb') as fh:
                data = pickle.load(fh)
        except Exception:
            # A cache that cannot be read (missing file, truncated write,
            # corrupt or incompatible pickle) is treated as empty.
            return {}
        return data if isinstance(data, dict) else {}

    def save(self):
        with open(self.filename, 'wb') as fh:
            pickle.dump(self._cache, fh)


if Redis:
    class RedisCache(Cache):
        """
        :param str namespace: key prefix.
        :param int timeout: expiration timeout in seconds
        """
        def __init__(self, namespace='micawber', timeout=None, **conn):
            self.namespace = namespace
            self.timeout = timeout
            self.conn = Redis(**conn)

        def key_fn(self, k):
            return '%s.%s' % (self.namespace, k)

        def get(self, k):
            cached = self.conn.get(self.key_fn(k))
            if cached:
                return pickle.loads(cached)

        def set(self, k, v, timeout=None):
            timeout = timeout or self.timeout
            self.conn.set(self.key_fn(k), pickle.dumps(v), ex=timeout)
