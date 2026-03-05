#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from django.test import Client
import json

client = Client()

print("\n" + "=" * 80)
print("TEST D'API DIRECTE")
print("=" * 80)

# Test avec chaque ID disponible
ref_ids = [40, 41, 42]

for ref_id in ref_ids:
    print(f"\n🔍 Test API avec referentiel_id={ref_id}")
    url = f'/api/competences/?referentiel_id={ref_id}'
    response = client.get(url)
    
    print(f"   Status: {response.status_code}")
    print(f"   URL: {url}")
    
    try:
        data = json.loads(response.content)
        if 'error' in data:
            print(f"   ❌ Erreur: {data['error']}")
            if 'available' in data:
                print(f"   ℹ️  Disponibles: {data['available']}")
        else:
            blocs_count = len(data) if isinstance(data, list) else 0
            print(f"   ✅ OK! {blocs_count} blocs reçus")
            if blocs_count > 0 and isinstance(data, list):
                print(f"      Premier bloc: {data[0].get('code', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Erreur parsing: {e}")
        print(f"   Contenu: {response.content[:100]}")

print("\n" + "=" * 80)
