#!/usr/bin/env python3
import os,sys,re,importlib
# Ensure project root is on sys.path so Django settings package is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','plateforme.settings')
import django
django.setup()

p = 'core/urls.py'
s = open(p, encoding='utf-8').read()
imports = []
imports += re.findall(r"from\s+\.views\s+import\s+([^\n]+)", s)
imports += re.findall(r"from\s+core\.views\s+import\s+([^\n]+)", s)
names = set()
for imp in imports:
    imp = imp.strip().strip('() ')
    parts = [p.strip() for p in imp.split(',') if p.strip()]
    for part in parts:
        part = part.split(' as ')[0].strip()
        names.add(part)

print('REQUIRED_NAMES')
for n in sorted(names):
    print(n)

v = importlib.import_module('core.views')
avail = set(dir(v))
print('AVAILABLE_NAMES')
for n in sorted(avail):
    print(n)

missing = [n for n in sorted(names) if n not in avail]
print('MISSING_NAMES')
for n in missing:
    print(n)

if missing:
    sys.exit(2)
sys.exit(0)
