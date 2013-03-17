import hashlib
import pickle
import re
import socket
import urllib2
from urllib import urlencode
try:
    import simplejson as json
except ImportError:
    import json

from micawber.exceptions import ProviderException, ProviderNotFoundException


class Provider(object):
    socket_timeout = 3.0
    user_agent = 'python-micawber'

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.base_params = {'format': 'json'}
        self.base_params.update(kwargs)

    def fetch(self, url):
        socket.setdefaulttimeout(self.socket_timeout)
        req = urllib2.Request(url, headers={'User-Agent': self.user_agent})
        try:
            resp = urllib2.urlopen(req)
        except urllib2.URLError:
            return False
        except urllib2.HTTPError:
            return False
        except socket.timeout:
            return False

        if resp.code < 200 or resp.code >= 300:
            return False

        content = resp.read()
        resp.close()
        return content

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
        json_data = json.loads(response)
        if 'url' not in json_data:
            json_data['url'] = url
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


class ProviderRegistry(object):
    def __init__(self, cache=None):
        self._registry = {}
        self.cache = cache

    def register(self, regex, provider):
        self._registry[regex] = provider

    def unregister(self, regex):
        del(self._registry[regex])

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
        raise ProviderNotFoundException('Provider not found for "%s"' % url)


def bootstrap_basic(cache=None):
    # complements of oembed.com#section7
    pr = ProviderRegistry(cache)

    # b
    pr.register('http://blip.tv/\S+', Provider('http://blip.tv/oembed'))

    # c
    pr.register('http://chirb.it/\S+', Provider('http://chirb.it/oembed.json'))
    pr.register('https://www.circuitlab.com/circuit/\S+', Provider('https://www.circuitlab.com/circuit/oembed'))
    pr.register('http://www.collegehumor.com/video/\S+', Provider('http://www.collegehumor.com/oembed.json'))

    # d
    pr.register('https?://(www\.)?dailymotion\.com/\S+', Provider('http://www.dailymotion.com/services/oembed'))

    # f
    pr.register('http://\S*?flickr.com/\S+', Provider('http://www.flickr.com/services/oembed/'))
    pr.register('http://flic\.kr/\S*', Provider('http://www.flickr.com/services/oembed/'))
    pr.register('https?://(www\.)?funnyordie\.com/videos/\S+', Provider('http://www.funnyordie.com/oembed'))

    # g
    pr.register(r'https?://gist.github.com/\S*', Provider('https://github.com/api/oembed'))

    # h
    pr.register('http://www.hulu.com/watch/\S+', Provider('http://www.hulu.com/api/oembed.json'))

    # i
    pr.register('http://www.ifixit.com/Guide/View/\S+', Provider('http://www.ifixit.com/Embed'))
    pr.register('http://\S*imgur\.com/\S+', Provider('http://api.imgur.com/oembed')),
    pr.register('http://instagr(\.am|am\.com)/p/\S+', Provider('http://api.instagram.com/oembed'))

    # j
    pr.register('http://www.jest.com/(video|embed)/\S+', Provider('http://www.jest.com/oembed.json'))

    # m
    pr.register('http://www.mobypicture.com/user/\S*?/view/\S*', Provider('http://api.mobypicture.com/oEmbed'))
    pr.register('http://moby.to/\S*', Provider('http://api.mobypicture.com/oEmbed'))

    # p
    pr.register('http://i\S*.photobucket.com/albums/\S+', Provider('http://photobucket.com/oembed'))
    pr.register('http://gi\S*.photobucket.com/groups/\S+', Provider('http://photobucket.com/oembed'))
    pr.register('http://www.polleverywhere.com/(polls|multiple_choice_polls|free_text_polls)/\S+', Provider('http://www.polleverywhere.com/services/oembed/'))
    pr.register('https?://(.+\.)?polldaddy\.com/\S*', Provider('http://polldaddy.com/oembed/'))

    # q
    pr.register('http://qik.com/video/\S+', Provider('http://qik.com/api/oembed.json'))

    # r
    pr.register('http://\S*.revision3.com/\S+', Provider('http://revision3.com/api/oembed/'))

    # s
    pr.register('http://www.slideshare.net/[^\/]+/\S+', Provider('http://www.slideshare.net/api/oembed/2'))
    pr.register('http://slidesha\.re/\S*', Provider('http://www.slideshare.net/api/oembed/2'))
    pr.register('http://\S*.smugmug.com/\S*', Provider('http://api.smugmug.com/services/oembed/'))
    pr.register('https://\S*?soundcloud.com/\S+', Provider('http://soundcloud.com/oembed'))
    pr.register('https?://speakerdeck\.com/\S*', Provider('https://speakerdeck.com/oembed.json')),
    pr.register('https?://(www\.)?scribd\.com/\S*', Provider('http://www.scribd.com/services/oembed'))

    # t
    pr.register('https?://(www\.)?twitter.com/\S+/status(es)?/\S+', Provider('http://api.twitter.com/1/statuses/oembed.json'))

    # v
    pr.register('http://\S*.viddler.com/\S*', Provider('http://lab.viddler.com/services/oembed/'))
    pr.register('http://vimeo.com/\S+', Provider('http://vimeo.com/api/oembed.json'))
    pr.register('https://vimeo.com/\S+', Provider('https://vimeo.com/api/oembed.json'))

    # y
    pr.register('https?://(\S*.)?youtu(\.be/|be\.com/watch)\S+', Provider('http://www.youtube.com/oembed'))
    pr.register('http://(\S*\.)?yfrog\.com/\S*', Provider('http://www.yfrog.com/api/oembed'))

    # w
    pr.register('http://\S+.wordpress.com/\S+', Provider('http://public-api.wordpress.com/oembed/'))
    pr.register('https?://wordpress.tv/\S+', Provider('http://wordpress.tv/oembed/'))

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
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_noembed(cache=None, **params):
    endpoint = 'http://noembed.com/embed'
    schema_url = 'http://noembed.com/providers'

    pr = ProviderRegistry(cache)

    # fetch the schema
    resp = urllib2.urlopen(schema_url)
    contents = resp.read()
    resp.close()

    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['patterns']:
            pr.register(regex, Provider(endpoint, **params))
    return pr
