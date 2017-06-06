import hashlib
import pickle
import re
import socket
import ssl
from .compat import get_charset
from .compat import HTTPError
from .compat import OrderedDict
from .compat import Request
from .compat import urlencode
from .compat import URLError
from .compat import urlopen
try:
    import simplejson as json
    try:
        InvalidJson = json.JSONDecodeError
    except AttributeError:
        InvalidJson = ValueError
except ImportError:
    import json
    InvalidJson = ValueError

from micawber.exceptions import InvalidResponseException
from micawber.exceptions import ProviderException
from micawber.exceptions import ProviderNotFoundException


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
            resp = fetch(req, self.socket_timeout)
        except URLError:
            return False
        except HTTPError:
            return False
        except socket.timeout:
            return False
        except ssl.SSLError:
            return False
        return resp

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
        except InvalidJson as exc:
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


def fetch(request, timeout=None):
    urlopen_params = {}
    if timeout:
        urlopen_params['timeout'] = timeout
    resp = urlopen(request, **urlopen_params)
    if resp.code < 200 or resp.code >= 300:
        return False

    # by RFC, default HTTP charset is ISO-8859-1
    charset = get_charset(resp) or 'iso-8859-1'

    content = resp.read().decode(charset)
    resp.close()
    return content


class ProviderRegistry(object):
    def __init__(self, cache=None):
        self._registry = OrderedDict()
        self._domains_registry = {}
        self.cache = cache

    def register(self, regex, provider, domains=None):
        self._registry[regex] = provider
        if domains:
            for domain in domains:
                if domain not in self._domains_registry:
                    self._domains_registry[domain] = {}
                self._domains_registry[domain][regex] = provider

    def unregister(self, regex, domains=None):
        del self._registry[regex]
        if domains:
            for domain in domains:
                if domain in self._domains_registry:
                    if regex in self._domains_registry[domain]:
                        del self._domains_registry[domain][regex]
                        if not self._domains_registry[domain]:
                            del self._domains_registry[domain]

    def __iter__(self):
        return iter(reversed(list(self._registry.items())))

    def provider_for_url(self, url, domain=None):
        if domain is not None:
            if domain in self._domains_registry:
                for regex, provider in self._domains_registry[domain].items():
                    if re.match(regex, url):
                        return provider
            return None
        for regex, provider in self:
            if re.match(regex, url):
                return provider

    @url_cache
    def request(self, url, **params):
        provider = self.provider_for_url(url)
        if provider:
            return provider.request(url, **params)
        raise ProviderNotFoundException('Provider not found for "%s"' % url)


def bootstrap_basic(cache=None, registry=None):
    # complements of oembed.com#section7
    pr = registry or ProviderRegistry(cache)

    # b
    pr.register('http://blip.tv/\S+', Provider('http://blip.tv/oembed'), domains=['blip.tv'])

    # c
    pr.register('http://chirb.it/\S+', Provider('http://chirb.it/oembed.json'), domains=['chirb.it'])
    pr.register('https://www.circuitlab.com/circuit/\S+', Provider('https://www.circuitlab.com/circuit/oembed'), domains=['circuitlab.com'])
    pr.register('http://www.collegehumor.com/video/\S+', Provider('http://www.collegehumor.com/oembed.json'), domains=['collegehumor.com'])

    # d
    pr.register('https?://(www\.)?dailymotion\.com/\S+', Provider('http://www.dailymotion.com/services/oembed'), domains=['dailymotion.com'])

    # f
    _p_flickr = Provider('https://www.flickr.com/services/oembed/')
    pr.register('https?://\S*?flickr.com/\S+', _p_flickr, domains=['flickr.com'])
    pr.register('https?://flic\.kr/\S*', _p_flickr, domains=['flic.kr'])
    pr.register('https?://(www\.)?funnyordie\.com/videos/\S+', Provider('http://www.funnyordie.com/oembed'), domains=['funnyordie.com'])

    # g
    pr.register(r'https?://gist.github.com/\S*', Provider('https://github.com/api/oembed'), domains=['gist.github.com'])

    # h
    pr.register('http://www.hulu.com/watch/\S+', Provider('http://www.hulu.com/api/oembed.json'), domains=['hulu.com'])

    # i
    pr.register('http://www.ifixit.com/Guide/View/\S+', Provider('http://www.ifixit.com/Embed'), domains=['ifixit.com'])
    pr.register('http://\S*imgur\.com/\S+', Provider('http://api.imgur.com/oembed'), domains=['imgur.com'])
    pr.register('https?://(www\.)?instagr(\.am|am\.com)/p/\S+', Provider('http://api.instagram.com/oembed'), domains=['instagr.am', 'instagram.com'])

    # j
    pr.register('http://www.jest.com/(video|embed)/\S+', Provider('http://www.jest.com/oembed.json'), domains=['jest.com'])

    # m
    _p_mobypicture = Provider('http://api.mobypicture.com/oEmbed')
    pr.register('http://www.mobypicture.com/user/\S*?/view/\S*', _p_mobypicture, domains=['mobypicture.com'])
    pr.register('http://moby.to/\S*', _p_mobypicture, domains=['moby.to'])

    # p
    _p_photobucket =Provider('http://photobucket.com/oembed')
    pr.register('http://i\S*.photobucket.com/albums/\S+', _p_photobucket, domains=['photobucket.com'])
    pr.register('http://gi\S*.photobucket.com/groups/\S+', _p_photobucket, domains=['photobucket.com'])
    pr.register('http://www.polleverywhere.com/(polls|multiple_choice_polls|free_text_polls)/\S+', Provider('http://www.polleverywhere.com/services/oembed/'), domains=['polleverywhere.com'])
    pr.register('https?://(.+\.)?polldaddy\.com/\S*', Provider('http://polldaddy.com/oembed/'), domains=['polldaddy.com'])

    # q
    pr.register('http://qik.com/video/\S+', Provider('http://qik.com/api/oembed.json'), domains=['qik.com'])

    # r
    pr.register('http://\S*.revision3.com/\S+', Provider('http://revision3.com/api/oembed/'), domains=['revision3.com'])

    # s
    _p_slideshare = Provider('http://www.slideshare.net/api/oembed/2')
    pr.register('https?://www.slideshare.net/[^\/]+/\S+', _p_slideshare, domains=['slideshare.net'])
    pr.register('https?://slidesha\.re/\S*', _p_slideshare, domains=['slidesha.re'])
    pr.register('http://\S*.smugmug.com/\S*', Provider('http://api.smugmug.com/services/oembed/'), domains=['smugmug.com'])
    pr.register('https://\S*?soundcloud.com/\S+', Provider('http://soundcloud.com/oembed'), domains=['soundcloud.com'])
    pr.register('https?://speakerdeck\.com/\S*', Provider('https://speakerdeck.com/oembed.json'), domains=['speakerdeck.com'])
    pr.register('https?://(www\.)?scribd\.com/\S*', Provider('http://www.scribd.com/services/oembed'), domains=['scribd.com'])

    # t
    pr.register('https?://(www\.)?twitter.com/\S+/status(es)?/\S+', Provider('https://api.twitter.com/1/statuses/oembed.json'), domains=['twitter.com'])

    # v
    _p_vimeo = Provider('http://vimeo.com/api/oembed.json')
    pr.register('http://\S*.viddler.com/\S*', Provider('http://lab.viddler.com/services/oembed/'), domains=['viddler.com'])
    pr.register('http://vimeo.com/\S+', _p_vimeo, domains=['vimeo.com'])
    pr.register('https://vimeo.com/\S+', _p_vimeo, domains=['vimeo.com'])

    # y
    pr.register('http://(\S*.)?youtu(\.be/|be\.com/watch)\S+', Provider('http://www.youtube.com/oembed'), domains=['youtu.be', 'youtube.com'])
    pr.register('https://(\S*.)?youtu(\.be/|be\.com/watch)\S+', Provider('http://www.youtube.com/oembed?scheme=https&'), domains=['youtu.be', 'youtube.com'])
    pr.register('http://(\S*\.)?yfrog\.com/\S*', Provider('http://www.yfrog.com/api/oembed'), domains=['yfrog.com'])

    # w
    pr.register('http://\S+.wordpress.com/\S+', Provider('http://public-api.wordpress.com/oembed/'), domains=['wordpress.com'])
    pr.register('https?://wordpress.tv/\S+', Provider('http://wordpress.tv/oembed/'), domains=['wordpress.tv'])

    return pr


def bootstrap_embedly(cache=None, registry=None, **params):
    endpoint = 'http://api.embed.ly/1/oembed'
    schema_url = 'http://api.embed.ly/1/services/python'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['regex']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_noembed(cache=None, registry=None, **params):
    endpoint = 'http://noembed.com/embed'
    schema_url = 'http://noembed.com/providers'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['patterns']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_oembedio(cache=None, registry=None, **params):
    endpoint = 'http://oembed.io/api'
    schema_url = 'http://oembed.io/providers'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        regex = provider_meta['s']
        if not regex.startswith('http'):
            regex = 'https?://(?:www\.)?' + regex
        pr.register(regex, Provider(endpoint, **params))
    return pr
