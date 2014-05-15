from django.template import Context
from django.template import Template
from django.test import TestCase

from micawber.parsers import parse_text
from micawber.test_utils import BaseTestCase
from micawber.test_utils import test_cache
from micawber.test_utils import test_pr
from micawber.test_utils import test_pr_cache
from micawber.test_utils import TestProvider


class MicawberDjangoTestCase(TestCase, BaseTestCase):
    def render(self, s, **params):
        s = '{%% load micawber_tags %%}%s' % s
        return Template(s).render(Context(params)).strip()

    def test_oembed_alt(self):
        from micawber.contrib.mcdjango import extension

        def custom_handler(url, response_data):
            return url

        oembed_alt = extension(
            'oembed_alt',
            urlize_all=False,
            block_handler=custom_handler)

        text = '\n'.join((
            'this is the first line',
            'http://photo-test2',
            'this is the third line http://photo-test2',
            'http://photo-test2 this is the fourth line'))
        rendered = self.render('{{ text|oembed_alt }}', text=text)
        self.assertEqual(rendered.splitlines(), [
            'this is the first line',
            self.full_pairs['http://photo-test2'],
            'this is the third line http://photo-test2',
            'http://photo-test2 this is the fourth line',
        ])

    def test_fix_wh(self):
        from micawber.contrib.mcdjango import fix_width_height
        self.assertEqual(fix_width_height('300x400', {}), {'maxwidth': 300, 'maxheight': 400})
        self.assertEqual(fix_width_height('300', {}), {'maxwidth': 300})

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
            self.assertHTMLEqual(parsed, frame % (expected, expected_inline, expected, expected_inline))

        for url, expected in self.full_pairs.items():
            expected_inline = self.inline_pairs[url]
            frame = '<p><a href="#foo">%s</a></p>\n<p>this is inline: %s</p>\n<p>last test\n%s\n</p>'

            test_str = frame % (url, url, url)

            parsed = self.render('{{ test_str|oembed_html }}', test_str=test_str)
            self.assertHTMLEqual(parsed, frame % (url, expected_inline, expected_inline))

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
