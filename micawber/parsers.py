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


def _safe_url(candidate, fallback):
    # Replace any non-http(s) scheme (e.g. javascript:).
    if scheme_re.match(candidate) and not http_scheme_re.match(candidate):
        return fallback
    return candidate

def _escape_data(url, response_data):
    # The url and title in a provider response frequently contain end-user
    # content (e.g. video titles) and cannot be trusted in html.
    return {
        'url': escape(_safe_url(str(response_data['url']), url)),
        'title': escape(str(response_data['title']))}

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
    return ('<a href="%(url)s" title="%(title)s">%(title)s</a>' %
            _escape_data(url, response_data))

def inline_handler(url, response_data, **params):
    return ('<a href="%(url)s" title="%(title)s">%(title)s</a>' %
            _escape_data(url, response_data))

def urlize(url, **params):
    params.setdefault('href', url)
    param_html = ' '.join('%s="%s"' % (key, escape(str(value)))
                          for key, value in sorted(params.items()))
    return '<a %s>%s</a>' % (param_html, escape(url))

def _extract_all(texts, providers, **params):
    urls = []
    for text in texts:
        urls.extend(url_re.findall(text))
    urls = list(dict.fromkeys(urls))
    return urls, providers.request_many(urls, **params)

def extract(text, providers, **params):
    return _extract_all([text], providers, **params)

def _render(text, urls, extracted, urlize_all, handler, urlize_params,
            **params):
    replacements = {}
    for url in urls:
        if url in extracted:
            replacements[url] = handler(url, extracted[url], **params)
        elif urlize_all:
            replacements[url] = urlize(url, **urlize_params)
    return url_re.sub(lambda m: replacements.get(m.group(), m.group()), text)

def parse_text_full(text, providers, urlize_all=True, handler=full_handler,
                    urlize_params=None, **params):
    urls, extracted = extract(text, providers, **params)
    return _render(text, urls, extracted, urlize_all, handler,
                   urlize_params or {}, **params)

def parse_text(text, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, urlize_params=None, **params):
    urlize_params = urlize_params or {}
    lines = text.splitlines()
    if block_handler is None:
        wanted = [line for line in lines if standalone_url_re.match(line)]
    else:
        wanted = lines
    _urls, extracted = _extract_all(wanted, providers, **params)

    parsed = []
    for line in lines:
        if standalone_url_re.match(line):
            url = line.strip()
            if url in extracted:
                line = handler(url, extracted[url], **params)
            elif urlize_all:
                line = urlize(url, **urlize_params)
        elif block_handler is not None:
            line = _render(line, url_re.findall(line), extracted, urlize_all,
                           block_handler, urlize_params, **params)
        parsed.append(line)

    return '\n'.join(parsed)

def parse_html(html, providers, urlize_all=True, handler=full_handler,
               block_handler=inline_handler, soup_class=BeautifulSoup,
               urlize_params=None, **params):

    if soup_class is None:
        raise Exception('Unable to parse HTML, please install beautifulsoup4 '
                        'or use the text parser')

    urlize_params = urlize_params or {}
    soup = soup_class(html, **bs_kwargs)
    nodes = [node for node in soup.find_all(string=url_re)
             if not _inside_skip(node)]
    texts = [node.string.replace('<', '&lt;').replace('>', '&gt;')
             for node in nodes]
    _urls, extracted = _extract_all(texts, providers, **params)

    for node, text in zip(nodes, texts):
        url_handler = handler if _is_standalone(node) else block_handler
        replacement = _render(text, url_re.findall(text), extracted,
                              urlize_all, url_handler, urlize_params,
                              **params)
        node.replace_with(soup_class(replacement, **replace_kwargs))

    return str(soup)

def extract_html(html, providers, soup_class=BeautifulSoup, **params):
    if soup_class is None:
        raise Exception('Unable to parse HTML, please install beautifulsoup4 '
                        'or use the text parser')

    soup = soup_class(html, **bs_kwargs)
    nodes = [node for node in soup.find_all(string=url_re)
             if not _inside_skip(node)]
    return _extract_all([str(node) for node in nodes], providers, **params)

def _is_standalone(soup_elem):
    if standalone_url_re.match(soup_elem):
        return soup_elem.parent.name in block_elements
    return False

def _inside_skip(soup_elem):
    if Comment is not None and isinstance(soup_elem, Comment):
        return True
    parent = soup_elem.parent
    while parent is not None:
        if parent.name in skip_elements:
            return True
        parent = parent.parent
    return False
