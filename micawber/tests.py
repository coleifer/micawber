import sys
import unittest

from micawber import *
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
        pr.register('1(\d+)', provider1)
        pr.register('1\d+', provider2)
        self.assertEqual(pr.provider_for_url('11'), provider2)
        pr.unregister('1\d+')
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

    def test_invalid_json(self):
        pr = ProviderRegistry()
        class BadProvider(Provider):
            def fetch(self, url):
                return 'bad'
        pr.register('http://bad', BadProvider('link'))
        self.assertRaises(InvalidResponseException, pr.request, 'http://bad')


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


if __name__ == '__main__':
    unittest.main(argv=sys.argv)
