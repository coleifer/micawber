import json
import re
from html import escape

try:
    from bs4 import BeautifulSoup, Comment
    bs_kwargs = replace_kwargs = {'features': 'html.parser'}
except ImportError:
    BeautifulSoup = None
    Comment = None
    bs_kwargs = replace_kwargs = {}

from micawber.exceptions import ProviderException


url_pattern = '(https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_|])'
url_re = re.compile(url_pattern)
standalone_url_re = re.compile(r'^\s*' + url_pattern + r'\s*$')

block_elements = set([
    'address', 'article', 'aside', 'blockquote', 'canvas', 'center', 'dir',
    'dd', 'div', 'dl', 'dt', 'fieldset', 'figcaption', 'figure', 'footer',
    'form', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hr',
    'isindex', 'li', 'main', 'menu', 'nav', 'noframes', 'noscript', 'ol', 'p',
    'pre', 'section', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr',
    'ul',
    # Additional elements.
    'button', 'del', 'iframe', 'ins', 'map', 'object', '[document]',
])

skip_elements = set([
    'a', 'pre', 'code', 'input', 'textarea', 'select',
    'head', 'script', 'style', 'svg', 'title',
])


def _escape_data(response_data):
    # The url and title in a provider response frequently contain end-user
    # content (e.g. video titles) and cannot be trusted in html.
    return {
        'url': escape(str(response_data['url'])),
        'title': escape(str(response_data['title']))}

def full_handler(url, response_data, **params):
    if response_data['type'] == 'link':
        return '<a href="%(url)s" title="%(title)s">%(title)s</a>' % _escape_data(response_data)
    elif response_data['type'] == 'photo':
        return '<a href="%(url)s" title="%(title)s"><img alt="%(title)s" src="%(url)s" /></a>' % _escape_data(response_data)
    else:
        html = response_data.get('html')
        if html is None:
            return '<a href="%(url)s" title="%(title)s">%(title)s</a>' % _escape_data(response_data)
        return html

def inline_handler(url, response_data, **params):
    return '<a href="%(url)s" title="%(title)s">%(title)s</a>' % _escape_data(response_data)

def urlize(url, **params):
    params.setdefault('href', url)
    param_html = ' '.join('%s="%s"' % (key, value)
                          for key, value in sorted(params.items()))
    return '<a %s>%s</a>' % (param_html, url)

class _RequestMemo(object):
    # Collapse repeated requests (or failures) for the same url within a
    # single parse call, e.g. one url appearing in several paragraphs.
    def __init__(self, providers):
        self.providers = providers
        self.responses = {}

    def request(self, url, **params):
        if url in self.responses:
            response, exc = self.responses[url]
        else:
            response = exc = None
            try:
                response = self.providers.request(url, **params)
            except ProviderException as e:
                exc = e
            self.responses[url] = (response, exc)
        if exc is not None:
            raise exc
        return response

def extract(text, providers, **params):
    all_urls = set()
    urls = []
    extracted_urls = {}

    for url in re.findall(url_re, text):
        if url in all_urls:
            continue

        all_urls.add(url)
        urls.append(url)
        try:
            extracted_urls[url] = providers.request(url, **params)
        except ProviderException:
            pass

    return urls, extracted_urls

def parse_text_full(text, providers, urlize_all=True, handler=full_handler,
                    urlize_params=None, **params):
    all_urls, extracted_urls = extract(text, providers, **params)
    replacements = {}
    urlize_params = urlize_params or {}

    for url in all_urls:
        if url in extracted_urls:
            replacements[url] = handler(url, extracted_urls[url], **params)
        elif urlize_all:
            replacements[url] = urlize(url, **urlize_params)

    return url_re.sub(lambda m: replacements.get(m.group(), m.group()), text)

def parse_text(text, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, urlize_params=None, **params):
    lines = text.splitlines()
    parsed = []
    urlize_params = urlize_params or {}
    providers = _RequestMemo(providers)

    for line in lines:
        if standalone_url_re.match(line):
            url = line.strip()
            try:
                response = providers.request(url, **params)
            except ProviderException:
                if urlize_all:
                    line = urlize(url, **urlize_params)
            else:
                line = handler(url, response, **params)
        elif block_handler is not None:
            line = parse_text_full(line, providers, urlize_all, block_handler,
                                   urlize_params=urlize_params, **params)

        parsed.append(line)

    return '\n'.join(parsed)

def parse_html(html, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, soup_class=BeautifulSoup,
               urlize_params=None, **params):

    if not soup_class:
        raise Exception('Unable to parse HTML, please install BeautifulSoup '
                        'or beautifulsoup4, or use the text parser')

    soup = soup_class(html, **bs_kwargs)
    providers = _RequestMemo(providers)

    for url in soup.find_all(string=url_re):
        if not _inside_skip(url):
            if _is_standalone(url):
                url_handler = handler
            else:
                url_handler = block_handler

            url_unescaped = (url.string
                             .replace('<', '&lt;')
                             .replace('>', '&gt;'))

            replacement = parse_text_full(
                url_unescaped,
                providers,
                urlize_all,
                url_handler,
                urlize_params=urlize_params,
                **params)
            url.replace_with(soup_class(replacement, **replace_kwargs))

    return str(soup)

def extract_html(html, providers, **params):
    if not BeautifulSoup:
        raise Exception('Unable to parse HTML, please install BeautifulSoup '
                        'or use the text parser')

    soup = BeautifulSoup(html, **bs_kwargs)
    all_urls = set()
    urls = []
    extracted_urls = {}
    providers = _RequestMemo(providers)

    for url in soup.find_all(string=url_re):
        if _inside_skip(url):
            continue

        block_all, block_ext = extract(str(url), providers, **params)
        for extracted_url in block_all:
            if extracted_url in all_urls:
                continue

            extracted_urls.update(block_ext)
            urls.append(extracted_url)
            all_urls.add(extracted_url)

    return urls, extracted_urls

def _is_standalone(soup_elem):
    if standalone_url_re.match(soup_elem):
        return soup_elem.parent.name in block_elements
    return False

def _inside_skip(soup_elem):
    # Comment nodes match url_re as strings; leave them like script/style skips.
    if Comment is not None and isinstance(soup_elem, Comment):
        return True
    parent = soup_elem.parent
    while parent is not None:
        if parent.name in skip_elements:
            return True
        parent = parent.parent
    return False
