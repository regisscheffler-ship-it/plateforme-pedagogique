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
	"""Optional: run migrations and collectstatic at startup when enabled.

	Activate by setting the environment variable `RUN_MIGRATIONS_ON_STARTUP=1`.
	This is guarded and will only run when explicitly enabled (useful when
	you cannot run shell commands on the host). Failures are caught so the
	process still starts and logs the traceback to stderr.
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
		call_command('collectstatic', '--noinput')
	except Exception:
		print('Error running startup maintenance (migrate/collectstatic):', file=sys.stderr)
		traceback.print_exc()


# Run optional startup tasks before creating the WSGI application
_run_startup_maintenance()

application = get_wsgi_application()
