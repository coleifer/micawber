import hashlib
import json
import logging
import os
import re
import time
import socket
import ssl

from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from micawber.exceptions import InvalidResponseException
from micawber.exceptions import ProviderException
from micawber.exceptions import ProviderHTTPException
from micawber.exceptions import ProviderNotFoundException
from micawber.exceptions import ProviderTimeoutException
from micawber.parsers import extract
from micawber.parsers import extract_html
from micawber.parsers import parse_html
from micawber.parsers import parse_text
from micawber.parsers import parse_text_full


logger = logging.getLogger('micawber')

DEFAULT_TIMEOUT = 3.0
NEGATIVE_TTL = 300
PROVIDERS_URL = 'https://oembed.com/providers.json'
PROVIDERS_FILE = os.path.join(os.path.dirname(__file__), 'providers.json')
MAX_RESPONSE_SIZE = 20 * 1024 * 1024


class Provider(object):
    def __init__(self, endpoint, timeout=DEFAULT_TIMEOUT, user_agent=None,
                 **kwargs):
        self.endpoint = endpoint
        self.socket_timeout = timeout
        self.user_agent = user_agent or 'python-micawber'
        self.base_params = {'format': 'json'}
        self.base_params.update(kwargs)

    def fetch(self, url):
        req = Request(url, headers={'User-Agent': self.user_agent})
        try:
            return fetch(req, self.socket_timeout)
        except HTTPError as exc:
            raise ProviderHTTPException(url, exc.code) from exc
        except (URLError, socket.timeout, ssl.SSLError,
                UnicodeDecodeError, LookupError) as exc:
            if isinstance(exc, socket.timeout) or \
               isinstance(getattr(exc, 'reason', None), socket.timeout):
                raise ProviderTimeoutException('Timed out fetching "%s"' % url) from exc
            raise ProviderException('Error fetching "%s"' % url) from exc

    def encode_params(self, url, **extra_params):
        params = dict(self.base_params)
        params.update(extra_params)
        if 'maxwidth' in params and not params.get('maxheight'):
            params['maxheight'] = int(params['maxwidth']) * 16 // 9
        params['url'] = url
        return urlencode(sorted(params.items()))

    def request(self, url, **extra_params):
        encoded_params = self.encode_params(url, **extra_params)

        endpoint_url = self.endpoint
        if '?' in endpoint_url:
            endpoint_url = '%s&%s' % (endpoint_url.rstrip('&'), encoded_params)
        else:
            endpoint_url = '%s?%s' % (endpoint_url, encoded_params)

        return self.handle_response(self.fetch(endpoint_url), url)

    def handle_response(self, response, url):
        try:
            json_data = json.loads(response)
        except ValueError as exc:
            raise InvalidResponseException(str(exc)) from exc

        # oEmbed responses must be JSON objects.
        if not isinstance(json_data, dict):
            raise InvalidResponseException('Response is not a JSON object')

        if 'url' not in json_data:
            json_data['url'] = url
        if 'title' not in json_data:
            json_data['title'] = json_data['url']
        if 'type' not in json_data:
            json_data['type'] = 'link'

        return json_data


def make_key(*args, **kwargs):
    data = json.dumps(
        (args, kwargs),
        sort_keys=True,
        separators=(',', ':'),
        default=str)
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def fetch(request, timeout=DEFAULT_TIMEOUT, max_bytes=MAX_RESPONSE_SIZE):
    with urlopen(request, timeout=timeout) as resp:
        charset = resp.headers.get_param('charset') or 'utf-8'
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ProviderException('Response larger than %d bytes' % max_bytes)
    return data.decode(charset)


def fetch_cache(cache, url, refresh=False, timeout=DEFAULT_TIMEOUT,
                max_bytes=MAX_RESPONSE_SIZE):
    contents = None
    if cache is not None and not refresh:
        contents = cache.get('micawber.%s' % url)
    if contents is None:
        contents = fetch(url, timeout=timeout, max_bytes=max_bytes)
        if cache is not None:
            cache.set('micawber.%s' % url, contents)
    return contents


class ProviderRegistry(object):
    def __init__(self, cache=None, max_workers=None, negative_ttl=NEGATIVE_TTL):
        self._registry = {}
        self.cache = cache
        self.max_workers = max_workers
        self.negative_ttl = negative_ttl

    def register(self, regex, provider, skip_invalid=False):
        try:
            pattern = re.compile(regex)
        except re.error as exc:
            if not skip_invalid:
                raise
            logger.warning('Skipping unusable provider pattern %r: %s',
                           regex, exc)
            return
        if regex in self._registry:
            logger.debug('Replacing provider registered for %r', regex)
        self._registry[regex] = (pattern, provider)

    def unregister(self, regex):
        del self._registry[regex]

    def __iter__(self):
        return iter(reversed(list(self._registry.values())))

    def provider_for_url(self, url):
        for pattern, provider in self:
            if pattern.match(url):
                return provider

    def request(self, url, **params):
        provider = self.provider_for_url(url)
        if provider is None:
            raise ProviderNotFoundException('Provider not found for "%s"' % url)
        if self.cache is None:
            return provider.request(url, **params)
        key = make_key(url, params)
        data = self.cache.get(key)
        if isinstance(data, float):
            if time.time() - data < self.negative_ttl:
                raise ProviderException('Recent failure fetching "%s"' % url)
            data = None
        if data is None:
            try:
                data = provider.request(url, **params)
            except ProviderException:
                if self.negative_ttl:
                    self.cache.set(key, time.time())
                raise
            self.cache.set(key, data)
        return data

    def request_many(self, urls, **params):
        def attempt(url):
            try:
                return url, self.request(url, **params)
            except ProviderException:
                return url, None

        urls = list(dict.fromkeys(urls))
        if self.max_workers:
            with ThreadPoolExecutor(self.max_workers) as pool:
                results = list(pool.map(attempt, urls))
        else:
            results = [attempt(url) for url in urls]
        return {url: data for url, data in results if data is not None}

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


youtube_re = r'https?://(?:\S*\.)?youtu(?:\.be/|be\.com/(?:watch|shorts/|live/|playlist))\S+'

def bootstrap_basic(cache=None, registry=None, max_workers=None):
    pr = registry or ProviderRegistry(cache, max_workers=max_workers)
    providers = (
        (r'https://podcasts\.apple\.com/\S+', 'https://podcasts.apple.com/api/oembed'),
        (r'https://music\.apple\.com/\S+', 'https://music.apple.com/api/oembed'),
        (r'https://bsky\.app/profile/\S+/post/\S+', 'https://embed.bsky.app/oembed'),
        (r'https?://(?:www\.)?dailymotion\.com/video/\S+', 'https://www.dailymotion.com/services/oembed'),
        (r'https://www\.facebook\.com/\S+', 'https://graph.facebook.com/v16.0/oembed_page'),
        (r'https://www\.facebook\.com/\S+/(?:posts|activity|photos)/\S+', 'https://graph.facebook.com/v16.0/oembed_post'),
        (r'https://www\.facebook\.com/(?:photo|permalink)\.php\?\S+', 'https://graph.facebook.com/v16.0/oembed_post'),
        (r'https://www\.facebook\.com/\S+/videos/\S+', 'https://graph.facebook.com/v16.0/oembed_video'),
        (r'https://www\.facebook\.com/video\.php\?\S+', 'https://graph.facebook.com/v16.0/oembed_video'),
        (r'https?://\S*?flickr\.com/\S+', 'https://www.flickr.com/services/oembed/'),
        (r'https?://flic\.kr/\S+', 'https://www.flickr.com/services/oembed/'),
        (r'https?://(?:www\.)?giphy\.com/(?:gifs|clips)/\S+', 'https://giphy.com/services/oembed'),
        (r'https?://gph\.is/\S+', 'https://giphy.com/services/oembed'),
        (r'https?://(?:www\.)?instagr(?:\.am|am\.com)/(?:\S+/)?(?:p|reel|tv)/\S+', 'https://graph.facebook.com/v16.0/instagram_oembed'),
        (r'https?://(?:www\.)?pinterest\.com/pin/\S+', 'https://www.pinterest.com/oembed.json'),
        (r'https?://(?:www\.)?reddit\.com/r/\S+/comments/\S+', 'https://www.reddit.com/oembed'),
        (r'https?://\S*?soundcloud\.com/\S+', 'https://soundcloud.com/oembed'),
        (r'https://open\.spotify\.com/\S+', 'https://open.spotify.com/oembed'),
        (r'https://spotify\.link/\S+', 'https://open.spotify.com/oembed'),
        (r'https?://(?:www\.)?tiktok\.com/\S+', 'https://www.tiktok.com/oembed'),
        (r'https?://\S+\.tumblr\.com/post/\S+', 'https://www.tumblr.com/oembed/1.0'),
        (r'https?://(?:www\.)?(?:twitter|x)\.com/\S+/status(?:es)?/\S+', 'https://publish.x.com/oembed'),
        (r'https?://(?:player\.)?vimeo\.com/\S+', 'https://vimeo.com/api/oembed.json'),
        (youtube_re, 'https://www.youtube.com/oembed'),
    )
    for regex, endpoint in providers:
        pr.register(regex, Provider(endpoint))

    # wordpress.com requires identifying yourself via the "for" parameter.
    pr.register(r'https?://(?:\S+\.)?wordpress\.com/\S+', Provider('https://public-api.wordpress.com/oembed/', **{'for': 'micawber'}))

    return pr


def bootstrap_embedly(cache=None, registry=None, refresh=False,
                      timeout=DEFAULT_TIMEOUT, max_workers=None, **params):
    endpoint = 'https://api.embed.ly/1/oembed'
    schema_url = 'https://api.embed.ly/1/services/python'

    pr = registry or ProviderRegistry(cache, max_workers=max_workers)

    # fetch the schema
    contents = fetch_cache(cache, schema_url, refresh=refresh, timeout=timeout)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['regex']:
            pr.register(regex, Provider(endpoint, timeout=timeout, **params),
                        skip_invalid=True)
    return pr


def bootstrap_noembed(cache=None, registry=None, refresh=False,
                      timeout=DEFAULT_TIMEOUT, max_workers=None, **params):
    endpoint = 'https://noembed.com/embed'
    schema_url = 'https://noembed.com/providers'

    pr = registry or ProviderRegistry(cache, max_workers=max_workers)

    # fetch the schema
    contents = fetch_cache(cache, schema_url, refresh=refresh, timeout=timeout)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['patterns']:
            pr.register(regex, Provider(endpoint, timeout=timeout, **params),
                        skip_invalid=True)
    return pr


def bootstrap_iframely(cache=None, registry=None, max_workers=None, **params):
    # Iframely requires authentication, either an "api_key" parameter or a
    # "key" parameter containing the md5 hexdigest of the api key.
    if not params.get('api_key') and not params.get('key'):
        raise ValueError('bootstrap_iframely() requires an "api_key" (or '
                         'md5-hashed "key") parameter.')

    pr = registry or ProviderRegistry(cache, max_workers=max_workers)

    # Iframely recommends sending all urls to the API rather than matching
    # against a list of supported providers, so register a catch-all pattern.
    pr.register(r'https?://\S+', Provider('https://iframe.ly/api/oembed',
                                          **params))
    return pr


def bootstrap_oembed(cache=None, registry=None, refresh=False,
                     timeout=DEFAULT_TIMEOUT, providers_file=None,
                     max_workers=None, **params):
    pr = registry or ProviderRegistry(cache, max_workers=max_workers)

    if refresh:
        contents = fetch_cache(cache, PROVIDERS_URL, refresh=True,
                               timeout=timeout)
    else:
        with open(providers_file or PROVIDERS_FILE) as fh:
            contents = fh.read()
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

            provider = Provider(url, timeout=timeout, **params)
            for scheme in endpoint['schemes']:
                # Transform the raw scheme into a regex. Everything is escaped
                # as a literal (dots, question-marks, etc.) except the "*"
                # wildcards.
                #
                # An interior wildcard matches one or more of any character
                # that is not a slash, whitespace, or a querystring separator.
                # A trailing wildcard takes the rest of the url instead.
                pattern = re.escape(scheme)
                if pattern.endswith(r'\*'):
                    pattern = pattern[:-2] + r'\S*'
                pattern = pattern.replace(r'\*', r'[^\/\s\?&]+?')
                pr.register(pattern, provider)

    # oembed.com's YouTube schemes are all "https://*.youtube.com/...", which
    # require a subdomain, and it publishes no http:// schemes at all. Keep our
    # own pattern to cover bare youtube.com and http urls.
    pr.register(youtube_re, Provider('https://www.youtube.com/oembed',
                                     timeout=timeout, **params))

    return pr


def refresh_providers(path=PROVIDERS_FILE):
    contents = fetch(PROVIDERS_URL)
    if not isinstance(json.loads(contents), list):
        raise InvalidResponseException('Provider list is not a JSON array')
    with open(path, 'w') as fh:
        fh.write(contents)
    return path
