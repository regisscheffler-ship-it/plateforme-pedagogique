"""
Script de nettoyage des doublons de CompetenceProfessionnelle avant réimport.
Lancer : python nettoyer_doublons.py
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from django.db.models import Count
from core.models import (
    CompetenceProfessionnelle, SousCompetence,
    CritereEvaluation, IndicateurPerformance,
    Connaissance, LigneContrat
)

print("🔍 Recherche des doublons CompetenceProfessionnelle...")

doublons = (
    CompetenceProfessionnelle.objects
    .values('code', 'competence_id')
    .annotate(nb=Count('id'))
    .filter(nb__gt=1)
)

print(f"  {doublons.count()} groupe(s) de doublons trouvés")

total_supprimes = 0

for doublon in doublons:
    code          = doublon['code']
    competence_id = doublon['competence_id']

    cps = list(
        CompetenceProfessionnelle.objects
        .filter(code=code, competence_id=competence_id)
        .order_by('id')
    )

    cp_gardee      = cps[0]
    cps_a_supprimer = cps[1:]

    print(f"\n  CP '{code}' (competence_id={competence_id}) : {len(cps)} entrées")
    print(f"    → Garde    : ID={cp_gardee.id} | {cp_gardee.nom[:50]}")

    for cp_doublon in cps_a_supprimer:
        print(f"    → Supprime : ID={cp_doublon.id} | {cp_doublon.nom[:50]}")

        nb_sc = SousCompetence.objects.filter(competence_pro=cp_doublon).count()
        if nb_sc > 0:
            print(f"      ↳ Rattache {nb_sc} SC vers ID={cp_gardee.id}")
            SousCompetence.objects.filter(competence_pro=cp_doublon).update(competence_pro=cp_gardee)

        nb_conn = Connaissance.objects.filter(competence_pro=cp_doublon).count()
        if nb_conn > 0:
            print(f"      ↳ Rattache {nb_conn} connaissances vers ID={cp_gardee.id}")
            Connaissance.objects.filter(competence_pro=cp_doublon).update(competence_pro=cp_gardee)

        nb_lc = LigneContrat.objects.filter(competence_pro=cp_doublon).count()
        if nb_lc > 0:
            print(f"      ↳ Rattache {nb_lc} LigneContrat vers ID={cp_gardee.id}")
            LigneContrat.objects.filter(competence_pro=cp_doublon).update(competence_pro=cp_gardee)

        cp_doublon.delete()
        total_supprimes += 1

print(f"\n✅ {total_supprimes} doublon(s) supprimé(s)")

print("\n🔍 Vérification après nettoyage...")
reste = (
    CompetenceProfessionnelle.objects
    .values('code', 'competence_id')
    .annotate(nb=Count('id'))
    .filter(nb__gt=1)
)
if reste.count() == 0:
    print("  ✅ Aucun doublon restant — relancez import_referentiels.py")
else:
    print(f"  ⚠️  {reste.count()} doublon(s) restant(s) !")
    for r in reste:
        print(f"    code={r['code']} competence_id={r['competence_id']} nb={r['nb']}")