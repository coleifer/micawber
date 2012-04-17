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
    python setup.py test
    sudo python setup.py install


Adding to your Django Project
--------------------------------

After installing, adding django-utils to your projects is a snap.  Simply
add it to your projects' INSTALLED_APPs and run 'syncdb'::
    
    # settings.py
    INSTALLED_APPS = [
        ...
        'micawber.contrib.mcdjango'
    ]
