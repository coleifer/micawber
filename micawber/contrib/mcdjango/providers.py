from django.conf import settings
from django.core.cache import cache

from micawber.providers import bootstrap_basic as _bootstrap_basic, bootstrap_embedly as _bootstrap_embedly


def bootstrap_basic():
    return _bootstrap_basic(cache)

def bootstrap_embedly():
    key = getattr(settings, 'MICAWBER_EMBEDLY_KEY', None)
    params = {}
    if key:
        params['key'] = key
    return _bootstrap_embedly(cache, **params)
