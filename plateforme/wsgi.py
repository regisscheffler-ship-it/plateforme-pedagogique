"""
WSGI config for plateforme project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys
import traceback

from django.core.wsgi import get_wsgi_application
import django
from django.core.management import call_command
import socket
from urllib.parse import urlparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')


def _run_startup_maintenance():
	"""Optional: run migrations at startup when enabled.

	Activate by setting the environment variable `RUN_MIGRATIONS_ON_STARTUP=1`.
	This is guarded and will only run when explicitly enabled.
	NOTE: collectstatic is intentionally NOT run here — it is handled by build.sh
	during the build phase. Running it at startup would process hundreds of files
	and cause gunicorn worker boot timeout (>30s), leading to an infinite restart loop.
	"""
	if os.environ.get('RUN_MIGRATIONS_ON_STARTUP') != '1':
		return
	try:
		# Quick connectivity check to the database host: avoid long blocking
		db_url = os.environ.get('DATABASE_URL')
		if db_url:
			try:
				parsed = urlparse(db_url)
				host = parsed.hostname
				port = parsed.port or 5432
				# try a short TCP connect
				socket.create_connection((host, port), timeout=5)
			except Exception as e:
				print(f"Database not reachable ({e}), skipping startup migrations.")
				return
		django.setup()
		call_command('migrate', '--noinput')
	except Exception:
		print('Error running startup maintenance (migrate):', file=sys.stderr)
		traceback.print_exc()


# Run optional startup tasks before creating the WSGI application
try:
    _run_startup_maintenance()
except Exception:
    print('wsgi startup maintenance failed (non-fatal):', file=sys.stderr)
    traceback.print_exc()

try:
    application = get_wsgi_application()
except Exception:
    print('FATAL: get_wsgi_application() failed:', file=sys.stderr)
    traceback.print_exc()
    raise
