.. _api:

API Documentation
=================

Providers
---------

.. py:module:: micawber.providers

.. py:class:: Provider(endpoint, **kwargs)

    The :py:class:`Provider` object is responsible for retrieving metadata about
    a given URL.  It implements a method called :py:meth:`~Provider.request`, which
    takes a URL and any parameters, which it sends off to an endpoint.  The endpoint
    should return a JSON dictionary containing metadata about the resource, which is
    returned to the caller.

    :param endpoint: the API endpoint which should return information about requested links
    :param kwargs: any additional url parameters to send to the endpoint on each
        request, used for providing defaults.  An example use-case might be for
        providing an API key on each request.

    .. py:method:: request(url, **extra_params)

        Retrieve information about the given url.  By default, will make a HTTP
        GET request to the endpoint.  The url will be sent to the endpoint, along
        with any parameters specified in the ``extra_params`` and those parameters
        specified when the class was instantiated.

        Will raise a :py:class:`ProviderException` in the event the URL is not
        accessible or the API times out.

        :param url: URL to retrieve metadata for
        :param extra_params: additional parameters to pass to the endpoint, for
            example a maxwidth or an API key.
        :rtype: a dictionary of JSON data


.. py:class:: ProviderRegistry([cache=None])

    A registry for encapsulating a group of :py:class:`Provider` instances,
    with optional caching support.

    Handles matching regular expressions to providers.  URLs are sent to the
    registry via its :py:meth:`~ProviderRegistry.request` method, it checks to
    see if it has a provider that matches the URL, and if so, requests the
    metadata from the provider instance.

    Exposes methods for parsing various types of text (including HTML), and
    either rendering oembed media inline or extracting embeddable links.

    :param cache: the cache simply needs to implement two methods, ``.get(key)`` and ``.set(key, value)``.

    .. py:method:: register(regex, provider)

        Register the provider with the following regex.

        Example:

        .. code-block:: python

            registry = ProviderRegistry()
            registry.register(
                'http://\S*.youtu(\.be|be\.com)/watch\S*',
                Provider('http://www.youtube.com/oembed'),
            )

        :param regex: a regex for matching URLs of a given type
        :param provider: a :py:class:`Provider` instance

    .. py:method:: request(url, **extra_params)

        Retrieve information about the given url if it matches a regex in the
        instance's registry.  If no provider matches the URL, a
        ``ProviderException`` is thrown, otherwise the URL and parameters are
        dispatched to the matching provider's :py:meth:`Provider.request`
        method.

        If a cache was specified, the resulting metadata will be cached.

        :param url: URL to retrieve metadata for
        :param extra_params: additional parameters to pass to the endpoint, for
            example a maxwidth or an API key.
        :rtype: a dictionary of JSON data

    .. py:method:: parse_text_full(text[, urlize_all=True[, handler=full_handler[, urlize_params=None[, **params]]]])

        Parse a block of text, converting *all* links by passing them to the
        given handler.  Links contained within a block of text (i.e. not on
        their own line) will be handled as well.

        Example input and output::

            IN: 'this is a pic http://example.com/some-pic/'
            OUT: 'this is a pic <a href="http://example.com/some-pic/"><img src="http://example.com/media/some-pic.jpg" /></a>'

        :param str text: a string to parse
        :param bool urlize_all: convert unmatched urls into links
        :param handler: function to use to convert metadata back into a string representation
        :param dict urlize_params: keyword arguments to be used to construct a link
            when a provider is not found and urlize is enabled.
        :param params: any additional parameters to use when requesting metadata, i.e.
            a maxwidth or maxheight.

    .. py:method:: parse_text(text[, urlize_all=True[, handler=full_handler[, block_handler=inline_handler[, urlize_params=None[, **params]]]]])

        Very similar to :py:meth:`~ProviderRegistry.parse_text_full` except
        URLs *on their own line* are rendered using the given ``handler``,
        whereas URLs within blocks of text are passed to the ``block_handler``.
        The default behavior renders full content for URLs on their own line
        (e.g. a video player), whereas URLs within text are rendered simply as
        links so as not to disrupt the flow of text.

        * URLs on their own line are converted into full representations
        * URLs within blocks of text are converted into clickable links

        :param str text: a string to parse
        :param bool urlize_all: convert unmatched urls into links
        :param handler: function to use to convert links found on their own line
        :param block_handler: function to use to convert links found within blocks of text
        :param dict urlize_params: keyword arguments to be used to construct a link
            when a provider is not found and urlize is enabled.
        :param params: any additional parameters to use when requesting metadata, i.e.
            a maxwidth or maxheight.

    .. py:method:: parse_html(html[, urlize_all=True[, handler=full_handler[, block_handler=inline_handler[, urlize_params=None[, **params]]]]])

        Parse HTML intelligently, rendering items on their own within block
        elements as full content (e.g. a video player), whereas URLs within
        text are passed to the ``block_handler`` which by default will render a
        simple link. URLs that are already enclosed within a ``<a>`` tag are
        **skipped over**.

        * URLs that are already within <a> tags are passed over
        * URLs on their own in block tags are converted into full representations
        * URLs interspersed with text are converted into clickable links

        .. note:: requires BeautifulSoup or beautifulsoup4

        :param str html: a string of HTML to parse
        :param bool urlize_all: convert unmatched urls into links
        :param handler: function to use to convert links found on their own within a block element
        :param block_handler: function to use to convert links found within blocks of text
        :param dict urlize_params: keyword arguments to be used to construct a link
            when a provider is not found and urlize is enabled.
        :param params: any additional parameters to use when requesting metadata, i.e.
            a maxwidth or maxheight.

    .. py:method:: extract(text, **params)

        Extract all URLs from a block of text, and additionally get any
        metadata for URLs we have providers for.

        :param str text: a string to parse
        :param params: any additional parameters to use when requesting
            metadata, i.e. a maxwidth or maxheight.
        :rtype: returns a 2-tuple containing a list of all URLs and a dict
            keyed by URL containing any metadata.  If a provider was not found
            for a URL it is not listed in the dictionary.

    .. py:method:: extract_html(html, **params)

        Extract all URLs from an HTML string, and additionally get any metadata
        for URLs we have providers for. :py:meth:`~ProviderRegistry.extract`
        but for HTML.

        .. note:: URLs within <a> tags will not be included.

        :param str html: a string to parse
        :param params: any additional parameters to use when requesting
            metadata, i.e. a maxwidth or maxheight.
        :rtype: returns a 2-tuple containing a list of all URLs and a dict
            keyed by URL containing any metadata.  If a provider was not found
            for a URL it is not listed in the dictionary.


.. py:function:: bootstrap_basic([cache=None[, registry=None]])

    Create a :py:class:`ProviderRegistry` and register some basic providers,
    including youtube, flickr, vimeo.

    :param cache: an object that implements simple ``get`` and ``set``
    :param registry: a ``ProviderRegistry`` instance, which will be updated with the list of supported providers. If not specified, an empty ``ProviderRegistry`` will be used.
    :rtype: a ``ProviderRegistry`` with a handful of providers registered


.. py:function:: bootstrap_oembed([cache=None[, registry=None[, **kwargs]])

    Create a :py:class:`ProviderRegistry` and register as many providers as
    are described in the `oembed.com <https://oembed.com>`_ providers list.

    .. note::
        This function makes a request over the internet whenever it is called.

    :param cache: an object that implements simple ``get`` and ``set``
    :param registry: a ``ProviderRegistry`` instance, which will be updated with the list of supported providers. If not specified, an empty ``ProviderRegistry`` will be used.
    :param kwargs: any default keyword arguments to use with providers
    :rtype: a ProviderRegistry with support for noembed


.. py:function:: bootstrap_embedly([cache=None[, registry=None[, **kwargs]])

    Create a :py:class:`ProviderRegistry` and register as many providers as
    are supported by `embed.ly <http://embed.ly>`_.  Valid services are
    fetched from http://api.embed.ly/1/services/python and parsed then registered.

    .. note::
        This function makes a request over the internet whenever it is called.

    :param cache: an object that implements simple ``get`` and ``set``
    :param registry: a ``ProviderRegistry`` instance, which will be updated with the list of supported providers. If not specified, an empty ``ProviderRegistry`` will be used.
    :param kwargs: any default keyword arguments to use with providers, useful for
        specifying your API key
    :rtype: a ProviderRegistry with support for embed.ly

    .. code-block:: python

        # if you have an API key, you can specify that here
        pr = bootstrap_embedly(key='my-embedly-key')
        pr.request('http://www.youtube.com/watch?v=54XHDUOHuzU')


.. py:function:: bootstrap_noembed([cache=None[, registry=None[, **kwargs]])

    Create a :py:class:`ProviderRegistry` and register as many providers as
    are supported by `noembed.com <http://noembed.com>`_.  Valid services are
    fetched from http://noembed.com/providers and parsed then registered.

    .. note::
        This function makes a request over the internet whenever it is called.

    :param cache: an object that implements simple ``get`` and ``set``
    :param registry: a ``ProviderRegistry`` instance, which will be updated with the list of supported providers. If not specified, an empty ``ProviderRegistry`` will be used.
    :param kwargs: any default keyword arguments to use with providers, useful for
        passing the ``nowrap`` option to noembed.
    :rtype: a ProviderRegistry with support for noembed

    .. code-block:: python

        # if you have an API key, you can specify that here
        pr = bootstrap_noembed(nowrap=1)
        pr.request('http://www.youtube.com/watch?v=54XHDUOHuzU')


Cache
-----

.. py:module:: micawber.cache

.. py:class:: Cache()

    A reference implementation for the cache interface used by the :py:class:`ProviderRegistry`.

    .. py:method:: get(key)

        Retrieve the key from the cache or ``None`` if not present

    .. py:method:: set(key, value)

        Set the cache key ``key`` to the given ``value``.

.. py:class:: PickleCache([filename='cache.db'])

    A cache that uses pickle to store data.

    .. note::
        To use this cache class be sure to call :py:meth:`~PickleCache.load` when
        initializing your cache and :py:meth:`~PickleCache.save` before your app
        terminates to persist cached data.

    .. py:method:: load()

        Load the pickled data into memory

    .. py:method:: save()

        Store the internal cache to an external file

.. py:class:: RedisCache([namespace='micawber'[, **conn]])

    A cache that uses Redis to store data

    .. note:: requires the redis-py library, ``pip install redis``

    :param namespace: prefix for cache keys
    :param conn: keyword arguments to pass when initializing redis connection
