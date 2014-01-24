import unittest
try:
    import simplejson as json
except ImportError:
    import json

from micawber import *
from micawber.parsers import BeautifulSoup, bs_kwargs
from micawber.providers import make_key


class TestProvider(Provider):
    test_data = {
        # link
        'link?format=json&url=http%3A%2F%2Flink-test1': {'title': 'test1', 'type': 'link'},
        'link?format=json&url=http%3A%2F%2Flink-test2': {'title': 'test2', 'type': 'link'},

        # photo
        'photo?format=json&url=http%3A%2F%2Fphoto-test1': {'title': 'ptest1', 'url': 'test1.jpg', 'type': 'photo'},
        'photo?format=json&url=http%3A%2F%2Fphoto-test2': {'title': 'ptest2', 'url': 'test2.jpg', 'type': 'photo'},

        # video
        'video?format=json&url=http%3A%2F%2Fvideo-test1': {'title': 'vtest1', 'html': '<test1>video</test1>', 'type': 'video'},
        'video?format=json&url=http%3A%2F%2Fvideo-test2': {'title': 'vtest2', 'html': '<test2>video</test2>', 'type': 'video'},

        # rich
        'rich?format=json&url=http%3A%2F%2Frich-test1': {'title': 'rtest1', 'html': '<test1>rich</test1>', 'type': 'rich'},
        'rich?format=json&url=http%3A%2F%2Frich-test2': {'title': 'rtest2', 'html': '<test2>rich</test2>', 'type': 'rich'},

        # with param
        'link?format=json&url=http%3A%2F%2Flink-test1&width=100': {'title': 'test1', 'type': 'link', 'width': 99},

        # no title
        'photo?format=json&url=http%3A%2F%2Fphoto-notitle': {'url': 'notitle.jpg', 'type': 'photo'},
    }

    def fetch(self, url):
        if url in self.test_data:
            return json.dumps(self.test_data[url])
        return False

test_pr = ProviderRegistry()

test_cache = Cache()
test_pr_cache = ProviderRegistry(test_cache)

for pr in (test_pr, test_pr_cache):
    pr.register('http://link\S*', TestProvider('link'))
    pr.register('http://photo\S*', TestProvider('photo'))
    pr.register('http://video\S*', TestProvider('video'))
    pr.register('http://rich\S*', TestProvider('rich'))

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        test_cache._cache = {}

        self.full_pairs = {
            'http://link-test1': '<a href="http://link-test1" title="test1">test1</a>',
            'http://photo-test2': '<a href="test2.jpg" title="ptest2"><img alt="ptest2" src="test2.jpg" /></a>',
            'http://video-test1': '<test1>video</test1>',
            'http://rich-test2': '<test2>rich</test2>',
            'http://photo-notitle': '<a href="notitle.jpg" title="notitle.jpg"><img alt="notitle.jpg" src="notitle.jpg" /></a>',
        }

        self.inline_pairs = {
            'http://link-test1': '<a href="http://link-test1" title="test1">test1</a>',
            'http://photo-test2': '<a href="test2.jpg" title="ptest2">ptest2</a>',
            'http://video-test1': '<a href="http://video-test1" title="vtest1">vtest1</a>',
            'http://rich-test2': '<a href="http://rich-test2" title="rtest2">rtest2</a>',
            'http://rich-test2': '<a href="http://rich-test2" title="rtest2">rtest2</a>',
            'http://photo-notitle': '<a href="notitle.jpg" title="notitle.jpg">notitle.jpg</a>',
        }

        self.data_pairs = {
            'http://link-test1': {'title': 'test1', 'type': 'link'},
            'http://photo-test2': {'title': 'ptest2', 'url': 'test2.jpg', 'type': 'photo'},
            'http://video-test1': {'title': 'vtest1', 'html': '<test1>video</test1>', 'type': 'video'},
            'http://rich-test2': {'title': 'rtest2', 'html': '<test2>rich</test2>', 'type': 'rich'},
            'http://photo-notitle': {'url': 'notitle.jpg', 'type': 'photo'},
        }

    def assertCached(self, url, data, **params):
        key = make_key(url, params)
        self.assertTrue(key in test_cache._cache)
        self.assertEqual(test_cache._cache[key], data)


    def assertHTMLEqual(self, first, second, msg=None):
        first = BeautifulSoup(first, **bs_kwargs)
        second = BeautifulSoup(second, **bs_kwargs)
        self.assertEqual(first, second, msg)
