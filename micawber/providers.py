import hashlib
import json
import logging
import re
import socket
import ssl

from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from micawber.exceptions import InvalidResponseException
from micawber.exceptions import ProviderException
from micawber.exceptions import ProviderNotFoundException
from micawber.parsers import extract
from micawber.parsers import extract_html
from micawber.parsers import parse_html
from micawber.parsers import parse_text
from micawber.parsers import parse_text_full


logger = logging.getLogger(__name__)


class Provider(object):
    def __init__(self, endpoint, timeout=3.0, user_agent=None, **kwargs):
        self.endpoint = endpoint
        self.socket_timeout = timeout
        self.user_agent = user_agent or 'python-micawber'
        self.base_params = {'format': 'json'}
        self.base_params.update(kwargs)

    def fetch(self, url):
        req = Request(url, headers={'User-Agent': self.user_agent})
        try:
            return fetch(req, self.socket_timeout)
        except (HTTPError, URLError, socket.timeout, ssl.SSLError) as exc:
            raise ProviderException('Error fetching "%s"' % url) from exc

    def encode_params(self, url, **extra_params):
        params = dict(self.base_params)
        params.update(extra_params)
        params['url'] = url
        return urlencode(sorted(params.items()))

    def request(self, url, **extra_params):
        encoded_params = self.encode_params(url, **extra_params)

        endpoint_url = self.endpoint
        if '?' in endpoint_url:
            endpoint_url = '%s&%s' % (endpoint_url.rstrip('&'), encoded_params)
        else:
            endpoint_url = '%s?%s' % (endpoint_url, encoded_params)

        response = self.fetch(endpoint_url)
        if response:
            return self.handle_response(response, url)
        else:
            raise ProviderException('Error fetching "%s"' % endpoint_url)

    def handle_response(self, response, url):
        try:
            json_data = json.loads(response)
        except ValueError as exc:
            try:
                msg = exc.message
            except AttributeError:
                msg = exc.args[0]
            raise InvalidResponseException(msg)

        if 'url' not in json_data:
            json_data['url'] = url
        if 'title' not in json_data:
            json_data['title'] = json_data['url']

        return json_data


def make_key(*args, **kwargs):
    # Serialized with json rather than pickle so that keys are stable across
    # python versions and parameter ordering. Values json cannot represent
    # fall back to their string form -- the same form urlencode gives them in
    # the actual request.
    data = json.dumps((args, kwargs), sort_keys=True, separators=(',', ':'),
                      default=str)
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def url_cache(fn):
    def inner(self, url, **params):
        if self.cache is not None:
            key = make_key(url, params)
            data = self.cache.get(key)
            if data is None:
                data = fn(self, url, **params)
                self.cache.set(key, data)
            return data
        return fn(self, url, **params)
    return inner


def fetch(request, timeout=None):
    urlopen_params = {}
    if timeout:
        urlopen_params['timeout'] = timeout
    resp = urlopen(request, **urlopen_params)
    if resp.code < 200 or resp.code >= 300:
        return False

    # oEmbed responses are JSON, for which the default charset is UTF-8
    # (RFC 8259) -- many providers omit the charset parameter entirely.
    charset = resp.headers.get_param('charset') or 'utf-8'

    content = resp.read().decode(charset)
    resp.close()
    return content


def fetch_cache(cache, url, refresh=False, timeout=None):
    contents = None
    if cache is not None and not refresh:
        contents = cache.get('micawber.%s' % url)
    if contents is None:
        contents = fetch(url, timeout=timeout)
        if cache is not None:
            cache.set('micawber.%s' % url, contents)
    return contents


class ProviderRegistry(object):
    def __init__(self, cache=None):
        self._registry = {}
        self.cache = cache

    def register(self, regex, provider):
        self._registry[regex] = provider

    def unregister(self, regex):
        del self._registry[regex]

    def __iter__(self):
        return iter(reversed(list(self._registry.items())))

    def provider_for_url(self, url):
        for regex, provider in self:
            if re.match(regex, url):
                return provider

    @url_cache
    def request(self, url, **params):
        provider = self.provider_for_url(url)
        if provider:
            return provider.request(url, **params)
        raise ProviderNotFoundException('Provider not found for "%s"' % url)

    def parse_text(self, text, **kwargs):
        return parse_text(text, self, **kwargs)

    def parse_text_full(self, text, **kwargs):
        return parse_text_full(text, self, **kwargs)

    def parse_html(self, html, **kwargs):
        return parse_html(html, self, **kwargs)

    def extract(self, text, **kwargs):
        return extract(text, self, **kwargs)

    def extract_html(self, html, **kwargs):
        return extract_html(html, self, **kwargs)


youtube_re = r'https?://(?:\S*\.)?youtu(?:\.be/|be\.com/(?:watch|shorts/))\S+'

def bootstrap_basic(cache=None, registry=None):
    # complements of oembed.com#section7
    pr = registry or ProviderRegistry(cache)

    # a
    pr.register(r'https://podcasts\.apple\.com/\S+', Provider('https://podcasts.apple.com/api/oembed'))

    # c
    pr.register(r'https?://www\.circuitlab\.com/circuit/\S+', Provider('https://www.circuitlab.com/circuit/oembed/'))

    # d
    pr.register(r'https?://(?:www\.)?dailymotion\.com/\S+', Provider('https://www.dailymotion.com/services/oembed'))

    # f
    pr.register(r'https?://\S*?flickr\.com/\S+', Provider('https://www.flickr.com/services/oembed/'))
    pr.register(r'https?://flic\.kr/\S*', Provider('https://www.flickr.com/services/oembed/'))

    # p
    pr.register(r'https?://(?:www\.)?polleverywhere\.com/(polls|multiple_choice_polls|free_text_polls)/\S+', Provider('https://www.polleverywhere.com/services/oembed/'))

    # s
    pr.register(r'https?://(?:www\.)?slideshare\.net/[^\/]+/\S+', Provider('https://www.slideshare.net/api/oembed/2'))
    pr.register(r'https?://slidesha\.re/\S*', Provider('https://www.slideshare.net/api/oembed/2'))
    pr.register(r'https?://\S*?soundcloud\.com/\S+', Provider('https://soundcloud.com/oembed'))
    pr.register(r'https?://speakerdeck\.com/\S*', Provider('https://speakerdeck.com/oembed.json'))
    pr.register(r'https?://(?:www\.)?scribd\.com/\S*', Provider('https://www.scribd.com/services/oembed'))

    # t
    pr.register(r'https?://(?:www\.)?tiktok\.com/\S+', Provider('https://www.tiktok.com/oembed'))
    pr.register(r'https?://(?:www\.)?(?:twitter|x)\.com/\S+/status(?:es)?/\S+', Provider('https://publish.x.com/oembed'))

    # v
    pr.register(r'https?://(?:player\.)?vimeo\.com/\S+', Provider('https://vimeo.com/api/oembed.json'))

    # w
    # wordpress.com requires identifying yourself via the "for" parameter.
    pr.register(r'https?://\S+\.wordpress\.com/\S+', Provider('https://public-api.wordpress.com/oembed/', **{'for': 'micawber'}))
    pr.register(r'https?://wordpress\.tv/\S+', Provider('https://wordpress.tv/oembed/'))

    # y
    pr.register(youtube_re, Provider('https://www.youtube.com/oembed'))

    return pr


def bootstrap_embedly(cache=None, registry=None, refresh=False, **params):
    endpoint = 'http://api.embed.ly/1/oembed'
    schema_url = 'http://api.embed.ly/1/services/python'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch_cache(cache, schema_url, refresh=refresh)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['regex']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_noembed(cache=None, registry=None, refresh=False, **params):
    endpoint = 'http://noembed.com/embed'
    schema_url = 'http://noembed.com/providers'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch_cache(cache, schema_url, refresh=refresh)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['patterns']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_oembed(cache=None, registry=None, refresh=False, **params):
    schema_url = 'https://oembed.com/providers.json'
    pr = registry or ProviderRegistry(cache)

    # Fetch schema.
    contents = fetch_cache(cache, schema_url, refresh=refresh)
    json_data = json.loads(contents)

    for item in json_data:
        for endpoint in reversed(item['endpoints']):
            # Possibly this provider only supports discovery via <link> tags,
            # which is not supported by micawber.
            if 'schemes' not in endpoint:
                continue

            # Consists of one or more schemes, a destination URL and optionally
            # a format, e.g. "json".
            url = endpoint['url']
            if '{format}' in url:
                url = url.replace('{format}', 'json')

            provider = Provider(url, **params)
            for scheme in endpoint['schemes']:
                # If a question-mark is being used, it is for the query-string
                # and should be treated as a literal.
                scheme = scheme.replace('?', r'\?')

                # Transform the raw pattern into a reasonable regex. Match one
                # or more of any character that is not a slash, whitespace, or
                # a parameter used for separating querystring/url params.
                pattern = scheme.replace('*', r'[^\/\s\?&]+?')
                try:
                    re.compile(pattern)
                except re.error:
                    logger.exception('oembed.com provider %s regex could not '
                                     'be compiled: %s', url, pattern)
                    continue

                pr.register(pattern, provider)

    # Currently oembed.com does not provide patterns for YouTube, so we'll add
    # these ourselves.
    pr.register(youtube_re, Provider('https://www.youtube.com/oembed'))

    return pr
