# ================================================================
# SCRIPT DE VÉRIFICATION DES DONNÉES IMPORTÉES
# ================================================================

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from core.models import (
    Referentiel, BlocCompetence, Competence, CompetenceProfessionnelle,
    SousCompetence, CritereEvaluation, IndicateurPerformance, Connaissance
)

def verifier_import():
    print("🔍 VÉRIFICATION DES DONNÉES PAR RÉFÉRENTIEL")
    print("=" * 70)
    
    referentiels = Referentiel.objects.all()
    
    for ref in referentiels:
        print(f"\n📚 {ref.nom}:")
        print("-" * 70)
        
        # Blocs
        blocs_count = BlocCompetence.objects.filter(referentiel=ref).count()
        print(f"   📦 Blocs: {blocs_count}")
        
        # Compétences
        comp_count = Competence.objects.filter(bloc__referentiel=ref).count()
        print(f"   🎯 Compétences: {comp_count}")
        
        # Compétences Pro
        cp_count = CompetenceProfessionnelle.objects.filter(
            competence__bloc__referentiel=ref
        ).count()
        print(f"   🔧 Compétences Pro: {cp_count}")
        
        # Sous-compétences
        sc_count = SousCompetence.objects.filter(
            competence_pro__competence__bloc__referentiel=ref
        ).count()
        print(f"   📋 Sous-compétences: {sc_count}")
        
        # Critères
        crit_count = CritereEvaluation.objects.filter(
            sous_competence__competence_pro__competence__bloc__referentiel=ref
        ).count()
        print(f"   ✅ Critères: {crit_count}")
        
        # Indicateurs
        ind_count = IndicateurPerformance.objects.filter(
            critere__sous_competence__competence_pro__competence__bloc__referentiel=ref
        ).count()
        print(f"   📊 Indicateurs: {ind_count}")
        
        # Connaissances
        conn_count = Connaissance.objects.filter(
            competence_pro__competence__bloc__referentiel=ref
        ).count()
        print(f"   📚 Connaissances: {conn_count}")
    
    print("\n" + "=" * 70)
    print("📊 TOTAUX GÉNÉRAUX:")
    print(f"   Indicateurs: {IndicateurPerformance.objects.count()}")
    print(f"   Connaissances: {Connaissance.objects.count()}")
    print("=" * 70)

if __name__ == '__main__':
    verifier_import()