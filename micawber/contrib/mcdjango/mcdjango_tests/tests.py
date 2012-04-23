from django.template import Template, Context
from django.test import TestCase

from micawber.test_utils import test_pr, test_cache, test_pr_cache, TestProvider, BaseTestCase


class MicawberDjangoTestCase(TestCase, BaseTestCase):
    def render(self, s, **params):
        s = '{%% load micawber_tags %%}%s' % s
        return Template(s).render(Context(params)).strip()

    def test_provider_loading(self):
        from micawber.contrib.mcdjango import providers
        self.assertEqual(providers, test_pr)
    
    def test_oembed_filter_multiline_plain(self):
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = 'this is inline: %s\n%s\nand yet another %s'

            test_str = frame % (url, url, url)

            parsed = self.render('{{ test_str|oembed }}', test_str=test_str)
            self.assertEqual(parsed, frame % (expected_inline, expected, expected_inline))
    
    def test_oembed_filter_multiline_html(self):
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '<p>%s</p>\n<p>this is inline: %s</p>\n<p>\n%s\n</p><p>last test\n%s\n</p>'

            test_str = frame % (url, url, url, url)

            parsed = self.render('{{ test_str|oembed_html }}', test_str=test_str)
            self.assertEqual(parsed, frame % (expected, expected_inline, expected, expected_inline))

        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '<p><a href="#foo">%s</a></p>\n<p>this is inline: %s</p>\n<p>last test\n%s\n</p>'

            test_str = frame % (url, url, url)

            parsed = self.render('{{ test_str|oembed_html }}', test_str=test_str)
            self.assertEqual(parsed, frame % (url, expected_inline, expected_inline))
    
    def test_urlize(self):
        u1 = 'http://fappio.com/'
        u2 = 'http://google.com/fap/'
        u1h = '<a href="%s">%s</a>' % (u1, u1)
        u2h = '<a href="%s">%s</a>' % (u2, u2)
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = 'test %s\n%s\n%s\nand another %s'

            test_str = frame % (u1, u2, url, url)

            parsed = self.render('{{ test_str|oembed }}', test_str=test_str)
            self.assertEqual(parsed, frame % (u1h, u2h, expected, expected_inline))
    
    def test_oembed_filter_extension(self):
        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = 'test http://fappio.com\nhttp://google.com\n%s\nand another %s'

            test_str = frame % (url, url)

            parsed = self.render('{{ test_str|oembed_no_urlize }}', test_str=test_str)
            self.assertEqual(parsed, frame % (expected, expected_inline))
    
    def test_extract_filter(self):
        blank = 'http://fapp.io/foo/'
        frame = 'test %s\n%s\n%s\n%s at last'
        frame_html = '<p>test %s</p><p><a href="foo">%s</a> %s</p><p>%s</p>'

        t = """{% for url, data in test_str|extract_oembed %}{{ url }}\n{% endfor %}"""
        t2 = """{% for url, data in test_str|extract_oembed_html %}{{ url }}\n{% endfor %}"""

        for url, expected in self.data_pairs.items():
            test_str = frame % (url, blank, url, blank)
            rendered = self.render(t, test_str=test_str)
            self.assertEqual(rendered, url)
            
            test_str = frame_html % (url, blank, url, blank)
            rendered = self.render(t, test_str=test_str)
            self.assertEqual(rendered, url)
