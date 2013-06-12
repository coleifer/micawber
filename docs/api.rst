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

    A registry for encapsulating a group of :py:class:`Provider` instances.
    It has optional caching support.
    
    Handles matching regular expressions to providers.  URLs are sent to the
    registry via its :py:meth:`~ProviderRegistry.request` method, it checks to
    see if it has a provider that matches the URL, and if so, requests the metadata
    from the provider instance.
    
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
    
        Retrieve information about the given url if it matches a regex in
        the instance's registry.  If no provider matches the URL, a ``ProviderException``
        is thrown, otherwise the URL and parameters are dispatched to the matching
        provider's :py:meth:`Provider.request` method.

        If a cache was specified, the resulting metadata will be cached.
        
        :param url: URL to retrieve metadata for
        :param extra_params: additional parameters to pass to the endpoint, for
            example a maxwidth or an API key.
        :rtype: a dictionary of JSON data

.. py:function:: bootstrap_basic([cache=None])

    Create a :py:class:`ProviderRegistry` and register some basic providers,
    including youtube, flickr, vimeo.
    
    :param cache: an object that implements simple ``get`` and ``set``
    :rtype: a ProviderRegistry with a handful of providers registered

.. py:function:: bootstrap_embedly([cache=None, [**kwargs]])

    Create a :py:class:`ProviderRegistry` and register as many providers as
    are supported by `embed.ly <http://embed.ly>`_.  Valid services are
    fetched from http://api.embed.ly/1/services/python and parsed then registered.
    
    :param cache: an object that implements simple ``get`` and ``set``
    :param kwargs: any default keyword arguments to use with providers, useful for
        specifying your API key
    :rtype: a ProviderRegistry with support for embed.ly

    .. code-block:: python

        # if you have an API key, you can specify that here
        pr = bootstrap_embedly(key='my-embedly-key')
        pr.request('http://www.youtube.com/watch?v=54XHDUOHuzU')

.. py:function:: bootstrap_noembed([cache=None, [**kwargs]])

    Create a :py:class:`ProviderRegistry` and register as many providers as
    are supported by `noembed.com <http://noembed.com>`_.  Valid services are
    fetched from http://noembed.com/providers and parsed then registered.

    :param cache: an object that implements simple ``get`` and ``set``
    :param kwargs: any default keyword arguments to use with providers, useful for
        passing the ``nowrap`` option to noembed.
    :rtype: a ProviderRegistry with support for noembed

    .. code-block:: python

        # if you have an API key, you can specify that here
        pr = bootstrap_noembed(nowrap=1)
        pr.request('http://www.youtube.com/watch?v=54XHDUOHuzU')

Parsers
-------

.. py:module:: micawber.parsers

Functions for parsing text and HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: parse_text_full(text, providers[, urlize_all=True[, handler=full_handler[, **params]]])

    Parse a block of text, converting *all* links by passing them to the given handler.
    Links contained within a block of text (i.e. not on their own line) will be handled
    as well.
    
    Example input and output::
    
        IN: 'this is a pic http://example.com/some-pic/'
        OUT: 'this is a pic <a href="http://example.com/some-pic/"><img src="http://example.com/media/some-pic.jpg" /></a>'
    
    :param text: a string to parse
    :param providers: a :py:class:`ProviderRegistry` instance
    :param urlize_all: whether to convert all urls irrespective of whether a provider exists
    :param handler: function to use to convert metadata back into a string representation
    :param params: any additional parameters to use when requesting metadata, i.e.
        a maxwidth or maxheight.

.. py:function:: parse_text(text, providers[, urlize_all=True[, handler=full_handler[, block_handler=inline_handler[, **params]]]])

    Very similar to the above :py:func:`parse_text_full` except URLs *on their own line*
    are rendered using the given ``handler``, whereas URLs within blocks of text are
    passed to the ``block_handler``.  The default behavior renders full content for
    URLs on their own line (e.g. a flash player), whereas URLs within text are rendered 
    simply as links so as not to disrupt the flow of text.
    
    :param text: a string to parse
    :param providers: a :py:class:`ProviderRegistry` instance
    :param urlize_all: whether to convert all urls irrespective of whether a provider exists
    :param handler: function to use to convert links found on their own line
    :param block_handler: function to use to convert links found within blocks of text
    :param params: any additional parameters to use when requesting metadata, i.e.
        a maxwidth or maxheight.

.. py:function:: parse_html(html, providers[, urlize_all=True[, handler=full_handler[, block_handler=inline_handler[, **params]]]])

    Parse HTML intelligently, rendering items on their own within block elements
    as full content (e.g. a flash player), whereas URLs within text are passed
    to the ``block_handler`` which by default will render a simple link.  Also
    worth noting is that URLs that are already enclosed within a <a> tag are skipped
    over.
    
    .. note:: requires BeautifulSoup or beautifulsoup4
    
    :param html: a string of HTML to parse
    :param providers: a :py:class:`ProviderRegistry` instance
    :param urlize_all: whether to convert all urls irrespective of whether a provider exists
    :param handler: function to use to convert links found on their own within a block element
    :param block_handler: function to use to convert links found within blocks of text
    :param params: any additional parameters to use when requesting metadata, i.e.
        a maxwidth or maxheight.


Functions for extracting rich content from text and HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: extract(text, providers, **params)

    Extract all URLs from a block of text, and additionally get any metadata for
    URLs we have providers for.

    :param text: a string to parse
    :param providers: a :py:class:`ProviderRegistry` instance
    :param params: any additional parameters to use when requesting metadata, i.e.
        a maxwidth or maxheight.
    :rtype: returns a 2-tuple containing a list of all URLs and a dictionary keyed
        by URL containing any metadata.  If a provider was not found for a URL
        it is not listed in the dictionary.

.. py:function:: extract_html(html, providers, **params)

    Extract all URLs from an HTML string, and additionally get any metadata for
    URLs we have providers for.  Same as :py:func:`extract` but for HTML.
    
    .. note:: URLs within <a> tags will not be included.

    :param html: a string to parse
    :param providers: a :py:class:`ProviderRegistry` instance
    :param params: any additional parameters to use when requesting metadata, i.e.
        a maxwidth or maxheight.
    :rtype: returns a 2-tuple containing a list of all URLs and a dictionary keyed
        by URL containing any metadata.  If a provider was not found for a URL
        it is not listed in the dictionary.


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
