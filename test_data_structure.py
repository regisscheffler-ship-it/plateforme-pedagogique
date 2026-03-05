#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from core.models import Referentiel, BlocCompetence, Competence, CompetenceProfessionnelle, SousCompetence, CritereEvaluation

print("\n" + "=" * 80)
print("TEST 1: STRUCTURE DES DONNÉES")
print("=" * 80)

# Test pour chaque référentiel
for ref in Referentiel.objects.all():
    print(f"\n📚 {ref.nom}:")
    blocs = ref.blocs.all()
    print(f"   📦 Blocs: {blocs.count()}")
    
    for bloc in blocs:
        comps = bloc.competences.all()
        print(f"      └─ {bloc.code}: {comps.count()} compétences")
        
        # Vérifier structure complete
        if comps.count() > 0:
            comp = comps.first()
            cps = comp.competences_pro.all()
            print(f"         └─ {comp.code}: {cps.count()} CP")
            
            if cps.count() > 0:
                cp = cps.first()
                scs = cp.sous_competences.all()
                print(f"            └─ {cp.code}: {scs.count()} SC")
                
                if scs.count() > 0:
                    sc = scs.first()
                    crits = sc.criteres.all()
                    print(f"               └─ {sc.nom[:40]}...: {crits.count()} critères")

print("\n" + "=" * 80)
print("TEST 2: VÉRIFICATION DES DOUBLONS")
print("=" * 80)

# Chercher les compétences qui existent dans plusieurs blocs
for ref in Referentiel.objects.all():
    print(f"\n📚 {ref.nom}:")
    comps = Competence.objects.filter(bloc__referentiel=ref)
    
    comp_codes = {}
    for comp in comps:
        code = comp.code
        if code not in comp_codes:
            comp_codes[code] = []
        comp_codes[code].append(comp.bloc.code)
    
    doublons = {k: v for k, v in comp_codes.items() if len(v) > 1}
    if doublons:
        print(f"   ⚠️  Compétences en plusieurs blocs:")
        for code, blocs in doublons.items():
            print(f"      • {code}: {blocs}")
    else:
        print(f"   ✓ Pas de doublons")

print("\n" + "=" * 80)
print("TEST 3: VÉRIFICATION DES LIENS")
print("=" * 80)

# Vérifier que toutes les CP ont une Compétence
cps_sans_comp = CompetenceProfessionnelle.objects.filter(competence__isnull=True).count()
print(f"CP sans compétence: {cps_sans_comp}")

# Vérifier que toutes les SC ont une CP
scs_sans_cp = SousCompetence.objects.filter(competence_pro__isnull=True).count()
print(f"SC sans CP: {scs_sans_cp}")

# Vérifier que tous les Critères ont une SC
crits_sans_sc = CritereEvaluation.objects.filter(sous_competence__isnull=True).count()
print(f"Critères sans SC: {crits_sans_sc}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80 + "\n")
