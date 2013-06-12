import re
from .compat import text_type
try:
    import simplejson as json
except ImportError:
    import json
try:
    from BeautifulSoup import BeautifulSoup
    bs_kwargs = {'convertEntities': BeautifulSoup.HTML_ENTITIES}
except ImportError:
    try:
        from bs4 import BeautifulSoup
        bs_kwargs = {} # BS4 converts entities by default
    except ImportError:
        BeautifulSoup = None

from micawber.exceptions import ProviderException


url_pattern = '(https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_|])'
url_re = re.compile(url_pattern)
standalone_url_re = re.compile('^\s*' + url_pattern + '\s*$')

block_elements = set([
    'address', 'blockquote', 'center', 'dir', 'div', 'dl', 'fieldset', 'form',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'isindex', 'menu', 'noframes',
    'noscript', 'ol', 'p', 'pre', 'table', 'ul', 'dd', 'dt', 'frameset', 'li',
    'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'button', 'del', 'iframe',
    'ins', 'map', 'object', 'script', '[document]'
])

skip_elements = set(['a', 'pre', 'code'])


def full_handler(url, response_data, **params):
    if response_data['type'] == 'link':
        return '<a href="%(url)s" title="%(title)s">%(title)s</a>' % response_data
    elif response_data['type'] == 'photo':
        return '<a href="%(url)s" title="%(title)s"><img alt="%(title)s" src="%(url)s" /></a>' % response_data
    else:
        return response_data['html']

def inline_handler(url, response_data, **params):
    return '<a href="%(url)s" title="%(title)s">%(title)s</a>' % response_data

def urlize(url):
    return '<a href="%s">%s</a>' % (url, url)

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

def parse_text_full(text, providers, urlize_all=True, handler=full_handler, **params):
    all_urls, extracted_urls = extract(text, providers, **params)
    replacements = {}

    for url in all_urls:
        if url in extracted_urls:
            replacements[url] = handler(url, extracted_urls[url], **params)
        elif urlize_all:
            replacements[url] = urlize(url)

    # go through the text recording URLs that can be replaced
    # taking note of their start & end indexes
    urls = re.finditer(url_re, text)
    matches = []
    for match in urls:
        if match.group() in replacements:
            matches.append([match.start(), match.end(), match.group()])

    # replace the URLs in order, offsetting the indices each go
    for indx, (start, end, url) in enumerate(matches):
        replacement = replacements[url]
        difference = len(replacement) - len(url)

        # insert the replacement between two slices of text surrounding the
        # original url
        text = text[:start] + replacement + text[end:]

        # iterate through the rest of the matches offsetting their indices
        # based on the difference between replacement/original
        for j in range(indx + 1, len(matches)):
            matches[j][0] += difference
            matches[j][1] += difference

    return text

def parse_text(text, providers, urlize_all=True, handler=full_handler, block_handler=inline_handler, **params):
    lines = text.splitlines()
    parsed = []

    for line in lines:
        if standalone_url_re.match(line):
            url = line.strip()
            try:
                response = providers.request(url, **params)
            except ProviderException:
                if urlize_all:
                    line = urlize(url)
            else:
                line = handler(url, response, **params)
        else:
            line = parse_text_full(line, providers, urlize_all, block_handler, **params)

        parsed.append(line)

    return '\n'.join(parsed)

def parse_html(html, providers, urlize_all=True, handler=full_handler, block_handler=inline_handler, **params):
    if not BeautifulSoup:
        raise Exception('Unable to parse HTML, please install BeautifulSoup or use the text parser')

    soup = BeautifulSoup(html, **bs_kwargs)

    for url in soup.findAll(text=re.compile(url_re)):
        if not _inside_skip(url):
            if _is_standalone(url):
                url_handler = handler
            else:
                url_handler = block_handler

            url_unescaped = url.string
            replacement = parse_text_full(url_unescaped, providers, urlize_all, url_handler, **params)
            url.replaceWith(BeautifulSoup(replacement))

    return text_type(soup)

def extract_html(html, providers, **params):
    if not BeautifulSoup:
        raise Exception('Unable to parse HTML, please install BeautifulSoup or use the text parser')

    soup = BeautifulSoup(html, **bs_kwargs)
    all_urls = set()
    urls = []
    extracted_urls = {}

    for url in soup.findAll(text=re.compile(url_re)):
        if _inside_skip(url):
            continue
    
        block_all, block_ext = extract(text_type(url), providers, **params)
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
    parent = soup_elem.parent
    while parent is not None:
        if parent.name in skip_elements:
            return True
        parent = parent.parent
    return False
