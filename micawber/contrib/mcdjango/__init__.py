from importlib import import_module

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from micawber.compat import string_types
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

def django_template_handler(url, response_data, **params):
    return mark_safe(render_to_string('micawber/%s.html' % response_data['type'], template.Context(dict(
        params=params,
        response=response_data,
        url=url,
    ))).strip())

def fix_width_height(width_height, params):
    if width_height:
        if 'x' in width_height:
            params['maxwidth'], params['maxheight'] = map(int, width_height.split('x'))
        else:
            params['maxwidth'] = int(width_height)
            params.pop('maxheight', None)
    return params

def extension(filter_name, providers=providers, urlize_all=True, html=False, handler=django_template_handler,
              block_handler=inline_handler, text_fn=parse_text, html_fn=parse_html, **kwargs):
    if html:
        fn = html_fn
    else:
        fn = text_fn
    def _extension(s, width_height=None):
        params = getattr(settings, 'MICAWBER_DEFAULT_SETTINGS', {})
        params.update(kwargs)
        params = fix_width_height(width_height, params)
        return mark_safe(fn(s, providers, urlize_all, handler, block_handler, **params))
    register.filter(filter_name, _extension)
    return _extension

oembed = extension('oembed')
oembed_html = extension('oembed_html', html=True)

def _extract_oembed(text, width_height=None, html=False):
    if html:
        fn = extract_html
    else:
        fn = extract
    params = getattr(settings, 'MICAWBER_DEFAULT_SETTINGS', {})
    params = fix_width_height(width_height, params)
    url_list, url_data = fn(text, providers, **params)
    return [(u, url_data[u]) for u in url_list if u in url_data]

@register.filter
def extract_oembed(text, width_height=None):
    return _extract_oembed(text, width_height)

@register.filter
def extract_oembed_html(text, width_height=None):
    return _extract_oembed(text, width_height, True)

user_extensions = getattr(settings, 'MICAWBER_TEMPLATE_EXTENSIONS', [])
if isinstance(user_extensions, string_types):
    user_extensions = _load_from_module(user_extensions)

for filter_name, filter_params in user_extensions:
    extension(filter_name, **filter_params)
