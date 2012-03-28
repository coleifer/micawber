from __future__ import with_statement
import os
import pickle
from contextlib import closing


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
            with closing(open(self.filename)) as fh:
                contents = fh.read()
            return pickle.loads(contents)
        return {}

    def save(self):
        with closing(open(self.filename, 'w')) as fh:
            fh.write(pickle.dumps(self._cache))
