.. _examples:

Examples
========

micawber comes with a handful of examples showing usage with

* :ref:`django <django_example>`
* :ref:`flask <flask_example>`
* :ref:`simple python script <python_example>`

.. _django_example:

Django example
--------------

The django example is very simple -- it illustrates a single view that renders
text inputted by the user by piping it through the :py:func:`~micawber.contrib.mcdjango.oembed`
filter.  It also shows the output of the :py:func:`~micawber.contrib.mcdjango.extract_oembed`
filter which returns a 2-tuple of URL -> metadata.  There is also an input where
you can experiment with entering HTML.

To run the example::

    cd examples/django_ex/
    ./manage.py runserver

Check out the `example source code <https://github.com/coleifer/micawber/tree/master/examples/django_ex>`_.


.. _flask_example:

Flask example
-------------

The flask example is almost identical in terms of functionality to the django example. It 
shows a one-file app with a single view that renders
text inputted by the user by piping it through the :py:func:`~micawber.contrib.mcflask.oembed`
filter.  It also shows the output of the :py:func:`~micawber.contrib.mcflask.extract_oembed`
filter which returns a 2-tuple of URL -> metadata.  There is also an input where
you can experiment with entering HTML.

To run the example::

    cd examples/flask_ex/
    python app.py

Check out the `example source code <https://github.com/coleifer/micawber/tree/master/examples/flask_ex>`_.

.. _python_example:

Python example
--------------

The python example is a command-line app that shows the use of the :py:class:`micawber.providers.ProviderRegistry`
and :py:class:`micawber.providers.bootstrap_embedly`.  It runs a loop asking the user to input
URLs, outputting rich metadata when possible (view http://embed.ly for a full list of providers).

To run the example::

    cd examples/python_ex/
    python example.py

Check out the `example source code <https://github.com/coleifer/micawber/tree/master/examples/python_ex/example.py>`_.
