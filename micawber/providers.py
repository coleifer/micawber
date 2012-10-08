import hashlib
import pickle
import re
import socket
import urllib2
import sys
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
    pr.register('http://\S*?flickr.com/\S*', Provider('http://www.flickr.com/services/oembed/'))
    pr.register('https?://(\S*.)?youtu(\.be/|be\.com/watch)\S*', Provider('http://www.youtube.com/oembed'))
    pr.register('http://\S*.viddler.com/\S*', Provider('http://lab.viddler.com/services/oembed/'))
    pr.register('http://qik.com/video/\S*', Provider('http://qik.com/api/oembed.json'))
    pr.register('http://\S*.revision3.com/\S*', Provider('http://revision3.com/api/oembed/'))
    pr.register('http://www.hulu.com/watch/\S*', Provider('http://www.hulu.com/api/oembed.json'))
    pr.register('http://vimeo.com/\S*', Provider('http://vimeo.com/api/oembed.json'))
    pr.register('http://www.polleverywhere.com/(polls|multiple_choice_polls|free_text_polls)/\S*', Provider('http://www.polleverywhere.com/services/oembed/'))
    pr.register('http://www.ifixit.com/Guide/View/\S*', Provider('http://www.ifixit.com/Embed'))
    pr.register('http://\S*.smugmug.com/\S*', Provider('http://api.smugmug.com/services/oembed/'))
    pr.register('http://\S+.wordpress.com/\S+', Provider('http://public-api.wordpress.com/oembed/'))
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
            pr.register(regex, Provider(endpoint, **params))
    return pr
