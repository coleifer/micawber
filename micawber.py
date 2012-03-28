from __future__ import with_statement
import hashlib
import os
import pickle
import re
import socket
import urllib2
from contextlib import closing
from urllib import urlencode
try:
    import simplejson as json
except ImportError:
    import json
try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    BeautifulSoup = None

__ALL__ = [
    'Cache', 'PickleCache', 'ProviderException', 'Provider', 'ProviderRegistry',
    'extract', 'extract_html', 'parse_text', 'parse_text_full', 'parse_html',
    'bootstrap_basic', 'bootstrap_embedly', 'make_key',
]


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


class ProviderException(Exception):
    pass


class Provider(object):
    socket_timeout = 3.0
    user_agent = 'python-micawber'

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.base_params = {'format': 'json'}
        self.base_params.update(kwargs)

    def fetch(self, url):
        req = urllib2.Request(url, headers={'User-Agent': self.user_agent})
        try:
            resp = urllib2.urlopen(req, timeout=self.socket_timeout)
        except urllib2.URLError:
            return False

        if resp.getcode() < 200 or resp.getcode() >= 300:
            return False

        content = resp.read()
        resp.close()
        return content

    def request(self, url, **extra_params):
        params = dict(self.base_params)
        params.update(extra_params)
        params['url'] = url
        encoded_params = urlencode(sorted(params.items()))

        endpoint_url = self.endpoint
        if '?' in endpoint_url:
            endpoint_url = '%s&%s' % (endpoint_url.rstrip('&'), encoded_params)
        else:
            endpoint_url = '%s?%s' % (endpoint_url, encoded_params)

        response = self.fetch(endpoint_url)
        if response:
            json_data = json.loads(response)
            if 'url' not in json_data:
                json_data['url'] = url
            return json_data
        else:
            raise ProviderException('Error fetching "%s"' % endpoint_url)


def make_key(*args, **kwargs):
    return hashlib.md5(pickle.dumps((args, kwargs))).hexdigest()

def url_cache(fn):
    def inner(self, url, **params):
        if self.cache:
            key = make_key(url, params)
            data = self.cache.get(key)
            if not data:
                data = fn(self, url, **params)
                self.cache.set(key, data)
            return data
        return fn(self, url, **params)
    return inner

class ProviderRegistry(object):
    def __init__(self, cache=None):
        self._registry = {}
        self.cache = cache

    def register(self, regex, provider):
        self._registry[regex] = provider

    def unregister(self, regex):
        del(self._registry[index])

    def __iter__(self):
        return iter(self._registry.items())

    def provider_for_url(self, url):
        for regex, provider in self:
            if re.match(regex, url):
                return provider

    @url_cache
    def request(self, url, **params):
        provider = self.provider_for_url(url)
        if provider:
            return provider.request(url, **params)
        raise ProviderException('Provider not found for "%s"' % url)


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
    all_urls = set(re.findall(url_re, text))
    extracted_urls = {}

    for url in all_urls:
        try:
            extracted_urls[url] = providers.request(url, **params)
        except ProviderException:
            pass

    return all_urls, extracted_urls

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
        for j in xrange(indx + 1, len(matches)):
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

    soup = BeautifulSoup(html)

    for url in soup.findAll(text=re.compile(url_re)):
        if not _inside_a(url):
            if _is_standalone(url):
                url_handler = handler
            else:
                url_handler = inline_handler

            replacement = parse_text_full(str(url), providers, urlize_all, url_handler, **params)
            url.replaceWith(BeautifulSoup(replacement))

    return unicode(soup)

def extract_html(html, providers, **params):
    if not BeautifulSoup:
        raise Exception('Unable to parse HTML, please install BeautifulSoup or use the text parser')

    soup = BeautifulSoup(html)
    all_urls = set()
    extracted_urls = {}

    for url in soup.findAll(text=re.compile(url_re)):
        if not _inside_a(url):
            block_all, block_ext = extract(unicode(url), providers, **params)
            all_urls.update(block_all)
            extracted_urls.update(block_ext)

    return all_urls, extracted_urls

def _is_standalone(soup_elem):
    if standalone_url_re.match(soup_elem):
        return soup_elem.parent.name in block_elements
    return False

def _inside_a(soup_elem):
    parent = soup_elem.parent
    while parent is not None:
        if parent.name == 'a':
            return True
        parent = parent.parent
    return False


def bootstrap_basic(cache=None):
    pr = ProviderRegistry(cache)
    pr.register('http://\S*?flickr.com/\S*', Provider('http://www.flickr.com/services/oembed/'))
    pr.register('http://\S*.youtu(\.be|be\.com)/watch\S*', Provider('http://www.youtube.com/oembed'))
    pr.register('http://www.hulu.com/watch/\S*', Provider('http://www.hulu.com/api/oembed.json'))
    pr.register('http://vimeo.com/\S*', Provider('http://vimeo.com/api/oembed.json'))
    pr.register('http://www.slideshare.net/[^\/]+/\S*', Provider('http://www.slideshare.net/api/oembed/2'))
    return pr

def bootstrap_embedly(cache=None, **params):
    endpoint = 'http://api.embed.ly/1/oembed'
    schema_url = 'http://api.embed.ly/1/services/python'

    pr = ProviderRegistry(cache)

    # fetch the schema
    resp = urllib2.urlopen(schema_url)
    contents = resp.read()
    resp.close()

    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['regex']:
            pr.register(regex, Provider(endpoint))
    return pr
