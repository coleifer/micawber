.. _flask:

Flask integration
=================

micawber exposes two Jinja template filters for use in your flask templates:

* oembed
* extract_oembed

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
