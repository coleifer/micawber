.. _flask:

Flask integration
=================

micawber exposes two Jinja template filters for use in your flask templates:

* :py:func:`~micawber.contrib.mcflask.oembed`
* :py:func:`~micawber.contrib.mcflask.extract_oembed`

You can add them to your jinja environment by using the helper function:

.. code-block:: python

    from flask import Flask
    from micawber.providers import bootstrap_basic
    from micawber.contrib.mcflask import add_oembed_filters

    app = Flask(__name__)

    oembed_providers = bootstrap_basic()
    add_oembed_filters(app, oembed_providers)

Now you can use the filters in your templates:

.. code-block:: html

    {% block content %}
      <p>{{ object.body|oembed(html=False, maxwidth=600, maxheight=600) }}</p>
    {% endblock %}

Flask filter API
----------------

.. py:module:: micawber.contrib.mcflask

The following filters are exposed via the :py:mod:`micawber.contrib.mcflask` module:

.. py:function:: oembed(text, urlize_all=True, html=False, **params)

    Parse the given text, rendering URLs as rich media

    Usage within a Jinja2 template:

    .. code-block:: python

        {{ blog_entry.body|oembed(urlize_all=False, maxwidth=600) }}

    :param text: the text to be parsed, can be HTML
    :param urlize_all: boolean indicating whether to convert bare links to clickable ones
    :param html: boolean indicating whether text is plaintext or markup
    :param params: any additional keyword arguments, e.g. maxwidth or an api key
    :rtype: parsed text with rich content embedded

.. py:function:: extract_oembed(text, html=False, **params)

    Returns a 2-tuple containing

    * a list of all URLs found within the text (if HTML, all URLs that aren't already links)
    * a dictionary of URL to metadata provided by the API endpoint

    .. note::
        Not all URLs listed will have matching entries in the dictionary, since there
        may not be a provider for them.

    :param text: the text to be parsed, can be HTML
    :param html: boolean indicating whether text is plaintext or markup
    :param params: any additional keyword arguments, e.g. maxwidth or an api key
    :rtype: 2-tuple containing a list of *all* urls and a dictionary of url -> metadata

Adding filters to the Jinja Environment
---------------------------------------

To actually use these filters they must be made available to the application.  Use the
following function to do this sometime after initializing your ``Flask`` app:

.. py:function:: add_oembed_filters(app, providers)

    Add the ``oembed`` and ``extract_oembed`` filters to the jinja environment

    :param app: a flask application
    :param providers: a :py:class:`micawber.providers.ProviderRegistry` instance
    :rtype: (no return value)
