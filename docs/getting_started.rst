.. _getting_started:

Getting Started
===============

If you want the dead simple get-me-up-and-running, try the following:

.. code-block:: python

    >>> import micawber
    >>> providers = micawber.bootstrap_basic() # may take a second
    >>> print providers.parse_text('this is a test:\nhttp://www.youtube.com/watch?v=54XHDUOHuzU')
    this is a test:
    <iframe width="640" height="360" src="http://www.youtube.com/embed/54XHDUOHuzU?fs=1&feature=oembed" frameborder="0" allowfullscreen></iframe>

Using django?  Add ``micawber.contrib.mcdjango`` to your ``INSTALLED_APP``, then
in your templates:

.. code-block:: html

    {% load micawber_tags %}
    {# show a video player for the youtube video #}
    {{ "http://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed }}

Using flask?  Use the ``add_oembed_filters`` function to register two jinja
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
    {{ "http://www.youtube.com/watch?v=mQEWI1cn7HY"|oembed() }}

Overview
--------

micawber is rather simple.  It is built to use the `oembed <http://oembed.com/>`_ spec,
which is designed for converting URLs into rich, embeddable content.  Many popular sites
support this, including youtube and flickr.  There is also a 3rd-party service called
`embedly <http://embed.ly>`_ that can convert many types of links into rich content.

micawber was designed to make it easy to integrate with these APIs.  There are
two concepts to understand when using micawber:

* :py:class:`~micawber.providers.Provider` objects - which describe how to
  match a URL (based on a regex) to an OEmbed endpoint.
* :py:class:`~micawber.providers.ProviderRegistry` objects - which encapsulate
  a collection or providers and expose methods for parsing text and HTML to
  convert links into media objects.


Providers
---------

Providers are used to convert URLs into rich metadata.  They have an endpoint
associated with them and can have any number of arbitrary URL parameters (such
as API keys) which are used when making API requests.

Example:

.. code-block:: python

    from micawber.providers import Provider

    youtube = Provider('http://www.youtube.com/oembed')
    youtube.request('http://www.youtube.com/watch?v=nda_OSWeyn8')

The above code returns a dictionary containing metadata about the requested
video, including the markup for an embeddable player::

    {'author_name': u'botmib',
     'author_url': u'http://www.youtube.com/user/botmib',
     'height': 344,
     'html': u'<iframe width="459" height="344" src="http://www.youtube.com/embed/nda_OSWeyn8?fs=1&feature=oembed" frameborder="0" allowfullscreen></iframe>',
     'provider_name': u'YouTube',
     'provider_url': u'http://www.youtube.com/',
     'thumbnail_height': 360,
     'thumbnail_url': u'http://i3.ytimg.com/vi/nda_OSWeyn8/hqdefault.jpg',
     'thumbnail_width': 480,
     'title': u'Leprechaun in Mobile, Alabama',
     'type': u'video',
     'url': 'http://www.youtube.com/watch?v=nda_OSWeyn8',
     'version': u'1.0',
     'width': 459}

More information can be found in the :py:class:`~micawber.providers.Provider` API docs.

ProviderRegistry
----------------

The :py:class:`~micawber.providers.ProviderRegistry` is a way of organizing lists
of providers.  URLs can be requested from the registry and if *any* provider matches
it will be used, otherwise a ``ProviderException`` will be raised.

The ``ProviderRegistry`` also supports an optional simple caching mechanism.

Here is an excerpt from the code from the :py:func:`micawber.providers.bootstrap_basic` function,
which is handy for grabbing a ``ProviderRegistry`` with a handful of basic providers
pre-populated:

.. code-block:: python

    def bootstrap_basic(cache=None, registry=None, **params):
        pr = registry or ProviderRegistry(cache)
        pr.register('http://\S*?flickr.com/\S*', Provider('http://www.flickr.com/services/oembed/'))
        pr.register('http://\S*.youtu(\.be|be\.com)/watch\S*', Provider('http://www.youtube.com/oembed'))
        pr.register('http://www.hulu.com/watch/\S*', Provider('http://www.hulu.com/api/oembed.json'))
        return pr

As you can see, the :py:meth:`~micawber.providers.ProviderRegistry.register` method takes
two parameters, a regular expression for valid URLs and a ``Provider`` instance.

You can use helper functions to get a populated registry:

* :py:func:`~micawber.providers.bootstrap_basic`
* :py:func:`~micawber.providers.bootstrap_oembed` - uses oembed.com's official providers list.
* :py:func:`~micawber.providers.bootstrap_embedly`
* :py:func:`~micawber.providers.bootstrap_noembed`

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

    providers.parse_text('this is a test:\nhttp://www.youtube.com/watch?v=54XHDUOHuzU')

This will result in the following output::

    this is a test:
    <iframe width="459" height="344" src="http://www.youtube.com/embed/54XHDUOHuzU?fs=1&feature=oembed" frameborder="0" allowfullscreen></iframe>

You can also parse HTML using the :py:meth:`~micawber.providers.ProviderRegistry.parse_html` method:

.. code-block:: python

    providers.parse_html('<p>http://www.youtube.com/watch?v=54XHDUOHuzU</p>')

    # yields the following output:
    <p><iframe width="459" height="344" src="http://www.youtube.com/embed/54XHDUOHuzU?fs=1&amp;feature=oembed" frameborder="0" allowfullscreen="allowfullscreen"></iframe></p>

If you would rather extract metadata, there are two functions:

* :py:meth:`~micawber.providers.ProviderRegistry.extract`, which finds all URLs
  within a block of text and returns a dictionary of metadata for each.
* :py:meth:`~micawber.providers.ProviderRegistry.extract_html`, which finds
  URLs within HTML and returns a dictionary of metadata for each.

The :ref:`API docs <api>` are extensive, so please refer there for a full list
of parameters and functions.
