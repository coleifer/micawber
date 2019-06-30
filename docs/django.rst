.. _django:

Django integration
==================

First be sure you have added ``micawber.contrib.mcdjango`` to ``INSTALLED_APPS``
so that we can use the template filters it defines.

.. code-block:: python

    # settings.py

    INSTALLED_APPS = [
        # ...
        'micawber.contrib.mcdjango',
    ]

micawber provides 4 template filters for converting URLs contained within
text or HTML to rich content:

* :py:func:`~micawber.contrib.mcdjango.oembed` for plain text
* :py:func:`~micawber.contrib.mcdjango.oembed_html` for html
* :py:func:`~micawber.contrib.mcdjango.extract_oembed` for extracting url data from plain text
* :py:func:`~micawber.contrib.mcdjango.extract_oembed_html` for extracting url data from html

These filters are registered in the ``micawber_tags`` library, which can be
invoked in your templates:

.. code-block:: html

    {% load micawber_tags %}

    <p>{{ object.body|oembed:"600x600" }}</p>

Each filter accepts one argument and one optional argument, due to django's template
filters being wack.

Piping a string through the ``oembed`` filter (or ``oembed_html``) will convert
URLs to things like youtube videos into video players.  A couple things to
understand about the parsers:

* the plaintext parser (``oembed``) will convert URLs *on their own line* into
  full images/video-players/etc.  URLs that are interspersed within text will
  simply be converted into clickable links so as not to disrupt the flow of text.
* the HTML parser (``oembed_html``) will convert URLs that *are not already links*
  into full images/video-players/etc. URLs within block elements along with other
  text will be converted into clickable links as this would likely disrupt the flow
  of text or produce invalid HTML.

.. note::
    You can control how things are rendered -- check out `the default templates <https://github.com/coleifer/micawber/tree/master/micawber/contrib/mcdjango/templates/micawber>`_
    for reference implementations.


Django filter API
-----------------

.. py:module:: micawber.contrib.mcdjango

The following filters are exposed via the :py:mod:`micawber.contrib.mcdjango` module:

.. py:function:: oembed(text[, width_height=None])

    Parse the given text, rendering URLs as rich media

    Usage within a django template:

    .. code-block:: python

        {{ blog_entry.body|oembed:"600x600" }}

    :param text: the text to be parsed **do not use HTML**
    :param width_height: string containing maximum for width and optionally height, of
        format "WIDTHxHEIGHT" or "WIDTH", e.g. "500x500" or "800"
    :rtype: parsed text with rich content embedded

.. py:function:: oembed_html(html[, width_height=None])

    Exactly the same as above except for usage *with html*

    Usage within a django template:

    .. code-block:: python

        {{ blog_entry.body|markdown|oembed_html:"600x600" }}

.. py:function:: extract_oembed(text[, width_height=None])

    Parse the given text, returning a list of 2-tuples containing url and metadata
    about the url.

    Usage within a django template:

    .. code-block:: python

        {% for url, metadata in blog_entry.body|extract_oembed:"600x600" %}
          <img src="{{ metadata.thumbnail_url }}" />
        {% endfor %}

    :param text: the text to be parsed **do not use HTML**
    :param width_height: string containing maximum for width and optionally height, of
        format "WIDTHxHEIGHT" or "WIDTH", e.g. "500x500" or "800"
    :rtype: 2-tuples containing the URL and a dictionary of metadata

.. py:function:: extract_oembed_html(html[, width_height=None])

    Exactly the same as above except for usage *with html*


Extending the filters
---------------------

For simplicity, micawber provides a setting allowing you to create custom template
filters.  An example use case would be to add a template filter that could embed
rich content, but did not automatically "urlize" all links.

Extensions are configured in the ``settings`` module and take the form of a list of
2-tuples containing:

1. the name for the custom filter
2. a dictionary of keyword arguments to pass in to the ``parse`` function

.. code-block:: python

    MICAWBER_TEMPLATE_EXTENSIONS = [
        ('oembed_no_urlize', {'urlize_all': False}),
    ]

Assume this is our template:

.. code-block:: html

    {% load micawber_tags %}

    DEFAULT:
    {{ "http://foo.com/ and http://bar.com/"|oembed }}

    CUSTOM:
    {{ "http://foo.com/ and http://bar.com/"|oembed_no_urlize }}

Rendering the above template will produce the following output:

.. code-block:: html

    DEFAULT:
    <a href="http://foo.com/">http://foo.com/</a> and <a href="http://bar.com/">http://bar.com/</a>

    CUSTOM:
    http://foo.com/ and http://bar.com/

Some examples of keyword arguments to override are:

* providers: a :py:class:`~micawber.providers.ProviderRegistry` instance
* urlize_all (default ``True``): whether to convert *all* URLs to clickable links
* html (default ``False``): whether to parse as plaintext or html
* handler: function used to render metadata as markup
* block_handler: function used to render inline links with rich metadata
* text_fn: function to use when parsing text
* html_fn: function to use when parsing html

The magic happens in :py:func:`micawber.contrib.mcdjango.extension` -- check
out the `source code <https://github.com/coleifer/micawber/blob/master/micawber/contrib/mcdjango/__init__.py>`_ for more details.

.. note::
    The ``MICAWBER_EXTENSIONS`` setting can also be a string path to
    a module and an attribute containing a similar data structure.


Additional settings
-------------------

Providers
^^^^^^^^^

The most important setting to configure is the module / attribute
path to the providers you wish to use.  The attribute can either
be a ProviderRegistry instance or a callable.  The default is:

``MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_basic'``

You can use the bootstrap embedly function, but beware this may take a few
seconds to load up:

``MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_embedly'``

If you want to use the embedly endpoints and have an API key, you can specify
that in the settings:

``MICAWBER_EMBEDLY_KEY = 'foo'``

You can also customize this with your own set of providers.  This must be either

* the module path to a :py:class:`~micawber.providers.ProviderRegistry` instance
* the module path to a callable which returns a :py:class:`~micawber.providers.ProviderRegistry` instance

Here is a quick example showing a custom ``ProviderRegistry``:

.. code-block:: python

    # settings.py
    MICAWBER_PROVIDERS = 'my_app.micawber_providers.oembed_providers'

.. code-block:: python

    # my_app/micawber_providers.py
    from django.core.cache import cache
    from micawber.providers import Provider, bootstrap_basic

    oembed_providers = boostrap_basic(cache)

    # add a custom provider
    oembed_providers.register('http://example.com/\S*', Provider('http://example.com/oembed/'))


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


Trying it out in the python shell
---------------------------------

.. code-block:: python

    >>> from django.template import Template, Context
    >>> t = Template('{% load micawber_tags %}{{ "http://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed }}')
    >>> t.render(Context())
    u'<iframe width="480" height="270" src="http://www.youtube.com/embed/mQEWI1cn7HY?fs=1&feature=oembed" frameborder="0" allowfullscreen></iframe>'
