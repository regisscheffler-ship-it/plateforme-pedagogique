"""Test upload script for Render deployment.

Usage (set env vars and run):
  - DEPLOY_URL: https://your-app.onrender.com (no trailing slash)
  - ADMIN_USER, ADMIN_PASS: admin credentials
  - FILE_PATH: path to local PDF to upload

This script logs into Django admin, opens the add form for `FichierAtelier`, and posts
the file as a new object. It prints the response status and the created object's admin URL.
"""

import os
import re
import sys
import requests

DEPLOY_URL = os.environ.get('DEPLOY_URL')
ADMIN_USER = os.environ.get('ADMIN_USER')
ADMIN_PASS = os.environ.get('ADMIN_PASS')
FILE_PATH = os.environ.get('FILE_PATH')

if not (DEPLOY_URL and ADMIN_USER and ADMIN_PASS and FILE_PATH):
    print('Missing one of DEPLOY_URL, ADMIN_USER, ADMIN_PASS, FILE_PATH')
    sys.exit(2)

session = requests.Session()

# Step 1: GET login page to fetch csrf
login_url = DEPLOY_URL.rstrip('/') + '/admin/login/'
resp = session.get(login_url, timeout=30)
if resp.status_code != 200:
    print('Cannot reach login page', resp.status_code)
    sys.exit(3)
m = re.search(r"name=['\"]csrfmiddlewaretoken['\"] value=['\"]([^\"]+)['\"]", resp.text)
csrf = m.group(1) if m else None

login_data = {
    'username': ADMIN_USER,
    'password': ADMIN_PASS,
}
headers = {'Referer': login_url}
if csrf:
    login_data['csrfmiddlewaretoken'] = csrf

resp = session.post(login_url, data=login_data, headers=headers, timeout=30)
if resp.status_code not in (200, 302):
    print('Login failed', resp.status_code)
    sys.exit(4)

# Step 2: open add form
add_url = DEPLOY_URL.rstrip('/') + '/admin/core/fichieratelier/add/'
resp = session.get(add_url, timeout=30)
if resp.status_code != 200:
    print('Cannot open add form', resp.status_code)
    sys.exit(5)
m = re.search(r"name=['\"]csrfmiddlewaretoken['\"] value=['\"]([^\"]+)['\"]", resp.text)
csrf = m.group(1) if m else None

files = {'fichier': open(FILE_PATH, 'rb')}
data = {
    'nom': os.path.basename(FILE_PATH),
    'type_contenu': 'fichier',
    'ordre': '0',
    'visible_eleves': 'on',
    '_save': 'Enregistrer',
}
if csrf:
    data['csrfmiddlewaretoken'] = csrf

headers = {'Referer': add_url}
resp = session.post(add_url, data=data, files=files, headers=headers, timeout=60)

print('POST status:', resp.status_code)
if resp.status_code in (200, 302):
    # try to find change list or success message
    m = re.search(r'href="([^"]+/admin/core/fichieratelier/[0-9]+/change/)"', resp.text)
    if m:
        print('Created object admin URL:', DEPLOY_URL.rstrip('/') + m.group(1))
    else:
        print('Upload done; check admin interface for the new file.')
else:
    print('Upload may have failed; response length:', len(resp.text))
