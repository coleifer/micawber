#!/usr/bin/env python
import os
import sys
import unittest

from micawber import tests


def run_django_tests():
    try:
        import django
    except ImportError:
        print('Skipping django tests')
        return
    else:
        print('Running django integration tests')

    providers = 'micawber.contrib.mcdjango.mcdjango_tests.tests.test_pr'
    extensions = (
        ('oembed_no_urlize', {'urlize_all': False}),
    )

    from django.conf import settings
    if not settings.configured:
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    },
                },
            SITE_ID=1,
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.sites',
                'micawber.contrib.mcdjango',
                'micawber.contrib.mcdjango.mcdjango_tests',
            ],
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [],
                    'APP_DIRS': True,
                    'OPTIONS': {}
                },
            ],
            MICAWBER_PROVIDERS=providers,
            MICAWBER_TEMPLATE_EXTENSIONS=extensions,
        )
    else:
        settings.MICAWBER_PROVIDERS = providers
        settings.MICAWBER_TEMPLATE_EXTENSIONS = extensions

    try:
        from django import setup
    except ImportError:
        pass
    else:
        setup()

    from django.test.runner import DiscoverRunner
    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)
    return DiscoverRunner().run_tests(['micawber/contrib/mcdjango'])


def runtests(*test_args):
    print("Running micawber tests")
    errors = failures = False
    suite = unittest.TestLoader().loadTestsFromModule(tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.failures:
        failures = True
    if result.errors:
        errors = True
    if not (errors or failures):
        print("All micawber tests passed")

    dj_failures = run_django_tests()

    if failures or errors or dj_failures:
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    runtests(*sys.argv[1:])
