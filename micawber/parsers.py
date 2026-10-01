import re
from functools import lru_cache
from html import escape

try:
    from bs4 import BeautifulSoup, Comment
    bs_kwargs = {'features': 'html.parser'}
except ImportError:
    BeautifulSoup = Comment = None
    bs_kwargs = {}


scheme_re = re.compile(r'^[\s\x00-\x1f]*[a-z][a-z0-9+.\-]*:', re.I)
http_scheme_re = re.compile(r'^[\s\x00-\x1f]*https?:', re.I)

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


def _escape_data(url, response_data):
    href = str(response_data['url'])
    # Replace any non-http(s) scheme (e.g. javascript:).
    if scheme_re.match(href) and not http_scheme_re.match(href):
        href = url
    return {'url': escape(href), 'title': escape(str(response_data['title']))}


def full_handler(url, response_data, **params):
    data_type = response_data.get('type')
    if data_type == 'photo':
        return ('<a href="%(url)s" title="%(title)s">'
                '<img alt="%(title)s" src="%(url)s" loading="lazy" decoding="async" />'
                '</a>' % _escape_data(url, response_data))
    elif data_type != 'link':
        html = response_data.get('html')
        if html is not None:
            return html
    return inline_handler(url, response_data)


def inline_handler(url, response_data, **params):
    return ('<a href="%(url)s" title="%(title)s">%(title)s</a>' %
            _escape_data(url, response_data))


def urlize(url, **params):
    params.setdefault('href', url)
    param_html = ' '.join('%s="%s"' % (key, escape(str(value)))
                          for key, value in sorted(params.items()))
    return '<a %s>%s</a>' % (param_html, escape(url))


def extract(text, providers, **params):
    return _extract([text], providers, params)


def extract_html(html, providers, soup_class=BeautifulSoup, **params):
    _, nodes = _text_nodes(html, soup_class)
    return _extract(nodes, providers, params)


def parse_text_full(text, providers, urlize_all=True, handler=full_handler,
                    urlize_params=None, **params):
    return _render([(text, handler)], providers, urlize_all, urlize_params,
                   params)[0]


def parse_text(text, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, urlize_params=None, **params):
    chunks = []
    for line in text.splitlines():
        if standalone_url_re.match(line):
            chunks.append((line.strip(), handler))
        else:
            chunks.append((line, block_handler))
    return '\n'.join(_render(chunks, providers, urlize_all, urlize_params,
                             params))

def parse_html(html, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, soup_class=BeautifulSoup,
               urlize_params=None, **params):
    soup, nodes = _text_nodes(html, soup_class)
    chunks = []
    for node in nodes:
        standalone = (standalone_url_re.match(node) and
                      node.parent.name in block_elements)
        chunks.append((str(node).replace('<', '&lt;').replace('>', '&gt;'),
                       handler if standalone else block_handler))

    rendered = _render(chunks, providers, urlize_all, urlize_params, params)
    for node, (text, _), new in zip(nodes, chunks, rendered):
        if new != text:
            node.replace_with(soup_class(new, **bs_kwargs))
    return str(soup)


def _text_nodes(html, soup_class):
    if soup_class is None:
        raise Exception('Unable to parse HTML, please install beautifulsoup4 '
                        'or use the text parser')
    soup = soup_class(html, **bs_kwargs)
    nodes = []
    for node in soup.find_all(string=url_re):
        if isinstance(node, Comment):
            continue
        for parent in node.parents:
            if parent.name in skip_elements:
                break
        else:
            nodes.append(node)
    return soup, nodes


def _extract(texts, providers, params):
    seen = set()
    accum = []
    for text in texts:
        for url in url_re.findall(text):
            if url not in seen:
                seen.add(url)
                accum.append(url)
    return accum, providers.request_many(accum, **params)


def _render(chunks, providers, urlize_all, urlize_params, params):
    _, extracted = _extract(
        [text for text, handler in chunks if handler is not None],
        providers, params)

    @lru_cache(maxsize=None)
    def render(url, handler):
        if url in extracted:
            return handler(url, extracted[url], **params)
        elif urlize_all:
            return urlize(url, **(urlize_params or {}))
        return url

    rendered = []
    for text, handler in chunks:
        if handler is not None:
            text = url_re.sub(lambda m: render(m.group(), handler), text)
        rendered.append(text)
    return rendered
