.. _installation:

Installation
============

First, you need to install micawber

There are a couple of ways:

Installing with pip
^^^^^^^^^^^^^^^^^^^

::

    pip install micawber
    
    or
    
    pip install -e git+https://github.com/coleifer/micawber.git#egg=micawber


Installing via git
^^^^^^^^^^^^^^^^^^

::

    git clone https://github.com/coleifer/micawber.git
    cd micawber
    python runtests.py
    pip install .


Adding to your Django Project
--------------------------------

micawber defines no models, so there is nothing to migrate. Add it to
``INSTALLED_APPS`` to pick up the template filters::

    # settings.py
    INSTALLED_APPS = [
        ...
        'micawber.contrib.mcdjango'
    ]
