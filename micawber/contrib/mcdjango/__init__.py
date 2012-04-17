"""
Django integration for micawber library
=======================================

micawber provides several templatetags and filters for use within
your django project.

Setting configuration
---------------------


Providers
^^^^^^^^^

The most important setting to configure is the module / attribute
path to the providers you wish to use.  The attribute can either
be a ProviderRegistry instance or a callable.  The default is:

``MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_basic'``

Suppose you want to customize this:

``MICAWBER_PROVIDERS = 'my_app.micawber_providers.oembed_providers'``

That module might look something like::

    from django.core.cache import cache
    from micawber.providers import Provider, bootstrap_basic

    oembed_providers = boostrap_basic(cache)
    oembed_providers.register('http://example.com/\S*', Provider('http://example.com/oembed/'))


Using with Embed.ly
^^^^^^^^^^^^^^^^^^^

You can use the bootstrap embedly function:

``MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_embedly'``

If you want to use the embedly endpoints and have an API key, you can specify
that in the settings:

``MICAWBER_EMBEDLY_KEY = 'foo'``


Default settings for requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because of the limitations of django's template filters, we do not
have the flexibility to pass in multiple arguments to the filters.
Default arguments need to be specified in the settings::

    MICAWBER_DEFAULT_SETTINGS = {
        'key': 'your-embedly-api-key',
        'maxwidth': 600,
        'maxheight': 600,
    }

You can also use the factory method to partially apply values to
generate new filters::

    MICAWBER_TEMPLATE_EXTENSIONS = [
        ('oembed_no_urlize', {'urlize_all': False}),
    ]

These can be automatically imported and loaded:

``MICAWBER_TEMPLATE_EXTENSIONS = 'my_app.micawber_extensions'``

.. note::

    the attribute ``micawber_extensions`` must be a list of the form::
    
        micawber_extensions = [
            ('oembed_no_urlize', {'urlize_all': False}),
        ]

"""

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
