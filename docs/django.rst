.. _django:

Django integration
==================

micawber provides several template filters for use within
your django project.

Setting configuration
---------------------

First be sure you have added ``micawber.contrib.mcdjango`` to ``settings.INSTALLED_APPS``

Providers
^^^^^^^^^

The most important setting to configure is the module / attribute
path to the providers you wish to use.  The attribute can either
be a ProviderRegistry instance or a callable.  The default is:

``MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_basic'``

Suppose you want to customize this:

``MICAWBER_PROVIDERS = 'my_app.micawber_providers.oembed_providers'``

That module might look something like:

.. code-block:: python

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
Default arguments need to be specified in the settings:

.. code-block:: python

    MICAWBER_DEFAULT_SETTINGS = {
        'key': 'your-embedly-api-key',
        'maxwidth': 600,
        'maxheight': 600,
    }

You can also use the factory method to partially apply values to
generate new filters:

.. code-block:: python

    MICAWBER_TEMPLATE_EXTENSIONS = [
        ('oembed_no_urlize', {'urlize_all': False}),
    ]

These can be automatically imported and loaded:

``MICAWBER_TEMPLATE_EXTENSIONS = 'my_app.micawber_extensions'``

.. note::

    the attribute ``micawber_extensions`` must be a list of the form:
    
    .. code-block:: python
    
        micawber_extensions = [
            ('oembed_no_urlize', {'urlize_all': False}),
        ]


Template filters
----------------

Here is some simple usage:

.. code-block:: html

    {% load micawber_tags %}
    
    {% block content %}
      <p>{{ object.body|oembed:"600x600" }}</p>
    {% endblock %}


Trying it out in the python shell:

.. code-block:: python

    >>> from django.template import Template, Context
    >>> t = Template('{% load micawber_tags %}{{ "http://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed }}')
    >>> t.render(Context())
    u'<iframe width="480" height="270" src="http://www.youtube.com/embed/mQEWI1cn7HY?fs=1&feature=oembed" frameborder="0" allowfullscreen></iframe>'
