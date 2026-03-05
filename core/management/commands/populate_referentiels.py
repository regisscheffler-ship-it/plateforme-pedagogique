from django.core.management.base import BaseCommand
from django.db import transaction
# On importe les modèles de base
from core.models import (
    Referentiel, BlocCompetence, Competence, 
    CompetenceProfessionnelle, SousCompetence, 
    CritereEvaluation
)

# On essaie d'importer Connaissance (si tu l'as créé)
try:
    from core.models import Connaissance
    HAS_CONNAISSANCE = True
except ImportError:
    HAS_CONNAISSANCE = False

class Command(BaseCommand):
    help = "Remplit la base de données (Arrêt aux Critères + Connaissances)"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Début de l'insertion des données...")

        with transaction.atomic():
            
            # 1. CRÉATION DU RÉFÉRENTIEL
            ref, _ = Referentiel.objects.get_or_create(
                nom="CAP Maçon TEST (Nouveau)",
                defaults={'description': "Référentiel testé sans indicateurs"}
            )
            self.stdout.write(f"✅ Référentiel : {ref.nom}")

            # 2. CRÉATION DU BLOC
            bloc, _ = BlocCompetence.objects.get_or_create(
                referentiel=ref,
                code="UP2",
                defaults={'nom': "Réalisation d'ouvrages", 'ordre': 1}
            )

            # 3. CRÉATION DE LA COMPÉTENCE
            comp, _ = Competence.objects.get_or_create(
                bloc=bloc,
                code="C3",
                defaults={'nom': "Réaliser des ouvrages", 'ordre': 1}
            )

            # 4. CRÉATION DE LA COMPÉTENCE PRO (CP)
            cp, _ = CompetenceProfessionnelle.objects.get_or_create(
                competence=comp,
                code="C3.2",
                defaults={'nom': "Maçonner des éléments", 'ordre': 1}
            )

            # --- GESTION DES CONNAISSANCES (REMPLACE SAVOIRS) ---
            if HAS_CONNAISSANCE:
                connaissances_data = [
                    "S1.2 - Les briques",
                    "S2.1 - Les mortiers",
                    "S3.4 - L'outillage du maçon"
                ]
                for nom_conn in connaissances_data:
                    # J'assume que Connaissance est lié à CompetenceProfessionnelle
                    # Si c'est lié ailleurs, adapte le paramètre 'competence_pro=cp'
                    try:
                        c, created = Connaissance.objects.get_or_create(
                            competence_pro=cp, 
                            nom=nom_conn
                        )
                        if created:
                            self.stdout.write(f"   📘 Connaissance ajoutée : {c.nom}")
                    except Exception as e:
                        self.stdout.write(f"   ⚠️ Erreur ajout connaissance : {e}")
            else:
                self.stdout.write("   ℹ️ Modèle 'Connaissance' non trouvé (étape ignorée)")

            # 5. CRÉATION DE LA SOUS-COMPÉTENCE
            sc, _ = SousCompetence.objects.get_or_create(
                competence_pro=cp,
                nom="Monter un mur de briques",
                defaults={'ordre': 1}
            )

            # 6. CRÉATION DES CRITÈRES (Niveau final de l'évaluation)
            criteres_data = [
                "Respect de l'aplomb",
                "Respect de l'alignement",
                "Propreté du parement",
                "Respect des dimensions"
            ]

            for i, nom_crit in enumerate(criteres_data, 1):
                crit, created = CritereEvaluation.objects.get_or_create(
                    sous_competence=sc,
                    nom=nom_crit,
                    defaults={'ordre': i}
                )
                if created:
                    self.stdout.write(f"   - Critère ajouté : {crit.nom}")

        self.stdout.write(self.style.SUCCESS("🎉 Base de données peuplée avec succès !"))