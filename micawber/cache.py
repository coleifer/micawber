import pickle
from collections import OrderedDict
try:
    from redis import Redis
except ImportError:
    Redis = None


class Cache(object):
    def __init__(self, max_size=1024):
        self.max_size = max_size
        self._cache = OrderedDict()

    def get(self, k):
        if k not in self._cache:
            return None
        self._cache.move_to_end(k)
        return self._cache[k]

    def set(self, k, v):
        self._cache[k] = v
        self._cache.move_to_end(k)
        while self.max_size and len(self._cache) > self.max_size:
            self._cache.popitem(last=False)


class PickleCache(Cache):
    def __init__(self, filename='cache.db', max_size=None):
        super(PickleCache, self).__init__(max_size)
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

        def set(self, k, v):
            self.conn.set(self.key_fn(k), pickle.dumps(v), ex=self.timeout)
