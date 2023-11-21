"""
Django settings for testsite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import logging, os, re, sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RUN_DIR = os.getenv('RUN_DIR', os.getcwd())
DB_NAME = os.path.join(RUN_DIR, 'db.sqlite')
LOG_FILE = os.path.join(RUN_DIR, 'testsite-app.log')

DEBUG = True
ALLOWED_HOSTS = ('*',)
APP_NAME = os.path.basename(BASE_DIR)


def load_config(confpath):
    '''
    Given a path to a file, parse its lines in ini-like format, and then
    set them in the current namespace.
    '''
    # todo: consider using something like ConfigObj for this:
    # http://www.voidspace.org.uk/python/configobj.html
    if os.path.isfile(confpath):
        sys.stderr.write('config loaded from %s\n' % confpath)
        with open(confpath) as conffile:
            line = conffile.readline()
            while line != '':
                if not line.startswith('#'):
                    look = re.match(r'(\w+)\s*=\s*(.*)', line)
                    if look:
                        value = look.group(2) \
                            % {'LOCALSTATEDIR': BASE_DIR + '/var'}
                        # Once Django 1.5 introduced ALLOWED_HOSTS (a tuple
                        # definitely in the site.conf set), we had no choice
                        # other than using eval. The {} are here to restrict
                        # the globals and locals context eval has access to.
                        # pylint: disable=eval-used
                        setattr(sys.modules[__name__],
                            look.group(1).upper(), eval(value, {}, {}))
                line = conffile.readline()
    else:
        sys.stderr.write('warning: config file %s does not exist.\n' % confpath)

load_config(os.path.join(
    os.getenv('TESTSITE_SETTINGS_LOCATION', RUN_DIR), 'credentials'))
load_config(os.path.join(
    os.getenv('TESTSITE_SETTINGS_LOCATION', RUN_DIR), 'site.conf'))

if not hasattr(sys.modules[__name__], "SECRET_KEY"):
    from random import choice
    SECRET_KEY = "".join([choice(
        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)])

JWT_SECRET_KEY = SECRET_KEY
JWT_ALGORITHM = 'HS256'

# SECURITY WARNING: don't run with debug turned on in production!
if os.getenv('DEBUG'):
    # Enable override on command line.
    DEBUG = bool(int(os.getenv('DEBUG')) > 0)

# Applications
# ------------
INSTALLED_APPS = (
    'django_extensions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'pages',
    'testsite',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'logfile':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'pages': {
            'handlers': ['logfile'],
            'level': 'INFO',
            'propagate': False,
        },
#        'django.db.backends': {
#             'handlers': ['logfile'],
#             'level': 'DEBUG',
#             'propagate': True,
#        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # If we don't disable 'django' handlers here, we will get an extra
        # copy on stderr.
        'django': {
            'handlers': [],
        },
        # This is the root logger.
        # The level will only be taken into account if the record is not
        # propagated from a child logger.
        #https://docs.python.org/2/library/logging.html#logging.Logger.propagate
        '': {
            'handlers': ['logfile', 'mail_admins'],
            'level': 'INFO'
        },
        'fontTools.subset': {
            'handlers': ['console'],
            'level': 'WARNING',
        }
    }
}
if logging.getLogger('gunicorn.error').handlers:
    LOGGING['handlers']['logfile'].update({
        'class':'logging.handlers.WatchedFileHandler',
        'filename': LOG_FILE
    })


MIDDLEWARE = (
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
)

MIDDLEWARE_CLASSES = MIDDLEWARE

ROOT_URLCONF = 'testsite.urls'
WSGI_APPLICATION = 'testsite.wsgi.application'


REST_FRAMEWORK = {
    'PAGE_SIZE': 25,
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'ORDERING_PARAM': 'o',
    'SEARCH_PARAM': 'q'
}

# Static assets (CSS, JavaScript, Images)
# --------------------------------------
HTDOCS = os.path.join(BASE_DIR, 'htdocs')

STATIC_URL = '/static/'
APP_STATIC_ROOT = HTDOCS + '/static'
if DEBUG:
    STATIC_ROOT = ''
    # Additional locations of static files
    STATICFILES_DIRS = (APP_STATIC_ROOT, HTDOCS,)
else:
    STATIC_ROOT = APP_STATIC_ROOT

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = HTDOCS + '/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

#
# Templates
# ---------
TEMPLATE_DEBUG = True

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request'
)

TEMPLATE_DIRS = (
    BASE_DIR + '/testsite/templates',
)

# Django 1.8+
TEMPLATES = [
    {
        'NAME': 'html',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': TEMPLATE_DEBUG,
            'context_processors': [proc.replace(
                'django.core.context_processors',
                'django.template.context_processors')
                for proc in TEMPLATE_CONTEXT_PROCESSORS]},
    },
]


# Database
# --------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_NAME,
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Internationalization
# --------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# debug panel
# -----------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '/static/vendor/jquery.js',
    'SHOW_COLLAPSED': True,
    'SHOW_TEMPLATE_CONTEXT': True,
}

INTERNAL_IPS = ('127.0.0.1', '::1')

# Authentication
# --------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/app/energy-utility/'
