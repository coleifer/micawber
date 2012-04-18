import os

#### MICAWBER SETTINGS

# add a template filter called "oembed_no_urlize" that will not automatically
# convert URLs to clickable links in the event a provider is not found for
# the given url
MICAWBER_TEMPLATE_EXTENSIONS = [
    ('oembed_no_urlize', {'urlize_all': False}),
]

# by default, micawber will use the "bootstrap_basic" providers, but should you
# wish to use embedly you can try out the second example.  You can also provide
# your own ProviderRegistry with a path to a module and either a callable or
# ProviderRegistry instance
MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_basic'
#MICAWBER_PROVIDERS = 'micawber.contrib.mcdjango.providers.bootstrap_embedly'

# if you are using embed.ly you can specify an API key that will be used with
# the bootstrap_embedly provider setting
# MICAWBER_EMBEDLY_KEY = 'foofoo'

# since template filters are limited to a single optional parameter, you can
# specify defaults, such as a maxwidth you prefer to use or an api key
#MICAWBER_DEFAULT_SETTINGS = {
#    'key': 'your-embedly-api-key',
#    'maxwidth': 600,
#    'maxheight': 600,
#}

#### END MICAWBER SETTINGS

CURRENT_DIR = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django_ex.db',
    }
}

SITE_ID = 1

SECRET_KEY = 'fapfapfap'

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(CURRENT_DIR, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'django_ex.urls'

TEMPLATE_DIRS = (
    os.path.join(CURRENT_DIR, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'micawber.contrib.mcdjango',
)
