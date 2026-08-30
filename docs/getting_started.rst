.. _getting_started:

Getting Started
===============

If you want the dead simple get-me-up-and-running, try the following:

.. code-block:: python

    >>> import micawber
    >>> providers = micawber.bootstrap_basic()
    >>> print(providers.parse_text('this is a test:\nhttps://www.youtube.com/watch?v=54XHDUOHuzU'))
    this is a test:
    <iframe width="200" height="150" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe>

Using django? Add ``micawber.contrib.mcdjango`` to your ``INSTALLED_APP``, then
in your templates:

.. code-block:: html

    {% load micawber_tags %}
    {# show a video player for the youtube video #}
    {{ "https://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed }}

Using flask? Use the ``add_oembed_filters`` function to register two jinja
template filters, ``oembed`` and ``extract_oembed``:

.. code-block:: python

    from flask import Flask
    from micawber.providers import bootstrap_basic
    from micawber.contrib.mcflask import add_oembed_filters

    app = Flask(__name__)

    oembed_providers = bootstrap_basic()
    add_oembed_filters(app, oembed_providers)

.. code-block:: html

    {# show a video player for the youtube video #}
    {{ "https://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed() }}

Overview
--------

micawber is rather simple. It is built to use the `oembed <https://oembed.com/>`_ spec,
which is designed for converting URLs into rich, embeddable content. Many popular sites
support this, including youtube and flickr. There is also a 3rd-party service called
`embedly <https://embed.ly>`_ that can convert many types of links into rich content.

micawber was designed to make it easy to integrate with these APIs. There are
two concepts to understand when using micawber:

* :py:class:`~micawber.providers.Provider` objects - which describe how to
  match a URL (based on a regex) to an OEmbed endpoint.
* :py:class:`~micawber.providers.ProviderRegistry` objects - which encapsulate
  a collection or providers and expose methods for parsing text and HTML to
  convert links into media objects.


Providers
---------

Providers are used to convert URLs into rich metadata. They have an endpoint
associated with them and can have any number of arbitrary URL parameters (such
as API keys) which are used when making API requests.

Example:

.. code-block:: python

    from micawber.providers import Provider

    youtube = Provider('https://www.youtube.com/oembed')
    youtube.request('https://www.youtube.com/watch?v=nda_OSWeyn8')

The above code returns a dictionary containing metadata about the requested
video, including the markup for an embeddable player::

    {'author_name': 'botmib',
     'author_url': 'https://www.youtube.com/@botmib',
     'height': 150,
     'html': '<iframe width="200" height="150" src="https://www.youtube.com/embed/nda_OSWeyn8?feature=oembed" ...></iframe>',
     'provider_name': 'YouTube',
     'provider_url': 'https://www.youtube.com/',
     'thumbnail_height': 360,
     'thumbnail_url': 'https://i.ytimg.com/vi/nda_OSWeyn8/hqdefault.jpg',
     'thumbnail_width': 480,
     'title': 'Leprechaun in Mobile, Alabama',
     'type': 'video',
     'url': 'https://www.youtube.com/watch?v=nda_OSWeyn8',
     'version': '1.0',
     'width': 200}

More information can be found in the :py:class:`~micawber.providers.Provider` API docs.

ProviderRegistry
----------------

The :py:class:`~micawber.providers.ProviderRegistry` is a way of organizing lists
of providers. URLs can be requested from the registry and if *any* provider matches
it will be used, otherwise a ``ProviderException`` will be raised.

The ``ProviderRegistry`` also supports an optional simple caching mechanism.

Here is an excerpt from the code from the :py:func:`micawber.providers.bootstrap_basic` function,
which is handy for grabbing a ``ProviderRegistry`` with a handful of basic providers
pre-populated:

.. code-block:: python

    def bootstrap_basic(cache=None, registry=None):
        pr = registry or ProviderRegistry(cache)
        pr.register(r'https?://\S*?flickr\.com/\S+', Provider('https://www.flickr.com/services/oembed/'))
        pr.register(r'https?://(?:player\.)?vimeo\.com/\S+', Provider('https://vimeo.com/api/oembed.json'))
        pr.register(r'https?://(?:www\.)?tiktok\.com/\S+', Provider('https://www.tiktok.com/oembed'))
        return pr

As you can see, the :py:meth:`~micawber.providers.ProviderRegistry.register` method takes
two parameters, a regular expression for valid URLs and a ``Provider`` instance.

You can use helper functions to get a populated registry:

* :py:func:`~micawber.providers.bootstrap_basic`
* :py:func:`~micawber.providers.bootstrap_oembed` - uses oembed.com's official providers list.
* :py:func:`~micawber.providers.bootstrap_embedly`
* :py:func:`~micawber.providers.bootstrap_noembed`
* :py:func:`~micawber.providers.bootstrap_iframely` - requires an `iframely <https://iframely.com/>`_ API key.

The ``bootstrap_oembed``, ``bootstrap_embedly``, and ``bootstrap_noembed``
functions make a HTTP request to the API server asking for a list of supported
providers, so you may experience some latency when using these helpers. For
most WSGI applications this will not be an issue, but if you'd like to speed it
up I suggest fetching the results, storing them in the db or a file, and then
pulling from there.

More information can be found in the :py:class:`~micawber.providers.ProviderRegistry` API docs.

Parsing Links
^^^^^^^^^^^^^

Replace URLs with rich media:

* :py:meth:`~micawber.providers.ProviderRegistry.parse_text`, which converts
  URLs on their own line into a rich media object. Links embedded within blocks
  of text are converted into clickable links.
* :py:meth:`~micawber.providers.ProviderRegistry.parse_html`, which converts
  URLs within HTML into rich media objects or clickable links, depending on the
  context in which the URL is found.

A quick example:

.. code-block:: python

    import micawber

    providers = micawber.bootstrap_basic()

    providers.parse_text('this is a test:\nhttps://www.youtube.com/watch?v=54XHDUOHuzU')

This will result in the following output::

    this is a test:
    <iframe width="200" height="150" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe>

You can also parse HTML using the :py:meth:`~micawber.providers.ProviderRegistry.parse_html` method:

.. code-block:: python

    providers.parse_html('<p>https://www.youtube.com/watch?v=54XHDUOHuzU</p>')

    # yields the following output:
    <p><iframe width="200" height="150" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe></p>

If you would rather extract metadata, there are two functions:

* :py:meth:`~micawber.providers.ProviderRegistry.extract`, which finds all URLs
  within a block of text and returns a dictionary of metadata for each.
* :py:meth:`~micawber.providers.ProviderRegistry.extract_html`, which finds
  URLs within HTML and returns a dictionary of metadata for each.

The :ref:`API docs <api>` are extensive, so please refer there for a full list
of parameters and functions.
