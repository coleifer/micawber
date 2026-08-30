.. micawber documentation master file, created by
   sphinx-quickstart on Tue Apr 17 13:43:41 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: http://media.charlesleifer.com/blog/photos/micawber-logo-0.png

A small library for extracting rich content from urls.

https://github.com/coleifer/micawber


what does it do?
----------------

micawber supplies a few methods for retrieving rich metadata about a variety of
links, such as links to youtube videos. micawber also provides functions for
parsing blocks of text and html and replacing links to videos with rich embedded
content.


examples
--------

here is a quick example:

.. code-block:: python

    import micawber

    # load up rules for some default providers, such as youtube and flickr
    providers = micawber.bootstrap_basic()

    providers.request('https://www.youtube.com/watch?v=54XHDUOHuzU', maxwidth=640)

    # returns the following dictionary:
    {
        'author_name': 'Pascal Brax',
        'author_url': 'https://www.youtube.com/@PascalBrax',
        'height': 360,
        'html': '<iframe width="640" height="360" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe>',
        'provider_name': 'YouTube',
        'provider_url': 'https://www.youtube.com/',
        'thumbnail_height': 360,
        'thumbnail_url': 'https://i.ytimg.com/vi/54XHDUOHuzU/hqdefault.jpg',
        'thumbnail_width': 480,
        'title': 'Future Crew - Second Reality demo - HD',
        'type': 'video',
        'url': 'https://www.youtube.com/watch?v=54XHDUOHuzU',
        'version': '1.0',
        'width': 640,
    }

    providers.parse_text('this is a test:\nhttps://www.youtube.com/watch?v=54XHDUOHuzU')

    # returns the following string:
    this is a test:
    <iframe width="200" height="150" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe>

    providers.parse_html('<p>https://www.youtube.com/watch?v=54XHDUOHuzU</p>')

    # returns the following html:
    <p><iframe width="200" height="150" src="https://www.youtube.com/embed/54XHDUOHuzU?feature=oembed" ...></iframe></p>

check out the :ref:`getting started <getting_started>` for more examples


integration with web frameworks
-------------------------------

* :ref:`flask <flask>`
* :ref:`django <django>`

Contents:

.. toctree::
   :maxdepth: 2
   :glob:

   installation
   getting_started
   examples
   flask
   django
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

