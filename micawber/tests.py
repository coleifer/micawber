import os
import shutil
import sys
import tempfile
import unittest

from micawber import *
try:
    from micawber.cache import RedisCache
except ImportError:
    RedisCache = None
try:
    from micawber.contrib import mcflask
except ImportError:
    mcflask = None
try:
    import flask
except ImportError:
    flask = None
from micawber.parsers import full_handler
from micawber.test_utils import test_pr, test_cache, test_pr_cache, TestProvider, BaseTestCase


class ProviderTestCase(BaseTestCase):
    def test_register_unregister(self):
        pr = ProviderRegistry()
        provider1 = TestProvider('link')
        provider2 = TestProvider('link')
        pr.register('1', provider1)
        pr.register('2', provider1)
        pr.register('3', provider2)
        pr.unregister('2')
        self.assertEqual(len(pr._registry), 2)

        # Multiple calls to remove() are OK.
        self.assertRaises(KeyError, pr.unregister, '2')

        self.assertEqual(pr.provider_for_url('1'), provider1)
        self.assertEqual(pr.provider_for_url('2'), None)
        self.assertEqual(pr.provider_for_url('3'), provider2)

        pr.unregister('1')
        pr.unregister('3')
        self.assertEqual(len(pr._registry), 0)
        for test_regex in ['1', '2', '3']:
            self.assertEqual(pr.provider_for_url(test_regex), None)

    def test_multiple_matches(self):
        pr = ProviderRegistry()
        provider1 = TestProvider('link')
        provider2 = TestProvider('link')
        pr.register(r'1(\d+)', provider1)
        pr.register(r'1\d+', provider2)
        self.assertEqual(pr.provider_for_url('11'), provider2)
        pr.unregister(r'1\d+')
        self.assertEqual(pr.provider_for_url('11'), provider1)

    def test_provider_matching(self):
        provider = test_pr.provider_for_url('http://link-test1')
        self.assertFalse(provider is None)
        self.assertEqual(provider.endpoint, 'link')

        provider = test_pr.provider_for_url('http://photo-test1')
        self.assertFalse(provider is None)
        self.assertEqual(provider.endpoint, 'photo')

        provider = test_pr.provider_for_url('http://video-test1')
        self.assertFalse(provider is None)
        self.assertEqual(provider.endpoint, 'video')

        provider = test_pr.provider_for_url('http://rich-test1')
        self.assertFalse(provider is None)
        self.assertEqual(provider.endpoint, 'rich')

        provider = test_pr.provider_for_url('http://none-test1')
        self.assertTrue(provider is None)

    def test_provider(self):
        resp = test_pr.request('http://link-test1')
        self.assertEqual(resp, {'title': 'test1', 'type': 'link', 'url': 'http://link-test1'})

        resp = test_pr.request('http://photo-test2')
        self.assertEqual(resp, {'title': 'ptest2', 'type': 'photo', 'url': 'test2.jpg'})

        resp = test_pr.request('http://video-test1')
        self.assertEqual(resp, {'title': 'vtest1', 'type': 'video', 'html': '<test1>video</test1>', 'url': 'http://video-test1'})

        resp = test_pr.request('http://link-test1', width=100)
        self.assertEqual(resp, {'title': 'test1', 'type': 'link', 'url': 'http://link-test1', 'width': 99})

        self.assertRaises(ProviderException, test_pr.request, 'http://not-here')
        self.assertRaises(ProviderException, test_pr.request, 'http://link-test3')

    def test_caching(self):
        resp = test_pr_cache.request('http://link-test1')
        self.assertCached('http://link-test1', resp)

        # check that its the same as what we tested in the previous case
        resp2 = test_pr.request('http://link-test1')
        self.assertEqual(resp, resp2)

        resp = test_pr_cache.request('http://photo-test2')
        self.assertCached('http://photo-test2', resp)

        resp = test_pr_cache.request('http://video-test1')
        self.assertCached('http://video-test1', resp)

        self.assertEqual(len(test_cache._cache), 3)

    def test_caching_params(self):
        resp = test_pr_cache.request('http://link-test1')
        self.assertCached('http://link-test1', resp)

        resp_p = test_pr_cache.request('http://link-test1', width=100)
        self.assertCached('http://link-test1', resp_p, width=100)

        self.assertFalse(resp == resp_p)

    def test_make_key_stable(self):
        from micawber.providers import make_key
        k1 = make_key('http://foo', {'maxwidth': 600, 'maxheight': 400})
        k2 = make_key('http://foo', {'maxheight': 400, 'maxwidth': 600})
        self.assertEqual(k1, k2)
        self.assertEqual(make_key('http://foo', a=1, b=2),
                         make_key('http://foo', b=2, a=1))
        self.assertNotEqual(k1, make_key('http://foo', {'maxwidth': 600}))

    def test_make_key_non_json_params(self):
        import datetime
        from decimal import Decimal
        from micawber.providers import make_key
        k1 = make_key('http://foo', {'maxwidth': Decimal('600'),
                                     'since': datetime.date(2026, 7, 5)})
        k2 = make_key('http://foo', {'since': datetime.date(2026, 7, 5),
                                     'maxwidth': Decimal('600')})
        self.assertEqual(k1, k2)

    def test_cache_falsy_value(self):
        from micawber.providers import make_key
        # A cached falsy value is a hit, not a miss -- link-test3 is unknown
        # to the provider, so an attempt to re-fetch would raise instead.
        test_cache.set(make_key('http://link-test3', {}), {})
        self.assertEqual(test_pr_cache.request('http://link-test3'), {})

    def test_fetch_error_chained(self):
        pr = ProviderRegistry()
        pr.register(r'http://refused\S*',
                    Provider('http://127.0.0.1:1/oembed', timeout=1.0))
        with self.assertRaises(ProviderException) as ctx:
            pr.request('http://refused-test')
        self.assertTrue(ctx.exception.__cause__ is not None)

    def test_bootstrap_basic_matching(self):
        pr = bootstrap_basic()
        urls = [
            'https://podcasts.apple.com/us/podcast/the-daily/id1200361736',
            'https://www.circuitlab.com/circuit/62vf6a/555-timer/',
            'https://www.dailymotion.com/video/x8kjx7v',
            'https://www.flickr.com/photos/bees/2341623661/',
            'https://flic.kr/p/4yVr32',
            'https://www.polleverywhere.com/polls/LTIwNzM4NTt8MQ',
            'https://www.slideshare.net/haraldf/business-quotes-for-2011',
            'https://soundcloud.com/forss/flickermood',
            'https://speakerdeck.com/rocio/or-mad-men',
            'https://www.scribd.com/document/110799637/Synthesis',
            'https://www.tiktok.com/@scout2015/video/6718335390845095173',
            'https://tiktok.com/@scout2015/video/6718335390845095173',
            'https://twitter.com/jack/status/20',
            'https://x.com/jack/status/20',
            'https://vimeo.com/76979871',
            'http://player.vimeo.com/76979871',
            'https://someblog.wordpress.com/2011/10/28/1000-posts/',
            'https://wordpress.tv/2026/06/06/fireside-chat/',
            'http://www.youtube.com/watch?v=54XHDUOHuzU',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://www.youtube.com/shorts/aqz-KE-bpKQ',
        ]
        for url in urls:
            self.assertTrue(pr.provider_for_url(url) is not None, url)

    def test_bootstrap_iframely(self):
        # An api key (or md5-hashed "key") is required.
        self.assertRaises(ValueError, bootstrap_iframely)

        pr = bootstrap_iframely(api_key='secret')
        for url in ('http://example.com/foo',
                    'https://vimeo.com/76979871',
                    'https://sub.domain.example/path?query=1'):
            provider = pr.provider_for_url(url)
            self.assertTrue(provider is not None, url)
            self.assertEqual(provider.endpoint, 'https://iframe.ly/api/oembed')
            self.assertEqual(provider.base_params['api_key'], 'secret')

        self.assertTrue(pr.provider_for_url('ftp://example.com/f') is None)

        pr = bootstrap_iframely(key='0123456789abcdef')
        provider = pr.provider_for_url('https://example.com/')
        self.assertEqual(provider.base_params['key'], '0123456789abcdef')

    def test_invalid_json(self):
        pr = ProviderRegistry()
        class BadProvider(Provider):
            def fetch(self, url):
                return 'bad'
        pr.register('http://bad', BadProvider('link'))
        self.assertRaises(InvalidResponseException, pr.request, 'http://bad')


class EscapingTestCase(BaseTestCase):
    # html-escaped form of the title in the "link-unsafe" test fixture.
    escaped_title = '&quot;&gt;&lt;script&gt;alert(0)&lt;/script&gt;'

    def test_unsafe_title_escaped(self):
        expected = '<a href="http://link-unsafe" title="%s">%s</a>' % (
            self.escaped_title, self.escaped_title)

        # Standalone link, rendered by the full handler.
        self.assertEqual(test_pr.parse_text('http://link-unsafe'), expected)
        self.assertEqual(test_pr.parse_text_full('http://link-unsafe'),
                         expected)

        # Inline link, rendered by the block handler.
        self.assertEqual(test_pr.parse_text('see: http://link-unsafe'),
                         'see: %s' % expected)

        # BeautifulSoup re-serializes the replacement html (e.g. quoting the
        # title attribute differently), so compare parse trees and verify no
        # script tag survives.
        parsed = test_pr.parse_html('<p>http://link-unsafe</p>')
        self.assertHTMLEqual(parsed, '<p>%s</p>' % expected)
        self.assertTrue('<script>' not in parsed)

    def test_unsafe_url_escaped(self):
        url = 'test.jpg&quot; onload=&quot;alert(0)'
        expected = ('<a href="%(url)s" title="pic">'
                    '<img alt="pic" src="%(url)s" /></a>' % {'url': url})
        self.assertEqual(test_pr.parse_text('http://photo-unsafe'), expected)

    def test_response_html_not_escaped(self):
        # The html of a video/rich response is provider-supplied embed markup
        # and is rendered as-is.
        resp = test_pr.request('http://video-test1')
        self.assertEqual(full_handler('http://video-test1', resp),
                         '<test1>video</test1>')


class PickleCacheTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.filename = os.path.join(self.tmpdir, 'cache.db')

    def test_load_missing_file(self):
        cache = PickleCache(self.filename)
        self.assertEqual(cache._cache, {})
        self.assertTrue(cache.get('key') is None)

    def test_load_bad_file(self):
        import pickle
        for content in (b'', b'not a pickle', pickle.dumps([1, 2, 3])):
            with open(self.filename, 'wb') as fh:
                fh.write(content)
            cache = PickleCache(self.filename)
            self.assertEqual(cache._cache, {})

        # The cache remains usable after recovering from a bad file.
        cache.set('key', 'value')
        cache.save()
        self.assertEqual(PickleCache(self.filename).get('key'), 'value')

    def test_save_load_roundtrip(self):
        cache = PickleCache(self.filename)
        cache.set('key', {'title': 'test', 'type': 'link'})
        cache.set('key2', [1, 2, 3])
        cache.save()

        cache2 = PickleCache(self.filename)
        self.assertEqual(cache2.get('key'), {'title': 'test', 'type': 'link'})
        self.assertEqual(cache2.get('key2'), [1, 2, 3])
        self.assertTrue(cache2.get('missing') is None)


@unittest.skipIf(mcflask is None, 'markupsafe/flask is not installed')
class McFlaskTestCase(BaseTestCase):
    class FakeApp(object):
        def __init__(self):
            self.jinja_env = type('JinjaEnv', (), {'filters': {}})()

    def test_oembed(self):
        result = mcflask.oembed('http://link-test1', test_pr)
        self.assertTrue(isinstance(result, mcflask.Markup))
        self.assertEqual(result, self.full_pairs['http://link-test1'])

        result = mcflask.oembed('<p>http://link-test1</p>', test_pr,
                                html=True)
        self.assertTrue(isinstance(result, mcflask.Markup))
        self.assertHTMLEqual(result,
                             '<p>%s</p>' % self.full_pairs['http://link-test1'])

    def test_extract_oembed(self):
        urls, data = mcflask.extract_oembed(
            'http://link-test1 http://fapp.io/foo/', test_pr)
        self.assertEqual(urls, ['http://link-test1', 'http://fapp.io/foo/'])
        self.assertEqual(list(data), ['http://link-test1'])

        urls, data = mcflask.extract_oembed(
            '<p>http://link-test1</p>', test_pr, html=True)
        self.assertEqual(urls, ['http://link-test1'])
        self.assertEqual(list(data), ['http://link-test1'])

    def test_add_oembed_filters(self):
        app = self.FakeApp()
        mcflask.add_oembed_filters(app, test_pr)
        filters = app.jinja_env.filters
        self.assertEqual(sorted(filters), ['extract_oembed', 'oembed'])

        result = filters['oembed']('http://link-test1')
        self.assertTrue(isinstance(result, mcflask.Markup))
        self.assertEqual(result, self.full_pairs['http://link-test1'])

        urls, data = filters['extract_oembed']('http://link-test1')
        self.assertEqual(urls, ['http://link-test1'])

    @unittest.skipIf(flask is None, 'flask is not installed')
    def test_flask_render(self):
        app = flask.Flask(__name__)
        mcflask.add_oembed_filters(app, test_pr)
        with app.app_context():
            # The oembed markup must survive jinja autoescaping...
            rendered = flask.render_template_string(
                '<div>{{ s|oembed }}</div>', s='http://link-test1')
            self.assertEqual(rendered, '<div>%s</div>'
                             % self.full_pairs['http://link-test1'])

            # ...while everything else is escaped as usual.
            rendered = flask.render_template_string(
                '{{ s|oembed }}', s='http://link-unsafe')
            self.assertTrue('<script>' not in rendered)


class FakeRedisConn(object):
    # Implements the redis-py >= 3.0 API for the commands RedisCache uses.
    def __init__(self):
        self.data = {}
        self.expiry = {}

    def get(self, name):
        return self.data.get(name)

    def set(self, name, value, ex=None):
        if ex is not None and not isinstance(ex, int):
            raise ValueError('ex must be an integer number of seconds')
        self.data[name] = value
        if ex is not None:
            self.expiry[name] = ex


@unittest.skipIf(RedisCache is None, 'redis-py is not installed')
class RedisCacheTestCase(unittest.TestCase):
    def get_cache(self, **kwargs):
        cache = RedisCache(**kwargs)
        cache.conn = FakeRedisConn()
        return cache

    def test_get_set(self):
        cache = self.get_cache()
        self.assertTrue(cache.get('key') is None)
        cache.set('key', {'title': 'test'})
        self.assertEqual(cache.get('key'), {'title': 'test'})
        self.assertTrue('micawber.key' in cache.conn.data)
        self.assertEqual(cache.conn.expiry, {})

    def test_timeout(self):
        cache = self.get_cache(timeout=60)
        cache.set('key', {'title': 'test'})
        self.assertEqual(cache.get('key'), {'title': 'test'})
        self.assertEqual(cache.conn.expiry['micawber.key'], 60)


class ParserTestCase(BaseTestCase):
    def test_parse_text_full(self):
        for url, expected in self.full_pairs.items():
            parsed = test_pr.parse_text_full(url)
            self.assertHTMLEqual(parsed, expected)

        # the parse_text_full will replace even inline content
        for url, expected in self.full_pairs.items():
            parsed = test_pr.parse_text_full('this is inline: %s' % url)
            self.assertHTMLEqual(parsed, 'this is inline: %s' % expected)

        for url, expected in self.full_pairs.items():
            parsed = test_pr.parse_html('<p>%s</p>' % url)
            self.assertHTMLEqual(parsed, '<p>%s</p>' % expected)

    def test_parse_text(self):
        for url, expected in self.inline_pairs.items():
            parsed = test_pr.parse_text('this is inline: %s' % url)
            self.assertHTMLEqual(parsed, 'this is inline: %s' % expected)

        # We can disable parsing inline links by specifying block_handler=None.
        for url, expected in self.inline_pairs.items():
            parsed = test_pr.parse_text('this is inline: %s' % url, block_handler=None)
            self.assertEqual(parsed, 'this is inline: %s' % url)

        # if the link comes on its own line it gets included in full
        for url, expected in self.full_pairs.items():
            parsed = test_pr.parse_text(url)
            self.assertHTMLEqual(parsed, expected)

            # Specifying block_handler=None only applies to inline links, so
            # the behavior is the same for standalone links.
            parsed = test_pr.parse_text(url, block_handler=None)
            self.assertHTMLEqual(parsed, expected)

        # links inside block tags will render as inline
        frame = '<p>Testing %s</p>'
        for url, expected in self.inline_pairs.items():
            parsed = test_pr.parse_html(frame % (url))
            self.assertHTMLEqual(parsed, frame % (expected))

        # links inside <a> tags won't change at all
        frame = '<p><a href="%s">%s</a></p>'
        for url, expected in self.inline_pairs.items():
            parsed = test_pr.parse_html(frame % (url, url))
            self.assertHTMLEqual(parsed, frame % (url, url))

        # links within tags within a tags are fine too
        frame = '<p><a href="%s"><span>%s</span></a></p>'
        for url, expected in self.inline_pairs.items():
            parsed = test_pr.parse_html(frame % (url, url))
            self.assertHTMLEqual(parsed, frame % (url, url))

    def test_multiline(self):
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = 'this is inline: %s\n%s\nand yet another %s'

            test_str = frame % (url, url, url)

            parsed = test_pr.parse_text(test_str)
            self.assertHTMLEqual(parsed, frame % (expected_inline, expected, expected_inline))

        # On multi-line text, if we specify block_handler=None, only standalone
        # links will be handled.
        for url, expected in self.full_pairs.items():
            frame = 'this is inline: %s\n%s\nand yet another %s'
            test_str = frame % (url, url, url)

            parsed = test_pr.parse_text(test_str, block_handler=None)
            self.assertHTMLEqual(parsed, frame % (url, expected, url))

        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '%s\nthis is inline: %s\n%s'

            test_str = frame % (url, url, url)

            parsed = test_pr.parse_text(test_str)
            self.assertHTMLEqual(parsed, frame % (expected, expected_inline, expected))

        # test mixing multiline with p tags
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '<p>%s</p>\n<p>this is inline: %s</p>\n<p>\n%s\n</p><p>last test\n%s\n</p>'

            test_str = frame % (url, url, url, url)

            parsed = test_pr.parse_html(test_str)
            self.assertHTMLEqual(parsed, frame % (expected, expected_inline, expected, expected_inline))

        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '<p><a href="#foo">%s</a></p>\n<p>this is inline: %s</p>\n<p>last test\n%s\n</p>'

            test_str = frame % (url, url, url)

            parsed = test_pr.parse_html(test_str)
            self.assertHTMLEqual(parsed, frame % (url, expected_inline, expected_inline))

    def test_multiline_full(self):
        for url, expected in self.full_pairs.items():
            frame = 'this is inline: %s\n%s\nand yet another %s'

            test_str = frame % (url, url, url)

            parsed = test_pr.parse_text_full(test_str)
            self.assertHTMLEqual(parsed, frame % (expected, expected, expected))

    def test_urlize(self):
        blank = 'http://fapp.io/foo/'
        blank_e = '<a href="http://fapp.io/foo/">http://fapp.io/foo/</a>'
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = 'test %s\n%s\n%s\nand finally %s'

            test_str = frame % (url, blank, url, blank)

            parsed = test_pr.parse_text(test_str)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank_e, expected, blank_e))

            parsed = test_pr.parse_text(test_str, urlize_all=False)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank, expected, blank))

            parsed = test_pr.parse_text_full(test_str)
            self.assertHTMLEqual(parsed, frame % (expected, blank_e, expected, blank_e))

            parsed = test_pr.parse_text_full(test_str, urlize_all=False)
            self.assertHTMLEqual(parsed, frame % (expected, blank, expected, blank))

            parsed = test_pr.parse_html(test_str)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank_e, expected_inline, blank_e))

            parsed = test_pr.parse_html(test_str, urlize_all=False)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank, expected_inline, blank))

            frame = '<p>test %s</p>\n<a href="foo">%s</a>\n<a href="foo2">%s</a>\n<p>and finally %s</p>'

            test_str = frame % (url, blank, url, blank)

            parsed = test_pr.parse_html(test_str)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank, url, blank_e))

            parsed = test_pr.parse_html(test_str, urlize_all=False)
            self.assertHTMLEqual(parsed, frame % (expected_inline, blank, url, blank))

    def test_request_deduplication(self):
        class CountingProvider(TestProvider):
            fetch_count = 0
            def fetch(self, url):
                CountingProvider.fetch_count += 1
                return super(CountingProvider, self).fetch(url)

        pr = ProviderRegistry()
        pr.register(r'http://link\S*', CountingProvider('link'))

        def assertFetches(n, fn, *args):
            CountingProvider.fetch_count = 0
            fn(*args)
            self.assertEqual(CountingProvider.fetch_count, n)

        text = 'http://link-test1\nsee http://link-test1\nhttp://link-test1'
        assertFetches(1, pr.parse_text, text)
        assertFetches(1, pr.parse_text_full, text)

        html = '<p>http://link-test1</p><p>x http://link-test1</p>'
        assertFetches(1, pr.parse_html, html)
        assertFetches(1, pr.extract_html, html)

        # Failed lookups are not retried within a single parse either --
        # link-test3 is unknown to the provider.
        assertFetches(1, pr.parse_text,
                      'http://link-test3\nhttp://link-test3')

        # Distinct urls are of course fetched individually.
        assertFetches(2, pr.parse_text,
                      'http://link-test1\nhttp://link-test2')

    def test_replacement_backslash(self):
        # Replacements must be inserted literally, without backslash-escape
        # processing.
        expected = '<x>\\1 \\g<0> C:\\path</x>'
        self.assertEqual(test_pr.parse_text('http://rich-backslash'), expected)
        self.assertEqual(
            test_pr.parse_text_full('inline http://rich-backslash'),
            'inline %s' % expected)

    def test_skip_script_and_style(self):
        for frame in ('<script>var u = "%s";</script>',
                      '<style>body { background: url(%s) }</style>',
                      '<svg><text>%s</text></svg>',
                      '<title>%s</title>'):
            html = frame % 'http://link-test1'
            self.assertEqual(test_pr.parse_html(html), html)

    def test_urlize_params(self):
        text = 'test http://foo.com/'
        urlize_params = {'target': '_blank', 'rel': 'nofollow'}
        exp = ('test <a href="http://foo.com/" rel="nofollow" target="_blank">'
               'http://foo.com/</a>')

        result = test_pr.parse_text(text, urlize_params=urlize_params)
        self.assertEqual(result, exp)

        result = test_pr.parse_text_full(text, urlize_params=urlize_params)
        self.assertEqual(result, exp)

        result = test_pr.parse_html(text, urlize_params=urlize_params)
        self.assertEqual(result, exp)

    def test_extract(self):
        blank = 'http://fapp.io/foo/'
        frame = 'test %s\n%s\n%s\n%s at last'
        frame_html = '<p>test %s</p><p><a href="foo">%s</a> %s</p><p>%s</p>'

        for url, expected in self.data_pairs.items():
            text = frame % (url, blank, url, blank)
            all_urls, extracted = test_pr.extract(text)
            self.assertEqual(all_urls, [url, blank])

            if 'url' not in expected:
                expected['url'] = url
            if 'title' not in expected:
                expected['title'] = expected['url']
            self.assertEqual(extracted, {url: expected})

            html = frame_html % (url, url, blank, blank)
            all_urls, extracted = test_pr.extract_html(html)
            self.assertEqual(all_urls, [url, blank])

            if 'url' not in expected:
                expected['url'] = url
            self.assertEqual(extracted, {url: expected})

    def test_outside_of_markup(self):
        frame = '%s<p>testing</p>'
        for url, expected in self.full_pairs.items():
            parsed = test_pr.parse_html(frame % (url))
            self.assertHTMLEqual(parsed, frame % (expected))

    def test_html_entities(self):
        frame_html = '<p>test %s</p><p><a href="foo">%s</a></p>'

        for url, expected in self.data_pairs.items():
            esc_url = url.replace('&', '&amp;')
            html = frame_html % (esc_url, esc_url)
            all_urls, extracted = test_pr.extract_html(html)
            self.assertEqual(all_urls, [url])

            if 'url' not in expected:
                expected['url'] = url
            if 'title' not in expected:
                expected['title'] = expected['url']
            self.assertEqual(extracted, {url: expected})

            rendered = test_pr.parse_html('<p>%s</p>' % esc_url)
            self.assertHTMLEqual(rendered, '<p>%s</p>' % self.full_pairs[url])


class TestHTMLEntities(BaseTestCase):
    def test_parse_html_entities(self):
        e = '&lt;script&gt;&lt;/script&gt;'
        p = '<p>Test %s</p>' % e
        self.assertEqual(test_pr.parse_html(p), p)

        a = '<p>http://google.com %s</p>' % e
        self.assertEqual(test_pr.parse_html(a),
                         '<p><a href="http://google.com">http://google.com</a>'
                         ' %s</p>' % e)

        h = ('<p><a href="http://foo.com">http://foo.com</a> http://bar.com '
             '<span>http://baz.com &lt;script&gt; '
             '<b>http://nug.com <i>X &lt;foo&gt;</i></b></span></p>')
        self.assertEqual(test_pr.parse_html(h), (
            '<p><a href="http://foo.com">http://foo.com</a> '
            '<a href="http://bar.com">http://bar.com</a> '
            '<span><a href="http://baz.com">http://baz.com</a> &lt;script&gt; '
            '<b><a href="http://nug.com">http://nug.com</a> '
            '<i>X &lt;foo&gt;</i></b></span></p>'))

        h = ('<p><a href="http://foo.com">http://foo.com</a> http://bar.com '
             '&lt;script&gt; http://baz.com &lt;/script&gt;\n'
             'http://baze.com\n&lt;foo&gt;</p>')
        self.assertEqual(test_pr.parse_html(h), (
            '<p><a href="http://foo.com">http://foo.com</a> '
            '<a href="http://bar.com">http://bar.com</a> &lt;script&gt; '
            '<a href="http://baz.com">http://baz.com</a> &lt;/script&gt;\n'
            '<a href="http://baze.com">http://baze.com</a>\n'
            '&lt;foo&gt;</p>'))



class GoogleMapsProviderTestCase(unittest.TestCase):
    def test_query_param_without_equals(self):
        from micawber.contrib.providers import GoogleMapsProvider
        p = GoogleMapsProvider('')
        # Flag-style query params (no '=') must not raise.
        result = p.request('https://maps.google.com/maps?q')
        self.assertEqual(result['type'], 'rich')
        self.assertIn('output=embed', result['html'])
        result = p.request('https://maps.google.com/maps?foo&q=Paris')
        self.assertIn('q=Paris', result['html'])
        self.assertNotIn('foo', result['html'].split('maps?')[1])


if __name__ == '__main__':
    unittest.main(argv=sys.argv)
