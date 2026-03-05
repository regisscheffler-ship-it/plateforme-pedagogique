#!/usr/bin/env python
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/api/competences/?referentiel_id=1')

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'unknown')}")

try:
    data = json.loads(response.content)
    
    if isinstance(data, list) and data:
        print(f"\n✅ JSON est une liste avec {len(data)} blocs")
        
        bloc = data[0]
        print(f"\nBloc[0] keys: {list(bloc.keys())}")
        print(f"Bloc: {bloc.get('code')} - {bloc.get('nom')}")
        
        if bloc.get('competences'):
            comp = bloc['competences'][0]
            print(f"\nCompetence[0] keys: {list(comp.keys())}")
            print(f"Competence: {comp.get('code')}")
            print(f"Competences Pro count: {len(comp.get('competences_pro', []))}")
            
            if comp.get('competences_pro'):
                cp = comp['competences_pro'][0]
                print(f"\nCP[0] keys: {list(cp.keys())}")
                print(f"CP: {cp.get('code')}")
                print(f"Has 'sous_competences': {'sous_competences' in cp}")
                print(f"Has 'connaissances': {'connaissances' in cp}")
                
                if cp.get('sous_competences'):
                    print(f"Sous-compétences count: {len(cp['sous_competences'])}")
    else:
        print(f"❌ Data is not a list or empty: {type(data)}")
        print(f"Data: {str(data)[:200]}")
        
except Exception as e:
    print(f"❌ Error parsing JSON: {e}")
    print(f"Content: {response.content[:500]}")
