from django import template
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.safestring import mark_safe

from micawber.parsers import full_handler, inline_handler, parse_text, \
    parse_html, extract, extract_html


def _load_from_module(path):
    package, attr = path.rsplit('.', 1)
    module = import_module(package)
    return getattr(module, attr)


PROVIDERS = getattr(settings, 'MICAWBER_PROVIDERS', 'micawber.contrib.mcdjango.providers.bootstrap_basic')

providers = _load_from_module(PROVIDERS)
if callable(providers):
    providers = providers()


register = template.Library()


def extension(filter_name, providers=providers, urlize_all=True, html=False, handler=full_handler, 
                  block_handler=inline_handler, **kwargs):
    if html:
        fn = parse_html
    else:
        fn = parse_text
    def _extension(s, width_height=None):
        params = getattr(settings, 'MICAWBER_DEFAULT_SETTINGS', {})
        params.update(kwargs)
        if width_height:
            if 'x' in width_height:
                params['maxwidth'], params['maxheight'] = map(int, width_height.split('x'))
            else:
                params['maxwidth'] = int(width_height[0])
                params.pop('maxheight', None)
        return mark_safe(fn(s, providers, urlize_all, handler, block_handler, **params))
    register.filter(filter_name, _extension)
    return _extension

oembed = extension('oembed')
oembed_html = extension('oembed_html')

user_extensions = getattr(settings, 'MICAWBER_TEMPLATE_EXTENSIONS', [])
if isinstance(user_extensions, basestring):
    user_extensions = _load_from_module(user_extensions)

for filter_name, filter_params in user_extensions:
    extension(filter_name, **filter_params)
