from __future__ import absolute_import, unicode_literals

SOUTH_ERROR_MESSAGE = """
For South support, customize the SOUTH_MIGRATION_MODULES setting
to point to the correct migrations module:

    SOUTH_MIGRATION_MODULES = {
        'karellen_kombu_transport_django': 'karellen.kombu.transport.django.south_migrations',
    }
"""

try:
    from django.db import migrations  # noqa
except ImportError:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(SOUTH_ERROR_MESSAGE)
